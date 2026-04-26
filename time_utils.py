from __future__ import annotations

from datetime import datetime


def local_now() -> datetime:
    return datetime.now().astimezone()


def naive_local_now() -> datetime:
    return local_now().replace(tzinfo=None)


def ensure_local_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=local_now().tzinfo)
    return value.astimezone()
