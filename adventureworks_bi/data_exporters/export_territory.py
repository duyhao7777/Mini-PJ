from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path
from os import path

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
        loader.export(
            df,
            'stg',
            'territory',
            index=False,
            if_exists='replace',
        )

