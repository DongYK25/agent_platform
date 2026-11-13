"""最简单的 RAG 文档向量入库示例。

这个文件只演示一条基本流程：

    读取文本 -> 切分文本 -> 生成向量 -> 保存到 PostgreSQL

不包含相似度计算、文档检索、重复文档更新、处理状态跟踪或 PDF 解析。
运行前请确保：

1. 已执行 vector.sql，创建 knowledge_bases、documents 和 document_chunks 表。
2. knowledge_bases 表中已经存在要使用的 kb_id。
3. agent/.env 中已经配置 DATABASE_URL。
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector
from psycopg.conninfo import make_conninfo
from datetime import datetime

RAG_DIR = Path(__file__).resolve().parent

# 从 fastapi_deom/agent/.env 加载数据库配置。
load_dotenv(RAG_DIR.parent / ".env")

# 这个模型会把每段文字转换成一个包含 384 个数字的向量。
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIMENSION = 384
DB_SCHEMA = "agent"


def read_and_split(file_path: Path) -> list[str]:
    """读取一个 UTF-8 文本文件，并把它切分成多个较短的文本块。"""
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在：{file_path}")
    if file_path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError("入门示例只支持 .txt 和 .md 文件")

    text = file_path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("文档内容为空")

    # 默认长度函数是 len，因此这里的 500 表示约 500 个字符，不是 500 Token。
    ##########################---------------------------------------------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=120,
        chunk_overlap=10,  ###前后两个块重叠字符数
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )
    chunks = splitter.split_text(text)
    print(f"步骤 1：文档已切分为 {len(chunks)} 个文本块")
    return chunks


def text_to_vectors(chunks: list[str]):
    """使用 Embedding 模型把每个文本块转换成一个向量。"""
    model = SentenceTransformer(EMBEDDING_MODEL)

    # 输入是 list[str]，输出是二维数组：
    # 行数等于文本块数量，每一行都是一个文本块对应的 384 维向量。
    embeddings = model.encode(
        chunks,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    if embeddings.shape[1] != VECTOR_DIMENSION:
        raise ValueError(
            f"模型生成了 {embeddings.shape[1]} 维向量，"
            f"但数据库字段要求 {VECTOR_DIMENSION} 维"
        )

    print(f"步骤 2：向量数组形状为 {embeddings.shape}")
    print(f"第一个向量的前 5 个数字：{embeddings[0][:5].tolist()}")
    return embeddings


def get_connection_info() -> str:
    """读取数据库连接地址，并指定数据表所在的 schema。"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("请先在 agent/.env 中配置 DATABASE_URL")

    # psycopg 使用 postgresql://，不使用 SQLAlchemy 的 +psycopg 写法。
    database_url = database_url.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )
    return make_conninfo(
        database_url,
        options=f"-csearch_path={DB_SCHEMA},public",
    )


def save_to_database(
    file_path: Path,
    kb_id: int,
    chunks: list[str],
    embeddings,
) -> int:
    """把文档记录、文本块和对应向量保存到数据库。"""
    # documents.file_hash 是现有表中的必填字段。
    # 这里计算 SHA256 只为满足表结构，并让数据库拒绝同一知识库中的重复文档。
    file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

    # connection 上下文代表一个事务：全部写入成功后提交，出错时全部回滚。
    with psycopg.connect(get_connection_info()) as connection:
        # 注册 pgvector 类型后，Psycopg 才能把 NumPy 数组写入 vector 字段。
        register_vector(connection)

        row = connection.execute(
            """
            INSERT INTO documents (
                kb_id, filename, file_type, file_path, file_hash, status
            )
            VALUES (%s, %s, %s, %s, %s, 'completed')
            RETURNING id
            """,
            (
                kb_id,
                file_path.name,
                file_path.suffix.lower().removeprefix("."),
                str(file_path),
                file_hash,
            ),
        ).fetchone()

        if row is None:
            raise RuntimeError("documents 表写入失败")
        document_id = int(row[0])

        # chunk_index 保留文本块在原文中的顺序。
        # content 保存原文，embedding 保存与原文对应的 384 个浮点数。
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO document_chunks (
                    document_id, chunk_index, content, embedding
                )
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (document_id, index, chunk, embedding)
                    for index, (chunk, embedding) in enumerate(
                        zip(chunks, embeddings, strict=True)
                    )
                ],
            )

    print(f"步骤 3：已将文档和 {len(chunks)} 个向量保存到数据库")
    return document_id


def ingest_text_file(file_path: str | Path, kb_id: int) -> int:
    """按顺序执行读取切分、生成向量和数据库写入。"""
    path = Path(file_path).resolve()
    ##1.第一步切块
    chunks = read_and_split(path)
    # print(11111,chunks)
    ##2.第二步生成向量
    embeddings = text_to_vectors(chunks)
    print(11111,embeddings)
    ##3.第三步入库
    document_id = save_to_database(path, kb_id, chunks, embeddings)

    print(f"入库完成，document_id={document_id}")
    return document_id


if __name__ == "__main__":
    # 修改下面两个值后直接运行本文件。
    example_file = RAG_DIR / "document" / "knowledge1.txt"
    example_kb_id = 1

    ingest_text_file(example_file, example_kb_id)
