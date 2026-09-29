-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------
-- PII Mapping
-- Stores placeholder-to-original mappings per document.
-- Never sent outside the server. Server-side only.
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pii_mappings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    placeholder     TEXT NOT NULL,      -- e.g. [CLIENT_1]
    original_value  TEXT NOT NULL,      -- e.g. "John Doe"
    entity_type     TEXT NOT NULL,      -- e.g. "PERSON", "EMAIL", "PHONE", "ADDRESS", etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pii_mappings_document_id ON pii_mappings(document_id);


-- ---------------------------------------------------------------
-- Document Chunks
-- Extracted and masked text, chunked for embedding.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,       -- Order of the chunk in the document
    masked_text     TEXT NOT NULL,      -- The actual text of the chunk
    char_start      INTEGER,       -- Start character index of the chunk in the original document
    char_end        INTEGER,       -- End character index of the chunk in the original
    token_count     INTEGER,       -- Number of tokens in the chunk
    embedding       VECTOR(768),       -- Embedding vector for the chunk
    embedded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(document_id, chunk_index)  -- Ensure no duplicate chunks for the same document
); 

CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------------------------------------------------------------
-- Compliance Rules Corpus
-- Seeded once; used for rule retrieval (job 1)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_code       TEXT NOT NULL UNIQUE,  -- e.g. "HIPAA-001"
    rule_type       TEXT NOT NULL,      -- e.g. DISCLOSURE | PROHIBITED_CLAIM | PERFORMANCE_STANDARD | REQUIRED_FIELD
    title           TEXT NOT NULL,      -- e.g. "HIPAA Privacy Rule"
    body        TEXT NOT NULL,
    embedding   vector(768),
    embedded_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rules_embedding ON compliance_rules
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_rules_type ON compliance_rules(rule_type);

-- ----------------------------------------------------------------
-- Disclosure Texts Corpus
-- Approved disclosure and disclaimer texts.
-- Used for missing-disclosure detection (job 2).
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disclosure_texts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    disclosure_code TEXT UNIQUE NOT NULL,     -- e.g. RISK-DISC-001
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    is_mandatory    BOOLEAN NOT NULL DEFAULT TRUE,
    embedding       vector(768),
    embedded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_disclosures_embedding ON disclosure_texts
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_disclosures_mandatory ON disclosure_texts(is_mandatory);

-- ----------------------------------------------------------------
-- Precedent Index
-- Reviewed documents stored for similarity search (job 3).
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS precedent_index (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    masked_summary  TEXT NOT NULL,            -- Concatenated masked text (truncated for storage)
    decision        TEXT NOT NULL,            -- approved | rejected | needs_revision
    officer_comment TEXT,
    decided_at      TIMESTAMPTZ NOT NULL,
    embedding       vector(768),
    embedded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id)
);

CREATE INDEX idx_precedents_embedding ON precedent_index
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_precedents_decision ON precedent_index(decision);