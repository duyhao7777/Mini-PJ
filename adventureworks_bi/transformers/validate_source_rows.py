from datetime import datetime

from adventureworks_bi.utils.etl_helpers import SOURCE_NAME

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def validate_source_rows(df, *args, **kwargs):
    if df.empty:
        print('Cửa sổ trích xuất không có dòng nào.')
        return df

    key_ok = df['ordernumber'].notna() & df['orderlineitem'].notna()
    dup = df.duplicated(subset=['ordernumber', 'orderlineitem'], keep='first') & key_ok
    valid = key_ok & ~dup
    rejected = int((~valid).sum())

    clean = df[valid].copy()
    clean['_ctl_rows_read'] = len(df)
    clean['_ctl_rows_rejected'] = rejected
    clean['_source_file'] = SOURCE_NAME
    clean['_loaded_at'] = datetime.utcnow()
    print(f'Kiểm tra: hợp lệ {len(clean)} dòng, bị loại {rejected} dòng (thiếu khoá hoặc trùng khoá)')
    return clean