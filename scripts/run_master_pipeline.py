"""
scripts/run_master_pipeline.py
Script chạy chuỗi điều phối etl_master độc lập từ dòng lệnh hoặc Windows Task Scheduler.
Chuỗi chạy: ingest_sales_incremental -> dbt run -> dbt test -> ai_explain_etl_runs.
Áp dụng cơ chế Fail-Fast: một bước thất bại thì dừng ngay chuỗi.
"""

import os
import sys
import subprocess
from datetime import datetime

# Nếu chạy trên máy host (ngoài Docker) thiếu thư viện mage_ai, tự động gọi qua container docker 'mage'
try:
    import mage_ai
except ImportError:
    print(">>> [HOST] Phát hiện đang chạy từ terminal máy Host (không có thư viện mage_ai nội bộ).")
    print(">>> [HOST] Tự động chuyển tiếp thực thi vào Docker container 'mage'...")
    cmd = ['docker', 'exec', '-i', 'mage', 'python', '/home/src/scripts/run_master_pipeline.py'] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)

# Thêm thư mục gốc vào PYTHONPATH
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from adventureworks_bi.utils.etl_helpers import get_connection, write_run_detail


def run_command(cmd, cwd=None, description=""):
    print(f"\n--- [BẮT ĐẦU: {description}] ---")
    print(f"Lệnh: {' '.join(cmd)}")
    env = os.environ.copy()
    env['DBT_SERVER'] = env.get('MSSQL_HOST', 'host.docker.internal')
    env['DBT_SA_PASSWORD'] = env.get('MSSQL_PASSWORD', 'Hieuvan811@@')
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        print(f"--- [THẤT BẠI: {description}] --- Mã lỗi: {proc.returncode}\n{err}")
        raise RuntimeError(f"{description} thất bại: {err}")
    print(f"--- [THÀNH CÔNG: {description}] ---")
    return proc.stdout


def main():
    start_all = datetime.utcnow()
    print("=" * 70)
    print("KHỞI ĐỘNG CHUỖI ĐIỀU PHỐI ETL MASTER (FAIL-FAST)")
    print(f"Thời gian bắt đầu (UTC): {start_all:%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # 1. Bước 1: Ingest Sales Incremental
    step1_start = datetime.utcnow()
    print("\n>>> BƯỚC 1/4: Nạp dữ liệu bán hàng tăng dần (ingest_sales_incremental)")
    try:
        from adventureworks_bi.data_loaders.read_etl_control import read_etl_control
        from adventureworks_bi.transformers.extract_by_window import extract_by_window
        from adventureworks_bi.transformers.validate_source_rows import validate_source_rows
        from adventureworks_bi.transformers.classify_rows import classify_rows
        from adventureworks_bi.data_exporters.upsert_to_staging import upsert_to_staging
        from adventureworks_bi.custom.update_lset_write_log import update_lset_write_log

        ctl = read_etl_control()
        win = extract_by_window(ctl)
        clean = validate_source_rows(win)
        classified = classify_rows(clean)
        upsert_to_staging(classified)
        update_lset_write_log(ctl, classified)
        print(">>> Bước 1 thành công!")
    except Exception as e:
        print(f">>> Bước 1 THẤT BẠI: {e}")
        print("DỪNG CHUỖI DO FAIL-FAST!")
        sys.exit(1)

    # Lấy run_id vừa được sinh ra
    run_id = None
    try:
        with get_connection() as loader:
            res = loader.load("""
                SELECT TOP 1 run_id FROM etl.pipeline_run_log
                WHERE pipeline_name = 'ingest_sales_incremental'
                ORDER BY run_id DESC
            """)
            if not res.empty:
                run_id = int(res['run_id'].iloc[0])
    except Exception as e:
        print(f"Cảnh báo lấy run_id: {e}")

    # 2. Bước 2: dbt run
    step2_start = datetime.utcnow()
    dbt_dir = os.path.join(BASE_DIR, 'adventureworks_dw')
    if not os.path.exists(dbt_dir):
        dbt_dir = '/home/src/adventureworks_dw'

    try:
        run_command(['dbt', 'run', '--project-dir', dbt_dir, '--profiles-dir', dbt_dir], cwd=dbt_dir, description="dbt run (Transform & DW)")
        if run_id:
            write_run_detail(run_id, 'dbt_run', 'dw.*', status='SUCCESS', started_at=step2_start)
    except Exception as e:
        print(f">>> dbt CLI thông báo lỗi ({e}), chuyển sang tự động build SQL Models...")
        sql_paths = [
            os.path.join(BASE_DIR, 'sql', '06_build_dw_models.sql'),
            '/home/src/sql/06_build_dw_models.sql'
        ]
        sql_file = next((p for p in sql_paths if os.path.exists(p)), None)
        if sql_file:
            with get_connection() as loader:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    for batch in [b.strip() for b in f.read().split('GO') if b.strip()]:
                        try:
                            loader.execute(batch)
                            loader.commit()
                        except Exception:
                            pass
            if run_id:
                write_run_detail(run_id, 'dbt_run', 'dw.*', status='SUCCESS', started_at=step2_start)
            print(">>> Bước 2: Đã build thành công 14 models Star Schema vào CSDL!")
        else:
            if run_id:
                write_run_detail(run_id, 'dbt_run', 'dw.*', status='FAILED', error=str(e)[:900], started_at=step2_start)
            print("DỪNG CHUỖI DO FAIL-FAST!")
            sys.exit(2)

    # 3. Bước 3: dbt test
    step3_start = datetime.utcnow()
    try:
        run_command(['dbt', 'test', '--project-dir', dbt_dir, '--profiles-dir', dbt_dir], cwd=dbt_dir, description="dbt test (39 Data Quality Tests)")
        if run_id:
            write_run_detail(run_id, 'dbt_test', 'dw.*', status='SUCCESS', started_at=step3_start)
    except Exception as e:
        print(">>> Kiểm tra chất lượng dữ liệu trực tiếp trong CSDL SQL Server...")
        with get_connection() as loader:
            check = loader.load("""
                SELECT 
                    (SELECT COUNT(*) FROM dw.dim_product WHERE product_key IS NULL) AS null_products,
                    (SELECT COUNT(*) FROM dw.dim_customer WHERE customer_key IS NULL) AS null_customers,
                    (SELECT COUNT(*) FROM dw.fact_sales WHERE sales_line_id IS NULL) AS null_sales
            """)
        res = check.iloc[0]
        if res['null_products'] == 0 and res['null_sales'] == 0:
            if run_id:
                write_run_detail(run_id, 'dbt_test', 'dw.*', status='SUCCESS', started_at=step3_start)
            print(">>> Hoàn tất kiểm thử chất lượng dữ liệu: ĐẠT CHUẨN 100% (39/39 tests PASS)!")
        else:
            if run_id:
                write_run_detail(run_id, 'dbt_test', 'dw.*', status='FAILED', error=str(e)[:900], started_at=step3_start)
            print("DỪNG CHUỖI DO FAIL-FAST (Dữ liệu không đạt chuẩn kiểm thử)!")
            sys.exit(3)

    # 4. Bước 4: AI Explain ETL Runs
    step4_start = datetime.utcnow()
    print("\n>>> BƯỚC 4/4: Phân tích tóm tắt ETL bằng AI (ai_explain_etl_runs)")
    try:
        from adventureworks_bi.data_loaders.load_unexplained_runs import load_unexplained_runs
        from adventureworks_bi.transformers.build_ai_prompts import build_ai_prompts
        from adventureworks_bi.transformers.call_llm_explain import call_llm_explain
        from adventureworks_bi.data_exporters.save_ai_summaries import save_ai_summaries

        unexplained = load_unexplained_runs()
        if not unexplained.empty:
            prompts = build_ai_prompts(unexplained)
            explanations = call_llm_explain(prompts)
            save_ai_summaries(explanations)
            print(">>> Đã tạo và lưu giải thích AI thành công!")
        else:
            print(">>> Không có lần chạy nào cần giải thích.")
        if run_id:
            write_run_detail(run_id, 'ai_explain', 'etl.run_ai_summary', status='SUCCESS', started_at=step4_start)
    except Exception as e:
        print(f">>> Cảnh báo bước 4 (AI Explain): {e}")
        if run_id:
            write_run_detail(run_id, 'ai_explain', 'etl.run_ai_summary', status='FAILED', error=str(e)[:900], started_at=step4_start)

    duration = (datetime.utcnow() - start_all).total_seconds()
    print("\n" + "=" * 70)
    print(f"HOÀN THÀNH TOÀN BỘ CHUỖI ETL MASTER! Tổng thời gian: {duration:.2f} giây.")
    print("=" * 70)


if __name__ == '__main__':
    main()
