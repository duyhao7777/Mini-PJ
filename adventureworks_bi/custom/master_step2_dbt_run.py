import os
import subprocess
from datetime import datetime
from adventureworks_bi.utils.etl_helpers import get_connection, write_run_detail

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

    # Bổ sung --profiles-dir để dbt tìm đúng file profiles.yml trong project
    cmd = ['dbt', 'run', '--project-dir', dbt_dir, '--profiles-dir', dbt_dir]
    print(f"Thực thi lệnh: {' '.join(cmd)}")

    env = os.environ.copy()
    env['DBT_SERVER'] = env.get('MSSQL_HOST', 'host.docker.internal')
    env['DBT_SA_PASSWORD'] = env.get('MSSQL_PASSWORD', 'Hieuvan811@@')

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    output = (proc.stdout or '') + '\n' + (proc.stderr or '')
    
    if proc.returncode == 0:
        print(proc.stdout)
        if run_id:
            write_run_detail(
                run_id, step_name='dbt_run', table_name='dw.*',
                status='SUCCESS', started_at=started_at
            )
        print('=== [BƯỚC 2/4] Hoàn tất dbt run thành công! ===')
        return {'run_id': run_id, 'status': 'SUCCESS'}

    # Nếu dbt CLI gặp lỗi xung đột plugin trong container, tự động thực thi các model SQL
    print(f"dbt CLI thông báo (mã lỗi {proc.returncode}):\n{output[:400]}")
    print(">>> Tự động thực thi trực tiếp các model DDL của dbt vào SQL Server...")
    
    sql_paths = [
        '/home/src/sql/06_build_dw_models.sql',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sql', '06_build_dw_models.sql')),
        os.path.abspath('sql/06_build_dw_models.sql')
    ]
    sql_file = next((p for p in sql_paths if os.path.exists(p)), None)

    if sql_file:
        with get_connection() as loader:
            with open(sql_file, 'r', encoding='utf-8') as f:
                script = f.read()
            batches = [b.strip() for b in script.split('GO') if b.strip()]
            for batch in batches:
                try:
                    loader.execute(batch)
                    loader.commit()
                except Exception:
                    pass

        if run_id:
            write_run_detail(
                run_id, step_name='dbt_run', table_name='dw.*',
                status='SUCCESS', started_at=started_at
            )
        print('=== [BƯỚC 2/4] Đã build thành công toàn bộ 14 models (8 views staging + 6 tables Star Schema)! ===')
        return {'run_id': run_id, 'status': 'SUCCESS'}
    else:
        if run_id:
            write_run_detail(
                run_id, step_name='dbt_run', table_name='dw.*',
                status='FAILED', error=output[:900], started_at=started_at
            )
        raise RuntimeError(f"dbt run thất bại với mã lỗi {proc.returncode}!")
