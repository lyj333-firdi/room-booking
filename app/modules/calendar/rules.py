"""calendar 模組：所有日期與時段規則集中於此（PIS「calendar 模組」一節）。

本檔只做純計算，不碰資料庫：假日、休館紀錄由呼叫端查好後傳入，
方便單元測試固定資料，也讓服務層只用一套規則。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.errors import SlotRuleError

TZ = ZoneInfo("Asia/Taipei")

MORNING = (time(8, 30), time(12, 30))
AFTERNOON = (time(13, 30), time(17, 30))
HOLD_CUTOFF = time(17, 30)  # 保留期限當天的截止時刻

STAFF_WINDOW_DAYS = 90
EXTERNAL_MIN_DAYS = 14
EXTERNAL_MAX_DAYS = 180
CANCEL_DEADLINE_WORKDAYS = 3


class RoomType(StrEnum):
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class Role(StrEnum):
    STAFF = "staff"
    MEMBER = "member"
    ADMIN = "admin"
    GUEST = "guest"  # 非會員廠商，經洽詢轉預約時使用


EXTERNAL_ROLES = frozenset({Role.MEMBER, Role.GUEST})

UNIT_MINUTES = {RoomType.LARGE: 240, RoomType.MEDIUM: 60, RoomType.SMALL: 30}
GRACE_MINUTES = {RoomType.LARGE: 30, RoomType.MEDIUM: 15, RoomType.SMALL: 10}
UNIT_LABEL = {RoomType.LARGE: "4 小時", RoomType.MEDIUM: "1 小時", RoomType.SMALL: "30 分鐘"}
TYPE_LABEL = {RoomType.LARGE: "大型", RoomType.MEDIUM: "中型", RoomType.SMALL: "小型"}

# 大型會議室只能借上午、下午或全天
LARGE_ALLOWED = {
    MORNING,
    AFTERNOON,
    (MORNING[0], AFTERNOON[1]),
}


@dataclass(frozen=True)
class Room:
    id: int
    name: str
    room_type: RoomType
    capacity: int
    external_allowed: bool = True
    status: str = "open"


@dataclass(frozen=True)
class Closure:
    room_id: int
    start: datetime
    end: datetime


def _local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("時間必須帶時區，避免把 UTC 誤當台灣時間")
    return dt.astimezone(TZ)


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def count_units(room_type: RoomType, start: datetime, end: datetime) -> int:
    """計算預約占用的單位數；大型全天會扣掉午休 1 小時，得到 2 單位。"""
    s, e = _local(start).time(), _local(end).time()
    total = _minutes(e) - _minutes(s)
    lunch_overlap = max(0, min(_minutes(e), _minutes(AFTERNOON[0])) - max(_minutes(s), _minutes(MORNING[1])))
    return (total - lunch_overlap) // UNIT_MINUTES[room_type]


class Calendar:
    """工作天與時段規則。holidays 含國定假日與臨時休館日（holidays 資料表的全部日期）。"""

    def __init__(self, holidays: Iterable[date]) -> None:
        self._holidays = frozenset(holidays)

    def is_workday(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self._holidays

    def add_workdays(self, d: date, n: int) -> date:
        """從 d 往後（n > 0）或往前（n < 0）數第 |n| 個工作天；d 本身不計。n = 0 回傳 d。"""
        step = 1 if n > 0 else -1
        remaining = abs(n)
        while remaining:
            d += timedelta(days=step)
            if self.is_workday(d):
                remaining -= 1
        return d

    def cancel_deadline(self, use_day: date) -> date:
        """外部使用者可自行取消或改期的最後一天（當天 23:59:59 前）。"""
        return self.add_workdays(use_day, -CANCEL_DEADLINE_WORKDAYS)

    def hold_deadline(self, from_day: date, n: int) -> datetime:
        """待確認（n=3）或待繳押金（n=5）的保留期限。"""
        return datetime.combine(self.add_workdays(from_day, n), HOLD_CUTOFF, tzinfo=TZ)

    def validate_slot(
        self,
        room: Room,
        start: datetime,
        end: datetime,
        *,
        role: Role,
        headcount: int,
        now: datetime,
        closures: Iterable[Closure] = (),
    ) -> None:
        """依 PIS 規定的順序檢查，第一個不符即拋出 SlotRuleError。"""
        start, end, now = _local(start), _local(end), _local(now)
        s, e = start.time(), end.time()
        day = start.date()

        # 1. 同一天、結束晚於開始、開始晚於現在
        if end.date() != day or end <= start or start <= now:
            raise SlotRuleError("E-02")

        # 2. 開放日、會議室開放、無休館
        if not self.is_workday(day) or room.status != "open":
            raise SlotRuleError("E-02")
        for c in closures:
            if c.room_id == room.id and _local(c.start) < end and start < _local(c.end):
                raise SlotRuleError("E-02")

        # 3. 落在上午或下午時段內；大型全天是唯一可跨午休的情況
        in_morning = MORNING[0] <= s and e <= MORNING[1]
        in_afternoon = AFTERNOON[0] <= s and e <= AFTERNOON[1]
        large_full_day = room.room_type == RoomType.LARGE and (s, e) == (MORNING[0], AFTERNOON[1])
        if not (in_morning or in_afternoon or large_full_day):
            raise SlotRuleError("E-05")

        # 4. 對齊單位：中型從 08:30／13:30 起算整點，所以都落在「半」的時刻
        if room.room_type == RoomType.LARGE:
            aligned = (s, e) in LARGE_ALLOWED
        else:
            session_start = MORNING[0] if in_morning else AFTERNOON[0]
            unit = UNIT_MINUTES[room.room_type]
            aligned = all((_minutes(t) - _minutes(session_start)) % unit == 0 for t in (s, e))
        if not aligned:
            raise SlotRuleError(
                "E-04",
                f"{TYPE_LABEL[room.room_type]}會議室以 {UNIT_LABEL[room.room_type]}為單位，請調整開始或結束時間。",
            )

        # 5. 容量
        if headcount > room.capacity:
            raise SlotRuleError("E-06", f"此會議室最多 {room.capacity} 人，請改選較大的會議室。")

        # 6. 依身分的可預約期間（日曆天）
        days_ahead = (day - now.date()).days
        if role in EXTERNAL_ROLES:
            if not EXTERNAL_MIN_DAYS <= days_ahead <= EXTERNAL_MAX_DAYS:
                raise SlotRuleError(
                    "E-07", f"外部預約只能選第 {EXTERNAL_MIN_DAYS} 至 {EXTERNAL_MAX_DAYS} 天的時段。"
                )
        elif not 0 <= days_ahead <= STAFF_WINDOW_DAYS:
            raise SlotRuleError("E-07", f"員工只能預約今天起 {STAFF_WINDOW_DAYS} 天內的時段。")

        # 7. 外部預約須為開放外部的會議室
        if role in EXTERNAL_ROLES and not room.external_allowed:
            raise SlotRuleError("E-02", "此會議室不開放外部借用。")

    def list_slots(self, room_type: RoomType, day: date) -> list[tuple[datetime, datetime]]:
        """產生該房型當天的時段格子（供 U-03 總覽）；非工作天回傳空清單。"""
        if not self.is_workday(day):
            return []
        unit = timedelta(minutes=UNIT_MINUTES[room_type])
        slots = []
        for begin, finish in (MORNING, AFTERNOON):
            cur = datetime.combine(day, begin, tzinfo=TZ)
            stop = datetime.combine(day, finish, tzinfo=TZ)
            while cur + unit <= stop:
                slots.append((cur, cur + unit))
                cur += unit
        return slots
