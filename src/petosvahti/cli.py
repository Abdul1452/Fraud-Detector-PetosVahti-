"""`petosvahti` command line: train, serve, demo, produce."""

import argparse
import contextlib
import logging
import threading
import time
import webbrowser
from dataclasses import replace
from pathlib import Path

from petosvahti.config import Settings


def _train(args: argparse.Namespace) -> int:
    from petosvahti.training import QUICK_CONFIG, TrainConfig, train
    from petosvahti.training.report import render
    from petosvahti.training.train import file_sha256

    cfg = QUICK_CONFIG if args.quick else TrainConfig()
    if args.customers:
        cfg = replace(cfg, n_customers=args.customers)
    if args.seed is not None:
        cfg = replace(cfg, seed=args.seed)
    print(f"Training on {cfg.n_customers:,} simulated customers, seed {cfg.seed} ...")
    started = time.perf_counter()
    result = train(cfg)
    result.model.save(args.model)
    sha = file_sha256(args.model)
    h, lat = result.evaluation["headline"], result.evaluation["latency_ms"]
    print(
        f"\nModel {result.model.version} saved to {args.model} (sha256 {sha}) "
        f"in {time.perf_counter() - started:.0f} s\n"
        f"  PR-AUC            {h['pr_auc']:.3f}\n"
        f"  fraud flagged     {100 * h['recall_flagged']:.1f} % "
        f"(precision {100 * h['precision_flagged']:.1f} %)\n"
        f"  fraud blocked     {100 * h['recall_blocked']:.1f} % "
        f"(precision {100 * h['precision_blocked']:.1f} %)\n"
        f"  latency p99       {lat['p99']:.2f} ms"
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render(result, args.model.as_posix(), sha), encoding="utf-8")
        print(f"  report            {args.report}")
    return 0


def _ensure_model(settings: Settings, quick: bool) -> None:
    if settings.model_path.exists():
        return
    print(f"No model at {settings.model_path} yet: training one first (one-off).")
    _train(
        argparse.Namespace(
            quick=quick, customers=None, seed=None, model=settings.model_path, report=None
        )
    )


def _serve(settings: Settings, host: str, port: int, open_browser: bool = False) -> int:
    import uvicorn

    from petosvahti.api import create_app

    url = f"http://{'localhost' if host in ('0.0.0.0', '127.0.0.1') else host}:{port}/"
    if open_browser:
        threading.Timer(2.0, webbrowser.open, args=(url,)).start()
    print(f"Petosvahti dashboard: {url}   API docs: {url}docs")
    uvicorn.run(create_app(settings), host=host, port=port, log_level="info")
    return 0


def _produce(args: argparse.Namespace) -> int:
    from petosvahti.streaming.kafka import run_producer

    overrides: dict[str, object] = {}
    if args.bootstrap:
        overrides["kafka_bootstrap"] = args.bootstrap
    if args.customers:
        overrides["sim_customers"] = args.customers
    settings = Settings(**overrides)  # type: ignore[arg-type]
    with contextlib.suppress(KeyboardInterrupt):
        run_producer(settings, history_days=args.history_days, rate=args.rate)
    return 0


def main(argv: list[str] | None = None) -> int:
    defaults = Settings()
    parser = argparse.ArgumentParser(
        prog="petosvahti", description="Real-time fraud detection for Finnish payments."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("train", help="simulate data, train + evaluate the model")
    t.add_argument("--quick", action="store_true", help="small run (~15 s) for CI / smoke tests")
    t.add_argument("--customers", type=int, help="override population size")
    t.add_argument("--seed", type=int, help="override RNG seed")
    t.add_argument("--model", type=Path, default=defaults.model_path, help="artifact path")
    t.add_argument("--report", type=Path, help="write the markdown evaluation report here")

    s = sub.add_parser("serve", help="run the scoring API + dashboard")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--source", choices=["simulator", "kafka", "none"], help="transaction source")

    d = sub.add_parser("demo", help="train if needed, then serve with the live simulator")
    d.add_argument("--host", default="127.0.0.1")
    d.add_argument("--port", type=int, default=8000)
    d.add_argument("--quick", action="store_true", help="train the quick model if none exists")
    d.add_argument("--no-browser", action="store_true")

    p = sub.add_parser("produce", help="stream synthetic transactions into Kafka")
    p.add_argument(
        "--bootstrap", help=f"Kafka bootstrap servers (default {defaults.kafka_bootstrap})"
    )
    p.add_argument("--rate", type=float, default=defaults.sim_rate, help="live tx per second")
    p.add_argument("--history-days", type=int, default=defaults.sim_history_days)
    p.add_argument("--customers", type=int)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if args.command == "train":
        return _train(args)
    if args.command == "serve":
        settings = Settings(source=args.source) if args.source else defaults
        return _serve(settings, args.host, args.port)
    if args.command == "demo":
        settings = Settings(source="simulator")
        _ensure_model(settings, args.quick)
        return _serve(settings, args.host, args.port, open_browser=not args.no_browser)
    return _produce(args)


if __name__ == "__main__":
    raise SystemExit(main())
