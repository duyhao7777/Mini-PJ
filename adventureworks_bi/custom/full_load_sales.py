import pandas as pd
from datetime import datetime
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path
from os import path

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

DATA_DIR = '/home/src/data'

SALES_FILES = [
    'AdventureWorks Sales Data 2020.csv',
    'AdventureWorks Sales Data 2021.csv',
    'AdventureWorks Sales Data 2022.csv',
]

SALES_COLUMNS = [
    'OrderDate', 'StockDate', 'OrderNumber', 'ProductKey',
    'CustomerKey', 'TerritoryKey', 'OrderLineItem', 'OrderQuantity',
]


@custom
def full_load_sales(*args, **kwargs):
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    loaded_at = datetime.utcnow()
    frames = []

    for file_name in SALES_FILES:
        df = pd.read_csv(
            path.join(DATA_DIR, file_name),
            dtype=str,
            usecols=SALES_COLUMNS,
        )
        df = df[SALES_COLUMNS]
        df['_source_file'] = file_name
        df['_row_number'] = range(1, len(df) + 1)
        df['_loaded_at'] = loaded_at
        print(f'{file_name}: {len(df)} rows')
        frames.append(df)

    sales = pd.concat(frames, ignore_index=True)

    with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
        loader.export(sales, 'stg', 'sales_raw', index=False, if_exists='replace')

    print(f'Total loaded into stg.sales_raw: {len(sales)} rows')