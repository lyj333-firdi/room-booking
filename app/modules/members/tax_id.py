"""統一編號檢核，依財政部 112 年 4 月起新制：加權位數和可被 5 整除即合法。

參考：財政部財政資訊中心「營利事業統一編號檢查碼邏輯修正說明」
https://www.fia.gov.tw/singlehtml/3?cntId=c4d9cff38c8642ef8872774ee9987283
"""

from __future__ import annotations

WEIGHTS = (1, 2, 1, 2, 1, 2, 4, 1)


def _digit_sum(n: int) -> int:
    # 乘積最大為 9 × 4 = 36，只會有兩位數
    return n // 10 + n % 10


def is_valid_tax_id(tax_id: str) -> bool:
    """檢查 8 碼統一編號；00000000 一律不收，防止個人以空號繞過「不受理個人」規則。"""
    if len(tax_id) != 8 or not tax_id.isascii() or not tax_id.isdigit() or tax_id == "00000000":
        return False
    total = sum(_digit_sum(int(d) * w) for d, w in zip(tax_id, WEIGHTS))
    if total % 5 == 0:
        return True
    # 第 7 碼為 7 時，7 × 4 = 28 的位數和 10 可再化為 1，因此總和加 1 也算合法
    return tax_id[6] == "7" and (total + 1) % 5 == 0
