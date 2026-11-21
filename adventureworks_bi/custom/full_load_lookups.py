import pandas as pd
from datetime import datetime
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path
from os import path

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

DATA_DIR = '/home/src/data'

LOOKUP_FILES = {
    'AdventureWorks Calendar Lookup.csv': 'calendar',
    'AdventureWorks Customer Lookup.csv': 'customer',
    'AdventureWorks Product Categories Lookup.csv': 'product_category',
    'AdventureWorks Product Subcategories Lookup.csv': 'product_subcategory',
    'AdventureWorks Product Lookup.csv': 'product',
    'AdventureWorks Returns Data.csv': 'returns_data',
    'AdventureWorks Territory Lookup.csv': 'territory',
}


def read_csv_raw(file_path):
    # Đọc toàn bộ cột dạng text; thử UTF-8 trước, lỗi thì dùng latin-1
    try:
        return pd.read_csv(file_path, dtype=str, encoding='utf-8')
    except UnicodeDecodeError:
        return pd.read_csv(file_path, dtype=str, encoding='latin-1')


@custom
def full_load_lookups(*args, **kwargs):
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    loaded_at = datetime.utcnow()
    with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
        for file_name, table_name in LOOKUP_FILES.items():
            df = read_csv_raw(path.join(DATA_DIR, file_name))
            df['_source_file'] = file_name
            df['_loaded_at'] = loaded_at
            loader.export(df, 'stg', table_name, index=False, if_exists='replace')
            print(f'{table_name}: {len(df)} rows')