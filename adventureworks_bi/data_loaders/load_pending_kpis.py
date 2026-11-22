import pandas as pd
from adventureworks_bi.utils.etl_helpers import get_connection
if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

@data_loader
def load_pending_kpis(*args, **kwargs):
    with get_connection() as db:
        df = db.load("""SELECT TOP 10 k.* FROM ai.kpi_monthly k
          WHERE NOT EXISTS (SELECT 1 FROM ai.analytics_summary s WHERE s.month_start=k.month_start)
          ORDER BY k.month_start DESC""")
    return df
