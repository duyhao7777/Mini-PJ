import os
import subprocess
from datetime import datetime
from adventureworks_bi.utils.etl_helpers import write_run_detail

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def master_step2_dbt_run(data, *args, **kwargs):
    started_at = datetime.utcnow()
    run_id = data.get('run_id') if isinstance(data, dict) else None
    print('=== [BƯỚC 2/4] Chạy dbt run (Tạo Views Staging và Tables Star Schema) ===')

    paths_to_try = [
        '/home/src/adventureworks_dw',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'adventureworks_dw')),
        os.path.abspath('adventureworks_dw')
    ]
    dbt_dir = next((p for p in paths_to_try if os.path.exists(p)), None)
    if not dbt_dir:
        raise FileNotFoundError('Không tìm thấy thư mục adventureworks_dw để chạy dbt!')

    cmd = ['dbt', 'run', '--project-dir', dbt_dir]
    print(f"Thực thi lệnh: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    print(proc.stdout)
    if proc.returncode != 0:
        err_msg = (proc.stderr or proc.stdout).strip()
        print(f"dbt run THẤT BẠI:\n{err_msg}")
        if run_id:
            write_run_detail(
                run_id, step_name='dbt_run', table_name='dw.*',
                status='FAILED', error=err_msg[:900], started_at=started_at
            )
        raise RuntimeError(f"dbt run thất bại với mã lỗi {proc.returncode}!")

    if run_id:
        write_run_detail(
            run_id, step_name='dbt_run', table_name='dw.*',
            status='SUCCESS', started_at=started_at
        )

    print('=== [BƯỚC 2/4] Hoàn tất dbt run thành công! ===')
    return {'run_id': run_id, 'status': 'SUCCESS'}
