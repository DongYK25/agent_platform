# fastapi-common

基于 FastAPI + Tortoise ORM 的通用后端项目，使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

## 环境要求

- Python >= 3.11
- uv

## 快速开始

### 1. 初始化项目（仅首次创建时）

```bash
uvx fastapi-new .
```

### 2. 安装依赖

```bash
uv add -r requirements.txt
```

使用阿里云镜像加速：

```bash
uv add --default-index https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

按需修改 `.env` 中的配置。

### 4. 启动开发服务器

```bash
uv run fastapi dev
```

服务默认运行在 http://127.0.0.1:8000 。

## API 文档

| 名称 | 地址 | 说明 |
| --- | --- | --- |
| Swagger UI | http://127.0.0.1:8000/docs | 可直接调试接口 |
| ReDoc | http://127.0.0.1:8000/redoc | 更适合阅读 |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json | 原始接口定义 |

下载 OpenAPI 定义文件：

```bash
curl http://127.0.0.1:8000/openapi.json -o openapi.json
```

## 代码生成

使用 `gen/generate_crud.py` 为模型生成 CRUD 接口：

```bash
uv run python gen/generate_crud.py --model Role --prefix /roles --tag "角色管理"
```

| 参数 | 说明 |
| --- | --- |
| `--model` | 模型类名 |
| `--prefix` | 路由前缀 |
| `--tag` | 接口文档中的分组标签 |

详细用法见 [gen/README.md](gen/README.md)。

## 部署

```bash
uv run fastapi deploy
```
