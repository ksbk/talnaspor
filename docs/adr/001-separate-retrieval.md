# ADR-001: Separate Statistical Retrieval from Question Interpretation

Status: Accepted
Date: 2026-10-30

## Context

The organizer's Track 2 reference implementation combines question
classification, PX-Web queries, statistical calculations and answer
presentation in a single FastAPI application.

Reference:
hIngolfur/hagstofa-ai-track2-
Commit: 3076c360393b14976ed9b7dcc9c93ba2105c604f

## Decision

Talnaspor will separate:

1. Statistical table discovery.
2. Query planning and validation.
3. PX-Web data retrieval.
4. Statistical interpretation.
5. Answer presentation.

Official statistical observations must come from source data, not
language-model-generated numbers.

## Consequences

Benefits:
- Individual components can be tested.
- Query failures can be diagnosed.
- Statistical answers can be independently verified.

Costs:
- More interfaces and files.
- Additional integration testing.

## Runtime constraints

Competition runtime must use free and open software.
No hosted proprietary language-model calls at runtime.
