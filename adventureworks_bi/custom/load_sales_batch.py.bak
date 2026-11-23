import pandas as pd
from datetime import datetime, date
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path
from os import path

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PIPELINE_NAME = 'ingest_sales_incremental'
SOURCE_FILE = '/home/src/data/AdventureWorks Sales Data 2020.csv'
SOURCE_NAME = 'AdventureWorks Sales Data 2020.csv'
SALES_COLUMNS = [
    'OrderDate', 'StockDate', 'OrderNumber', 'ProductKey',
    'CustomerKey', 'TerritoryKey', 'OrderLineItem', 'OrderQuantity',
]

# (batch_id, load_type, batch_start, batch_end)
BATCHES = [
    ('FULL_2020',  'FULL',        date(2020, 1, 1),  date(2020, 12, 31)),
    ('INC_2021Q1', 'INCREMENTAL', date(2021, 1, 1),  date(2021, 3, 31)),
    ('INC_2021Q2', 'INCREMENTAL', date(2021, 4, 1),  date(2021, 6, 30)),
    ('INC_2021Q3', 'INCREMENTAL', date(2021, 7, 1),  date(2021, 9, 30)),
    ('INC_2021Q4', 'INCREMENTAL', date(2021, 10, 1), date(2021, 12, 31)),
    ('INC_2022Q1', 'INCREMENTAL', date(2022, 1, 1),  date(2022, 3, 31)),
    ('INC_2022Q2', 'INCREMENTAL', date(2022, 4, 1),  date(2022, 6, 30)),
]


def write_log(config_path, batch, status, rows_read, rows_loaded,
                rows_rejected, error, started_at):
    batch_id, load_type, b_start, b_end = batch
    err = 'NULL'
    if error:
        err = "'" + str(error).replace("'", "''")[:900] + "'"
    sql = f"""
        INSERT INTO etl.pipeline_run_log
        (pipeline_name, load_type, batch_id, batch_start, batch_end, status,
        rows_read, rows_loaded, rows_rejected, error_message, started_at)
        VALUES ('{PIPELINE_NAME}', '{load_type}', '{batch_id}',
                '{b_start}', '{b_end}', '{status}',
                {rows_read}, {rows_loaded}, {rows_rejected}, {err},
                '{started_at:%Y-%m-%d %H:%M:%S}')
    """
    with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
        loader.execute(sql)
        loader.commit()


@custom
def load_sales_batch(*args, **kwargs):
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    started_at = datetime.utcnow()

    # 1. Tìm batch tiếp theo chưa chạy thành công
    with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
        done = loader.load(
            f"SELECT batch_id FROM etl.pipeline_run_log "
            f"WHERE pipeline_name = '{PIPELINE_NAME}' AND status = 'SUCCESS'"
        )
    done_ids = set(done['batch_id']) if len(done) else set()
    pending = [b for b in BATCHES if b[0] not in done_ids]
    if not pending:
        print('Tất cả batch đã được nạp. Không còn gì để chạy.')
        return
    batch = pending[0]
    batch_id, load_type, b_start, b_end = batch
    print(f'Chạy batch {batch_id} ({load_type}): {b_start} -> {b_end}')

    rows_read = rows_loaded = rows_rejected = 0
    try:
        # 2. Đọc file nguồn (text) và lọc theo khoảng ngày của batch
        df = pd.read_csv(SOURCE_FILE, dtype=str, usecols=SALES_COLUMNS)
        df = df[SALES_COLUMNS]
        order_dt = pd.to_datetime(df['OrderDate'], format='%d/%m/%Y', errors='coerce')
        mask = (order_dt >= pd.Timestamp(b_start)) & (order_dt <= pd.Timestamp(b_end))
        batch_df = df[mask].copy()
        rows_read = len(batch_df)

        # 3. Loại các dòng thiếu khoá nghiệp vụ
        valid = batch_df['OrderNumber'].notna() & batch_df['OrderLineItem'].notna()
        rows_rejected = int((~valid).sum())
        batch_df = batch_df[valid].copy()

        # 4. Thêm cột siêu dữ liệu
        batch_df['_batch_id'] = batch_id
        batch_df['_source_file'] = SOURCE_NAME
        batch_df['_row_number'] = batch_df.index + 1
        batch_df['_loaded_at'] = datetime.utcnow()

        # 5. Xoá dữ liệu cũ của chính batch này (để chạy lại không bị trùng) rồi nạp
        with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
            loader.execute(
                f"IF OBJECT_ID('stg.sales', 'U') IS NOT NULL "
                f"DELETE FROM stg.sales WHERE _batch_id = '{batch_id}'"
            )
            loader.commit()
            loader.export(batch_df, 'stg', 'sales', index=False, if_exists='append')
        rows_loaded = len(batch_df)

        write_log(config_path, batch, 'SUCCESS', rows_read, rows_loaded,
                    rows_rejected, None, started_at)
        print(f'SUCCESS: đọc {rows_read}, nạp {rows_loaded}, loại {rows_rejected}')
    except Exception as e:
        write_log(config_path, batch, 'FAILED', rows_read, rows_loaded,
                    rows_rejected, e, started_at)
        print(f'FAILED: {e}')
        raise