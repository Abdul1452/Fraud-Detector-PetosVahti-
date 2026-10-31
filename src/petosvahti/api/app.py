"""FastAPI service: scoring endpoint, health, Prometheus metrics and live dashboard.

A thin adapter: all decisions are made by `petosvahti.scoring.Scorer`; this
module only translates HTTP to and from it.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from petosvahti import __version__
from petosvahti.api.feed import Feed, FeedEvent
from petosvahti.api.sources import KafkaSource, SimulatorSource, StreamSource
from petosvahti.config import Settings
from petosvahti.domain import HELSINKI, HOME_COUNTRY, Channel, FraudPattern, Transaction
from petosvahti.scoring.features import FEATURE_NAMES
from petosvahti.scoring.model import FraudModel
from petosvahti.scoring.policy import APPROVE_BELOW, BLOCK_ABOVE
from petosvahti.scoring.reasons import REASON_RULES
from petosvahti.scoring.scorer import Scorer, ScoreResult

log = logging.getLogger("petosvahti")

STATIC_DIR = Path(__file__).parent / "static"


class ScoreRequest(BaseModel):
    """A transaction to score. `transaction_id` and `timestamp` are filled in if omitted."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str | None = Field(default=None, min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64, examples=["C00042"])
    timestamp: AwareDatetime | None = None
    amount_eur: float = Field(gt=0, le=1_000_000, examples=[4800.0])
    channel: Channel = Field(examples=[Channel.SIIRTO])
    payee_id: str = Field(min_length=1, max_length=64, examples=["FI4979900000012345"])
    payee_name: str = Field(min_length=1, max_length=120, examples=["Matti Virtanen"])
    country: str = Field(default=HOME_COUNTRY, pattern=r"^[A-Z]{2}$")
    device_id: str = Field(min_length=1, max_length=64, examples=["dev-0123456789"])


class InjectRequest(BaseModel):
    pattern: FraudPattern
    customer_id: str | None = None


class ControlRequest(BaseModel):
    paused: bool | None = None
    rate: float | None = Field(default=None, gt=0, le=200)


@dataclass
class AppContext:
    settings: Settings
    model: FraudModel
    scorer: Scorer
    feed: Feed
    source: StreamSource | None


def load_or_train(settings: Settings) -> FraudModel:
    if settings.model_path.exists():
        return FraudModel.load(settings.model_path)
    if not settings.auto_train:
        raise FileNotFoundError(f"No model at {settings.model_path}. Run `petosvahti train` first.")
    from petosvahti.training import QUICK_CONFIG, train

    log.warning(
        "No model at %s: training the quick demo model now (~15 s). "
        "Run `petosvahti train` for the full model.",
        settings.model_path,
    )
    model = train(QUICK_CONFIG, log=log.info).model
    model.save(settings.model_path)
    return model


def get_ctx(request: Request) -> AppContext:
    ctx: AppContext = request.app.state.ctx
    return ctx


Ctx = Annotated[AppContext, Depends(get_ctx)]


def _make_source(settings: Settings, scorer: Scorer, feed: Feed) -> StreamSource | None:
    if settings.source == "simulator":
        return SimulatorSource(scorer, feed, settings)
    if settings.source == "kafka":
        return KafkaSource(scorer, feed, settings)
    return None


def create_app(settings: Settings | None = None, model: FraudModel | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        loaded = model if model is not None else await run_in_threadpool(load_or_train, settings)
        loaded.risk_one(tuple(0.0 for _ in FEATURE_NAMES))  # warm numpy paths before traffic
        scorer = Scorer(loaded)
        feed = Feed()
        source = _make_source(settings, scorer, feed)
        app.state.ctx = AppContext(settings, loaded, scorer, feed, source)
        log.info("serving model %s, source=%s", loaded.version, settings.source)
        if source:
            source.start()
        try:
            yield
        finally:
            if source:
                source.stop()

    app = FastAPI(
        title="Petosvahti",
        version=__version__,
        summary="Real-time transaction fraud scoring for the Finnish payments market",
        lifespan=lifespan,
    )

    def simulator(ctx: AppContext) -> SimulatorSource:
        if not isinstance(ctx.source, SimulatorSource):
            raise HTTPException(409, "Only available when PETOSVAHTI_SOURCE=simulator")
        return ctx.source

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health", tags=["ops"])
    def health(ctx: Ctx) -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "model_version": ctx.model.version,
            "source": ctx.source.status() if ctx.source else {"kind": "none"},
        }

    @app.post("/score", response_model=ScoreResult, tags=["scoring"])
    def score(req: ScoreRequest, ctx: Ctx) -> ScoreResult:
        """Score one transaction: risk 0-100, decision, and reason codes."""
        clock: datetime = ctx.source.clock() if ctx.source else datetime.now(HELSINKI)
        fields = req.model_dump(exclude={"transaction_id", "timestamp"})
        if req.transaction_id:
            fields["transaction_id"] = req.transaction_id
        tx = Transaction(timestamp=req.timestamp or clock, **fields)
        result = ctx.scorer.score(tx)
        ctx.feed.add(tx, result, "api", None)
        return result

    @app.get("/metrics", response_class=PlainTextResponse, tags=["ops"])
    def metrics(ctx: Ctx) -> PlainTextResponse:
        return PlainTextResponse(
            ctx.feed.prometheus(ctx.model.version), media_type="text/plain; version=0.0.4"
        )

    @app.get("/api/model", tags=["dashboard"])
    def model_info(ctx: Ctx) -> dict[str, Any]:
        return {
            **ctx.model.describe(),
            "thresholds": {"review_from": APPROVE_BELOW, "block_above": BLOCK_ABOVE},
            "features": list(FEATURE_NAMES),
            "reason_codes": {r.code: r.description for r in REASON_RULES},
        }

    @app.get("/api/stats", tags=["dashboard"])
    def stats(ctx: Ctx) -> dict[str, Any]:
        return {
            **ctx.feed.stats(),
            "source": ctx.source.status() if ctx.source else {"kind": "none"},
            "model_version": ctx.model.version,
            "customers_profiled": len(ctx.scorer.store),
        }

    @app.get("/api/events", tags=["dashboard"])
    def events(
        ctx: Ctx,
        since: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[FeedEvent]:
        return ctx.feed.since(since, limit)

    @app.get("/api/scenarios", tags=["dashboard"])
    def scenarios(ctx: Ctx, customer_id: str | None = None) -> dict[str, Any]:
        return simulator(ctx).scenarios(customer_id)

    @app.post("/api/simulator/inject", tags=["dashboard"])
    def inject(req: InjectRequest, ctx: Ctx) -> dict[str, str]:
        sim = simulator(ctx)
        if not sim.ready:
            raise HTTPException(409, "Simulator is still warming up")
        try:
            victim = sim.inject(req.pattern, req.customer_id)
        except KeyError:
            raise HTTPException(404, f"Unknown customer {req.customer_id}") from None
        return {"pattern": req.pattern.value, "customer_id": victim}

    @app.post("/api/simulator/control", tags=["dashboard"])
    def control(req: ControlRequest, ctx: Ctx) -> dict[str, Any]:
        sim = simulator(ctx)
        if req.paused is not None:
            sim.set_paused(req.paused)
        if req.rate is not None:
            sim.rate = req.rate
        return sim.status()

    return app
