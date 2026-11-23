-- 06_create_ai_qa_views.sql — view + tài khoản chỉ đọc cho Q&A (phần C).
-- Idempotent. 2 view KPI chỉ được tạo khi dbt đã build ai.kpi_monthly / kpi_by_dim;
-- chạy lại file này sau `dbt run` là đủ (KHÔNG chạy full init vì 03 DROP stg.sales).
USE BI_AdventureWorks;
GO
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name='ai') EXEC('CREATE SCHEMA ai');
GO

IF OBJECT_ID('ai.kpi_monthly','U') IS NOT NULL
    EXEC('CREATE OR ALTER VIEW ai.v_kpi_monthly AS SELECT * FROM ai.kpi_monthly');
GO
IF OBJECT_ID('ai.kpi_by_dim','U') IS NOT NULL
    EXEC('CREATE OR ALTER VIEW ai.v_kpi_by_dim AS SELECT * FROM ai.kpi_by_dim');
GO
IF OBJECT_ID('ai.analytics_summary','U') IS NOT NULL
    EXEC('CREATE OR ALTER VIEW ai.v_latest_summary AS SELECT month_start, summary_text, verified, model_name FROM ai.analytics_summary');
GO
IF OBJECT_ID('ai.insight_explanation','U') IS NOT NULL
    EXEC('CREATE OR ALTER VIEW ai.v_trend_explain AS SELECT month_start, metric_name, change_pct, explanation_text, verified FROM ai.insight_explanation');
GO

IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name='qa_reader')
    CREATE LOGIN qa_reader WITH PASSWORD='__QA_PASSWORD__';
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name='qa_reader')
    CREATE USER qa_reader FOR LOGIN qa_reader;
GO

-- Chỉ SELECT trên 4 VIEW (không GRANT trên SCHEMA, kẻo đọc được cả bảng gốc).
REVOKE SELECT ON SCHEMA::ai FROM qa_reader;
GO
IF OBJECT_ID('ai.v_kpi_monthly','V') IS NOT NULL GRANT SELECT ON OBJECT::ai.v_kpi_monthly TO qa_reader;
GO
IF OBJECT_ID('ai.v_kpi_by_dim','V') IS NOT NULL GRANT SELECT ON OBJECT::ai.v_kpi_by_dim TO qa_reader;
GO
IF OBJECT_ID('ai.v_latest_summary','V') IS NOT NULL GRANT SELECT ON OBJECT::ai.v_latest_summary TO qa_reader;
GO
IF OBJECT_ID('ai.v_trend_explain','V') IS NOT NULL GRANT SELECT ON OBJECT::ai.v_trend_explain TO qa_reader;
GO
DENY INSERT, UPDATE, DELETE, ALTER ON SCHEMA::ai TO qa_reader;
GO
