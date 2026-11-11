-- ============================================================
-- RAG 知识库管理
-- PostgreSQL + pgvector
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 表1：知识库主表 knowledge_bases
-- ============================================================

CREATE TABLE knowledge_bases (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    embedding_model  VARCHAR(255) NOT NULL
        DEFAULT 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    vector_dimension SMALLINT NOT NULL DEFAULT 384,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_kb_vector_dimension
        CHECK (vector_dimension > 0),

    CONSTRAINT uq_kb_user_name
        UNIQUE (user_id, name)
);

COMMENT ON TABLE knowledge_bases IS '知识库主表，管理用户创建的知识库及其向量模型配置';

COMMENT ON COLUMN knowledge_bases.id IS '知识库ID，主键';
COMMENT ON COLUMN knowledge_bases.user_id IS '所属用户ID';
COMMENT ON COLUMN knowledge_bases.name IS '知识库名称，同一用户下名称不可重复';
COMMENT ON COLUMN knowledge_bases.description IS '知识库描述';
COMMENT ON COLUMN knowledge_bases.embedding_model IS '知识库使用的Embedding模型名称';
COMMENT ON COLUMN knowledge_bases.vector_dimension IS 'Embedding向量维度，当前默认384维';
COMMENT ON COLUMN knowledge_bases.created_at IS '知识库创建时间';
COMMENT ON COLUMN knowledge_bases.updated_at IS '知识库最后更新时间';


-- ============================================================
-- 表2：原始文档表 documents
-- ============================================================

CREATE TABLE documents (
    id           SERIAL PRIMARY KEY,
    kb_id        INTEGER NOT NULL
        REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    filename     VARCHAR(255) NOT NULL,
    file_type    VARCHAR(10) NOT NULL,
    file_path    TEXT NOT NULL,
    file_hash    VARCHAR(64) NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_documents_kb_hash
        UNIQUE (kb_id, file_hash),

    CONSTRAINT ck_documents_status
        CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

COMMENT ON TABLE documents IS '原始文档表，记录知识库上传的文件及其向量化处理状态';

COMMENT ON COLUMN documents.id IS '文档ID，主键';
COMMENT ON COLUMN documents.kb_id IS '所属知识库ID，关联knowledge_bases.id';
COMMENT ON COLUMN documents.filename IS '原始文件名称';
COMMENT ON COLUMN documents.file_type IS '文件类型，例如pdf、txt、md';
COMMENT ON COLUMN documents.file_path IS '服务器本地存储路径';
COMMENT ON COLUMN documents.file_hash IS '文件内容的SHA256哈希值，用于识别重复文件';
COMMENT ON COLUMN documents.status IS '处理状态：pending待处理、processing处理中、completed已完成、failed失败';
COMMENT ON COLUMN documents.error_message IS '文档解析或向量化失败时的错误信息';
COMMENT ON COLUMN documents.created_at IS '文档首次入库时间';

CREATE INDEX idx_documents_kb
    ON documents (kb_id);


-- ============================================================
-- 表3：文档切片表 document_chunks
-- ============================================================

CREATE TABLE document_chunks (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL
        REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(384) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_document_chunks_index
        UNIQUE (document_id, chunk_index)
);

COMMENT ON TABLE document_chunks IS '文档切片表，保存文档切分后的文本内容、向量及来源元数据';

COMMENT ON COLUMN document_chunks.id IS '切片ID，主键';
COMMENT ON COLUMN document_chunks.document_id IS '所属文档ID，关联documents.id';
COMMENT ON COLUMN document_chunks.chunk_index IS '切片在文档中的顺序，从0开始';
COMMENT ON COLUMN document_chunks.content IS '切片的原始文本内容';
COMMENT ON COLUMN document_chunks.embedding IS '切片文本的Embedding向量，当前为384维';
COMMENT ON COLUMN document_chunks.metadata IS '切片元数据，JSON格式，可保存文件名、类型、PDF页码等';
COMMENT ON COLUMN document_chunks.created_at IS '切片记录创建时间';

-- 普通查询索引
CREATE INDEX idx_document_chunks_document
    ON document_chunks (document_id, chunk_index);

-- HNSW余弦相似度索引
CREATE INDEX idx_document_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);