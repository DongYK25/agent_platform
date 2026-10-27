import uuid

from toollib.utils import now2timestamp


def gen_uuid_hex() -> str:
    return uuid.uuid4().hex


def now_timestamp() -> int:
    return now2timestamp()  # type: ignore
