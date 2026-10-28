from sqlalchemy import URL
from sqlmodel import SQLModel, create_engine

from .config import load_config

_cfg = load_config()

database_url = URL.create(
    drivername=_cfg["DB_DRIVERNAME"],
    username=_cfg["DB_USERNAME"],
    password=_cfg["DB_PASSWORD"],
    host=_cfg["DB_HOST"],
    port=int(_cfg["DB_PORT"]),
    database=_cfg["DB_DATABASE"],
    query={"charset": _cfg["DB_CHARSET"]},
)

engine = create_engine(database_url, pool_pre_ping=True)


def create_db_and_tables() -> None:
    # 先导入模型，SQLModel 才会把表注册进 metadata。
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
