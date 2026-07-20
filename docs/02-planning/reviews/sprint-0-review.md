# Sprint 0 Review — Foundation

**Dates:** 4–18 Jul 2026 · **Goal:** Project starts like a real one: governance baselined, environment and CI working, dataset scripted.

## Outcome vs commitment

| Story | Pts | Status | Evidence |
|---|---|---|---|
| S1.1 Governance doc set | 3 | ✅ | 14 docs in docs/, + templates & references v1.1 |
| S1.2 Dev environment | 2 | ✅ | 10/10 tests passing locally |
| S1.3 CI on every push | 2 | ✅ | Green run on main (CI #1, 38 s) |
| S1.4 Scripted dataset download | 1 | ✅ | data/creditcard.csv present, git-ignored |

**Velocity:** committed 8 → delivered 8

## Demo
Public repo live with 27-issue backlog, green CI badge-worthy pipeline, and one-command test suite.

## Goal met?
Yes. Note: took ~2 weeks vs the planned 1 (tooling friction: gh install, venv duplication, Kaggle token) — normal for Sprint 0; velocity assumption for Sprint 1 unchanged.

## Changes to plan
None to scope. Environment risk noted: consolidate to a single venv before Sprint 1.
