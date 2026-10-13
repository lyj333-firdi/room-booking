"""billing 模組：租金、押金與取消退費計算（PIS「billing 模組」一節）。

金額一律為含稅整數元，只用整數運算，避免浮點誤差。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.calendar.rules import EXTERNAL_ROLES, Calendar, Role, RoomType

UNIT_PRICE = {RoomType.LARGE: 5000, RoomType.MEDIUM: 800, RoomType.SMALL: 200}  # 非會員單價
MEMBER_DISCOUNT_PCT = 20
DEPOSIT_PCT = 10
FULL_REFUND_DAYS = 14  # 使用日前 14 天（含）以上取消，押金全額退還
UNPAID_STATUSES = frozenset({"pending", "awaiting_deposit"})


@dataclass(frozen=True)
class Charge:
    units: int
    unit_price: int
    discount_pct: int
    rent: int
    deposit: int

    @property
    def balance(self) -> int:
        return self.rent - self.deposit


@dataclass(frozen=True)
class CancellationResult:
    retained: int    # 中心保留的金額（沒收押金或收取租金）
    refund: int      # 應退給客戶
    receivable: int  # 客戶尚欠（保留金額大於已付時）


def charge_for(role: Role, room_type: RoomType, units: int) -> Charge | None:
    """外部預約的費用；內部員工與行政人員免費，回傳 None（不建立 charges 紀錄）。"""
    if role not in EXTERNAL_ROLES:
        return None
    if units <= 0:
        raise ValueError("units 必須大於 0")
    discount = MEMBER_DISCOUNT_PCT if role == Role.MEMBER else 0
    unit_price = UNIT_PRICE[room_type]
    rent = units * unit_price * (100 - discount) // 100
    # 單價皆為 10 的倍數，10% 必為整數
    deposit = rent * DEPOSIT_PCT // 100
    return Charge(units, unit_price, discount, rent, deposit)


def calc_cancellation(
    cal: Calendar,
    *,
    status: str,
    rent: int,
    deposit: int,
    paid: int,
    use_day: date,
    cancel_day: date,
    force_majeure: bool = False,
) -> CancellationResult:
    """依取消時間計算保留、退費與應收金額；判斷順序與 PIS 表格一致。"""
    if force_majeure or status in UNPAID_STATUSES:
        retained = 0
    elif status == "no_show":
        retained = rent
    elif (use_day - cancel_day).days >= FULL_REFUND_DAYS:
        retained = 0
    elif cancel_day <= cal.cancel_deadline(use_day):
        retained = deposit
    else:
        retained = rent
    return CancellationResult(
        retained=retained,
        refund=max(0, paid - retained),
        receivable=max(0, retained - paid),
    )
