from datetime import datetime
from os import path

from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path

PIPELINE_NAME = 'ingest_sales_incremental'
SOURCE_KEY = 'sales'   # khoá của nguồn trong etl.etl_control
SOURCE_FILE = '/home/src/data/AdventureWorks Sales Data 2020.csv'
SOURCE_NAME = 'AdventureWorks Sales Data 2020.csv'
SALES_COLUMNS = [
    'OrderDate', 'StockDate', 'OrderNumber', 'ProductKey',
    'CustomerKey', 'TerritoryKey', 'OrderLineItem', 'OrderQuantity',
]
KEY_COLS = ['ordernumber', 'orderlineitem']
VALUE_COLS = ['orderdate', 'stockdate', 'productkey', 'customerkey',
              'territorykey', 'orderquantity']
STAGING_COLS = [
    'orderdate', 'stockdate', 'ordernumber', 'productkey', 'customerkey',
    'territorykey', 'orderlineitem', 'orderquantity',
    '_batch_id', '_source_file', '_row_number', '_loaded_at',
]

MERGE_SQL = """
MERGE stg.sales AS t
USING stg.sales_delta AS s
   ON t.ordernumber = s.ordernumber AND t.orderlineitem = s.orderlineitem
WHEN MATCHED THEN UPDATE SET
     t.orderdate = s.orderdate, t.stockdate = s.stockdate,
     t.productkey = s.productkey, t.customerkey = s.customerkey,
     t.territorykey = s.territorykey, t.orderquantity = s.orderquantity,
     t._batch_id = s._batch_id, t._source_file = s._source_file,
     t._row_number = s._row_number, t._loaded_at = s._loaded_at
WHEN NOT MATCHED BY TARGET THEN INSERT
     (orderdate, stockdate, ordernumber, productkey, customerkey,
      territorykey, orderlineitem, orderquantity,
      _batch_id, _source_file, _row_number, _loaded_at)
VALUES
     (s.orderdate, s.stockdate, s.ordernumber, s.productkey, s.customerkey,
      s.territorykey, s.orderlineitem, s.orderquantity,
      s._batch_id, s._source_file, s._row_number, s._loaded_at);
"""


def get_connection():
    try:
        repo_dir = get_repo_path()
    except Exception:
        repo_dir = '/home/src'

    paths_to_check = [
        path.join(repo_dir, 'io_config.yaml'),
        path.abspath('io_config.yaml'),
    ]
    if '__file__' in globals():
        paths_to_check.append(path.abspath(path.join(path.dirname(__file__), '..', 'io_config.yaml')))

    config_path = next((p for p in paths_to_check if path.exists(p)), path.join(repo_dir, 'io_config.yaml'))
    return MSSQL.with_config(ConfigFileLoader(config_path, 'default'))


def new_run_id(now=None):
    now = now or datetime.utcnow()
    return 'RUN_' + now.strftime('%Y%m%d_%H%M%S')


def _date_sql(value):
    return 'NULL' if value is None else f"'{str(value)[:10]}'"


def write_log(batch_id, load_type, status, lset=None, cet=None,
              rows_read=0, rows_inserted=0, rows_updated=0, rows_unchanged=0,
              rows_rejected=0, rows_deleted=0, error=None, started_at=None,
              pipeline_name=None, step_name=None):
    """
    Ghi log vào etl.pipeline_run_log và etl.pipeline_run_detail.
    Tuyệt đối không để load_type = 'UNKNOWN' khi có lỗi.
    Trả về run_id (int) được sinh tự động.
    """
    started_at = started_at or datetime.utcnow()
    finished_at = datetime.utcnow()
    pipe_name = pipeline_name or PIPELINE_NAME
    
    # Chuẩn hoá load_type: không bao giờ ghi UNKNOWN
    if not load_type or str(load_type).upper() == 'UNKNOWN':
        if lset and str(lset)[:10] <= '1900-01-01':
            load_type = 'FULL'
        else:
            load_type = 'INCREMENTAL'
    else:
        load_type = str(load_type).upper()

    err = 'NULL'
    if error:
        err = "'" + str(error).replace("'", "''")[:900] + "'"

    sql = f"""
        SET NOCOUNT ON;
        INSERT INTO etl.pipeline_run_log
        (pipeline_name, load_type, batch_id, batch_start, batch_end, status,
         rows_read, rows_loaded, rows_rejected,
         rows_inserted, rows_updated, rows_unchanged, error_message, started_at, finished_at)
        OUTPUT INSERTED.run_id
        VALUES ('{pipe_name}', '{load_type}', '{batch_id}',
                {_date_sql(lset)}, {_date_sql(cet)}, '{status}',
                {rows_read}, {rows_inserted + rows_updated}, {rows_rejected},
                {rows_inserted}, {rows_updated}, {rows_unchanged}, {err},
                '{started_at:%Y-%m-%d %H:%M:%S}', '{finished_at:%Y-%m-%d %H:%M:%S}');
    """
    run_id = None
    with get_connection() as loader:
        try:
            res = loader.load(sql)
            loader.commit()
            if not res.empty and 'run_id' in res.columns and res['run_id'].iloc[0] is not None:
                run_id = int(res['run_id'].iloc[0])
        except Exception as e_output:
            # Fallback
            try:
                loader.execute(f"""
                    INSERT INTO etl.pipeline_run_log
                    (pipeline_name, load_type, batch_id, batch_start, batch_end, status,
                     rows_read, rows_loaded, rows_rejected,
                     rows_inserted, rows_updated, rows_unchanged, error_message, started_at, finished_at)
                    VALUES ('{pipe_name}', '{load_type}', '{batch_id}',
                            {_date_sql(lset)}, {_date_sql(cet)}, '{status}',
                            {rows_read}, {rows_inserted + rows_updated}, {rows_rejected},
                            {rows_inserted}, {rows_updated}, {rows_unchanged}, {err},
                            '{started_at:%Y-%m-%d %H:%M:%S}', '{finished_at:%Y-%m-%d %H:%M:%S}')
                """)
                loader.commit()
                id_res = loader.load("SELECT CAST(IDENT_CURRENT('etl.pipeline_run_log') AS INT) AS run_id")
                loader.commit()
                if not id_res.empty and id_res['run_id'].iloc[0] is not None:
                    run_id = int(id_res['run_id'].iloc[0])
            except Exception as e_fallback:
                print(f"Lỗi fallback ghi log: {e_fallback}")

        # Ghi đồng thời vào bảng etl.pipeline_run_detail nếu bảng đã tồn tại
        if run_id:
            try:
                detail_sql = f"""
                    IF OBJECT_ID('etl.pipeline_run_detail', 'U') IS NOT NULL
                    INSERT INTO etl.pipeline_run_detail
                    (run_id, step_name, table_name, rows_inserted, rows_updated, rows_deleted, rows_rejected, status, error_message, started_at, finished_at)
                    VALUES ({run_id}, '{step_name or pipe_name}', 'stg.sales',
                            {rows_inserted}, {rows_updated}, {rows_deleted}, {rows_rejected},
                            '{status}', {err}, '{started_at:%Y-%m-%d %H:%M:%S}', '{finished_at:%Y-%m-%d %H:%M:%S}')
                """
                loader.execute(detail_sql)
                loader.commit()
            except Exception as e_detail:
                print(f"Lưu chi tiết log cảnh báo: {e_detail}")

    return run_id


def write_run_detail(run_id, step_name, table_name='stg.sales',
                     rows_inserted=0, rows_updated=0, rows_deleted=0, rows_rejected=0,
                     status='SUCCESS', error=None, started_at=None, finished_at=None):
    """
    Ghi log cho từng bước con vào etl.pipeline_run_detail.
    """
    started_at = started_at or datetime.utcnow()
    finished_at = finished_at or datetime.utcnow()
    err = 'NULL'
    if error:
        err = "'" + str(error).replace("'", "''")[:900] + "'"

    sql = f"""
        IF OBJECT_ID('etl.pipeline_run_detail', 'U') IS NOT NULL
        INSERT INTO etl.pipeline_run_detail
        (run_id, step_name, table_name, rows_inserted, rows_updated, rows_deleted, rows_rejected, status, error_message, started_at, finished_at)
        VALUES ({int(run_id)}, '{step_name}', '{table_name}',
                {rows_inserted}, {rows_updated}, {rows_deleted}, {rows_rejected},
                '{status}', {err}, '{started_at:%Y-%m-%d %H:%M:%S}', '{finished_at:%Y-%m-%d %H:%M:%S}')
    """
    with get_connection() as loader:
        loader.execute(sql)
        loader.commit()
