CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id            BIGSERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    source        TEXT NOT NULL,
    format        TEXT NOT NULL,
    content_hash  TEXT NOT NULL UNIQUE,
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(384),
    tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_tsv_idx
    ON chunks USING gin (tsv);

CREATE TABLE IF NOT EXISTS eval_questions (
    id           TEXT PRIMARY KEY,
    question     TEXT NOT NULL,
    answer       TEXT,
    qtype        TEXT NOT NULL,       -- bridge | comparison | unanswerable | contradiction
    supporting   JSONB NOT NULL DEFAULT '[]',   -- სწორი პარაგრაფების სათაურები
    source       TEXT NOT NULL DEFAULT 'hotpotqa'
);



CREATE TABLE IF NOT EXISTS chunks_fixed (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(384),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_fixed_embedding_idx
    ON chunks_fixed USING hnsw (embedding vector_cosine_ops);