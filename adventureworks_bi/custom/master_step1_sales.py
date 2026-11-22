from datetime import datetime
from mage_ai.data_preparation.models.pipeline import Pipeline
from adventureworks_bi.utils.etl_helpers import get_connection, write_run_detail

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def master_step1_sales(*args, **kwargs):
    started_at = datetime.utcnow()
    print('=== [BƯỚC 1/4] Chạy pipeline nạp bán hàng ingest_sales_incremental ===')
    try:
        p = Pipeline.get('ingest_sales_incremental')
        p.execute_sync()
        
        # Lấy thông tin lần chạy gần nhất từ log (etl.pipeline_run_log không có cột rows_deleted)
        with get_connection() as loader:
            res = loader.load("""
                SELECT TOP 1 run_id, status, error_message, rows_inserted, rows_updated, rows_rejected
                FROM etl.pipeline_run_log
                WHERE pipeline_name = 'ingest_sales_incremental'
                ORDER BY run_id DESC
            """)
        if not res.empty:
            latest = res.iloc[0]
            if latest['status'] == 'FAILED':
                raise RuntimeError(f"ingest_sales_incremental thất bại: {latest['error_message']}")
            print(f"Bước 1 thành công (Run ID {latest['run_id']}): Inserted={latest['rows_inserted']}, Updated={latest['rows_updated']}")
            return {'run_id': int(latest['run_id']), 'status': 'SUCCESS', 'started_at': started_at}
        return {'status': 'SUCCESS', 'started_at': started_at}
    except Exception as e:
        print(f"LỖI ở Bước 1 (ingest_sales_incremental): {e}")
        raise
