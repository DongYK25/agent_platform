"""基于 pgvector 的 RAG 基础模块。

QueryRAG：检索流程
    用户问题 -> Embedding 向量 -> 数据库计算余弦距离 -> 返回最相关文本块

ImportRAG：入库流程
    读取文本 -> 切分文本 -> 生成向量 -> 保存到 PostgreSQL

不使用 LangGraph，也不调用大模型生成答案。
检索前需要先用 ImportRAG 把文档写入数据库。
"""

from __future__ import annotations

import psycopg

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from agent.baseConfig import get_connection_info, EMBEDDING_MODEL, VECTOR_DIMENSION

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hashlib

model_embedding = SentenceTransformer(EMBEDDING_MODEL)

class QueryRAG:
    """RAG类,查询数据库相关"""
    @classmethod
    def question_to_vector(cls,question: str):
        """把用户问题转换成一个 384 维向量。"""
        question = question.strip()
        if not question:
            raise ValueError("问题不能为空")

        query_vector = model_embedding.encode(
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

    @classmethod
    def search_similar_chunks(cls,query_vector,kb_id: int,top_k: int = 3) -> list[dict]:
        """从指定知识库中找出与问题最相似的文本块。"""
        if kb_id <= 0:
            raise ValueError("kb_id 必须是正整数")
        if top_k <= 0:
            raise ValueError("top_k 必须是正整数")

        with psycopg.connect(get_connection_info()) as connection:
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


    @classmethod
    def test_search(cls, question: str, kb_id: int, top_k: int = 3) -> list[dict]:
        """执行一次完整的向量检索，并在终端展示结果。"""
        ##1.把用户的问题转为向量
        query_vector = cls.question_to_vector(question)
        results = cls.search_similar_chunks(query_vector, kb_id, top_k)

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

class ImportRAG:
    """RAG类,导入数据库相关"""
    def __init__(self, conninfo: str, txt_path: str | Path, kb_id: int):
        self.conninfo = conninfo
        self.path = Path(txt_path).resolve()
        self.kb_id = kb_id

        if not self.path.is_file():
            raise FileNotFoundError(f"文件不存在：{self.path}")
        if self.path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("只支持 .txt 和 .md 文件")

    def read_txt_and_split(self) -> list[str]:
        """读取一个 UTF-8 文本文件，并把它切分成多个较短的文本块。"""
        text = self.path.read_text(encoding="utf-8-sig")
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
    
    def text_to_vectors(self, chunks: list[str]):
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
    def save_to_database(self, chunks: list[str], embeddings) -> int:
        """把文档记录、文本块和对应向量保存到数据库。"""
        # documents.file_hash 是现有表中的必填字段。
        # 这里计算 SHA256 只为满足表结构，并让数据库拒绝同一知识库中的重复文档。
        file_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()

        # connection 上下文代表一个事务：全部写入成功后提交，出错时全部回滚。
        with psycopg.connect(self.conninfo) as connection:
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
                    self.kb_id,
                    self.path.name,
                    self.path.suffix.lower().removeprefix("."),
                    str(self.path),
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

    def ingest_text_file(self) -> int:
        """按顺序执行读取切分、生成向量和数据库写入。"""
        ##1.第一步切块
        chunks = self.read_txt_and_split()
        # print(11111,chunks)
        ##2.第二步生成向量
        embeddings = self.text_to_vectors(chunks)
        # print(11111,embeddings)
        ##3.第三步入库
        document_id = self.save_to_database(chunks, embeddings)

        print(f"入库完成，document_id={document_id}")
        return document_id




if __name__ == "__main__":
    # 修改为实际存在的知识库 ID。
    example_kb_id = 1
    #############-------------------------------------------------
    ## 检索
    # user_question = input("请输入要查询的问题：").strip()
    user_question = """公司几点下班""".strip()

    QueryRAG.test_search(
        question=user_question,
        kb_id=example_kb_id,
        top_k=3,
    )
    # #############-------------------------------------------------
    # ## 入库
    # instance = ImportRAG(
    #     conninfo=get_connection_info(),
    #     txt_path=Path(__file__).parent / "rag" / "document" / "knowledge1.txt",
    #     kb_id=example_kb_id,
    # )
    # instance.ingest_text_file()
