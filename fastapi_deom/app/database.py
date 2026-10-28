from pathlib import Path

from sqlmodel import SQLModel, create_engine

BASE_DIR = Path(__file__).resolve().parent.parent
sqlite_file = BASE_DIR / "database.db"
sqlite_url = f"sqlite:///{sqlite_file.as_posix()}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    # 先导入模型，SQLModel 才会把表注册进 metadata。
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
