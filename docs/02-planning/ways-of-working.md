# Ways of Working — Petosvahti

The engineering handbook: how code and docs get made. Modeled on Finnish enterprise team conventions, adapted for a solo learner.

## Git workflow

- **Trunk-based with short-lived branches**: `main` is always green; work happens on `feat/S4.1-score-endpoint`, `fix/…`, `docs/…` branches named after backlog IDs.
- **Every change lands via Pull Request** — yes, solo. You write the PR description, review your own diff the next day (cold review catches real bugs), then merge. PRs link the Issue (`Closes #12`).
- Commits follow **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
- `main` is protected: CI must pass before merge.

## Definition of Ready (a story may enter a sprint when…)

1. Acceptance criteria written on the Issue
2. Estimated in points
3. Dependencies identified (e.g., S5.2 needs S5.1)
4. Fits in one sprint (else split)

## Definition of Done (a story is done when…)

1. Acceptance criteria demonstrably met (evidence in PR or review note)
2. Tests written and passing; coverage on touched code ≥ 80 %
3. Lint (ruff) and formatting clean; CI green
4. Documentation updated (README, architecture doc, or docstrings as appropriate)
5. No secrets, no data files, no notebooks with real output committed
6. Merged to `main`

## Code standards

- Python 3.12, `ruff` (lint + format), type hints on all public functions, `mypy` on `src/`
- Tests with `pytest`; API tests via `httpx` test client
- Config via environment variables / `pydantic-settings` — never hardcoded
- Structured JSON logging; every scored transaction gets a correlation ID (audit-trail thinking, per FIN-FSA expectations for traceability)

## Quality gates (CI)

`push / PR → ruff → mypy → pytest (+coverage) → docker build`

## Documentation rules

- Decisions with lasting consequences → ADR (`docs/03-architecture/adr/`), numbered, never edited after acceptance (superseded instead)
- Sprint evidence → `docs/02-planning/reviews/sprint-N.md`
- Doc changes ride the same PR as the code they describe

## Working agreement with yourself

- Calendar-block the ~10 h/week; protect at least one 3 h deep-work block
- End every session with a stand-up note (done / next / blockers) — future-you is a colleague
- When stuck > 45 min: write the problem down, timebox one more attempt, then simplify scope (that's an engineering decision, log it)
