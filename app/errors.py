"""業務例外。錯誤碼與訊息對應 PES「錯誤訊息與驗證規則」一節。"""

from __future__ import annotations


class BusinessError(Exception):
    """所有業務例外的基底類別；路由層依 code 轉成畫面訊息與 HTTP 狀態碼。"""

    code: str = ""
    default_message: str = ""

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class SlotRuleError(BusinessError):
    """calendar.validate_slot 檢查失敗（E-02、E-04 至 E-07）。"""

    MESSAGES = {
        "E-02": "此時段不開放（週末、國定假日、休館或午休）。",
        "E-04": "時間未對齊會議室的預約單位，請調整開始或結束時間。",
        "E-05": "預約不可跨越 12:30–13:30，請分成兩筆。",
        "E-06": "人數超過此會議室容量，請改選較大的會議室。",
        "E-07": "超出可預約期間。",
    }

    def __init__(self, code: str, message: str | None = None) -> None:
        if code not in self.MESSAGES:
            raise ValueError(f"未定義的時段錯誤碼：{code}")
        self.code = code
        super().__init__(message or self.MESSAGES[code])
