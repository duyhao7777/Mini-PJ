# Hướng dẫn vận hành toàn dự án (A → B → C)

**Windows + macOS · Docker Compose**

```
10 CSV (data/) → Mage ingest → stg.* → dbt → dw.fact_sales → ai.kpi_* → 4 view ai.v_*
                                      │                          │
                              Power BI (A+)              Streamlit Q&A (C)
                              AI summary (B)
```

Thứ tự: **A → A+ → B → C**. Lệnh `docker compose ...` chạy giống hệt trên Windows PowerShell lẫn macOS zsh; chỉ mục 1.1 có 2 bản cài tool.

---

## 1. Chuẩn bị

### 1.1 Cài tool

**macOS (zsh)**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install --cask docker visual-studio-code tableplus
brew install git python@3.11
open -a Docker
```

**Windows (PowerShell)**
```powershell
winget install Docker.DockerDesktop
winget install Microsoft.VisualStudioCode
winget install TablePlus.TablePlus
winget install Git.Git
winget install Python.Python.3.11
# Mở Docker Desktop từ Start Menu
```

Docker Desktop → **Settings → Resources** → RAM ≥ 6GB, Disk ≥ 40GB.

### 1.2 Tạo `.env`

**macOS**
```bash
cd ~/Documents/Code/Mini-PJ
cp .env.example .env
chmod 600 .env
```

**Windows PowerShell**
```powershell
cd $HOME\Documents\Code\Mini-PJ
Copy-Item .env.example .env
```

Mở `.env`, điền `GEMINI_API_KEY` (https://aistudio.google.com/app/apikey):
```
MSSQL_PASSWORD=AdventureBI@2026
GEMINI_API_KEY=thay_bang_key_that
GEMINI_MODEL=gemini-3.5-flash-lite
```

Compose tự đọc `.env`, không cần `source`. 10 file CSV đã có sẵn trong `data/`. `compose.yaml` dùng `mcr.microsoft.com/azure-sql-edge` cho cả Win lẫn Mac; Compose tự pull.

### 1.3 TablePro
New Connection → SQL Server → `localhost,1433` / `sa` / `AdventureBI@2026` → bật **Trust server certificate**.

---

## 2. Khởi động

```bash
cd Mini-PJ
docker compose --env-file .env up -d --build
docker compose ps
docker compose logs -f sqlserver      # thấy "SQL Server is now ready..." thì Ctrl+C
```

Nếu máy đã có container chạy bằng `docker run` cùng tên:
```bash
docker rm -f sqlserver mage qa
docker compose --env-file .env up -d --build
```

Mở trình duyệt: **Mage** `http://localhost:6789` · **Q&A** `http://localhost:8501`.

---

## 3. PHẦN A — ETL & Data Warehouse

### 3.1 Khởi tạo DB
```bash
docker compose exec mage python /home/src/scripts/init_db_via_mage.py
```
7 file SQL → `SCHEMAS: ai, dw, etl, stg`.

> Sau khi ingest, chỉ chạy lại **có đối số**: `docker compose exec mage python /home/src/scripts/init_db_via_mage.py 06_create_ai_qa_views.sql`.

### 3.2 Ingestion

#### Cách A — CLI (1 lệnh)
```bash
docker compose exec mage python /home/src/scripts/run_ingest.py
```
Log: `calendar: 912 rows` … `territory: 10 rows` … `Đã nạp 56046 dòng vào stg.sales` … `INGEST DONE`.

#### Cách B — Bấm ▶ trong Mage

**Bước 0.** Mở `http://localhost:6789` → sidebar trái → **Pipelines**.

**Bước 1 — `ingest_lookups_full`**
1. Click pipeline **`ingest_lookups_full`**.
2. Click block **`full_load_lookups`**.
3. Bấm **▶ Execute block** (hoặc **Execute pipeline** trên thanh công cụ).
4. Đợi log hiện `calendar: 912 rows` … `territory: 10 rows` và badge **SUCCESS**.

**Bước 2 — `ingest_sales`** *(tuỳ chọn, tạo `stg.sales_raw` làm bằng chứng trùng lặp)*
1. **Pipelines** → `ingest_sales` → block **`full_load_sales`** → **▶ Execute block**.

**Bước 3 — `ingest_sales_incremental`**
1. **Pipelines** → click **`ingest_sales_incremental`**.
2. Click block **`load_sales_batch`** → **▶ Execute block**.
3. Log: `Trích xuất 56046 dòng` → `Đã nạp 56046 dòng vào stg.sales` → `SUCCESS`.
4. Bấm **1 lần** là đủ.

**Bước 4 — Kiểm tra** trong TablePlus:
```sql
SELECT COUNT(*) FROM stg.sales;   -- 56046
SELECT run_id, load_type, status, rows_inserted FROM etl.pipeline_run_log ORDER BY run_id;
```

### 3.3 dbt
```bash
docker compose exec qa dbt run  --project-dir /home/src/adventureworks_dw --profiles-dir /home/src/adventureworks_dw
docker compose exec qa dbt test --project-dir /home/src/adventureworks_dw --profiles-dir /home/src/adventureworks_dw
```
`dbt run` = 14 model (8 view `dw_staging` + 6 bảng `dw`), `dbt test` = 39 test.

### 3.4 Trigger & log
`adventureworks_bi/triggers.yaml`: `etl_master_demo_10min` (`*/10 * * * *`, active), `etl_master_daily_prod` (`0 2 * * *`, inactive), retry 3 lần, UTC+7. Pipeline `etl_master` gồm 4 block fail-fast: `master_step1_sales` → `master_step2_dbt_run` → `master_step3_dbt_test` → `master_step4_ai_explain`.

3 bảng nối qua `run_id`: `etl.pipeline_run_log` (1–*) `etl.pipeline_run_detail`, (1–1) `etl.run_ai_summary`.

Để có dữ liệu cho Power BI: **Pipelines → `ai_explain_etl_runs` → Execute pipeline** (4 block: `load_unexplained_runs` → `build_ai_prompts` → `call_llm_explain` → `save_ai_summaries`).

### 3.5 Power BI

1. Mở `powerbi/AdventureWorks_BI_Dashboard.pbix` (Power BI Desktop, có trên Windows).
2. **Get Data → SQL Server** → `localhost,1433` / `BI_AdventureWorks` → chọn `etl.pipeline_run_log`, `etl.pipeline_run_detail`, `etl.run_ai_summary` → **Load**.
3. **Model view**: kéo `pipeline_run_log[run_id]` → `pipeline_run_detail[run_id]` (1–*); `pipeline_run_log[run_id]` → `run_ai_summary[run_id]` (1–1).
4. **DAX query view**: dán `powerbi/ETL_Monitoring_Measures.dax` → **Run** → **Update model: Add new measure**.
5. **Trang ETL Monitoring**: 3 Card (`Total Runs`, `Success Rate %`, `Avg Duration (Seconds)`); Stacked Column (X = `run_id`, Y = `Total Inserted/Updated/Deleted/Rejected`); Table (`run_id`, `started_at`, `error_message`, filter `status = FAILED`); bật **Drill-through** theo `run_id`.
6. **Trang AI Insights**: Multi-row Card `summary_text` + `model_name` đặt cạnh Table KPI gốc.

---

## 4. PHẦN B — AI Business Analytics

### 4.1 Hai model KPI
```bash
docker compose exec qa dbt run  --project-dir /home/src/adventureworks_dw --profiles-dir /home/src/adventureworks_dw --select +kpi_monthly +kpi_by_dim
docker compose exec qa dbt test --project-dir /home/src/adventureworks_dw --profiles-dir /home/src/adventureworks_dw \
  --select kpi_monthly kpi_by_dim assert_ai_kpi_monthly_reconcile assert_ai_by_dim_reconcile assert_ai_by_dim_unique
```
`ai.kpi_monthly` (Sales, Profit, Orders, Units, AOV, MoM/YoY) · `ai.kpi_by_dim` (CATEGORY / TERRITORY / PRODUCT). Kết quả AI lưu ở `ai.analytics_summary`, `ai.insight_explanation`.

### 4.2 Secrets — bấm từng bước
1. `http://localhost:6789` → góc dưới trái ⚙️ **Settings** → **Secrets**.
2. **+ Add secret** → `Name = GEMINI_API_KEY`, `Value = <key trong .env>` → **Save**.
3. **+ Add secret** → `Name = GEMINI_MODEL`, `Value = gemini-3.5-flash-lite` → **Save**.
4. `docker compose restart mage`.

### 4.3 Chạy 2 pipeline AI

**`ai_generate_kpi_summary`**
1. **Pipelines** → click `ai_generate_kpi_summary`.
2. 3 block nối tiếp: `load_pending_kpis` → `generate_kpi_summaries` → `save_kpi_summaries`.
3. Bấm **Execute pipeline** (hoặc ▶ từng block theo đúng thứ tự trên, đợi SUCCESS rồi mới bấm block kế).
4. Log: `Processed 10 AI monthly summaries`.

**`ai_explain_trends`**
1. **Pipelines** → click `ai_explain_trends`.
2. 3 block: `load_trend_candidates` → `explain_business_trends` → `save_trend_explanations`.
3. Bấm **Execute pipeline**.

Mỗi lượt xử lý `TOP 10`; 1 lượt mỗi pipeline = 18 lần gọi Gemini, đủ demo.

Kiểm tra trong TablePlus:
```sql
SELECT month_start, verified, verification_note, summary_text FROM ai.analytics_summary ORDER BY month_start DESC;
SELECT month_start, change_pct, verified, explanation_text FROM ai.insight_explanation ORDER BY month_start DESC;
```

---

## 5. PHẦN C — Q&A

### 5.1 View + tài khoản chỉ đọc
```bash
docker compose exec mage python /home/src/scripts/init_db_via_mage.py 06_create_ai_qa_views.sql
```
4 view `ai.v_kpi_monthly`, `ai.v_kpi_by_dim`, `ai.v_latest_summary`, `ai.v_trend_explain` + login `qa_reader` (chỉ `SELECT` trên 4 view).

### 5.2 App Streamlit — bấm từng bước
1. Mở `http://localhost:8501`.
2. Ô **"Nhập câu hỏi tiếng Việt"** → gõ `Doanh thu tháng 6/2022 là bao nhiêu?`.
3. Bấm **Hỏi**.
4. Màn hình hiện: **1️⃣ Câu SQL được thực thi** → **2️⃣ Kết quả** → **3️⃣ Giải thích** (bản nhận định 5 đoạn).
5. Bấm **`🔎 Lưu ý & kiểm chứng`** (đóng sẵn) để xem badge `✅ Đã đối chiếu` / `⚠️ Cần rà soát`, `verification_note`, JSON thô.
6. Gõ `DROP TABLE ai.kpi_monthly` → **Hỏi** → chỉ hiện 1 thông báo chung, không có SQL.

File: `app/qa_app.py` (UI), `app/qa_core.py` (logic), `app/qa_prompts.py` (prompt), `app/Dockerfile`. Sửa `.py` → `docker compose restart qa`.

---

## 6. Kiểm thử toàn hệ thống

`app/test_questions.md` — 12 câu, ghi `câu hỏi → SQL → số dòng → số chính → giải thích → badge → PASS`:

| Nhóm | Số câu | Ví dụ |
|---|---|---|
| Đối chiếu Power BI | 5 | Doanh thu 06/2022? / tháng cao nhất 2021? / AOV 03/2021? / MoM 05/2022? / YoY 06/2022? |
| Chiều phân tích | 4 | Category đóng góp nhất? / Territory giảm mạnh nhất? / Top 3 product 12/2021? / tháng MoM > 20%? |
| An toàn + rerun | 3 | `Xóa dữ liệu…` / `DROP TABLE…` / hỏi lại 2 lần |

Đối chiếu: `SELECT * FROM ai.kpi_monthly WHERE month_start='2022-06-01'` so với Power BI. Mốc `2022-06`: Sales `3,029,916.14` · Profit `1,444,115.29` · Orders `2,146` · AOV `1,411.89` · MoM `+3.86%`.

```sql
SELECT month_start, COUNT(*) FROM ai.analytics_summary GROUP BY month_start HAVING COUNT(*)>1;   -- rỗng
SELECT month_start, metric_name, comparison_type, COUNT(*) FROM ai.insight_explanation
  GROUP BY month_start, metric_name, comparison_type HAVING COUNT(*)>1;                          -- rỗng
```

---

## 7. Báo cáo + video

`docs/C_QA_Report.md` — điền 3 ô **[ĐIỀN KHI DEMO]** sau khi hỏi thử.

| Thời lượng | Nội dung |
|---|---|
| 0:00–0:30 | Power BI: ETL Monitoring + AI Insights |
| 0:30–1:00 | Q&A câu 1, chỉ vào SQL + bảng + giải thích |
| 1:00–1:30 | Đối chiếu `3,029,916.14` với Power BI |
| 1:30–2:00 | Câu chiều dim + câu `DROP TABLE…` bị chặn |
| 2:00–2:40 | Rerun 2 pipeline + 2 truy vấn `HAVING COUNT(*)>1` |
| 2:40–3:00 | Sơ đồ kiến trúc + 3 hạn chế |

---

## 8. Checklist & lệnh nhanh

- [ ] `.env` có key thật; `docker compose up -d --build` → 3 service `Up`
- [ ] Init DB xong; `stg.sales` = `dw.fact_sales` = 56,046
- [ ] dbt `run` / `test` PASS; Power BI 2 trang dựng xong
- [ ] `ai.kpi_monthly` 30 tháng, `ai.kpi_by_dim` 2,017; 2 pipeline AI chạy xong
- [ ] 4 view `ai.v_*`; `localhost:8501` hỏi được, badge ✅
- [ ] 12 câu test, đối chiếu Power BI, 3 ô `[ĐIỀN KHI DEMO]`, video 3 phút

```bash
docker compose ps
docker compose logs -f qa
docker compose restart qa
docker compose exec mage python /home/src/scripts/init_db_via_mage.py 06_create_ai_qa_views.sql
docker compose down
```
