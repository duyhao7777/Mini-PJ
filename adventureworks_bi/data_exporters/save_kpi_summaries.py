from adventureworks_bi.utils.etl_helpers import get_connection
from adventureworks_bi.utils.business_ai import sql_string
if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

@data_exporter
def save_kpi_summaries(df, *args, **kwargs):
    if df.empty:
        return
    with get_connection() as db:
        for r in df.to_dict('records'):
            d=r['month_start']
            db.execute(f"""INSERT INTO ai.analytics_summary
              (month_start,input_json,summary_text,model_name,verified,verification_note)
              SELECT '{d}',{sql_string(r['input_json'])},{sql_string(r['summary_text'])},
                     {sql_string(r['model_name'])},{int(r['verified'])},{sql_string(r['verification_note'])}
              WHERE NOT EXISTS(SELECT 1 FROM ai.analytics_summary WHERE month_start='{d}')""")
        db.commit()
    print('Processed',len(df),'AI monthly summaries')
