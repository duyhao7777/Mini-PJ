import pandas as pd

from adventureworks_bi.utils.etl_helpers import SALES_COLUMNS, SOURCE_FILE, write_log

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def extract_by_window(control, *args, **kwargs):
    row = control.iloc[0]
    started_at = pd.Timestamp(row['started_at']).to_pydatetime()
    try:
        df = pd.read_csv(SOURCE_FILE, dtype=str, usecols=SALES_COLUMNS)[SALES_COLUMNS]
        order_dt = pd.to_datetime(df['OrderDate'], format='%d/%m/%Y', errors='coerce')
        mask = (order_dt >= pd.Timestamp(row['lset'])) & (order_dt <= pd.Timestamp(row['cet']))
        win = df[mask].copy()
    except Exception as e:
        write_log(row['run_id'], row['load_type'], 'FAILED',
                  lset=row['lset'], cet=row['cet'], error=e, started_at=started_at)
        raise

    win.columns = [c.lower() for c in win.columns]
    win['_row_number'] = win.index + 1
    win['_batch_id'] = row['run_id']
    win['_ctl_load_type'] = row['load_type']
    win['_ctl_lset'] = row['lset']
    win['_ctl_cet'] = row['cet']
    win['_ctl_started_at'] = row['started_at']
    print(f"Trích xuất {len(win)} dòng có OrderDate từ {row['lset']} đến {row['cet']}")
    return win