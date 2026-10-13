"""billing 與統一編號單元測試，編號對應 SQA 測試計畫 BIL-01 至 BIL-15、TAX-01 至 TAX-07。"""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.billing.pricing import calc_cancellation, charge_for
from app.modules.calendar.rules import Role, RoomType
from app.modules.members.tax_id import is_valid_tax_id


# ---------- 金額試算 ----------

@pytest.mark.parametrize(
    "case, role, room_type, units, rent, deposit, balance",
    [
        ("BIL-01", Role.MEMBER, RoomType.LARGE, 2, 8000, 800, 7200),
        ("BIL-02", Role.GUEST, RoomType.LARGE, 1, 5000, 500, 4500),
        ("BIL-03", Role.GUEST, RoomType.LARGE, 2, 10000, 1000, 9000),
        ("BIL-04", Role.MEMBER, RoomType.MEDIUM, 3, 1920, 192, 1728),
        ("BIL-05", Role.MEMBER, RoomType.MEDIUM, 1, 640, 64, 576),
        ("BIL-06", Role.MEMBER, RoomType.SMALL, 1, 160, 16, 144),
    ],
)
def test_charge_for(case, role, room_type, units, rent, deposit, balance):
    c = charge_for(role, room_type, units)
    assert (c.rent, c.deposit, c.balance) == (rent, deposit, balance), case


def test_bil07_staff_has_no_charge():
    assert charge_for(Role.STAFF, RoomType.LARGE, 2) is None


# ---------- calc_cancellation ----------
# 共用條件：R-M1 3 小時，rent 1,920，deposit 192，使用日 2026-11-30
USE_DAY = date(2026, 11, 30)
RENT, DEPOSIT = 1920, 192


@pytest.mark.parametrize(
    "case, status, paid, cancel_day, force, expected",
    [
        ("BIL-08", "booked", 192, date(2026, 11, 16), False, (0, 192, 0)),
        ("BIL-09", "booked", 192, date(2026, 11, 17), False, (192, 0, 0)),
        ("BIL-10", "booked", 192, date(2026, 11, 25), False, (192, 0, 0)),
        ("BIL-11", "booked", 192, date(2026, 11, 26), False, (1920, 0, 1728)),
        ("BIL-12", "no_show", 1920, date(2026, 11, 30), False, (1920, 0, 0)),
        ("BIL-13", "booked", 1920, date(2026, 11, 27), True, (0, 1920, 0)),
        ("BIL-14", "booked", 1920, date(2026, 11, 16), False, (0, 1920, 0)),
        ("BIL-15", "awaiting_deposit", 0, date(2026, 11, 17), False, (0, 0, 0)),
    ],
)
def test_calc_cancellation(cal, case, status, paid, cancel_day, force, expected):
    r = calc_cancellation(
        cal, status=status, rent=RENT, deposit=DEPOSIT, paid=paid,
        use_day=USE_DAY, cancel_day=cancel_day, force_majeure=force,
    )
    assert (r.retained, r.refund, r.receivable) == expected, case


# ---------- 統一編號 ----------

@pytest.mark.parametrize(
    "case, tax_id, expected",
    [
        ("TAX-01", "04595252", True),   # 財政部測試號，新制才有效
        ("TAX-02", "10458570", True),   # 財政部測試號，第 7 碼為 7
        ("TAX-03", "12345675", True),
        ("TAX-04", "12345678", False),
        ("TAX-05", "00000000", False),
        ("TAX-06", "1234567", False),
        ("TAX-07", "1234567A", False),
    ],
)
def test_tax_id(case, tax_id, expected):
    assert is_valid_tax_id(tax_id) is expected, case


def test_fullwidth_digits_rejected():
    """補充：全形數字 str.isdigit() 也是 True，須另外擋下。"""
    assert is_valid_tax_id("０４５９５２５２") is False
