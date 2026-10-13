# 會議室預約系統（AI 課程練習）

依 MRS → PES → SW Arch → PIS → SQA 流程開發。本版（v0.1）包含三個純計算模組與其單元測試，
尚未有資料庫、網頁與排程。不使用 Docker。

## 目前內容

| 路徑 | 內容 | 對應文件 |
| --- | --- | --- |
| `app/errors.py` | 業務例外與錯誤碼 | PIS「錯誤處理」 |
| `app/modules/calendar/rules.py` | 工作天、保留與取消期限、單位計算、時段檢查 | PIS「calendar 模組」 |
| `app/modules/billing/pricing.py` | 租金、押金（10%）、取消退費 | PIS「billing 模組」 |
| `app/modules/members/tax_id.py` | 統一編號檢核（財政部 112 年 4 月新制） | PIS「members 模組」 |
| `tests/unit/` | CAL-01～38、BIL-01～15、TAX-01～07，另加補充測試 | SQA 測試計畫 |
| `.github/workflows/ci.yml` | 推上 GitHub 後自動執行單元測試（Python 3.11、3.12） | SW Arch「部署與開發環境」 |
| `.env.example` | 環境變數範本，後續模組使用 | SW Arch「部署與開發環境」 |

## 本機執行測試

需要 Python 3.11 以上。

```bash
python -m venv .venv
# Windows：.venv\Scripts\activate　　macOS／Linux：source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=app --cov-report=term-missing
```

## 推上 GitHub

1. 在 GitHub 建立一個空的儲存庫（不要勾選自動產生 README）。
2. 在專案資料夾執行（把網址換成你的儲存庫）：

   ```bash
   git init
   git add .
   git commit -m "初版：calendar、billing、統編檢核與單元測試"
   git branch -M main
   git remote add origin https://github.com/<帳號>/<儲存庫名稱>.git
   git push -u origin main
   ```

3. 到儲存庫的 Actions 頁籤，確認 CI 執行成功（綠色勾勾）。

`.env` 已列入 `.gitignore`；密碼只放在自己電腦的 `.env`，不要寫進程式碼或 `.env.example`。

## 設計說明

- `Calendar` 不直接查資料庫，假日與休館紀錄由呼叫端傳入，所以單元測試可以固定資料。
- 所有時間都必須帶時區；沒有時區的 datetime 會拋出 `ValueError`。
- 角色 `guest` 代表非會員廠商（經洽詢轉預約），計費不打折。

## 下一步

1. 在本機安裝 PostgreSQL，建立 `room_booking` 與 `room_booking_test` 兩個資料庫，並在兩者執行 `CREATE EXTENSION btree_gist;`。
2. 加入資料表（Alembic）與 bookings 模組，實作整合測試 INT-01～30。
3. 在 CI 加上整合測試工作，使用 GitHub Actions 提供的 PostgreSQL 服務。
