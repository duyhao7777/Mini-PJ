USE BI_AdventureWorks;
GO
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name='ai') EXEC('CREATE SCHEMA ai');
GO
IF OBJECT_ID('ai.analytics_summary','U') IS NULL
CREATE TABLE ai.analytics_summary (
 summary_id bigint identity(1,1) primary key,
 month_start date not null,
 input_json nvarchar(max) not null,
 summary_text nvarchar(max) not null,
 model_name nvarchar(100) not null,
 verified bit not null default 0,
 verification_note nvarchar(1000) null,
 created_at datetime2 not null default sysutcdatetime(),
 CONSTRAINT UQ_ai_analytics_summary_month UNIQUE(month_start)
);
GO
IF OBJECT_ID('ai.insight_explanation','U') IS NULL
CREATE TABLE ai.insight_explanation (
 insight_id bigint identity(1,1) primary key,
 month_start date not null,
 metric_name varchar(50) not null,
 comparison_type varchar(10) not null,
 change_pct decimal(18,2) not null,
 input_json nvarchar(max) not null,
 explanation_text nvarchar(max) not null,
 model_name nvarchar(100) not null,
 verified bit not null default 0,
 verification_note nvarchar(1000) null,
 created_at datetime2 not null default sysutcdatetime(),
 CONSTRAINT UQ_ai_insight UNIQUE(month_start,metric_name,comparison_type)
);
GO
