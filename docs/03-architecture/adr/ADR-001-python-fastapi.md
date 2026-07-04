# ADR-001: Python + FastAPI for the scoring service

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: A. Abdulwasiu

## Context
The service must serve ML model inferences over HTTP with low latency, be quick to build solo, and use technology credible in the Finnish fintech job market. The ML ecosystem (scikit-learn, pandas) is Python-native; a JVM service (common at Nordea/OP for core systems) would force a model-serving boundary across languages.

## Decision
Python 3.12 with FastAPI for the API layer; the scoring core is a framework-free Python package.

## Consequences
+ One language across data science and service code; fastest iteration for one person
+ FastAPI gives Pydantic validation, OpenAPI docs, async support for free — recruiter-recognisable
+ Type hints + mypy recover some of the safety a JVM would give
− Lower raw throughput than JVM/Go — acceptable: NFR is 50 tx/s, FastAPI handles thousands
− GIL constrains CPU-bound concurrency — mitigated by worker processes if needed

## Alternatives considered
- **Kotlin/Spring Boot** (very Nordea-realistic): stronger enterprise signal, but doubles the learning surface and splits the ML/service stack. Rejected for scope.
- **Flask**: no built-in validation/docs. Rejected.
- **Go**: great latency, immature ML story. Rejected.
