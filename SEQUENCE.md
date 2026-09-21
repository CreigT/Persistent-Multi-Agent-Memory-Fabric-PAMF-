# Locked sequence — autonomous company exists after step 5

Doctrine: motion by default. Review only on over-cap and irreversible.

## Control plane
Identity · Event bus · PAMF · Governance/approval · Warden admit/review/kill · Observability

## Money loop
Research → list → price → ads → order → collect → fulfill/refund → bookkeep → tax reserve
One SKU or one janitorial contract. One channel. One rail.

## Hard gates
Legal, irreversible, or over $ cap → review. Everything else moves.

## Memory
Done when agents cite `memory_id` on decisions. Specs are not done.

## Proof
Idempotent writes. Forget certificates. Replay Tuesday from the event log.

---

1. PAMF in-memory → Postgres (SQL is truth)  ← this commit
2. Identity Management Agent (zero-trust tokens)
3. Event Trigger Agent (the bus)
4. Governance approval policy + Warden wired to PAMF freeze
5. One live money loop

After 5 the company exists. Later agents raise profit. They do not define existence.
