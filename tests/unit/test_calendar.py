"""calendar 單元測試，編號對應 SQA 測試計畫 CAL-01 至 CAL-38。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time

import pytest

from app.errors import SlotRuleError
from app.modules.calendar.rules import TZ, Closure, Role, RoomType, count_units
from tests.conftest import NOW, at


# ---------- 工作天與單位 ----------

@pytest.mark.parametrize(
    "case, day, expected",
    [
        ("CAL-01", date(2026, 11, 2), True),
        ("CAL-02", date(2026, 11, 7), False),   # 週六
        ("CAL-03", date(2026, 11, 11), False),  # 測試假日
    ],
)
def test_is_workday(cal, case, day, expected):
    assert cal.is_workday(day) is expected, case


@pytest.mark.parametrize(
    "case, start, n, expected",
    [
        ("CAL-04", date(2026, 11, 6), 1, date(2026, 11, 9)),    # 跳過週末
        ("CAL-05", date(2026, 11, 10), 1, date(2026, 11, 12)),  # 跳過假日
    ],
)
def test_add_workdays(cal, case, start, n, expected):
    assert cal.add_workdays(start, n) == expected, case


@pytest.mark.parametrize(
    "case, use_day, expected",
    [
        ("CAL-06", date(2026, 11, 13), date(2026, 11, 9)),   # 往前跳過假日
        ("CAL-07", date(2026, 11, 30), date(2026, 11, 25)),
    ],
)
def test_cancel_deadline(cal, case, use_day, expected):
    assert cal.cancel_deadline(use_day) == expected, case


@pytest.mark.parametrize(
    "case, n, expected",
    [
        ("CAL-08", 3, datetime(2026, 11, 5, 17, 30, tzinfo=TZ)),
        ("CAL-09", 5, datetime(2026, 11, 9, 17, 30, tzinfo=TZ)),
    ],
)
def test_hold_deadline(cal, case, n, expected):
    assert cal.hold_deadline(date(2026, 11, 2), n) == expected, case


@pytest.mark.parametrize(
    "case, room_type, start, end, expected",
    [
        ("CAL-10", RoomType.LARGE, "08:30", "17:30", 2),
        ("CAL-11", RoomType.LARGE, "13:30", "17:30", 1),
        ("CAL-12", RoomType.MEDIUM, "09:30", "12:30", 3),
        ("CAL-13", RoomType.SMALL, "13:30", "14:30", 2),
    ],
)
def test_count_units(case, room_type, start, end, expected):
    day = "2026-11-03"
    assert count_units(room_type, at(day, start), at(day, end)) == expected, case


# ---------- validate_slot ----------
# (編號, 會議室, 日期, 開始, 結束, 人數, 角色, 預期錯誤碼；None 代表通過)
SLOT_CASES = [
    ("CAL-14", "R-M1", "2026-11-03", "09:30", "10:30", 10, Role.STAFF, None),
    ("CAL-15", "R-M1", "2026-11-07", "09:30", "10:30", 4, Role.STAFF, "E-02"),
    ("CAL-16", "R-M1", "2026-11-11", "09:30", "10:30", 4, Role.STAFF, "E-02"),
    ("CAL-17", "R-S1", "2026-11-02", "08:30", "09:00", 4, Role.STAFF, "E-02"),
    ("CAL-20", "R-M1", "2026-11-03", "11:30", "13:30", 4, Role.STAFF, "E-05"),
    ("CAL-21", "R-S1", "2026-11-03", "17:00", "18:00", 4, Role.STAFF, "E-05"),
    ("CAL-22", "R-L", "2026-11-03", "08:30", "17:30", 4, Role.STAFF, None),
    ("CAL-23", "R-L", "2026-11-03", "13:30", "17:30", 4, Role.STAFF, None),
    ("CAL-24", "R-L", "2026-11-03", "10:30", "12:30", 4, Role.STAFF, "E-04"),
    ("CAL-25", "R-M1", "2026-11-03", "09:00", "10:00", 4, Role.STAFF, "E-04"),
    ("CAL-26", "R-S1", "2026-11-03", "09:00", "09:30", 4, Role.STAFF, None),
    ("CAL-27", "R-S1", "2026-11-03", "09:15", "09:45", 4, Role.STAFF, "E-04"),
    ("CAL-28", "R-S1", "2026-11-03", "09:00", "09:30", 5, Role.STAFF, None),
    ("CAL-29", "R-S1", "2026-11-03", "09:00", "09:30", 6, Role.STAFF, "E-06"),
    ("CAL-30", "R-M1", "2026-11-03", "09:30", "10:30", 21, Role.STAFF, "E-06"),
    ("CAL-31", "R-M1", "2027-01-29", "09:30", "10:30", 4, Role.STAFF, None),
    ("CAL-32", "R-M1", "2027-02-01", "09:30", "10:30", 4, Role.STAFF, "E-07"),
    ("CAL-33", "R-M1", "2026-11-13", "09:30", "10:30", 4, Role.MEMBER, "E-07"),
    ("CAL-34", "R-M1", "2026-11-16", "09:30", "10:30", 4, Role.MEMBER, None),
    ("CAL-35", "R-M1", "2027-04-30", "09:30", "10:30", 4, Role.MEMBER, None),
    ("CAL-36", "R-M1", "2027-05-03", "09:30", "10:30", 4, Role.MEMBER, "E-07"),
    ("CAL-38", "R-M1", "2026-11-07", "11:30", "13:30", 30, Role.STAFF, "E-02"),
]


@pytest.mark.parametrize("case, room, day, start, end, headcount, role, expected", SLOT_CASES)
def test_validate_slot(cal, rooms, case, room, day, start, end, headcount, role, expected):
    call = lambda: cal.validate_slot(
        rooms[room], at(day, start), at(day, end), role=role, headcount=headcount, now=NOW
    )
    if expected is None:
        call()
    else:
        with pytest.raises(SlotRuleError) as exc:
            call()
        assert exc.value.code == expected, case


def test_cal18_suspended_room(cal, rooms):
    room = replace(rooms["R-M1"], status="suspended")
    with pytest.raises(SlotRuleError) as exc:
        cal.validate_slot(room, at("2026-11-03", "09:30"), at("2026-11-03", "10:30"),
                          role=Role.STAFF, headcount=4, now=NOW)
    assert exc.value.code == "E-02"


def test_cal19_closure_overlap(cal, rooms):
    closure = Closure(room_id=rooms["R-M1"].id,
                      start=at("2026-11-03", "08:30"), end=at("2026-11-03", "12:30"))
    with pytest.raises(SlotRuleError) as exc:
        cal.validate_slot(rooms["R-M1"], at("2026-11-03", "09:30"), at("2026-11-03", "10:30"),
                          role=Role.STAFF, headcount=4, now=NOW, closures=[closure])
    assert exc.value.code == "E-02"


def test_cal37_room_not_open_to_external(cal, rooms):
    room = replace(rooms["R-L"], external_allowed=False)
    with pytest.raises(SlotRuleError) as exc:
        cal.validate_slot(room, at("2026-11-16", "08:30"), at("2026-11-16", "12:30"),
                          role=Role.MEMBER, headcount=4, now=NOW)
    assert exc.value.code == "E-02"


def test_closure_of_other_room_does_not_block(cal, rooms):
    """補充：其他會議室的休館紀錄不影響本房（防止 room_id 比對漏寫）。"""
    closure = Closure(room_id=rooms["R-M2"].id,
                      start=at("2026-11-03", "08:30"), end=at("2026-11-03", "12:30"))
    cal.validate_slot(rooms["R-M1"], at("2026-11-03", "09:30"), at("2026-11-03", "10:30"),
                      role=Role.STAFF, headcount=4, now=NOW, closures=[closure])


def test_naive_datetime_rejected(cal, rooms):
    """補充：沒有時區的時間一律拒絕，避免把 UTC 誤當台灣時間。"""
    with pytest.raises(ValueError):
        cal.validate_slot(rooms["R-M1"], datetime(2026, 11, 3, 9, 30), datetime(2026, 11, 3, 10, 30),
                          role=Role.STAFF, headcount=4, now=NOW)


@pytest.mark.parametrize(
    "room_type, day, expected_count",
    [
        (RoomType.LARGE, date(2026, 11, 3), 2),
        (RoomType.MEDIUM, date(2026, 11, 3), 8),
        (RoomType.SMALL, date(2026, 11, 3), 16),
        (RoomType.MEDIUM, date(2026, 11, 7), 0),   # 週六
    ],
)
def test_list_slots(cal, room_type, day, expected_count):
    """補充：每日單位數須與 MRS 表一致（大型 2、中型 8、小型 16）。"""
    slots = cal.list_slots(room_type, day)
    assert len(slots) == expected_count
    assert all(not (s.time() < time(13, 30) and e.time() > time(12, 30)) for s, e in slots)
