"""上传接口使用的文档向量化工具。

上传接口先把文件保存到磁盘，再调用：

    result = document_vector_tool.save(
        file_path=saved_file_path,
        user_id=user_id,
        kb_id=kb_id,
    )

本模块只负责加载、切分、向量化和入库，不包含 LangGraph 检索或回答节点。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import psycopg
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


RAG_DIR = Path(__file__).resolve().parent
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}
VECTOR_DIMENSION = 384

load_dotenv(RAG_DIR.parent / ".env")


class SaveResult(TypedDict):
    document_id: int
    filename: str
    file_type: str
    chunk_count: int
    status: str


class DocumentVectorTool:
    """将上传后保存在磁盘上的单个文档保存到 pgvector。"""

    def __init__(
        self,
        database_url: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self.database_url = database_url
        self.embedding_model = (
            embedding_model
            or os.getenv("EMBEDDING_MODEL")
            or DEFAULT_EMBEDDING_MODEL
        )
        # 延迟加载，避免 FastAPI 启动时立即下载和加载模型。
        self._model: SentenceTransformer | None = None

    def save(
        self,
        file_path: str | Path,
        user_id: int,
        kb_id: int,
    ) -> SaveResult:
        """解析一个已上传文件，切分并保存到 documents/document_chunks。"""
        path = Path(file_path).resolve()
        self._validate(path, user_id, kb_id)

        chunks = self._load_and_split(path)
        if not chunks:
            raise ValueError(f"文档没有可保存的文本内容：{path.name}")

        embeddings = self._get_model().encode(
            [chunk.page_content for chunk in chunks],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if embeddings.shape[1] != VECTOR_DIMENSION:
            raise ValueError(
                f"Embedding 模型输出 {embeddings.shape[1]} 维，"
                f"数据库字段要求 {VECTOR_DIMENSION} 维"
            )

        file_type = path.suffix.lower().removeprefix(".")
        with psycopg.connect(self._get_database_url()) as connection:
            register_vector(connection)
            row = connection.execute(
                """
                INSERT INTO documents
                    (user_id, kb_id, filename, file_type, file_path, status)
                VALUES (%s, %s, %s, %s, %s, 'processing')
                ON CONFLICT (user_id, kb_id, file_path)
                DO UPDATE SET
                    filename = EXCLUDED.filename,
                    file_type = EXCLUDED.file_type,
                    status = 'processing'
                RETURNING id
                """,
                (user_id, kb_id, path.name, file_type, str(path)),
            ).fetchone()
            if row is None:
                raise RuntimeError("保存 documents 记录失败")
            document_id = row[0]

            # 同一文件再次上传时，用新切片替换旧切片。
            connection.execute(
                "DELETE FROM document_chunks WHERE document_id = %s",
                (document_id,),
            )
            connection.executemany(
                """
                INSERT INTO document_chunks
                    (document_id, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (
                        document_id,
                        index,
                        chunk.page_content,
                        embedding,
                        Jsonb(chunk.metadata),
                    )
                    for index, (chunk, embedding) in enumerate(
                        zip(chunks, embeddings, strict=True)
                    )
                ],
            )
            connection.execute(
                "UPDATE documents SET status = 'completed' WHERE id = %s",
                (document_id,),
            )

        return {
            "document_id": document_id,
            "filename": path.name,
            "file_type": file_type,
            "chunk_count": len(chunks),
            "status": "completed",
        }

    @staticmethod
    def _validate(path: Path, user_id: int, kb_id: int) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"上传文件不存在：{path}")
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise ValueError(f"不支持 {path.suffix} 文件，仅支持：{supported}")
        if user_id <= 0 or kb_id <= 0:
            raise ValueError("user_id 和 kb_id 必须是正整数")

    def _load_and_split(self, path: Path) -> list[Document]:
        suffix = path.suffix.lower()
        source = str(path)

        if suffix == ".pdf":
            documents = self._load_pdf(path, source)
            chunk_size, chunk_overlap = 800, 100
        else:
            documents = [
                Document(
                    page_content=self._read_text(path),
                    metadata={"source": source, "file_type": suffix[1:]},
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
    def _load_pdf(path: Path, source: str) -> list[Document]:
        documents: list[Document] = []
        for page_number, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": source,
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
        raise UnicodeError(f"无法识别文本编码：{path}")

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.embedding_model)
        return self._model

    def _get_database_url(self) -> str:
        url = self.database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("请先配置 DATABASE_URL")
        return url.replace("postgresql+psycopg://", "postgresql://", 1)


# FastAPI 路由可以直接导入并复用该实例，Embedding 模型只会加载一次。
document_vector_tool = DocumentVectorTool()


def save_document_to_pgvector(
    file_path: str | Path,
    user_id: int,
    kb_id: int,
) -> SaveResult:
    """函数形式的调用入口，方便上传接口直接使用。"""
    return document_vector_tool.save(file_path, user_id, kb_id)