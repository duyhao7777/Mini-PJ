import pandas as pd

from adventureworks_bi.utils.etl_helpers import (
    MERGE_SQL, STAGING_COLS, get_connection, write_log,
)

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def upsert_to_staging(df, *args, **kwargs):
    if df.empty or '_change_type' not in df.columns:
        print('Không có dữ liệu trong cửa sổ. Bỏ qua bước nạp.')
        return

    changes = df[df['_change_type'].isin(['NEW', 'CHANGED'])]
    if changes.empty:
        print('Không có dòng mới hoặc thay đổi. Bỏ qua bước nạp.')
        return

    out = changes[STAGING_COLS]
    try:
        with get_connection() as loader:
            oid = loader.load("SELECT OBJECT_ID('stg.sales', 'U') AS oid")['oid'].iloc[0]
            if pd.isna(oid):
                # Lần đầu: chưa có bảng, nạp thẳng (Full Load)
                loader.export(out, 'stg', 'sales', index=False, if_exists='append')
            else:
                # Các lần sau: nạp vào bảng tạm rồi MERGE (upsert)
                loader.export(out, 'stg', 'sales_delta', index=False, if_exists='replace')
                loader.execute(MERGE_SQL)
                loader.commit()
                loader.execute('DROP TABLE stg.sales_delta')
                loader.commit()
        print(f'Đã nạp {len(out)} dòng vào stg.sales')
    except Exception as e:
        write_log(df['_batch_id'].iloc[0], df['_ctl_load_type'].iloc[0], 'FAILED',
                  lset=df['_ctl_lset'].iloc[0], cet=df['_ctl_cet'].iloc[0],
                  rows_read=int(df['_ctl_rows_read'].iloc[0]), error=e,
                  started_at=pd.Timestamp(df['_ctl_started_at'].iloc[0]).to_pydatetime())
        raise