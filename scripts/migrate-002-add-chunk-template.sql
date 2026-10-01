-- 知识库切块模板:general(默认)/section/qa/one
-- 对齐 RAGFlow 模板化切块,worker 按知识库的模板分派切块策略
ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS chunk_template VARCHAR(20) NOT NULL DEFAULT 'general';
