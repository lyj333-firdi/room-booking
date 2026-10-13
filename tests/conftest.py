"""固定測試資料，對應 SQA 測試計畫「測試環境與固定測試資料」一節。"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.modules.calendar.rules import TZ, Calendar, Room, RoomType

# 基準時間：2026-11-02（週一）09:00
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=TZ)

# 虛構的測試假日，不代表真實國定假日
TEST_HOLIDAY = date(2026, 11, 11)


def at(day: str, hhmm: str) -> datetime:
    """把 '2026-11-03' 與 '09:30' 組成 Asia/Taipei 的 datetime。"""
    y, m, d = (int(x) for x in day.split("-"))
    hh, mm = (int(x) for x in hhmm.split(":"))
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


@pytest.fixture
def cal() -> Calendar:
    return Calendar(holidays={TEST_HOLIDAY})


@pytest.fixture
def rooms() -> dict[str, Room]:
    return {
        "R-L": Room(id=1, name="R-L", room_type=RoomType.LARGE, capacity=60),
        "R-M1": Room(id=2, name="R-M1", room_type=RoomType.MEDIUM, capacity=20),
        "R-M2": Room(id=3, name="R-M2", room_type=RoomType.MEDIUM, capacity=20),
        "R-S1": Room(id=4, name="R-S1", room_type=RoomType.SMALL, capacity=5),
        "R-S2": Room(id=5, name="R-S2", room_type=RoomType.SMALL, capacity=5),
    }
