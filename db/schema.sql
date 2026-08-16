-- pgvector 插件提供 vector 类型和向量相似度运算符(<=>)，这是 archival memory 语义检索的基础
CREATE EXTENSION IF NOT EXISTS vector;

-- Core Memory：常驻在 prompt 里的记忆块，数量少、体积小，对应原项目 letta/services/block_manager.py 管理的 Block
CREATE TABLE IF NOT EXISTS core_memory_blocks (
    agent_id    TEXT NOT NULL,
    label       TEXT NOT NULL,          -- 块的名字，例如 "persona"、"human"
    value       TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (agent_id, label)
);

-- Recall Memory：完整对话历史，不受 context window 限制，对应原项目 message_manager.py
CREATE TABLE IF NOT EXISTS messages (
    id         BIGSERIAL PRIMARY KEY,
    agent_id   TEXT NOT NULL,
    role       TEXT NOT NULL,           -- 'user' / 'assistant' / 'tool'
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Archival Memory：长期知识库，按向量相似度检索，对应原项目 archive_manager.py + passage_manager.py
-- 384 维对应 sentence-transformers 的 all-MiniLM-L6-v2 模型输出的向量长度
CREATE TABLE IF NOT EXISTS archival_passages (
    id         BIGSERIAL PRIMARY KEY,
    agent_id   TEXT NOT NULL,
    content    TEXT NOT NULL,
    tags       TEXT[] NOT NULL DEFAULT '{}',
    embedding  vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ivfflat 索引加速向量近邻检索；数据量小时其实全表扫描也够用，这里保留是为了忠实还原原项目的检索机制
CREATE INDEX IF NOT EXISTS archival_passages_embedding_idx
    ON archival_passages USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
