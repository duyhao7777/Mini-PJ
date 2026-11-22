import pandas as pd
from adventureworks_bi.utils.etl_helpers import get_connection
if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

@data_loader
def load_trend_candidates(*args, **kwargs):
    with get_connection() as db:
        return db.load("""SELECT TOP 10 k.month_start,k.sales_amount,k.prior_month_sales,
            k.sales_mom_pct, k.profit_amount,k.order_count
            FROM ai.kpi_monthly k
            WHERE k.sales_mom_pct IS NOT NULL AND ABS(k.sales_mom_pct)>=20
              AND NOT EXISTS (SELECT 1 FROM ai.insight_explanation i
                              WHERE i.month_start=k.month_start AND i.metric_name='sales_amount'
                              AND i.comparison_type='MoM')
            ORDER BY k.month_start DESC""")
