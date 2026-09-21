# Daily Module — Day 1
## Memory Agent (Persistent Multi-Agent Memory Fabric)

This is the first production module in the autonomous AI commerce platform. Every later agent assumes this fabric already exists: they read and write memory through APIs and events rather than keeping private, ephemeral context.

## 1. Module Name
Memory Agent — Persistent Multi-Agent Memory Fabric (PAMF)

## 2. Purpose
Provide a shared, typed, versioned, and policy-gated memory substrate so every specialized agent can:
- recall prior decisions, outcomes, and customer context
- distinguish working memory, episodic memory, semantic memory, and procedural memory
- learn from results without silently mutating production behavior
- remain stateless at the compute layer while remaining stateful at the business layer

The Memory Agent is not a chatbot transcript store. It is the company’s long-term operational memory.

## 3. Business Value
- Agents stop “forgetting” why a price was changed, why a SKU was killed, or why a customer was refunded.
- Cross-agent continuity: Sales, Support, Pricing, and Finance share one source of truth instead of conflicting local notes.
- Compounding intelligence: successful and failed experiments become reusable procedures.
- Lower LLM cost: retrieval of compact memory packets replaces stuffing entire histories into every prompt.
- Auditability: every consequential recollection used in a decision is attributable.
- Owner override: the human legal owner can freeze, redact, or export memory without operating the business day-to-day.

## 4. Agent Responsibilities
The Memory Agent owns:
- Ingesting memory write requests from any authenticated agent
- Classifying memory type (working / episodic / semantic / procedural / preference / risk)
- Deduplicating, summarizing, and embedding content
- Enforcing retention, redaction, and purpose-limitation policies from Governance and Ethics agents
- Serving ranked memory packets for a given agent, goal, entity, and time window
- Emitting memory-change events for downstream agents
- Running nightly consolidation (sleep-cycle): merge, forget low-value items, promote stable facts into semantic memory
- Detecting memory poisoning and contradictory facts
- Providing point-in-time recall for audits and incident reconstruction
- Exposing health, lag, and freshness SLOs

It does not own: product catalog truth (Commerce), ledger truth (Finance), or legal document truth (Legal). Those systems remain systems of record; Memory stores interpretations, outcomes, and context.

## 5. Inputs
- memory.write events and API calls from any agent
- Structured records: `{actor_agent, entity_type, entity_id, memory_type, payload, confidence, evidence_refs, ttl, sensitivity}`
- Conversation / tool traces (summarized, never raw secrets)
- Outcome labels from later agents (success, refunded, chargeback, policy_violation)
- Policy updates from Governance, Ethics & Compliance, and Risk agents
- Redaction / legal-hold orders from Legal / Policy Management
- Human-owner emergency freeze / purge commands
- Clock and scheduler ticks from the Scheduler Agent (assumed future module)

## 6. Outputs
- Ranked memory.packet objects for RAG / planning
- memory.updated, memory.contradiction, memory.poisoning_suspected events
- Consolidation reports
- Audit export packages
- SLO metrics and dead-letter items
- “Forgotten” certificates when TTL or policy requires deletion

Canonical packet shape:
```json
{
  "memory_id": "mem_01J...",
  "type": "episodic",
  "entities": [{"type": "customer", "id": "cus_123"}],
  "summary": "Customer requested refund after 11-day late delivery; approved under policy R-14.",
  "facts": [{"k": "refund_amount_usd", "v": 48.20}],
  "confidence": 0.93,
  "evidence_refs": ["evt_order_9912", "ticket_8841"],
  "sensitivity": "restricted",
  "created_by": "refund_agent",
  "valid_from": "2026-09-18T16:02:11Z",
  "valid_to": null
}
```

## 7. APIs Required
All APIs are versioned, idempotent where writes occur, and mTLS-only inside the mesh.

| API | Method | Purpose |
|---|---|---|
| /v1/memory/write | POST | Create or upsert a memory item |
| /v1/memory/query | POST | Hybrid lexical + vector + filter retrieval |
| /v1/memory/{id} | GET | Fetch one item + provenance |
| /v1/memory/{id} | PATCH | Correct / supersede (never silent rewrite) |
| /v1/memory/{id}/forget | POST | Policy-compliant deletion |
| /v1/memory/entities/{type}/{id} | GET | Timeline for a customer, SKU, supplier, campaign |
| /v1/memory/export | POST | Legal / owner export |
| /v1/memory/health | GET | Readiness + lag |
| /v1/memory/admin/freeze | POST | Owner / Governance kill-switch |

Async contract: NATS JetStream (or Kafka) subjects:
- memory.write.requested
- memory.written
- memory.queried (sampled)
- memory.contradiction.detected
- memory.consolidation.completed

## 8. MCP Tools Required
The Memory Agent publishes an MCP server so other agents do not invent ad-hoc tool schemas.

| Tool | Description |
|---|---|
| memory_write | Persist a typed memory with evidence refs |
| memory_search | Retrieve top-k packets with filters and recency bias |
| memory_get_entity_timeline | Ordered history for one business entity |
| memory_supersede | Mark prior memory obsolete and attach replacement |
| memory_forget | Request deletion under policy |
| memory_explain_used | Given a decision_id, list memories that influenced it |

MCP resource templates:
- memory://entity/{type}/{id}
- memory://policy/retention
- memory://alerts/contradictions

## 9. Databases Required
| Store | Role |
|---|---|
| PostgreSQL 16+ | System of record for metadata, provenance, validity intervals, ACLs, legal holds |
| pgvector or Qdrant | Semantic index of summaries and fact embeddings |
| Redis | Working-memory hot cache, rate limits, write idempotency keys |
| Object storage (S3-compatible) | Raw evidence blobs, export packages, consolidation snapshots |
| Append-only event log (NATS JetStream / Kafka) | Immutable write intent log |

Schema principles:
- Memories are immutable rows. Corrections create a new version and close the previous valid_to.
- Soft-delete only when legal hold is absent; hard-delete emits a forget certificate.
- Row-level security by tenant, agent role, and sensitivity.

## 10. Memory Requirements
This module is the memory tier. Internally it uses four bands:
1. Working memory — Redis, minutes to 24h, per-task scratch.
2. Episodic memory — “what happened”: orders, tickets, campaigns, negotiations.
3. Semantic memory — durable facts and learned priors (“SKU-441 converts poorly above $29”).
4. Procedural memory — approved playbooks and tool sequences that survived testing.

Context windows for the Memory Agent itself stay small: it retrieves, it does not load the whole company into one prompt.

## 11. Security Controls
Zero-trust defaults:
- SPIFFE/SPIRE identities for every agent workload
- mTLS everywhere; no ambient cluster trust
- Short-lived workload tokens scoped to memory:write:episodic etc.
- Sensitivity labels: public, internal, restricted, secret
- Secret material (PAN, raw credentials, government IDs) is rejected at the write gate — only tokenized references allowed
- Field-level encryption for restricted payloads (envelope keys in KMS)
- Prompt-injection / memory-poisoning classifier on inbound free text
- Query-time authorization: an agent may only retrieve memories it is entitled to use
- Owner emergency freeze disables writes in < 30 seconds
- Egress deny-by-default; Memory Agent talks only to approved stores and the event bus

## 12. Failure Recovery Strategy
| Failure | Response |
|---|---|
| Write API down | Producers persist to local outbox; event bus retains; replay on recovery |
| Vector index lag | Serve lexical + metadata results; mark packets freshness=degraded |
| Postgres primary loss | Automated failover; RPO ≤ 1s with sync replica; RTO ≤ 2 min |
| Poisoned batch detected | Quarantine vector partition; roll back embeddings from snapshot; keep SQL truth |
| Consolidation job crash | Exactly-once via job leases; resume from checkpoint |
| Split-brain embeddings | Rebuild index from SQL source of truth (SQL always wins) |
| Region outage | Active-passive second region; memory freeze rather than divergent writes if replication lag exceeds SLO |

Every write is idempotent on `idempotency_key = hash(actor, entity, payload_hash, day)`.

## 13. Agent-to-Agent Communications
Inbound consumers:
- All layer agents may write
- Governance / Ethics / Legal may freeze, redact, or change retention
- Model Evaluation and Prompt Optimization agents may read retrieval quality traces

Outbound publishers:
- Analytics / BI / KPI agents subscribe to consolidation summaries
- Risk Agent subscribes to memory.poisoning_suspected and contradiction storms
- Customer Success / CRM subscribe to entity timeline updates
- Incident Response subscribes to integrity alerts

Protocol: CloudEvents 1.0 over NATS. Payload signed. Correlation IDs mandatory (trace_id, decision_id, run_id).

## 14. Workflow Diagram (text)
```text
[Any Agent]
    |  memory.write (API or event)
    v
[Write Gateway]
    |-- authz + schema + secret-scan + poison-scan
    |-- reject -> dead-letter + alert Risk/SOC
    v
[Outbox + Event Log] -----> [Postgres immutable insert]
    |
    +--> [Embed + Index async worker] --> [Vector store]
    +--> [Cache invalidate]
    +--> publish memory.written

[Any Agent planning]
    |  memory_search / timeline
    v
[Query Gateway]
    |-- authz + purpose check
    |-- hybrid retrieve (SQL filters + vector + recency + confidence)
    |-- pack + cite evidence_refs
    v
[Memory Packet] --> caller
    +--> sampled memory.queried (for eval)

[Scheduler 02:00 UTC]
    v
[Consolidation Worker]
    |-- cluster near-duplicates
    |-- promote stable facts to semantic
    |-- decay low-utility episodic items
    |-- emit consolidation.completed
```

## 15. Data Flow
1. Producer agent emits a structured write (never a raw chain-of-thought dump).
2. Gateway validates identity, schema, sensitivity, and prohibited data classes.
3. SQL row committed first (source of truth).
4. Embedding worker reads the commit, writes vectors, ACKs the event.
5. Query path always applies ACL and purpose filters before similarity search.
6. Packets returned to callers include memory_ids that must be copied into the caller’s decision log.
7. Nightly consolidation reads SQL, not vectors, so index drift cannot invent facts.

## 16. Decision Logic
Write acceptance:
- Reject if actor lacks scope
- Reject if payload contains secrets / PAN / credentials
- Reject if confidence missing or evidence_refs empty for restricted items
- Quarantine if poison score > threshold
- Supersede rather than update-in-place

Retrieval ranking score:
`S = α·sim(q, m) + β·recency(m) + γ·confidence(m) + δ·entity_match - ε·sensitivity_penalty`

Default weights: α=0.45, β=0.20, γ=0.20, δ=0.15, ε applied only when caller clearance is below label.

Contradiction handling:
- If two semantic facts about the same entity conflict above threshold, emit memory.contradiction.detected and serve both with flags rather than picking a winner autonomously.
- Promotion to semantic memory requires either N independent agents agreeing or a Governance policy rule.

High-impact forget/export/freeze: configurable approval policy (default: Governance Agent + owner notification). Not fully autonomous when legally irreversible.

## 17. Escalation Rules
| Condition | Escalate to |
|---|---|
| Poisoning suspected at volume | Threat Detection + Incident Response + freeze writes for source agent |
| Contradiction on tax, contract, or safety fact | Legal + Risk + Governance |
| Forget request on legally held data | Legal (block) |
| Retrieval SLO burn | Cloud Infrastructure + DevOps |
| Owner emergency | Immediate freeze; notify Governance and SOC |
| Repeated low-confidence writes from one agent | Model Evaluation Agent (possible prompt or model regression) |

No silent drop. Every escalation is an event plus a durable ticket-like record.

## 18. KPIs
- Write success rate ≥ 99.9%
- P95 write ACK ≤ 150 ms (SQL path)
- P95 query ≤ 250 ms (hybrid)
- Index lag P95 ≤ 5 s
- Poison / injection catch rate (red-team)
- Contradiction open time
- % of downstream decisions that cite ≥1 memory_id
- Compaction ratio (tokens saved vs. naive full-history prompts)
- Illegal-data write attempts blocked
- RPO / RTO actuals vs. targets

## 19. Logging Requirements
Structured JSON logs (OpenTelemetry):
- Every write attempt: actor, entity, type, accept/reject reason
- Every query: filters, k, packet ids returned (not full payloads at info level)
- Consolidation actions
- Authz denials
- Poison scores

Payload bodies at restricted+ go to a sealed audit sink, not stdout.

## 20. Audit Trail Requirements
- Append-only event log is the legal trail
- Each memory version has created_by, superseded_by, valid_from/to
- Decision reconstruction API: given decision_id, return memories cited
- Exports are hashed and time-stamped
- Forget certificates prove what was deleted and under which policy, not the deleted content
- Retention of audit meta: ≥ 7 years or per Regulatory Compliance Agent policy

## 21. Compliance Requirements
- Purpose limitation: query purpose must match write purpose tags
- Data minimization at the write gate
- GDPR / CPRA style rights: export and forget paths, with legal-hold override
- PCI: no card data in memory (references only)
- SOC 2 style change control on policy and model versions used for classification
- Cross-border: region pin for restricted memories
- High-impact legal deletes require the configurable approval policy, not inferred consent from an LLM

## 22. Future Expansion Ideas
- Per-agent private memory vaults with share grants
- Causal memory graphs (“price drop caused refund spike”)
- Counterfactual memory: “what we would have done”
- On-device / edge working memory for low-latency storefront agents
- Memory marketplace between affiliated autonomous companies (opt-in, contracted)
- Automatic playbook synthesis from repeated successful episodes

## 23. Risks
- Memory poisoning steering Pricing or Refunds
- Embedding drift creating false “facts”
- Over-retention of customer data
- Agents treating recalled opinions as ledger truth
- Cost blow-up from embedding every token
- Split-brain after a bad consolidation
- Prompt injection via customer tickets written into episodic memory

Mitigations are built into write gates, SQL-as-truth, dual-fact contradiction handling, and Governance approval for irreversible actions.

## 24. Testing Strategy
- Contract tests on OpenAPI + MCP tool schemas
- Property tests: immutability, idempotency, valid-interval integrity
- Red-team: injection in tickets, support chats, supplier emails
- Chaos: kill Postgres primary, partition NATS, stale vector index
- Retrieval eval set: 500 gold questions with expected memory_ids
- Load: 2k writes/s burst, 5k queries/s
- Policy tests: restricted agent cannot read secret memories
- DR rehearsal quarterly
- Canary: new embed model scores against frozen eval before promotion

Agents may recommend embed-model or ranker changes; they may not deploy them until tests pass.

## 25. Production Readiness Checklist
- OpenAPI and MCP server published in the internal registry
- SPIFFE identities and NetworkPolicies applied
- KMS envelope encryption verified
- Secret scanner blocking in staging
- Dashboards + paging SLOs live
- Backup + restore tested in the last 14 days
- Legal-hold path tested
- Owner freeze switch tested
- Data-residency pin verified
- Runbook in Knowledge Base (next module)
- Load test signed off by Cloud Infrastructure Agent
- Threat model reviewed by Risk + SOC

## 26. Suggested Technology Stack
- Language / API: Python 3.12, FastAPI, Pydantic v2
- Orchestration: Kubernetes, Helm, KEDA
- Identity: SPIFFE/SPIRE, OPA/Gatekeeper for policy
- SQL: PostgreSQL 16, Citus or native partitioning by month
- Vectors: pgvector to start; Qdrant if recall SLOs demand it
- Cache / working memory: Redis
- Events: NATS JetStream (lower ops than Kafka at this stage; Kafka-compatible later)
- Observability: OpenTelemetry, Tempo, Prometheus, Grafana, Loki
- Embeddings: vendor-agnostic interface; start with a strong open encoder, swap via Model Evaluation Agent
- Object store: S3-compatible
- IaC: Terraform
- CI: GitHub Actions or equivalent; images signed (Cosign)

Vendor-agnostic rule: every store sits behind an internal port interface so Pinecone/Weaviate/Bedrock can replace pgvector without rewriting agents.

## 27. Cost Estimate
Steady-state for a mid-size autonomous commerce company (~10M memory items, 50–150 agent replicas, 100 qps query, 20 wps write):

| Item | Monthly (USD, 2026-ish) |
|---|---|
| Postgres HA + replica | $400–900 |
| Vector index / extra compute | $300–800 |
| Redis | $80–200 |
| NATS / event log | $150–400 |
| Object storage + egress | $50–200 |
| Embeddings inference | $200–1,200 (dominant variable) |
| Observability | $150–350 |
| K8s share | $200–500 |
| Total | ~$1.5k–$4.5k / month |

Burst and multi-region DR roughly 1.6–2.0×. Cost is dominated by embedding calls; consolidation and summarization must stay aggressive.

## 28. Deployment Plan
1. Namespace memory-prod + memory-staging with NetworkPolicies
2. Migrate schema; enable RLS
3. Deploy write path only, dual-write to event log
4. Backfill embeddings offline
5. Open query path to a canary set: Governance, Risk, Analytics
6. Require memory_id citation in those agents’ decision logs
7. Progressive rollout to Revenue and Customer layers
8. Enable nightly consolidation after 7 days of clean writes
9. Register MCP server in the platform catalog
10. Turn on owner freeze + paging

No big-bang cutover. SQL truth can exist before vectors are perfect.

## 29. Maintenance Strategy
- Weekly: index health, contradiction queue, cost per 1k writes
- Continuous: embed-model eval shadow mode
- Monthly: retention enforcement job, restore drill sample
- Quarterly: region failover game day
- Policy changes ship as versioned config, not prompt edits
- The Memory Agent may propose ranker weight changes; CI tests + Governance policy gate deployment

## 30. Opportunities for Additional AI Automation
- Auto-summarize long ticket threads into episodic packets
- Detect when a “fact” has been stable for 30 days and nominate it for semantic promotion
- Generate eval questions from real contradictions
- Predict which memories will be needed next hour (prefetch)
- Suggest retention exceptions when a SKU is under legal dispute
- Self-tune α/β/γ/δ weights against downstream profit and CSAT — only after offline eval

# Close of Day 1

## What was completed today
A production-ready design for the Memory Agent / Persistent Multi-Agent Memory Fabric: APIs, MCP tools, data stores, security, failure handling, decision logic, compliance, cost, and rollout. This is the shared brain every later module is required to use.

## Dependencies on previous modules
None. This is Day 1. No prior daily module exists in this project.

## What should be generated tomorrow
Identity Management Agent (Cybersecurity Layer).

Reason: zero-trust identities, workload attestation, scoped tokens, and human-owner break-glass are now the blocker. Without them, Memory’s ACLs and every subsequent agent’s mTLS story are paper designs.

Alternate acceptable Day 2 if identity is deferred: Event Trigger Agent (the nervous system) or Knowledge Base Agent (policies and runbooks that Memory will point at).

## Remaining estimated completion
Platform scope ≈ 66 named agents plus shared platform concerns (bus, observability, approval policy engine).

Completed: ~1.5%

Remaining: ~98.5%

The company still has no products, no money movement, no customers, and no legal execution path. It does have a memory. That is the correct first organ.
