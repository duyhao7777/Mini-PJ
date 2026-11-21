# Mini Project BI: Hệ thống Business Intelligence tích hợp AI (Giai đoạn 1: ETL và Data Warehouse)

Dự án xây dựng quy trình ETL và Data Warehouse cho bộ dữ liệu **AdventureWorks Sales** (Kaggle):

```
CSV (Kaggle) --> Mage.ai --> SQL Server: schema stg (dữ liệu thô) --> dbt --> schema dw_staging (view làm sạch) --> schema dw (Star Schema)
```

- **Mage.ai** nạp 10 file CSV vào schema `stg` (Full Load cho bảng danh mục; Full Load và Incremental Load theo quý cho bảng bán hàng, có log trong `etl.pipeline_run_log`).
- **dbt** làm sạch, chuẩn hoá và xây Data Warehouse: 4 Dimension (`dim_date`, `dim_product`, `dim_customer`, `dim_territory`) và 2 Fact (`fact_sales`, `fact_returns`), kèm 39 test chất lượng dữ liệu.
- **Power BI và Generative AI** thuộc giai đoạn 2 (chưa có trong gói này).

Dataset: https://www.kaggle.com/datasets/dorcasdavid/adventureworks-sales

---

## 1. Yêu cầu hệ thống

| Thành phần | Ghi chú |
|---|---|
| Windows 10/11 | Các lệnh dưới đây viết cho PowerShell |
| Docker Desktop | Chạy SQL Server và Mage.ai |
| Python 3.10 trở lên | Dự án đã chạy với Python 3.14.6 |
| ODBC Driver 18 for SQL Server | Để dbt kết nối SQL Server. Kiểm tra: `Get-OdbcDriver \| Where-Object Name -like "*SQL Server*"` |
| SSMS hoặc DBeaver | Chạy script SQL và truy vấn kiểm tra |
| Git (tuỳ chọn) | dbt có thể yêu cầu khi chạy `dbt debug` |

Phiên bản đã dùng: SQL Server 2022 (Docker), Mage.ai v0.9.79, dbt-core 1.12.6, dbt-sqlserver 1.12.1.

## 2. Cấu trúc thư mục

```
bi_project/
├── data/                    # 10 file CSV tải từ Kaggle (không nằm trong gói nộp)
├── adventureworks_bi/       # Dự án Mage.ai (pipelines, blocks, io_config.yaml)
├── adventureworks_dw/       # Dự án dbt (models, tests, profiles.yml)
├── sql/                     # Script SQL tạo database, schema, bảng log
├── requirements.txt         # Thư viện Python cho dbt
└── README.md
```

## 3. Cài đặt và chạy

Đặt mật khẩu `sa` của SQL Server là `<MẬT_KHẨU>` (tối thiểu 8 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt). Hãy thay `<MẬT_KHẨU>` trong mọi lệnh bên dưới bằng mật khẩu của bạn.

### Bước 0. Chuẩn bị dữ liệu

1. Tải dataset từ đường dẫn Kaggle ở trên, giải nén.
2. Tạo thư mục `bi_project/data/` và chép vào đó các file CSV với đúng tên gốc:

```
AdventureWorks Calendar Lookup.csv
AdventureWorks Customer Lookup.csv
AdventureWorks Product Categories Lookup.csv
AdventureWorks Product Lookup.csv
AdventureWorks Product Subcategories Lookup.csv
AdventureWorks Returns Data.csv
AdventureWorks Sales Data 2020.csv
AdventureWorks Sales Data 2021.csv
AdventureWorks Sales Data 2022.csv
AdventureWorks Territory Lookup.csv
```

(File `AdventureWorks Product Category Sales (Unpivot Demo).csv` chỉ để minh hoạ, không dùng.)

### Bước 1. Khởi động SQL Server và tạo cấu trúc database

```powershell
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<MẬT_KHẨU>" -p 1433:1433 --name sqlserver -d mcr.microsoft.com/mssql/server:2022-latest
```

Đợi khoảng 20 đến 30 giây cho SQL Server khởi động xong. Mở SSMS và kết nối:

- Server name: `localhost,1433`
- Authentication: SQL Server Authentication, user `sa`, mật khẩu như trên
- Bật **Trust Server Certificate**

Chạy lần lượt hai file trong thư mục `sql/`:

1. `01_create_database_schemas.sql` (tạo database `BI_AdventureWorks`, schema `stg` và `dw`)
2. `02_create_etl_log.sql` (tạo schema `etl` và bảng `etl.pipeline_run_log`)

### Bước 2. Chạy Mage.ai (Data Ingestion)

**2.1. Cấu hình kết nối.** Mở file `adventureworks_bi/io_config.yaml`, trong profile `default` đặt các dòng `MSSQL_` như sau:

```yaml
MSSQL_DATABASE: BI_AdventureWorks
MSSQL_SCHEMA: stg
MSSQL_DRIVER: 'ODBC Driver 18 for SQL Server'
MSSQL_HOST: host.docker.internal
MSSQL_PASSWORD: "{{ env_var('MSSQL_PASSWORD') }}"
MSSQL_PORT: 1433
MSSQL_USER: sa
```

`host.docker.internal` là bắt buộc: Mage chạy trong container riêng nên không dùng được `localhost` để tới SQL Server.

Trước khi khởi động Mage, đặt biến môi trường cho phiên PowerShell hiện tại:

```powershell
$env:MSSQL_PASSWORD = "<MẬT_KHẨU>"
```

**2.2. Khởi động Mage** (đứng trong thư mục `bi_project`, cùng phiên PowerShell):

```powershell
docker run -d --name mage -e MSSQL_PASSWORD -p 6789:6789 -v "${PWD}:/home/src" mageai/mageai /app/run_app.sh mage start adventureworks_bi
```

Mở `http://localhost:6789` (không cần đăng nhập). Kiểm tra dữ liệu đã được gắn đúng:

```powershell
docker exec mage ls /home/src/data
```

**2.3. Chạy các pipeline theo thứ tự.** Trong giao diện Mage, vào **Pipelines**, mở từng pipeline và chạy block bằng nút ▶ (hoặc dùng trigger Run@once):

| Thứ tự | Pipeline | Block | Kết quả |
|---|---|---|---|
| 1 | `ingest_lookups_full` | `full_load_lookups` | Tạo 7 bảng `stg.calendar`, `customer`, `product`, `product_category`, `product_subcategory`, `returns_data`, `territory` |
| 2 | `ingest_sales` | `full_load_sales` | Tạo `stg.sales_raw` (84,710 dòng của cả 3 file Sales, dùng làm bằng chứng trùng lặp) |
| 3 | `ingest_sales_incremental` | `load_sales_batch` | Nạp `stg.sales` theo batch. **Chạy block 7 lần**, mỗi lần nạp một batch (`FULL_2020`, rồi `INC_2021Q1` đến `INC_2022Q2`). Lần chạy thứ 8 báo đã nạp đủ |

Hai pipeline `test_connection` và `ingest_lookups` chỉ là bản thử nghiệm kết nối và có thể bỏ qua.

**2.4. Kiểm tra ingestion** (chạy trong SSMS):

```sql
USE BI_AdventureWorks;

-- Mong đợi: 7 batch SUCCESS
SELECT run_id, batch_id, status, rows_read, rows_loaded FROM etl.pipeline_run_log ORDER BY run_id;

-- Mong đợi: 56046 dòng, 56046 khoá duy nhất
SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT CONCAT(ordernumber, '|', orderlineitem)) AS unique_keys
FROM stg.sales;
```

Số dòng theo batch: 2,630; 775; 931; 8,923; 13,306; 13,649; 15,832.

### Bước 3. Chạy dbt (Transform và Data Warehouse)

**3.1. Tạo môi trường Python** (đứng trong thư mục `bi_project`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu PowerShell báo lỗi execution policy, chạy `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` rồi kích hoạt lại.

**3.2. Đặt mật khẩu qua biến môi trường** (file `profiles.yml` không chứa mật khẩu). Lệnh này chỉ có hiệu lực trong cửa sổ PowerShell hiện tại, mỗi lần mở terminal mới cần gõ lại:

```powershell
cd adventureworks_dw
$env:DBT_SA_PASSWORD = "<MẬT_KHẨU>"
```

**3.3. Kiểm tra kết nối, build và test:**

```powershell
dbt debug      # phải thấy: All checks passed!
dbt run        # 14 model: 8 view (dw_staging) và 6 bảng (dw)
dbt test       # mong đợi: PASS=39 WARN=0 ERROR=0
```

Chạy riêng từng nhóm nếu cần:

```powershell
dbt run --select staging
dbt run --select marts
```

**3.4. Sinh tài liệu và sơ đồ lineage:**

```powershell
dbt docs generate
dbt docs serve     # mở http://localhost:8080, nhấn Ctrl+C để dừng
```

**3.5. Kiểm tra Data Warehouse** (chạy trong SSMS):

```sql
USE BI_AdventureWorks;

SELECT COUNT(*) AS n, SUM(sales_amount) AS revenue, SUM(profit_amount) AS profit
FROM dw.fact_sales;             -- 56046 dòng; revenue 36,597,335.82; profit 16,955,011.43

SELECT COUNT(*) AS n, SUM(return_quantity) AS return_qty
FROM dw.fact_returns;           -- 1809 dòng; 2308
```

Số dòng các Dimension: `dim_date` 912, `dim_product` 293, `dim_customer` 18,148, `dim_territory` 10.

## 4. Chạy lại và dọn dẹp

**Chạy lại dbt:** chạy lại `dbt run` bất cứ lúc nào, dbt tự tạo lại các model.

**Chạy lại một batch của Mage:** đánh dấu batch cũ là đã bị thay thế rồi chạy lại block `load_sales_batch`; pipeline sẽ xoá và nạp lại đúng batch đó, không sinh dòng trùng:

```sql
UPDATE etl.pipeline_run_log SET status = 'SUPERSEDED'
WHERE batch_id = 'INC_2022Q2' AND status = 'SUCCESS';
```

**Nạp lại toàn bộ dữ liệu bán hàng từ đầu:**

```sql
DROP TABLE IF EXISTS stg.sales;
DELETE FROM etl.pipeline_run_log WHERE pipeline_name = 'ingest_sales_incremental';
```

**Tắt và bật lại container** (dữ liệu được giữ nguyên):

```powershell
docker stop mage sqlserver
docker start sqlserver
docker start mage
```

Không dùng `docker rm sqlserver` nếu muốn giữ dữ liệu.

## 5. Xử lý lỗi thường gặp

| Triệu chứng | Nguyên nhân và cách xử lý |
|---|---|
| `dbt debug` báo `pyodbc` chưa cài | Chạy `pip install pyodbc` trong môi trường ảo đang kích hoạt |
| `dbt debug` báo không kết nối được | Kiểm tra `docker ps` thấy `sqlserver` đang `Up`, đã đặt `$env:DBT_SA_PASSWORD`, và mật khẩu đúng |
| Lỗi SSL certificate khi kết nối | Bật Trust Server Certificate (SSMS) hoặc giữ `trust_cert: true` trong `profiles.yml` |
| Mage không kết nối được SQL Server | `MSSQL_HOST` phải là `host.docker.internal`, không phải `localhost` |
| Model dbt báo `Invalid column name` | Mage tự đổi tên một số cột khi nạp (ví dụ `Prefix` thành `_prefix`, `Date` thành `_date`). Xem tên cột thật: `SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema='stg' AND table_name='customer'` |
| Mage báo không thấy file CSV | Kiểm tra thư mục `data/` có đủ file, đúng tên, và container `mage` được chạy từ thư mục `bi_project` |
| `docker run` báo trùng tên container | Container đã tồn tại, dùng `docker start sqlserver` (hoặc `mage`) thay vì `docker run` |

## 6. Ghi chú thiết kế quan trọng

- **Ba file Sales chồng lấn:** file 2020 chứa toàn bộ 01/2020 đến 06/2022, file 2021 và 2022 là tập con. Nối cả ba sẽ thổi phồng doanh thu khoảng 47%. Pipeline nạp tăng dần chỉ dùng file 2020; `stg.sales_raw` giữ cả ba file làm bằng chứng.
- **Staging dạng text:** mọi cột nạp ở dạng text, ép kiểu ở dbt, vì ngày dùng hai định dạng khác nhau (dd/MM/yyyy và yyyy-MM-dd).
- **Doanh thu** = số lượng × giá niêm yết (dữ liệu không có chiết khấu hay phí vận chuyển).
- **`stock_date`** là cột ngày thường trong `fact_sales` (không nối `dim_date`) vì ngày nhập kho có thể sớm hơn 01/01/2020.
- Dữ liệu dừng ở 30/06/2022, nên năm 2022 chỉ có nửa năm.

## 7. Bảo mật

Mật khẩu `sa` chỉ dành cho môi trường phát triển trên máy cá nhân. File `adventureworks_bi/io_config.yaml` trong gói nộp đã thay mật khẩu bằng giá trị giả; không đưa mật khẩu thật lên Git hoặc nộp kèm.
