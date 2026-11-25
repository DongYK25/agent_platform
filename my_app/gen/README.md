# 通用 CRUD 代码生成器

该工具根据 `models/__init__.py` 中导出的 Tortoise ORM 模型，生成项目现有风格的 Schema、Service 和 API，并自动注册到 `api/router.py`。

## 使用前提

在运行生成器前：

1. 模型类必须已经定义。
2. 模型类必须从 `models/__init__.py` 导出。
3. 在项目根目录执行命令。

例如：

```python
# models/__init__.py
from models.work_order import WorkOrder
```

## 基本用法

```powershell
uv run python gen/generate_crud.py `
  --model WorkOrder `
  --prefix /workOrders `
  --tag "工作订单管理"
```

也可以写成一行：

```powershell
uv run python gen/generate_crud.py --model WorkOrder --prefix /workOrders --tag "工作订单管理"
```

参数说明：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--model` | 是 | `models/__init__.py` 导出的模型类名 |
| `--prefix` | 是 | FastAPI 路由前缀，必须以 `/` 开头 |
| `--tag` | 是 | Swagger/OpenAPI 中显示的接口标签 |
| `--force` | 否 | 覆盖已经存在的 Schema、Service 和 API 文件 |
| `--dry-run` | 否 | 只检查并显示操作，不写入文件 |

建议先预览：

```powershell
uv run python gen/generate_crud.py --model WorkOrder --prefix /workOrders --tag "工作订单管理" --force --dry-run
```

`--dry-run` 仍会执行文件冲突检查。目标文件已经存在时，需要同时添加 `--force` 才能完成预览，但不会实际覆盖文件。

## 生成结果

以 `WorkOrder` 为例，生成器创建或覆盖：

```text
schemas/workOrderSchemas.py
services/workOrderServices.py
api/v1/workOrderApi.py
```

并在 `api/router.py` 中补充：

```python
from api.v1 import workOrderApi

api_router.include_router(workOrderApi.router)
```

重复运行时不会重复注册路由。

## Schema 规则

### QuerySet

QuerySet 包含模型中可以直接映射为 Python 标量类型的字段。所有查询字段均为非必填字段，并额外提供成对使用的 `page` 和 `page_size`。

`id` 会生成最小值为 1 的校验：

```python
id: int | None = Field(default=None, ge=1)
```

关系字段没有统一的标量查询形式，因此生成器会跳过关系字段并在终端提示。可以根据实际外键字段手动补充，例如：

```python
owner_id: int | None = Field(default=None, ge=1)
```

### List

默认返回模型全部字段：

```python
exclude=()
```

如果模型含密码、密钥等敏感字段，生成后必须按业务需要加入 `exclude`，避免接口返回敏感数据。

### Create

默认配置：

```python
exclude_readonly=True
exclude=("deleted_at", "is_deleted")
```

UUID 等业务字段不会自动排除。如果某个模型需要排除 UUID 或其他字段，请在生成后的 Schema 中手动添加。

### Update

默认配置：

```python
exclude_readonly=False
exclude=("deleted_at", "is_deleted", "created_at", "updated_at")
```

生成的更新接口按照 PUT 整体更新处理，`id` 用于定位记录，不参与字段更新。

## Service 字段要求

通用 Service 依赖这些模型字段：

```text
id
is_deleted
deleted_at
updated_at
```

如果模型缺少字段，生成器会显示：

```text
是否忽略错误并继续生成？[yes/no]
```

- 输入 `yes` 或 `y`：继续生成，之后需要手动修改 Service。
- 输入 `no`、`n` 或直接回车：取消，不写入文件。

查询接口始终限定 `is_deleted=False`。删除接口执行软删除，并设置当前时区时间到 `deleted_at`。

## 文件保护

目标文件已存在时，生成器默认终止，并且不会写入任何文件：

```powershell
uv run python gen/generate_crud.py --model WorkOrder --prefix /workOrders --tag "工作订单管理"
```

确认需要覆盖后使用：

```powershell
uv run python gen/generate_crud.py --model WorkOrder --prefix /workOrders --tag "工作订单管理" --force
```

`--force` 只允许覆盖对应的 Schema、Service 和 API 文件。`api/router.py` 只会补充缺少的导入或路由注册。

## 生成后检查

生成完成后建议运行：

```powershell
uv run python -m compileall schemas services api
uv run fastapi dev
```

然后访问 `http://127.0.0.1:8000/docs` 检查请求字段、返回字段和路由。
