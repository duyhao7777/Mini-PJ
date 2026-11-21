from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path
from os import path

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_data(*args, **kwargs):
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    with MSSQL.with_config(ConfigFileLoader(config_path, 'default')) as loader:
        return loader.load('SELECT @@VERSION AS version, DB_NAME() AS db')