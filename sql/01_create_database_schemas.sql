-- 01_create_database_schemas.sql
-- Tạo database và các schema cho Staging và Data Warehouse.
-- Chạy trong SSMS (hoặc DBeaver) sau khi SQL Server đã khởi động.

IF DB_ID('BI_AdventureWorks') IS NULL
    CREATE DATABASE BI_AdventureWorks;
GO

USE BI_AdventureWorks;
GO

-- Staging: dữ liệu thô do Mage.ai nạp vào
IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');
GO

-- Data Warehouse: các bảng Dim/Fact do dbt tạo
IF SCHEMA_ID('dw') IS NULL EXEC('CREATE SCHEMA dw');
GO

-- Kiểm tra: phải trả về 2 dòng (dw, stg)
SELECT name FROM sys.schemas WHERE name IN ('stg', 'dw');
