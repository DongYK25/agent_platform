from sqlalchemy import URL, create_engine
from sqlalchemy.engine.url import make_url
from sqlmodel import SQLModel

from .config import load_config

_cfg = load_config()

# 改这里切换数据库："mysql" 或 "pg"。
USE_DB = "pg"


def _mysql_connection():
    url = URL.create(
        drivername=_cfg["DB_DRIVERNAME"],
        username=_cfg["DB_USERNAME"],
        password=_cfg["DB_PASSWORD"],
        host=_cfg["DB_HOST"],
        port=int(_cfg["DB_PORT"]),
        database=_cfg["DB_DATABASE"],
        query={"charset": _cfg["DB_CHARSET"]},
    )
    return url, None


def _pg_connection():
    url = make_url(_cfg["DATABASE_URL"])
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    schema = _cfg.get("DB_SCHEMA") or None
    # postgresql://host/server/agent 里的第二段是 schema，不是库名。
    database = url.database or ""
    if "/" in database:
        database, schema_in_path = database.split("/", 1)
        url = url.set(database=database)
        schema = schema or schema_in_path
    return url, schema


if USE_DB == "mysql":
    database_url, DB_SCHEMA = _mysql_connection()
elif USE_DB == "pg":
    database_url, DB_SCHEMA = _pg_connection()
else:
    raise ValueError('USE_DB 只能是 "mysql" 或 "pg"')

connect_args = {}
if USE_DB == "pg" and DB_SCHEMA:
    connect_args["options"] = f"-csearch_path={DB_SCHEMA}"

engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def create_db_and_tables() -> None:
    # 先导入模型，SQLModel 才会把表注册进 metadata。
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
