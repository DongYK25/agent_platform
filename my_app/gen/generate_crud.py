from __future__ import annotations

import argparse
import ast
import re
import sys
import types
import typing
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_SERVICE_FIELDS = {"id", "is_deleted", "deleted_at", "updated_at"}
STANDARD_TYPES: dict[type[Any], tuple[str, tuple[str, str] | None]] = {
    str: ("str", None),
    int: ("int", None),
    float: ("float", None),
    bool: ("bool", None),
    bytes: ("bytes", None),
    dict: ("dict", None),
    list: ("list", None),
    date: ("date", ("datetime", "date")),
    datetime: ("datetime", ("datetime", "datetime")),
    time: ("time", ("datetime", "time")),
    timedelta: ("timedelta", ("datetime", "timedelta")),
    Decimal: ("Decimal", ("decimal", "Decimal")),
    UUID: ("UUID", ("uuid", "UUID")),
}


@dataclass(frozen=True)
class Names:
    model: str
    stem: str

    @property
    def schema_module(self) -> str:
        return f"{self.stem}Schemas"

    @property
    def service_module(self) -> str:
        return f"{self.stem}Services"

    @property
    def api_module(self) -> str:
        return f"{self.stem}Api"


@dataclass(frozen=True)
class GeneratedFile:
    path: Path
    content: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="根据 Tortoise ORM 模型生成 FastAPI 通用 CRUD 代码。",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="models/__init__.py 导出的模型类名，例如 WorkOrder",
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help='API 路由前缀，例如 "/workOrders"',
    )
    parser.add_argument(
        "--tag",
        required=True,
        help='OpenAPI 标签，例如 "工作订单管理"',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已经存在的 schema、service 和 API 文件",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="检查模型并显示将要执行的操作，但不写文件",
    )
    return parser.parse_args()


def to_lower_camel(name: str) -> str:
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", name)
    if not words:
        raise ValueError(f"无法从模型名 {name!r} 生成文件名")
    return words[0].lower() + "".join(word[:1].upper() + word[1:].lower() for word in words[1:])


def load_model(model_name: str) -> type[Any]:
    try:
        import models
        from tortoise.models import Model
    except ImportError as exc:
        raise RuntimeError(f"无法导入项目模型或 Tortoise ORM：{exc}") from exc

    model = getattr(models, model_name, None)
    if model is None:
        raise ValueError(
            f"models/__init__.py 没有导出模型 {model_name!r}，请先在该文件中导入模型类"
        )
    if not isinstance(model, type) or not issubclass(model, Model):
        raise ValueError(f"models.{model_name} 不是 Tortoise ORM 模型")
    return model


def confirm_ignoring_missing_fields(missing_fields: set[str]) -> bool:
    fields = ", ".join(sorted(missing_fields))
    print(f"模型缺少通用 CRUD service 所需字段：{fields}", file=sys.stderr)
    print("继续生成的代码可能无法直接运行，需要手动修改。", file=sys.stderr)

    while True:
        try:
            answer = input("是否忽略错误并继续生成？[yes/no] ").strip().lower()
        except EOFError:
            return False
        if answer in {"yes", "y"}:
            return True
        if answer in {"no", "n", ""}:
            return False
        print("请输入 yes 或 no。", file=sys.stderr)


def format_annotation(
    annotation: Any,
    imports: dict[str, set[str]],
) -> str:
    if annotation is None or annotation is Any:
        imports["typing"].add("Any")
        return "Any"

    if annotation in STANDARD_TYPES:
        name, import_spec = STANDARD_TYPES[annotation]
        if import_spec:
            imports[import_spec[0]].add(import_spec[1])
        return name

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin in {typing.Union, types.UnionType}:
        return " | ".join(format_annotation(arg, imports) for arg in args)
    if origin in {list, set, tuple, dict}:
        origin_name = origin.__name__
        if not args:
            return origin_name
        return f"{origin_name}[{', '.join(format_annotation(arg, imports) for arg in args)}]"

    if isinstance(annotation, type):
        module = annotation.__module__
        name = annotation.__name__
        if module == "builtins":
            return name
        imports[module].add(name)
        return name

    imports["typing"].add("Any")
    return "Any"


def query_fields(model: type[Any]) -> tuple[list[str], dict[str, set[str]], list[str]]:
    lines: list[str] = []
    imports: dict[str, set[str]] = defaultdict(set)
    skipped_relations: list[str] = []

    # fields_map 保留模型字段的声明顺序。关系字段没有可直接用于 Query 的 Python 标量类型，
    # 第一版生成器跳过它们，并在命令输出中明确提示用户手动补充关联键查询字段。
    for field_name, field in model._meta.fields_map.items():
        field_type = getattr(field, "field_type", None)
        if field_type is None:
            skipped_relations.append(field_name)
            continue

        annotation = format_annotation(field_type, imports)
        if field_name == "id" and annotation == "int":
            lines.append("    id: int | None = Field(default=None, ge=1)")
        else:
            lines.append(f"    {field_name}: {annotation} | None = None")

    return lines, imports, skipped_relations


def render_imports(imports: dict[str, set[str]]) -> str:
    ordered_modules = ["datetime", "decimal", "uuid", "typing"]
    remaining = sorted(module for module in imports if module not in ordered_modules)
    modules = [module for module in ordered_modules if imports.get(module)] + remaining
    return "\n".join(
        f"from {module} import {', '.join(sorted(imports[module]))}" for module in modules
    )


def render_schema(model: type[Any], names: Names) -> tuple[str, list[str]]:
    fields, type_imports, skipped_relations = query_fields(model)
    optional_imports = render_imports(type_imports)
    if optional_imports:
        optional_imports += "\n\n"

    field_block = "\n".join(fields)
    content = f'''{optional_imports}from pydantic import BaseModel, Field, model_validator
from tortoise.contrib.pydantic import pydantic_model_creator

from models import {names.model}


class {names.model}QuerySet(BaseModel):
{field_block}
    page: int | None = Field(default=None, ge=1, description="页码，从 1 开始")
    page_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="每页数量，最大 100",
    )

    @model_validator(mode="after")
    def validate_pagination(self) -> "{names.model}QuerySet":
        if (self.page is None) != (self.page_size is None):
            raise ValueError("page 和 page_size 必须同时提供")
        return self


{names.model}List_Pydantic = pydantic_model_creator(
    {names.model},
    name="{names.model}List",
    exclude=(),
)

{name_list(names.model, "Create")} = pydantic_model_creator(
    {names.model},
    name="{names.model}Create",
    exclude_readonly=True,
    exclude=("deleted_at", "is_deleted"),
)

{name_list(names.model, "Update")} = pydantic_model_creator(
    {names.model},
    name="{names.model}Update",
    exclude_readonly=False,
    exclude=(
        "deleted_at",
        "is_deleted",
        "created_at",
        "updated_at",
    ),
)
'''
    return content, skipped_relations


def name_list(model_name: str, operation: str) -> str:
    return f"{model_name}{operation}_Pydantic"


def render_service(names: Names) -> str:
    return f'''from datetime import datetime

from models import {names.model}
from schemas.{names.schema_module} import (
    {names.model}Create_Pydantic,
    {names.model}List_Pydantic,
    {names.model}QuerySet,
    {names.model}Update_Pydantic,
)


async def get_instances(data: {names.model}QuerySet):
    filters = data.model_dump(
        exclude={{"page", "page_size", "is_deleted"}},
        exclude_none=True,
    )
    query = {names.model}.filter(is_deleted=False, **filters).order_by("id")

    if data.page is not None and data.page_size is not None:
        offset = (data.page - 1) * data.page_size
        query = query.offset(offset).limit(data.page_size)

    instances = await query.all()
    return [{names.model}List_Pydantic.model_validate(instance) for instance in instances]


async def create_instance(data: {names.model}Create_Pydantic):
    instance = await {names.model}.create(**data.model_dump())
    return {names.model}List_Pydantic.model_validate(instance)


async def update_instance(data: {names.model}Update_Pydantic):
    instance = await {names.model}.get_or_none(id=data.id, is_deleted=False)
    if not instance:
        return None

    instance.update_from_dict(data.model_dump(exclude={{"id"}}))
    await instance.save()
    return {names.model}List_Pydantic.model_validate(instance)


async def delete_instance(id: int):
    instance = await {names.model}.get_or_none(id=id, is_deleted=False)
    if not instance:
        return None

    instance.is_deleted = True
    instance.deleted_at = datetime.now().astimezone()
    await instance.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return instance
'''


def render_api(names: Names, prefix: str, tag: str) -> str:
    return f'''from typing import Annotated

from fastapi import APIRouter, Query

from schemas.commonSchemas import ResponseCommon
from schemas.{names.schema_module} import (
    {names.model}Create_Pydantic,
    {names.model}QuerySet,
    {names.model}Update_Pydantic,
)
from services import {names.service_module}


router = APIRouter(prefix={prefix!r}, tags=[{tag!r}])


@router.get("", response_model=ResponseCommon)
async def get_instance(data: Annotated[{names.model}QuerySet, Query()]):
    instances = await {names.service_module}.get_instances(data)
    return ResponseCommon.success(data=instances)


@router.post("", response_model=ResponseCommon)
async def create_instance(data: {names.model}Create_Pydantic):
    try:
        instance = await {names.service_module}.create_instance(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    return ResponseCommon.success(data=instance)


@router.put("", response_model=ResponseCommon)
async def update_instance(data: {names.model}Update_Pydantic):
    try:
        instance = await {names.service_module}.update_instance(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    if not instance:
        return ResponseCommon.failed(msg="数据不存在", code=404)
    return ResponseCommon.success(data=instance)


@router.delete("", response_model=ResponseCommon)
async def delete_instance(id: Annotated[int, Query(ge=1)]):
    instance = await {names.service_module}.delete_instance(id)
    if not instance:
        return ResponseCommon.failed(msg="数据不存在", code=404)
    return ResponseCommon.success(data="删除成功")
'''


def update_router_source(source: str, api_module: str) -> tuple[str, bool]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"api/router.py 语法错误，无法自动注册路由：{exc}") from exc

    imported_modules = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "api.v1"
        for alias in node.names
    }
    registration_pattern = re.compile(
        rf"^\s*api_router\.include_router\(\s*{re.escape(api_module)}\.router\s*\)\s*$",
        re.MULTILINE,
    )

    changed = False
    if api_module not in imported_modules:
        import_nodes = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        insert_at = max((node.end_lineno or node.lineno) for node in import_nodes) if import_nodes else 0
        lines = source.splitlines(keepends=True)
        newline = "\r\n" if "\r\n" in source else "\n"
        lines.insert(insert_at, f"from api.v1 import {api_module}{newline}")
        source = "".join(lines)
        changed = True

    if not registration_pattern.search(source):
        source = source.rstrip() + f"\napi_router.include_router({api_module}.router)\n"
        changed = True

    return source, changed


def build_files(model: type[Any], names: Names, prefix: str, tag: str) -> tuple[list[GeneratedFile], list[str]]:
    schema, skipped_relations = render_schema(model, names)
    files = [
        GeneratedFile(PROJECT_ROOT / "schemas" / f"{names.schema_module}.py", schema),
        GeneratedFile(PROJECT_ROOT / "services" / f"{names.service_module}.py", render_service(names)),
        GeneratedFile(PROJECT_ROOT / "api" / "v1" / f"{names.api_module}.py", render_api(names, prefix, tag)),
    ]
    return files, skipped_relations


def validate_generated_python(files: list[GeneratedFile], router_source: str) -> None:
    for generated_file in files:
        compile(generated_file.content, str(generated_file.path), "exec")
    compile(router_source, str(PROJECT_ROOT / "api" / "router.py"), "exec")


def main() -> int:
    args = parse_args()

    if not args.prefix.startswith("/"):
        print("错误：--prefix 必须以 / 开头", file=sys.stderr)
        return 2

    try:
        model = load_model(args.model)
        names = Names(model=args.model, stem=to_lower_camel(args.model))
    except (RuntimeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    model_fields = set(model._meta.fields_map)
    missing_fields = REQUIRED_SERVICE_FIELDS - model_fields
    if missing_fields and not confirm_ignoring_missing_fields(missing_fields):
        print("已取消生成。", file=sys.stderr)
        return 1

    generated_files, skipped_relations = build_files(model, names, args.prefix, args.tag)
    existing_files = [generated_file.path for generated_file in generated_files if generated_file.path.exists()]
    if existing_files and not args.force:
        print("以下文件已经存在，未执行任何写入：", file=sys.stderr)
        for path in existing_files:
            print(f"  {path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        print("确认需要覆盖后，请添加 --force。", file=sys.stderr)
        return 1

    router_path = PROJECT_ROOT / "api" / "router.py"
    if not router_path.exists():
        print("错误：找不到 api/router.py，无法注册生成的路由", file=sys.stderr)
        return 1

    try:
        router_source, router_changed = update_router_source(
            router_path.read_text(encoding="utf-8"),
            names.api_module,
        )
        validate_generated_python(generated_files, router_source)
    except (OSError, UnicodeError, ValueError, SyntaxError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"模型：{names.model}")
    for generated_file in generated_files:
        action = "覆盖" if generated_file.path.exists() else "创建"
        print(f"{action}：{generated_file.path.relative_to(PROJECT_ROOT)}")
    print(f"路由：{'更新 api/router.py' if router_changed else '已经注册，无需修改'}")

    if skipped_relations:
        print(
            "提示：QuerySet 跳过了关系字段：" + ", ".join(skipped_relations) + "。请按关联键需求手动补充。",
            file=sys.stderr,
        )

    if args.dry_run:
        print("dry-run 完成，未写入文件。")
        return 0

    try:
        for generated_file in generated_files:
            generated_file.path.parent.mkdir(parents=True, exist_ok=True)
            generated_file.path.write_text(generated_file.content, encoding="utf-8", newline="\n")
        if router_changed:
            router_path.write_text(router_source, encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"写入失败：{exc}", file=sys.stderr)
        return 1

    print("生成完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
