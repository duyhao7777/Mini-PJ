"""Khởi tạo DB BI_AdventureWorks từ bên trong container Mage.

Azure SQL Edge trên Mac M1 không kèm sqlcmd, nhưng image Mage có sẵn
pyodbc + ODBC Driver 18, nên script này đọc .sql và tách batch bằng GO.

    docker exec mage python /home/src/scripts/init_db_via_mage.py
    docker exec mage python /home/src/scripts/init_db_via_mage.py 06_create_ai_qa_views.sql

⚠️ Sau khi ingest KHÔNG chạy lại toàn bộ: 03_create_etl_control.sql có
   DROP TABLE stg.sales. Khi đó chỉ truyền tên file 06 như lệnh thứ 2.

File 06 chứa token __QA_PASSWORD__, được thay bằng $MSSQL_PASSWORD lúc chạy
để login qa_reader khớp với app mà không hard-code mật khẩu trong repo.
"""
import os
import re
import sys

import pyodbc

SQL_DIR = '/home/src/sql'
SQL_FILES = (
    '01_create_database_schemas.sql',
    '02_create_etl_log.sql',
    '03_create_etl_control.sql',
    '04_create_AI_summary.sql',
    '05_create_pipeline_run_detail.sql',
    '05_create_ai_analytics.sql',
    '06_create_ai_qa_views.sql',
)
_GO = re.compile(r'(?im)^\s*GO\s*$')
_QA_TOKEN = '__QA_PASSWORD__'
_QA_VIEW_FILE = '06_create_ai_qa_views.sql'


def connect():
    conn_str = (
        'DRIVER={ODBC Driver 18 for SQL Server};'
        f"SERVER={os.environ.get('MSSQL_HOST', 'host.docker.internal')},1433;"
        'DATABASE=master;UID=sa;'
        f"PWD={os.environ['MSSQL_PASSWORD']};"
        'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str, autocommit=True)


def run_files(cur, names):
    for name in names:
        path = os.path.join(SQL_DIR, name)
        if not os.path.exists(path):
            print(f'SKIP (chưa có): {name}')
            continue
        with open(path, encoding='utf-8-sig') as fh:
            sql = fh.read()
        if name == _QA_VIEW_FILE:
            pwd = os.environ['MSSQL_PASSWORD'].replace("'", "''")
            sql = sql.replace(_QA_TOKEN, pwd)
        batches = [b for b in _GO.split(sql) if b.strip()]
        for batch in batches:
            cur.execute(batch)
        print(f'OK  {name}  ({len(batches)} batch)')


def main():
    requested = [a for a in sys.argv[1:] if a.endswith('.sql')]
    conn = connect()
    try:
        cur = conn.cursor()
        run_files(cur, requested or SQL_FILES)
        schemas = [r[0] for r in cur.execute(
            "SELECT name FROM sys.schemas WHERE name IN ('stg','dw','etl','ai') ORDER BY name"
        ).fetchall()]
    finally:
        conn.close()
    print('SCHEMAS:', ', '.join(schemas))


if __name__ == '__main__':
    main()
