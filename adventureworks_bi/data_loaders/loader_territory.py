import pandas as pd
from datetime import datetime

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_data(*args, **kwargs):
    file_name = 'AdventureWorks Territory Lookup.csv'
    df = pd.read_csv(
        f'/home/src/data/{file_name}',
        dtype=str,
        encoding='latin-1',
    )
    df['_source_file'] = file_name
    df['_loaded_at'] = datetime.utcnow()
    return df