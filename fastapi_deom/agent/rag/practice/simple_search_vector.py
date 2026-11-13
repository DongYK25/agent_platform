"""最简单的 pgvector 文档检索示例。

这个文件只演示 RAG 的“检索”流程：

    用户问题 -> Embedding 向量 -> 数据库计算余弦距离 -> 返回最相关文本块

不使用 LangGraph，也不调用大模型生成答案。
运行前请先用 simple_document_ingest.py 把文档写入数据库。
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.conninfo import make_conninfo
from sentence_transformers import SentenceTransformer


PRACTICE_DIR = Path(__file__).resolve().parent

# .env 位于 fastapi_deom/agent/.env。
load_dotenv(PRACTICE_DIR.parent.parent / ".env")

# 查询和入库必须使用同一个 Embedding 模型。
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIMENSION = 384
DB_SCHEMA = os.getenv("DB_SCHEMA", "agent")


def get_connection_info() -> str:
    """从环境变量读取 PostgreSQL 连接信息。"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("请先在 agent/.env 中配置 DATABASE_URL")

    database_url = database_url.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )
    return make_conninfo(
        database_url,
        options=f"-csearch_path={DB_SCHEMA},public",
    )


def question_to_vector(question: str):
    """把用户问题转换成一个 384 维向量。"""
    question = question.strip()
    if not question:
        raise ValueError("问题不能为空")

    model = SentenceTransformer(EMBEDDING_MODEL)
    query_vector = model.encode(
        question,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    if query_vector.shape[0] != VECTOR_DIMENSION:
        raise ValueError(
            f"模型生成了 {query_vector.shape[0]} 维向量，"
            f"但数据库字段要求 {VECTOR_DIMENSION} 维"
        )

    # print(f"步骤 1：问题已经转换为 {query_vector.shape[0]} 维向量")
    # print(f"向量的前 5 个数字：{query_vector[:5].tolist()}")
    return query_vector


def search_similar_chunks(query_vector,kb_id: int,top_k: int = 3,connection_info=get_connection_info()) -> list[dict]:
    """从指定知识库中找出与问题最相似的文本块。"""
    if kb_id <= 0:
        raise ValueError("kb_id 必须是正整数")
    if top_k <= 0:
        raise ValueError("top_k 必须是正整数")

    with psycopg.connect(connection_info) as connection:
        # 让 Psycopg 能够把 NumPy 数组作为 PostgreSQL vector 参数传入。
        register_vector(connection)

        rows = connection.execute(
            """
            SELECT
                dc.content,
                d.filename,
                dc.chunk_index,
                dc.embedding <=> %s AS cosine_distance
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE d.kb_id = %s
              AND d.status = 'completed'
            ORDER BY cosine_distance
            LIMIT %s
            """,
            (query_vector, kb_id, top_k),
        ).fetchall()

    # pgvector 的 <=> 返回余弦距离：距离越小，两个向量越接近。
    # 为了更直观，这里用 1 - 距离得到相似度：相似度越大，文本越相关。
    results = []
    for content, filename, chunk_index, cosine_distance in rows:
        results.append(
            {
                "content": content,
                "filename": filename,
                "chunk_index": chunk_index,
                "distance": float(cosine_distance),
                "similarity": 1.0 - float(cosine_distance),
            }
        )

    print(f"步骤 2：数据库返回了 {len(results)} 个最相关的文本块")
    return results


def search(question: str, kb_id: int, top_k: int = 3) -> list[dict]:
    """执行一次完整的向量检索，并在终端展示结果。"""
    ##1.把用户的问题转为向量
    query_vector = question_to_vector(question)
    results = search_similar_chunks(query_vector, kb_id, top_k)

    if not results:
        print("该知识库中没有可以检索的文本块")
        return results

    for index, result in enumerate(results, start=1):
        print(f"\n===== 检索结果 {index} =====")
        print(f"来源文件：{result['filename']}")
        print(f"文本块序号：{result['chunk_index']}")
        print(f"余弦距离：{result['distance']:.4f}（越小越相关）")
        print(f"相似度：{result['similarity']:.4f}（越大越相关）")
        print(f"文本内容：\n{result['content']}")

    return results


if __name__ == "__main__":
    # 修改为实际存在的知识库 ID。
    example_kb_id = 1

    # user_question = input("请输入要查询的问题：").strip()
    user_question = """
    5. 工作日加班可以申请调休，调休应当在加班后 3 个月内使用完毕。

    6. 工作电脑仅限处理公司业务，禁止安装无关游戏、违规软件。

    7. 公司业务资料、客户信息属于保密信息，不得私自对外转发。
    """.strip()

    search(
        question=user_question,
        kb_id=example_kb_id,
        top_k=3,
    )
