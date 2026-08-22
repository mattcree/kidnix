# ADR-0002: Agent roles — Fable 5 thinks, Opus 5 implements

- Status: accepted
- Date: 2026-08-22

## Context

The project is developed largely by AI agents under human direction. The
human asked that Claude Fable 5 act as the orchestrating "thinker" and that
Claude Opus 5 workers do implementation.

## Decision

- **Thinker (Fable 5, the main session):** research synthesis, product
  priorities, plans, ADRs, specs, reviewing implementer output, committing,
  conversation with the human.
- **Implementers / researchers (Opus 5 subagents, `model: "opus"`):** code,
  build system, tests, CI, research documents. They do not commit or push;
  they report back with what is verified green and what is not.
- Ownership boundaries are written in `AGENTS.md` §2 and §4 so parallel
  workers don't collide (thinker owns `docs/{research,plan,adr}`, `README.md`,
  `AGENTS.md`; implementers own code paths they are assigned).

## Consequences

- Parallelism: many Opus workers can run at once on disjoint paths.
- Every change passes through one reviewer (the thinker) before commit, which
  keeps the history coherent.
- If the human changes the model assignment, update `AGENTS.md` §2 and this ADR.
