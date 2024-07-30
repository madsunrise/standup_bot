import zoneinfo
from datetime import datetime, timezone

import pytz
from pytz import tzinfo


def with_zone_same_instant(datetime_obj: datetime, timezone_to: tzinfo) -> datetime:
    return datetime_obj.astimezone(timezone_to)


def to_string(datetime_obj: datetime, pattern: str) -> str:
    return datetime_obj.strftime(pattern)


def get_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def get_moscow_time() -> datetime:
    return datetime.now(get_moscow_zone())


def get_moscow_zone() -> zoneinfo:
    return pytz.timezone('Europe/Moscow')
