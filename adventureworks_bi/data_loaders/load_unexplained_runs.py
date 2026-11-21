from adventureworks_bi.utils.etl_helpers import PIPELINE_NAME, get_connection

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_unexplained_runs(*args, **kwargs):
    # Giới hạn 10 lần chạy mỗi lượt để không vượt hạn mức của gói miễn phí
    sql = f"""
        SELECT TOP 10 l.run_id, l.load_type, l.batch_id, l.status,
               CONVERT(varchar(10), l.batch_start, 23) AS lset,
               CONVERT(varchar(10), l.batch_end, 23)   AS cet,
               l.rows_read, l.rows_inserted, l.rows_updated, l.rows_unchanged,
               l.rows_rejected, l.error_message,
               CONVERT(varchar(19), l.started_at, 120) AS started_at
        FROM etl.pipeline_run_log l
        LEFT JOIN etl.run_ai_summary s ON s.run_id = l.run_id
        WHERE s.run_id IS NULL AND l.pipeline_name = '{PIPELINE_NAME}'
        ORDER BY l.run_id
    """
    with get_connection() as loader:
        df = loader.load(sql)
    print(f'Có {len(df)} lần chạy chưa được giải thích')
    return df