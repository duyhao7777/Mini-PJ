import pandas as pd

from adventureworks_bi.utils.etl_helpers import SOURCE_KEY, get_connection, write_log

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def update_lset_write_log(*upstream, **kwargs):
    dfs = [d for d in upstream if isinstance(d, pd.DataFrame)]
    control = next(d for d in dfs if 'cet_source' in d.columns)
    data = next((d for d in dfs if '_change_type' in d.columns), None)
    row = control.iloc[0]

    rows_read = rows_rejected = inserted = updated = unchanged = 0
    if data is not None and not data.empty:
        counts = data['_change_type'].value_counts()
        inserted = int(counts.get('NEW', 0))
        updated = int(counts.get('CHANGED', 0))
        unchanged = int(counts.get('UNCHANGED', 0))
        rows_read = int(data['_ctl_rows_read'].iloc[0])
        rows_rejected = int(data['_ctl_rows_rejected'].iloc[0])

    # LSET = CET, chỉ chạy khi các bước trước đã thành công; không lùi mốc
    with get_connection() as loader:
        loader.execute(f"""
            UPDATE etl.etl_control
            SET lset = CASE WHEN '{row['cet']}' > lset THEN '{row['cet']}' ELSE lset END,
                cet = '{row['cet']}',
                cet_override = NULL,
                last_run_id = '{row['run_id']}',
                updated_at = SYSUTCDATETIME()
            WHERE source_name = '{SOURCE_KEY}'
        """)
        loader.commit()

    write_log(row['run_id'], row['load_type'], 'SUCCESS',
              lset=row['lset'], cet=row['cet'], rows_read=rows_read,
              rows_inserted=inserted, rows_updated=updated, rows_unchanged=unchanged,
              rows_rejected=rows_rejected,
              started_at=pd.Timestamp(row['started_at']).to_pydatetime())
    print(f"SUCCESS {row['run_id']} ({row['load_type']}): mới {inserted}, thay đổi {updated}, "
          f"không đổi {unchanged}. LSET mới = {row['cet']}")