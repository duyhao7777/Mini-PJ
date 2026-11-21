USE BI_AdventureWorks;
CREATE TABLE etl.run_ai_summary (
    run_id       INT NOT NULL PRIMARY KEY,          -- khớp etl.pipeline_run_log.run_id
    summary_text NVARCHAR(MAX) NOT NULL,
    model_name   VARCHAR(100) NOT NULL,
    created_at   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);