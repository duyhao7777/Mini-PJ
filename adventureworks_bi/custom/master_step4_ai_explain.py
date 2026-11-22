from datetime import datetime
from mage_ai.data_preparation.models.pipeline import Pipeline
from adventureworks_bi.utils.etl_helpers import write_run_detail

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def master_step4_ai_explain(data, *args, **kwargs):
    started_at = datetime.utcnow()
    run_id = data.get('run_id') if isinstance(data, dict) else None
    print('=== [BƯỚC 4/4] Kích hoạt pipeline phân tích AI ai_explain_etl_runs ===')

    try:
        p = Pipeline.get('ai_explain_etl_runs')
        p.execute_sync()
        if run_id:
            write_run_detail(
                run_id, step_name='ai_explain', table_name='etl.run_ai_summary',
                status='SUCCESS', started_at=started_at
            )
        print('=== [BƯỚC 4/4] Hoàn tất toàn bộ chuỗi etl_master thành công! ===')
        return {'run_id': run_id, 'status': 'SUCCESS'}
    except Exception as e:
        print(f"LỖI ở Bước 4 (ai_explain_etl_runs): {e}")
        if run_id:
            write_run_detail(
                run_id, step_name='ai_explain', table_name='etl.run_ai_summary',
                status='FAILED', error=str(e)[:900], started_at=started_at
            )
        raise
