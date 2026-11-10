-- pgvector 扩展提供 vector 类型和向量索引。
-- 首次执行需要当前数据库用户具有 CREATE EXTENSION 权限。
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================
-- 表1：原始文档表 (documents)
-- 用于保存用户上传的文件信息
-- =============================================
CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,                -- 文档ID，自增主键
    user_id     INTEGER NOT NULL,                  -- 所属用户ID
    kb_id       INTEGER NOT NULL,                  -- 所属知识库ID
    filename    VARCHAR(255) NOT NULL,             -- 文件名称
    file_type   VARCHAR(10) NOT NULL,              -- 文件类型，如 pdf / txt / docx
    file_path   TEXT NOT NULL,                     -- 原始文件存储路径
    status      VARCHAR(20) DEFAULT 'pending',     -- 解析状态，如 pending / processing / completed / failed
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 上传时间
);

-- 可选：为常用查询字段添加索引
CREATE INDEX IF NOT EXISTS idx_documents_user_kb ON documents (user_id, kb_id);
-- 同一用户、同一知识库中的同一路径只保存一份，脚本重复运行时会更新它。
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_unique_file
    ON documents (user_id, kb_id, file_path);


-- =============================================
-- 表2：文档切片表 (document_chunks)
-- 用于保存分割后的文本及其向量数据
-- =============================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id            SERIAL PRIMARY KEY,              -- Chunk ID，自增主键
    document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE, -- 所属文档ID，外键关联 documents 表
    chunk_index   INTEGER NOT NULL,                -- 切片顺序，表示该 chunk 在文档中的位置
    content       TEXT NOT NULL,                   -- 切片文本内容
    embedding     vector(384),                     -- paraphrase-multilingual-MiniLM-L12-v2 输出 384 维
    metadata      JSONB DEFAULT '{}',              -- 元数据，以 JSON 格式存储额外信息（如页码、段落标题等）
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 创建时间
);

-- 可选：为向量检索添加 HNSW 索引，大幅提升相似度搜索性能
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);