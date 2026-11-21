-- 02_create_etl_log.sql
-- Tạo schema etl và bảng log trạng thái chạy pipeline Mage.ai.
-- Chạy sau 01_create_database_schemas.sql.

USE BI_AdventureWorks;
GO

IF SCHEMA_ID('etl') IS NULL EXEC('CREATE SCHEMA etl');
GO

IF OBJECT_ID('etl.pipeline_run_log', 'U') IS NULL
CREATE TABLE etl.pipeline_run_log (
    run_id        INT IDENTITY(1,1) PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    load_type     VARCHAR(20)  NOT NULL,   -- FULL / INCREMENTAL
    batch_id      VARCHAR(50)  NOT NULL,
    batch_start   DATE NULL,
    batch_end     DATE NULL,
    status        VARCHAR(20)  NOT NULL,   -- SUCCESS / FAILED / SUPERSEDED
    rows_read     INT NULL,
    rows_loaded   INT NULL,
    rows_rejected INT NULL,
    error_message NVARCHAR(1000) NULL,
    started_at    DATETIME2 NOT NULL,
    finished_at   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO
