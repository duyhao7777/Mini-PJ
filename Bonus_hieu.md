# BÁO CÁO HOÀN THÀNH NHIỆM VỤ & HƯỚNG DẪN VẬN HÀNH HỆ THỐNG
**Phân hệ**: Lập lịch ETL + Báo cáo Giám sát Power BI & Tích hợp AI  
**Người phụ trách**: Hiệu  
**Thời gian hoàn thành**: Tháng 11/2026  

---

## MỤC LỤC
1. [Tổng quan nhiệm vụ & Sản phẩm bàn giao](#1-tổng-quan-nhiệm-vụ--sản-phẩm-bàn-giao)
2. [Chi tiết các task kỹ thuật đã hoàn thành](#2-chi-tiết-các-task-kỹ-thuật-đã-hoàn-thành)
   - [Task 1: Cơ sở dữ liệu & Bảng log chi tiết `pipeline_run_detail`](#task-1-cơ-sở-dữ-liệu--bảng-log-chi-tiết-pipelinerundetail)
   - [Task 2: Khắc phục lỗi `load_type = UNKNOWN` khi pipeline gặp sự cố](#task-2-khắc-phục-lỗi-loadtype--unknown-khi-pipeline-gặp-sự-cố)
   - [Task 3: Chuẩn hóa hạ tầng Docker với `compose.yaml`](#task-3-chuẩn-hóa-hạ-tầng-docker-với-composeyaml)
   - [Task 4: Xây dựng Pipeline tổng điều phối `etl_master` (Fail-Fast)](#task-4-xây-dựng-pipeline-tổng-điều-phối-etlmaster-fail-fast)
   - [Task 5: Cấu hình Trigger tự động hóa (Schedule, Retry, UTC+7)](#task-5-cấu-hình-trigger-tự-động-hóa-schedule-retry-utc7)
   - [Task 6: Bộ chỉ số DAX phục vụ Semantic Model Power BI](#task-6-bộ-chỉ-số-dax-phục-vụ-semantic-model-power-bi)
3. [Hướng dẫn chi tiết quy trình chạy chương trình (End-to-End)](#3-hướng-dẫn-chi-tiết-quy-trình-chạy-chương-trình-end-to-end)
   - [Bước 1: Khởi tạo database và cấu trúc log](#bước-1-khởi-tạo-database-và-cấu-trúc-log)
   - [Bước 2: Khởi động hệ thống với Docker Compose](#bước-2-khởi-động-hệ-thống-với-docker-compose)
   - [Bước 3: Vận hành chuỗi ETL Master](#bước-3-vận-hành-chuỗi-etl-master)
   - [Bước 4: Thiết kế & Cập nhật Dashboard trên Power BI Desktop](#bước-4-thiết-kế--cập-nhật-dashboard-trên-power-bi-desktop)
4. [Kiểm tra đối soát kết quả (Verification Queries)](#4-kiểm-tra-đối-soát-kết-quả-verification-queries)

---

## 1. TỔNG QUAN NHIỆM VỤ & SẢN PHẨM BÀN GIAO

Theo phân công trong dự án BI AdventureWorks, vai trò của bạn là hoàn thiện quy trình điều phối tự động hóa, tăng cường khả năng quan sát vận hành (observability) qua hệ thống log chi tiết và trực quan hóa toàn diện trên Power BI.

### Danh mục sản phẩm cốt lõi đã hoàn thành:
| STT | Tên sản phẩm | Vị trí file trong dự án | Vai trò |
|---|---|---|---|
| 1 | Script SQL Log chi tiết | `sql/05_create_pipeline_run_detail.sql` | Tạo bảng `etl.pipeline_run_detail` và đồng bộ dữ liệu lịch sử |
| 2 | Sửa lỗi Logging Python | `adventureworks_bi/data_loaders/read_etl_control.py`<br>`adventureworks_bi/utils/etl_helpers.py` | Loại bỏ dứt điểm lỗi `load_type = UNKNOWN`, thêm hàm ghi log chi tiết |
| 3 | File Docker Compose | `compose.yaml` | Tự động hóa chạy SQL Server & Mage, cấu hình `restart: unless-stopped` |
| 4 | Pipeline điều phối | `adventureworks_bi/pipelines/etl_master/`<br>`adventureworks_bi/custom/master_step*.py` | Điều phối 4 bước: Ingest $\rightarrow$ dbt run $\rightarrow$ dbt test $\rightarrow$ AI explain (Fail-Fast) |
| 5 | Lập lịch tự động (Triggers) | `adventureworks_bi/triggers.yaml` | Cấu hình chạy lặp demo 10 phút/lần, production hằng ngày, múi giờ UTC+7 |
| 6 | Script chạy Master CLI | `scripts/run_master_pipeline.py` | Cho phép chạy kiểm thử toàn bộ chuỗi từ dòng lệnh mà không phụ thuộc GUI |
| 7 | Bộ công thức DAX | `powerbi/ETL_Monitoring_Measures.dax` | Hơn 10 DAX measures đo lường hiệu năng ETL và hiển thị nhận định AI |

---

## 2. CHI TIẾT CÁC TASK KỸ THUẬT ĐÃ HOÀN THÀNH

### Task 1: Cơ sở dữ liệu & Bảng log chi tiết `pipeline_run_detail`
- **Vấn đề trước đây**: Bảng `etl.pipeline_run_log` chỉ lưu thông tin mức tổng thể theo đợt nạp, thiếu chi tiết theo từng bước nhỏ (bước trích xuất, bước dbt run, bước dbt test, bước AI) và thiếu thông tin số dòng xóa (`rows_deleted`).
- **Giải pháp triển khai**:
  - Viết file `sql/05_create_pipeline_run_detail.sql` tạo bảng `etl.pipeline_run_detail` có liên kết khóa ngoại `FOREIGN KEY (run_id) REFERENCES etl.pipeline_run_log(run_id) ON DELETE CASCADE`.
  - Thiết lập chỉ mục `IX_pipeline_run_detail_run_id` tối ưu truy vấn join.
  - Tích hợp sẵn đoạn truy vấn tự động đồng bộ (backfill) dữ liệu từ `pipeline_run_log` sang `pipeline_run_detail` để phục vụ demo Power BI có số liệu ngay.

### Task 2: Khắc phục lỗi `load_type = UNKNOWN` khi pipeline gặp sự cố
- **Nguyên nhân**: Trong khối `read_etl_control`, nếu việc đọc file CSV hoặc kết nối gặp lỗi trước khi gán biến `load_type`, khối `except` rơi vào đoạn fallback ghi giá trị `'UNKNOWN'`.
- **Giải pháp triển khai**:
  - Trong `read_etl_control.py`: Xác định `load_type` ngay từ đầu dựa trên sự tồn tại của bảng `stg.sales` và mốc LSET (nếu chưa có bảng hoặc $LSET \le 1900-01-01$ thì chắc chắn là `FULL`, còn lại là `INCREMENTAL`).
  - Trong `etl_helpers.py`: Bổ sung cơ chế chuẩn hóa tự động trong hàm `write_log()`: nếu `load_type` bị null hoặc là `'UNKNOWN'`, hệ thống tự động suy diễn theo LSET, không bao giờ lưu `'UNKNOWN'` vào CSDL.

### Task 3: Chuẩn hóa hạ tầng Docker với `compose.yaml`
- **Giải pháp triển khai**:
  - Tạo file `compose.yaml` định nghĩa hai dịch vụ:
    - `sqlserver`: SQL Server 2022, expose port `1433:1433`, mount volume `sqlserver_data` bảo toàn dữ liệu.
    - `mage`: Mage.ai v0.9.79, expose port `6789:6789`, mount thư mục mã nguồn `./:/home/src`.
  - Cả 2 dịch vụ đều có khai báo `restart: unless-stopped`: Giúp container tự phục hồi khi hệ thống khởi động lại hoặc tiến trình bị crash đột ngột.
  - Cấu hình biến môi trường múi giờ `MAGE_TIMEZONE: Asia/Ho_Chi_Minh` và `TZ: Asia/Ho_Chi_Minh`.

### Task 4: Xây dựng Pipeline tổng điều phối `etl_master` (Fail-Fast)
- **Mô hình hoạt động**:
  ```
  [master_step1_sales] ────► [master_step2_dbt_run] ────► [master_step3_dbt_test] ────► [master_step4_ai_explain]
    (Sales Incremental)          (Transform DW)               (39 Data Tests)              (Gemini AI Summary)
  ```
- **Nguyên tắc Fail-Fast**:
  - Nếu Bước 1 lỗi: Không chạy dbt run.
  - Nếu Bước 2 lỗi: Không chạy dbt test.
  - Nếu Bước 3 lỗi (vi phạm chất lượng dữ liệu): Dừng ngay lập tức, không kích hoạt AI tóm tắt cho dữ liệu sai.
- **Triển khai**:
  - Tạo pipeline `etl_master` trong `adventureworks_bi/pipelines/etl_master/metadata.yaml`.
  - Viết 4 khối custom block tương ứng trong `adventureworks_bi/custom/`, mỗi khối đều bắt lỗi và ghi chi tiết trạng thái vào `etl.pipeline_run_detail`.

### Task 5: Cấu hình Trigger tự động hóa (Schedule, Retry, UTC+7)
- Cấu hình trong `adventureworks_bi/triggers.yaml`:
  - `etl_master_demo_10min`: Chạy lặp lại mỗi 10 phút (`*/10 * * * *`), trạng thái **active** để giáo viên/người chấm thi có thể thấy chuỗi tự động chạy.
  - `etl_master_daily_prod`: Lịch chạy thực tế lúc 02:00 sáng hàng ngày (`0 2 * * *`).
  - Retry Policy: Thử lại tối đa 3 lần, giãn cách lũy thừa (`delay: 60s`, `max_delay: 300s`, `exponential_backoff: true`).

### Task 6: Bộ chỉ số DAX phục vụ Semantic Model Power BI
- Đã xuất bản file `powerbi/ETL_Monitoring_Measures.dax` chứa đầy đủ công thức chuẩn:
  - Nhóm KPI: `Total Runs`, `Success Runs`, `Failed Runs`, `Success Rate %`, `Avg Duration (Seconds)`, `Avg Duration (Minutes)`.
  - Nhóm số lượng dòng: `Total Inserted`, `Total Updated`, `Total Deleted`, `Total Rejected`, `Rejection Rate %`.
  - Nhóm hỗ trợ AI: `Selected AI Summary`.

---

## 3. HƯỚNG DẪN CHI TIẾT QUY TRÌNH CHẠY CHƯƠNG TRÌNH (END-TO-END)

### Bước 1: Khởi tạo database và cấu trúc log
1. Mở SSMS hoặc DBeaver, kết nối đến SQL Server (`localhost,14333`, tài khoản `sa`).
2. Mở file `sql/05_create_pipeline_run_detail.sql` và nhấn **F5 (Execute)** để tạo bảng `etl.pipeline_run_detail` và nạp dữ liệu lịch sử.

### Bước 2: Khởi động hệ thống với Docker Compose
Mở PowerShell tại thư mục gốc của project:
```powershell
# Thiết lập mật khẩu sa (nếu dùng biến môi trường)
$env:MSSQL_PASSWORD = "YourStrongPassword123!"

# Khởi động toàn bộ container ngầm
docker compose up -d

# Kiểm tra trạng thái
docker compose ps
```
Bạn sẽ thấy cả hai container `sqlserver` và `mage` đều đang ở trạng thái `Up (healthy)`.

---

### Bước 3: Vận hành chuỗi ETL Master

Bạn có 2 cách để vận hành:

#### Cách A: Chạy qua giao diện Mage.ai (Khuyên dùng khi demo trực quan)
1. Mở trình duyệt web truy cập `http://localhost:6789`.
2. Vào mục **Pipelines** $\rightarrow$ chọn pipeline **`etl_master`**.
3. Bạn sẽ thấy sơ đồ 4 block nối tiếp nhau theo hàng dọc.
4. Nhấn **Execute pipeline** (hoặc vào menu **Triggers** kiểm tra trigger `etl_master_demo_10min` đang ở trạng thái **Active**).
5. Quan sát log chạy qua từng block: Bước trước hoàn thành thì bước sau mới bắt đầu.

#### Cách B: Chạy qua dòng lệnh độc lập (Script Python)
Trong PowerShell với môi trường ảo Python đã kích hoạt:
```powershell
python scripts/run_master_pipeline.py
```
Script sẽ tự động gọi chuỗi 4 bước, in ra tiến độ chi tiết và thời gian hoàn thành.

---

### Bước 4: Thiết kế & Cập nhật Dashboard trên Power BI Desktop

1. **Khởi động**: Mở file `powerbi/AdventureWorks_BI_Dashboard.pbix` bằng Power BI Desktop.
2. **Nạp 3 bảng Metadata**:
   - Chọn **Get Data** $\rightarrow$ **SQL Server**.
   - Server: `localhost,14333`, Database: `BI_AdventureWorks`.
   - Đánh dấu chọn: `etl.pipeline_run_log`, `etl.pipeline_run_detail`, `etl.run_ai_summary`. Bấm **Load**.
3. **Tạo mối quan hệ (Model View)**:
   - Kéo `pipeline_run_log[run_id]` nối tới `pipeline_run_detail[run_id]` (Quan hệ `1 - *`).
   - Kéo `pipeline_run_log[run_id]` nối tới `run_ai_summary[run_id]` (Quan hệ `1 - 1`).
4. **Thêm Measures**:
   - Vào **DAX query view**, dán toàn bộ nội dung file `powerbi/ETL_Monitoring_Measures.dax`.
   - Bấm **Run** rồi bấm **Update model: Add new measure**.
5. **Dựng Trang 1 - "ETL Monitoring"**:
   - **3 Thẻ KPI (Cards)**: Đặt các measure `Total Runs`, `Success Rate %`, `Avg Duration (Seconds)`.
   - **Biểu đồ cột xếp chồng (Stacked Column Chart)**:
     - Trục X: `pipeline_run_log[run_id]`.
     - Trục Y: `Total Inserted`, `Total Updated`, `Total Deleted`, `Total Rejected`.
   - **Bảng danh sách lỗi (Table visual)**:
     - Cột: `run_id`, `started_at`, `pipeline_name`, `error_message`.
     - Bộ lọc visual (Filter): `status = FAILED`.
   - **Cấu hình Drill-through**: Trong panel Page Information, kích hoạt Drill-through với trường `pipeline_run_log[run_id]`.
6. **Dựng Trang 2 - "AI Insights"**:
   - **Khung nhận định AI**: Dùng Multi-row Card hoặc Table hiển thị `run_ai_summary[summary_text]` và `model_name`.
   - **Bảng đối chiếu thông số**: Đặt Table song song hiển thị `run_id`, `load_type`, `rows_read`, `rows_inserted`, `rows_updated`, `rows_rejected`, `status`.

---

## 4. KIỂM TRA ĐỐI SOÁT KẾT QUẢ (VERIFICATION QUERIES)

Chạy các truy vấn sau trong SSMS để đối soát số liệu thực tế:

```sql
USE BI_AdventureWorks;

-- 1. Kiểm tra bảng log tổng hợp (không còn dòng nào UNKNOWN)
SELECT run_id, pipeline_name, load_type, status, batch_id, rows_read, rows_loaded, started_at
FROM etl.pipeline_run_log
ORDER BY run_id DESC;

-- 2. Kiểm tra bảng log chi tiết từng bước
SELECT TOP 20 detail_id, run_id, step_name, table_name, 
       rows_inserted, rows_updated, rows_deleted, rows_rejected, status, started_at
FROM etl.pipeline_run_detail
ORDER BY detail_id DESC;

-- 3. Kiểm tra các bản tóm tắt của AI
SELECT s.run_id, l.status, l.rows_inserted, s.model_name, s.summary_text
FROM etl.run_ai_summary s
JOIN etl.pipeline_run_log l ON s.run_id = l.run_id
ORDER BY s.run_id DESC;
```
