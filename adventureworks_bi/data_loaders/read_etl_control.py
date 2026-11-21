import pandas as pd
from datetime import datetime

from adventureworks_bi.utils.etl_helpers import (
    SOURCE_FILE, SOURCE_KEY, get_connection, new_run_id, write_log,
)

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def read_etl_control(*args, **kwargs):
    started_at = datetime.utcnow()
    run_id = new_run_id(started_at)
    lset_text = None
    try:
        with get_connection() as loader:
            ctl = loader.load(
                "SELECT lset, cet_override FROM etl.etl_control "
                f"WHERE source_name = '{SOURCE_KEY}'"
            )
        if ctl.empty:
            raise ValueError(f"Chưa có dòng '{SOURCE_KEY}' trong etl.etl_control")

        lset = pd.Timestamp(ctl['lset'].iloc[0]).normalize()
        lset_text = lset.strftime('%Y-%m-%d')
        override = ctl['cet_override'].iloc[0]
        if pd.notna(override):
            cet = pd.Timestamp(override).normalize()
            cet_source = 'cet_override'
        else:
            dates = pd.read_csv(SOURCE_FILE, dtype=str, usecols=['OrderDate'])['OrderDate']
            cet = pd.to_datetime(dates, format='%d/%m/%Y', errors='coerce').max().normalize()
            cet_source = 'ngày lớn nhất của nguồn'
    except Exception as e:
        try:
            write_log(run_id, 'UNKNOWN', 'FAILED', lset=lset_text, error=e, started_at=started_at)
        except Exception:
            pass   # nếu chính database lỗi thì không ghi log được, vẫn báo lỗi gốc
        raise

    load_type = 'FULL' if lset <= pd.Timestamp('1900-01-01') else 'INCREMENTAL'
    print(f'{run_id} ({load_type}): LSET = {lset.date()}, CET = {cet.date()} ({cet_source})')
    return pd.DataFrame([{
        'run_id': run_id,
        'load_type': load_type,
        'lset': lset.strftime('%Y-%m-%d'),
        'cet': cet.strftime('%Y-%m-%d'),
        'cet_source': cet_source,
        'started_at': started_at.strftime('%Y-%m-%d %H:%M:%S'),
    }])