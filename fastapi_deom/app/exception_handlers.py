import contextvars
import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas.responseCommon import ResponseCommon

_LOC_SKIP = {"body", "query", "path", "header", "cookie"}
_APP_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _APP_DIR.parent
_NOISE_FILES = {"app/exception_handlers.py"}
_request_label: contextvars.ContextVar[str] = contextvars.ContextVar("app_error_request", default="")
_PARAMS_LIMIT = 2000


def error_content(code: int, msg: str, data=None) -> dict:
    return ResponseCommon(code=code, msg=msg, data=data).model_dump()


def _field_name(loc: tuple) -> str:
    parts = [str(item) for item in loc if str(item) not in _LOC_SKIP]
    return ".".join(parts) or "参数"


def _validation_message(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        field = _field_name(tuple(err.get("loc", ())))
        if err.get("type") == "missing":
            parts.append(f"缺少 {field}")
        else:
            parts.append(f"{field}: {err.get('msg', '无效')}")
    return "；".join(parts) or "参数校验失败"


def _is_app_file(filename: str) -> bool:
    try:
        Path(filename).resolve().relative_to(_APP_DIR)
    except (ValueError, OSError):
        return False
    return True


def _display_path(filename: str) -> str:
    path = Path(filename).resolve()
    try:
        return path.relative_to(_PROJECT_DIR).as_posix()
    except ValueError:
        return path.name


def _is_noise(filename: str) -> bool:
    rel = _display_path(filename)
    return rel in _NOISE_FILES or rel.startswith("app/middleware/")


def _iter_exceptions(exc: BaseException) -> list[BaseException]:
    """展开 ExceptionGroup 和 cause。context 里多半是中间件包装，不跟。"""
    seen: set[int] = set()
    ordered: list[BaseException] = []
    pending: list[BaseException | None] = [exc]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, BaseExceptionGroup):
            pending.extend(reversed(current.exceptions))
            continue
        ordered.append(current)
        pending.append(current.__cause__)
    return ordered


def _exc_text(exc: BaseException) -> str:
    # SQLAlchemy 的 str() 会把 SQL 再拼一遍，这里只用原始说明，SQL 单独输出。
    message = getattr(exc, "_message", None)
    text = message() if callable(message) else str(exc)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    body = "\n".join(lines) if lines else ""
    return f"{type(exc).__name__}: {body}" if body else type(exc).__name__


def _raised_frame(exc: BaseException) -> traceback.FrameSummary | None:
    frames = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
    app_frames = [frame for frame in frames if _is_app_file(frame.filename)]
    business = [frame for frame in app_frames if not _is_noise(frame.filename)]
    chosen = business or app_frames or frames
    return chosen[-1] if chosen else None


def _select_exception(exceptions: list[BaseException]) -> BaseException:
    business: list[BaseException] = []
    in_app: list[BaseException] = []
    for item in exceptions:
        frame = _raised_frame(item)
        if frame is None or not _is_app_file(frame.filename):
            continue
        if _is_noise(frame.filename):
            in_app.append(item)
        else:
            business.append(item)
    if business:
        return business[-1]
    if in_app:
        return in_app[-1]
    return exceptions[-1]


def _location(exc: BaseException) -> list[str]:
    frame = _raised_frame(exc)
    if frame is None:
        return []
    lines = [f"位置: {_display_path(frame.filename)}:{frame.lineno}  {frame.name}"]
    if frame.line:
        lines.append(f"    {frame.line.strip()}")
    return lines


def _sql_lines(exceptions: list[BaseException]) -> list[str]:
    for exc in reversed(exceptions):
        statement = getattr(exc, "statement", None)
        if not statement:
            continue
        lines = [f"SQL: {statement}"]
        params = getattr(exc, "params", None)
        if params is not None and not getattr(exc, "hide_parameters", False):
            rendered = repr(params)
            if len(rendered) > _PARAMS_LIMIT:
                rendered = rendered[:_PARAMS_LIMIT] + "...(truncated)"
            lines.append(f"参数: {rendered}")
        return lines
    return []


def format_app_error(exc: BaseException) -> str:
    """只保留项目代码里的出错位置；有 SQL 时把语句和参数附上。"""
    exceptions = _iter_exceptions(exc) or [exc]
    target = _select_exception(exceptions)

    lines = [_exc_text(target), *_location(target), *_sql_lines(exceptions)]
    label = _request_label.get()
    if label:
        lines.insert(0, label)
    return "\n".join(lines)


class _ConciseErrorFilter(logging.Filter):
    """Uvicorn 会把冒泡出来的异常打成完整堆栈。这里换成一行位置说明。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if not record.exc_info or record.exc_info[1] is None:
            return True
        try:
            brief = format_app_error(record.exc_info[1])
        except Exception:
            return True
        _request_label.set("")
        record.msg = brief
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def install_concise_error_log() -> None:
    error_logger = logging.getLogger("uvicorn.error")
    if any(isinstance(item, _ConciseErrorFilter) for item in error_logger.filters):
        return
    error_logger.addFilter(_ConciseErrorFilter())


def register_exception_handlers(app: FastAPI) -> None:
    """把校验失败、HTTPException 和未捕获异常都收成 {code, msg, data}。"""
    install_concise_error_log()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=error_content(422, _validation_message(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            msg, data = detail, None
        else:
            msg, data = "请求失败", detail
        return JSONResponse(
            status_code=exc.status_code,
            content=error_content(exc.status_code, msg, data),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # 路径交给日志过滤器。Uvicorn 随后还会再记一次，过滤器会收成同一条短日志。
        _request_label.set(f"{request.method} {request.url.path}")
        return JSONResponse(status_code=500, content=error_content(500, "服务器内部错误"))
