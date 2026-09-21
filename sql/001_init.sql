-- PAMF source of truth. Vectors are a projection. Do not invent facts from embeddings.

CREATE TABLE IF NOT EXISTS memory_control (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO memory_control (k, v) VALUES ('frozen', 'false')
ON CONFLICT (k) DO NOTHING;

CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    memory_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    facts JSONB NOT NULL DEFAULT '[]',
    entities JSONB NOT NULL DEFAULT '[]',
    confidence DOUBLE PRECISION NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]',
    sensitivity TEXT NOT NULL,
    purpose TEXT,
    created_by TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to TIMESTAMPTZ,
    freshness TEXT NOT NULL DEFAULT 'fresh'
);

CREATE INDEX IF NOT EXISTS memories_open_idx ON memories (valid_to) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS memories_summary_trgm ON memories USING gin (to_tsvector('simple', summary));

CREATE TABLE IF NOT EXISTS legal_holds (
    memory_id TEXT PRIMARY KEY REFERENCES memories (memory_id)
);

CREATE TABLE IF NOT EXISTS forget_certificates (
    certificate_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    policy_id TEXT,
    forgotten_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS decision_citations (
    decision_id TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    cited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (decision_id, memory_id)
);
