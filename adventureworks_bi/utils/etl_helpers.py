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
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    return MSSQL.with_config(ConfigFileLoader(config_path, 'default'))


def new_run_id(now=None):
    now = now or datetime.utcnow()
    return 'RUN_' + now.strftime('%Y%m%d_%H%M%S')


def _date_sql(value):
    return 'NULL' if value is None else f"'{str(value)[:10]}'"


def write_log(batch_id, load_type, status, lset=None, cet=None,
              rows_read=0, rows_inserted=0, rows_updated=0, rows_unchanged=0,
              rows_rejected=0, error=None, started_at=None):
    started_at = started_at or datetime.utcnow()
    err = 'NULL'
    if error:
        err = "'" + str(error).replace("'", "''")[:900] + "'"
    sql = f"""
        INSERT INTO etl.pipeline_run_log
        (pipeline_name, load_type, batch_id, batch_start, batch_end, status,
         rows_read, rows_loaded, rows_rejected,
         rows_inserted, rows_updated, rows_unchanged, error_message, started_at)
        VALUES ('{PIPELINE_NAME}', '{load_type}', '{batch_id}',
                {_date_sql(lset)}, {_date_sql(cet)}, '{status}',
                {rows_read}, {rows_inserted + rows_updated}, {rows_rejected},
                {rows_inserted}, {rows_updated}, {rows_unchanged}, {err},
                '{started_at:%Y-%m-%d %H:%M:%S}')
    """
    with get_connection() as loader:
        loader.execute(sql)
        loader.commit()