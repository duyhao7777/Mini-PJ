import numpy as np
import pandas as pd

from adventureworks_bi.utils.etl_helpers import KEY_COLS, VALUE_COLS, get_connection

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def classify_rows(src, *args, **kwargs):
    if src.empty:
        src = src.copy()
        src['_change_type'] = pd.Series(dtype='object')
        return src

    cols = KEY_COLS + VALUE_COLS
    with get_connection() as loader:
        oid = loader.load("SELECT OBJECT_ID('stg.sales', 'U') AS oid")['oid'].iloc[0]
        if pd.notna(oid):
            stg = loader.load('SELECT ' + ', '.join(cols) + ' FROM stg.sales')
        else:
            stg = pd.DataFrame(columns=cols)

    src = src.copy()
    src['_key'] = src['ordernumber'] + '|' + src['orderlineitem']
    stg = stg.drop_duplicates(subset=KEY_COLS).copy()
    stg['_key'] = stg['ordernumber'] + '|' + stg['orderlineitem']
    stg = stg.set_index('_key')

    in_stg = src['_key'].isin(stg.index)
    changed = pd.Series(False, index=src.index)
    if in_stg.any():
        left = src.loc[in_stg, ['_key'] + VALUE_COLS].set_index('_key').fillna('')
        right = stg.loc[left.index, VALUE_COLS].fillna('')
        changed.loc[in_stg] = (left != right).any(axis=1).values

    src['_change_type'] = np.where(~in_stg, 'NEW', np.where(changed, 'CHANGED', 'UNCHANGED'))
    src = src.drop(columns=['_key'])

    counts = src['_change_type'].value_counts()
    print(f"Phân loại: mới {int(counts.get('NEW', 0))}, thay đổi {int(counts.get('CHANGED', 0))}, "
          f"không đổi {int(counts.get('UNCHANGED', 0))}")
    return src