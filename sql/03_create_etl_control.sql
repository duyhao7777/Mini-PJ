USE BI_AdventureWorks;

-- Cột đếm chi tiết cho bảng log
ALTER TABLE etl.pipeline_run_log
    ADD rows_inserted INT NULL, rows_updated INT NULL, rows_unchanged INT NULL;

-- Bảng điều khiển LSET/CET
CREATE TABLE etl.etl_control (
    source_name  VARCHAR(100) NOT NULL PRIMARY KEY,
    lset         DATE NOT NULL,      -- Last Successful Extract Time
    cet          DATE NULL,          -- Current Extract Time của lần chạy gần nhất
    cet_override DATE NULL,          -- (tuỳ chọn) ép CET để giả lập thời gian
    last_run_id  VARCHAR(50) NULL,
    updated_at   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
INSERT INTO etl.etl_control (source_name, lset) VALUES ('sales', '1900-01-01');

-- Giữ lại lịch sử log cũ dưới tên v1
UPDATE etl.pipeline_run_log
SET pipeline_name = 'ingest_sales_incremental_v1'
WHERE pipeline_name = 'ingest_sales_incremental';

-- Xoá stg.sales để lần chạy đầu là Full Load thật
DROP TABLE IF EXISTS stg.sales;

UPDATE etl.etl_control SET cet_override = '2020-12-31' WHERE source_name = 'sales';

UPDATE etl.etl_control SET cet_override = '2021-12-31' WHERE source_name = 'sales';

USE BI_AdventureWorks;

SELECT * FROM etl.etl_control;                      -- lset = 2021-12-31

SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT CONCAT(ordernumber, '|', orderlineitem)) AS unique_keys
FROM stg.sales;                                     -- 26565 / 26565

SELECT run_id, load_type, status, batch_start AS lset, batch_end AS cet,
       rows_read, rows_inserted, rows_updated, rows_unchanged
FROM etl.pipeline_run_log
WHERE pipeline_name = 'ingest_sales_incremental'
ORDER BY run_id;