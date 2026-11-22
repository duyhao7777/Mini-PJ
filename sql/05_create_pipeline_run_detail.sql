-- 05_create_pipeline_run_detail.sql
-- Bổ sung bảng log chi tiết cho từng bước/từng bảng trong pipeline ETL
-- Chạy trong SSMS (hoặc DBeaver).

USE BI_AdventureWorks;
GO

IF SCHEMA_ID('etl') IS NULL EXEC('CREATE SCHEMA etl');
GO

-- 0. Đảm bảo etl.pipeline_run_log có đủ các cột đếm chi tiết (tránh lỗi nếu chưa chạy 03)
IF COL_LENGTH('etl.pipeline_run_log', 'rows_inserted') IS NULL
    ALTER TABLE etl.pipeline_run_log ADD rows_inserted INT NULL;
IF COL_LENGTH('etl.pipeline_run_log', 'rows_updated') IS NULL
    ALTER TABLE etl.pipeline_run_log ADD rows_updated INT NULL;
IF COL_LENGTH('etl.pipeline_run_log', 'rows_unchanged') IS NULL
    ALTER TABLE etl.pipeline_run_log ADD rows_unchanged INT NULL;
GO

-- 1. Tạo bảng etl.pipeline_run_detail nếu chưa có
IF OBJECT_ID('etl.pipeline_run_detail', 'U') IS NULL
BEGIN
    CREATE TABLE etl.pipeline_run_detail (
        detail_id     INT IDENTITY(1,1) PRIMARY KEY,
        run_id        INT NOT NULL,                           -- Khóa ngoại tới etl.pipeline_run_log.run_id
        step_name     VARCHAR(100) NOT NULL,                  -- Tên bước (vd: ingest_sales, dbt_run, dbt_test, ai_explain)
        table_name    VARCHAR(100) NULL,                      -- Bảng chịu tác động (vd: stg.sales, dw.fact_sales)
        rows_inserted INT NULL DEFAULT 0,                     -- Số dòng thêm mới
        rows_updated  INT NULL DEFAULT 0,                     -- Số dòng cập nhật
        rows_deleted  INT NULL DEFAULT 0,                     -- Số dòng xóa
        rows_rejected INT NULL DEFAULT 0,                     -- Số dòng bị loại (lỗi khóa, rác)
        status        VARCHAR(20)  NOT NULL,                  -- SUCCESS / FAILED / SKIPPED
        error_message NVARCHAR(MAX) NULL,                     -- Chi tiết lỗi nếu có
        started_at    DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        finished_at   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_pipeline_run_detail_run_id FOREIGN KEY (run_id)
            REFERENCES etl.pipeline_run_log(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IX_pipeline_run_detail_run_id ON etl.pipeline_run_detail(run_id);
    PRINT 'Đã tạo bảng etl.pipeline_run_detail thành công.';
END
ELSE
BEGIN
    PRINT 'Bảng etl.pipeline_run_detail đã tồn tại.';
END
GO

-- 2. Đồng bộ/Backfill dữ liệu lịch sử từ pipeline_run_log sang detail nếu chưa có
INSERT INTO etl.pipeline_run_detail 
    (run_id, step_name, table_name, rows_inserted, rows_updated, rows_deleted, rows_rejected, status, error_message, started_at, finished_at)
SELECT 
    l.run_id,
    l.pipeline_name,
    'stg.sales',
    ISNULL(l.rows_inserted, ISNULL(l.rows_loaded, 0)),
    ISNULL(l.rows_updated, 0),
    0 AS rows_deleted,
    ISNULL(l.rows_rejected, 0),
    l.status,
    l.error_message,
    l.started_at,
    l.finished_at
FROM etl.pipeline_run_log l
WHERE NOT EXISTS (
    SELECT 1 FROM etl.pipeline_run_detail d WHERE d.run_id = l.run_id
);
GO

-- 3. Kiểm tra lại
SELECT COUNT(*) AS total_detail_rows FROM etl.pipeline_run_detail;
SELECT TOP 10 * FROM etl.pipeline_run_detail ORDER BY detail_id DESC;
GO
