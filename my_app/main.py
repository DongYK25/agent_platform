from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

app = FastAPI()
register_tortoise(
    app,
    db_url="postgres://user:password@localhost:5432/mydb", # 数据库连接串
    modules={"models": ["db.models"]}, # 你的模型所在模块路径
    generate_schemas=True,  # 启动时自动建表（仅开发环境用！）
    add_exception_handlers=True # 自动处理 DoesNotExist 等 ORM 异常
)
@app.get("/")
def main():
    return {"message": "Hello World"}
