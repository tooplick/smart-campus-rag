-- Migration: Add conversations table and new qa_records columns
-- Run against: campus_rag database
-- Date: 2026-09-20

BEGIN;

-- 1. Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    client_id VARCHAR(36) NOT NULL,
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id),
    title VARCHAR(200) DEFAULT '新对话',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_conversations_client_id ON conversations(client_id);

-- 2. Add new columns to qa_records
ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS retrieval_latency_ms INTEGER DEFAULT 0;
ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS llm_latency_ms INTEGER DEFAULT 0;
ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS candidate_top_k INTEGER DEFAULT 8;
ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS final_top_k INTEGER DEFAULT 5;
ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS similarity_threshold FLOAT DEFAULT 0.6;

-- 3. Add index on qa_records.conversation_id (if not exists)
CREATE INDEX IF NOT EXISTS ix_qa_records_conversation_id ON qa_records(conversation_id);

COMMIT;