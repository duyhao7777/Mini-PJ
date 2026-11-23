"""Nạp dữ liệu phần A bằng CLI, chạy được cả Windows lẫn macOS.

Thay cho heredoc `python - <<'PY'` (không dùng được trong PowerShell):

    docker compose exec mage python /home/src/scripts/run_ingest.py

Tương đương việc bấm ▶ lần lượt trên 3 pipeline trong Mage UI:
ingest_lookups_full -> ingest_sales (tuỳ chọn) -> ingest_sales_incremental.
"""
import sys
from datetime import datetime
from os import path

sys.path.insert(0, '/home/src')

import pandas as pd

from adventureworks_bi.custom.update_lset_write_log import update_lset_write_log
from adventureworks_bi.data_exporters.upsert_to_staging import upsert_to_staging
from adventureworks_bi.data_loaders.read_etl_control import read_etl_control
from adventureworks_bi.transformers.classify_rows import classify_rows
from adventureworks_bi.transformers.extract_by_window import extract_by_window
from adventureworks_bi.transformers.validate_source_rows import validate_source_rows
from adventureworks_bi.utils.etl_helpers import get_connection

DATA_DIR = '/home/src/data'
LOOKUPS = {
    'AdventureWorks Calendar Lookup.csv': 'calendar',
    'AdventureWorks Customer Lookup.csv': 'customer',
    'AdventureWorks Product Categories Lookup.csv': 'product_category',
    'AdventureWorks Product Subcategories Lookup.csv': 'product_subcategory',
    'AdventureWorks Product Lookup.csv': 'product',
    'AdventureWorks Returns Data.csv': 'returns_data',
    'AdventureWorks Territory Lookup.csv': 'territory',
}


def load_lookups():
    loaded_at = datetime.utcnow()
    with get_connection() as db:
        for file_name, table in LOOKUPS.items():
            file_path = path.join(DATA_DIR, file_name)
            try:
                df = pd.read_csv(file_path, dtype=str, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, dtype=str, encoding='latin-1')
            df['_source_file'] = file_name
            df['_loaded_at'] = loaded_at
            db.export(df, 'stg', table, index=False, if_exists='replace')
            print(f'{table:22s}: {len(df)} rows')


def load_sales():
    ctl = read_etl_control()
    classified = classify_rows(validate_source_rows(extract_by_window(ctl)))
    upsert_to_staging(classified)
    update_lset_write_log(ctl, classified)


if __name__ == '__main__':
    load_lookups()
    load_sales()
    print('INGEST DONE')
