"""RAG 文档入库工具。

本模块只负责：文件校验、文档解析、文本切分、Embedding 和 pgvector 入库。
不包含 LangGraph 检索或回答节点。

FastAPI 上传接口示例：

    result = document_vector_tool.save(
        file_path=saved_file_path,
        user_id=current_user.id,
        kb_id=kb_id,
    )

写入前会校验 knowledge_bases 中存在 id=kb_id 且 user_id 匹配的知识库，
并检查知识库配置的 Embedding 模型与当前工具一致。
表位于 DB_SCHEMA（默认 agent）下，连接时通过 search_path 指定。
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import TypedDict

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

RAG_DIR = Path(__file__).resolve().parent
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}
VECTOR_DIMENSION = 384
ERROR_MESSAGE_MAX_LENGTH = 2000
HASH_BUFFER_SIZE = 1024 * 1024
# vector.sql 中的三张表建在 agent schema 下。
DEFAULT_DB_SCHEMA = "agent"

load_dotenv(RAG_DIR.parent / ".env")


class SaveResult(TypedDict):
    document_id: int
    filename: str
    file_type: str
    file_hash: str
    chunk_count: int
    embedding_model: str
    status: str


class DocumentVectorTool:
    """将一个已保存到磁盘的文档切分、向量化并保存到 pgvector。"""

    def __init__(
        self,
        database_url: str | None = None,
        embedding_model: str | None = None,
        db_schema: str | None = None,
    ) -> None:
        self.database_url = database_url
        self.db_schema = db_schema or os.getenv("DB_SCHEMA") or DEFAULT_DB_SCHEMA
        self.embedding_model = (
            embedding_model
            or os.getenv("EMBEDDING_MODEL")
            or DEFAULT_EMBEDDING_MODEL
        )
        # 当前 SQL 使用 vector(384)，因此该工具要求模型输出 384 维向量。
        self.vector_dimension = VECTOR_DIMENSION
        # 延迟加载，避免 FastAPI 启动时立即加载 Embedding 模型。
        self._model: SentenceTransformer | None = None

    def save(
        self,
        file_path: str | Path,
        user_id: int,
        kb_id: int,
    ) -> SaveResult:
        """解析并保存单个文档。

        同一知识库上传相同内容时，通过 SHA256 哈希定位已有文档，
        并用新切片替换旧切片。处理状态先提交为 processing，完成后再更新为
        completed；处理失败时记录 failed 和错误信息。
        """
        path = Path(file_path).resolve()
        self._validate(path, user_id, kb_id)

        # 对文件内容计算哈希，而不是依赖上传时生成的临时文件路径。
        file_hash = self._calculate_file_hash(path)
        file_type = path.suffix.lower().removeprefix(".")

        document_id: int | None = None
        try:
            # 先单独提交文档记录，使 processing 状态在解析和向量化期间可见。
            document_id = self._create_or_update_document(
                path=path,
                user_id=user_id,
                kb_id=kb_id,
                file_type=file_type,
                file_hash=file_hash,
            )

            chunks = self._load_and_split(path)
            if not chunks:
                raise ValueError(f"文档没有可保存的文本内容：{path.name}")

            model = self._get_model()
            model_dimension = model.get_embedding_dimension()
            if model_dimension != self.vector_dimension:
                raise ValueError(
                    f"Embedding 模型输出维度为 {model_dimension}，"
                    f"数据库字段要求 {self.vector_dimension} 维"
                )

            embeddings = model.encode(
                [chunk.page_content for chunk in chunks],
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            if embeddings.shape[1] != self.vector_dimension:
                raise ValueError(
                    f"Embedding 模型实际输出 {embeddings.shape[1]} 维，"
                    f"数据库字段要求 {self.vector_dimension} 维"
                )

            self._replace_chunks(document_id, path.name, chunks, embeddings)

        except Exception as exc:
            if document_id is not None:
                self._mark_failed(document_id, exc)
            raise

        return {
            "document_id": document_id,
            "filename": path.name,
            "file_type": file_type,
            "file_hash": file_hash,
            "chunk_count": len(chunks),
            "embedding_model": self.embedding_model,
            "status": "completed",
        }

    @staticmethod
    def _validate(path: Path, user_id: int, kb_id: int) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"文档文件不存在：{path}")
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise ValueError(f"不支持 {path.suffix or '无扩展名'} 文件，仅支持：{supported}")
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id 必须是正整数")
        if not isinstance(kb_id, int) or kb_id <= 0:
            raise ValueError("kb_id 必须是正整数")

    @staticmethod
    def _calculate_file_hash(path: Path) -> str:
        """分块读取文件计算 SHA256，避免一次性将大文件读入内存。"""
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
                digest.update(block)
        return digest.hexdigest()

    def _create_or_update_document(
        self,
        path: Path,
        user_id: int,
        kb_id: int,
        file_type: str,
        file_hash: str,
    ) -> int:
        """校验知识库归属与 Embedding 模型，再创建或更新文档记录。"""
        with psycopg.connect(self._get_conninfo()) as connection:
            # FOR SHARE 锁住知识库行，防止写入期间知识库被删除或修改模型配置。
            kb_row = connection.execute(
                """
                SELECT embedding_model, vector_dimension
                FROM knowledge_bases
                WHERE id = %s AND user_id = %s
                FOR SHARE
                """,
                (kb_id, user_id),
            ).fetchone()
            if kb_row is None:
                raise ValueError(f"知识库不存在或不属于该用户：kb_id={kb_id}, user_id={user_id}")

            kb_model, kb_dimension = kb_row
            if kb_model != self.embedding_model or kb_dimension != self.vector_dimension:
                raise ValueError(
                    "知识库配置的 Embedding 模型与当前工具不一致，不能写入。"
                    f"知识库：{kb_model} ({kb_dimension} 维)；"
                    f"当前工具：{self.embedding_model} ({self.vector_dimension} 维)。"
                )

            row = connection.execute(
                """
                INSERT INTO documents (
                    kb_id,
                    filename,
                    file_type,
                    file_path,
                    file_hash,
                    status,
                    error_message
                )
                VALUES (%s, %s, %s, %s, %s, 'processing', NULL)
                ON CONFLICT (kb_id, file_hash)
                DO UPDATE SET
                    filename = EXCLUDED.filename,
                    file_type = EXCLUDED.file_type,
                    file_path = EXCLUDED.file_path,
                    status = 'processing',
                    error_message = NULL
                RETURNING id
                """,
                (kb_id, path.name, file_type, str(path), file_hash),
            ).fetchone()

            if row is None:
                raise RuntimeError("创建或更新 documents 记录失败")
            return int(row[0])

    def _load_and_split(self, path: Path) -> list[Document]:
        suffix = path.suffix.lower()
        source_name = path.name

        if suffix == ".pdf":
            documents = self._load_pdf(path, source_name)
            chunk_size, chunk_overlap = 800, 100
        else:
            documents = [
                Document(
                    page_content=self._read_text(path),
                    metadata={"source": source_name, "file_type": suffix[1:]},
                )
            ]
            chunk_size, chunk_overlap = 500, 50

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        )
        return splitter.split_documents(documents)

    @staticmethod
    def _load_pdf(path: Path, source_name: str) -> list[Document]:
        documents: list[Document] = []
        for page_number, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": source_name,
                            "file_type": "pdf",
                            "page": page_number,
                        },
                    )
                )
        return documents

    @staticmethod
    def _read_text(path: Path) -> str:
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeError(f"无法识别文本编码：{path.name}")

    def _replace_chunks(
        self,
        document_id: int,
        filename: str,
        chunks: list[Document],
        embeddings,
    ) -> None:
        """在一个事务中替换全部切片并标记完成。

        若插入过程中失败，事务回滚会保留旧切片，不会留下半套新切片。
        """
        with psycopg.connect(self._get_conninfo()) as connection:
            register_vector(connection)
            connection.execute(
                "DELETE FROM document_chunks WHERE document_id = %s",
                (document_id,),
            )
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_index, content, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            document_id,
                            index,
                            chunk.page_content,
                            embedding,
                            Jsonb(
                                {
                                    **chunk.metadata,
                                    "document_id": document_id,
                                    "filename": filename,
                                }
                            ),
                        )
                        for index, (chunk, embedding) in enumerate(
                            zip(chunks, embeddings, strict=True)
                        )
                    ],
                )
            connection.execute(
                """
                UPDATE documents
                SET status = 'completed', error_message = NULL
                WHERE id = %s
                """,
                (document_id,),
            )

    def _mark_failed(self, document_id: int, exc: Exception) -> None:
        """记录失败状态；失败状态更新不能覆盖最初的处理异常。"""
        try:
            with psycopg.connect(self._get_conninfo()) as connection:
                connection.execute(
                    """
                    UPDATE documents
                    SET status = 'failed', error_message = %s
                    WHERE id = %s
                    """,
                    (str(exc)[:ERROR_MESSAGE_MAX_LENGTH], document_id),
                )
        except Exception:
            logger.exception("更新文档失败状态时发生异常，document_id=%s", document_id)

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.embedding_model)
        return self._model

    def _get_conninfo(self) -> str:
        url = self.database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("请先配置 DATABASE_URL")
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
        # 表在 db_schema 下；保留 public，以便找到装在 public 的 vector 扩展类型。
        # make_conninfo 负责转义，不手工拼接连接串。
        return make_conninfo(url, options=f"-csearch_path={self.db_schema},public")


# FastAPI 路由可以复用该实例，Embedding 模型在当前进程内只加载一次。
document_vector_tool = DocumentVectorTool()


def save_document_to_pgvector(
    file_path: str | Path,
    user_id: int,
    kb_id: int,
) -> SaveResult:
    """函数形式的调用入口，方便上传接口直接调用。"""
    return document_vector_tool.save(file_path, user_id, kb_id)


if __name__ == "__main__":
    # 基于脚本所在目录定位，避免受运行时工作目录影响。
    file_path = RAG_DIR / "document" / "knowledge1.txt"
    save_document_to_pgvector(file_path=file_path,user_id=12,kb_id=1)
    