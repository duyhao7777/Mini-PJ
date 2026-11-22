from adventureworks_bi.utils.etl_helpers import get_connection
from adventureworks_bi.utils.business_ai import sql_string
if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

@data_exporter
def save_trend_explanations(df, *args, **kwargs):
    if df.empty:
        return
    with get_connection() as db:
        for r in df.to_dict('records'):
            db.execute(f"""INSERT INTO ai.insight_explanation
               (month_start,metric_name,comparison_type,change_pct,input_json,explanation_text,
                model_name,verified,verification_note)
               SELECT '{r['month_start']}','sales_amount','MoM',{float(r['change_pct'])},
                {sql_string(r['input_json'])},{sql_string(r['explanation_text'])},
                {sql_string(r['model_name'])},{int(r['verified'])},{sql_string(r['verification_note'])}
               WHERE NOT EXISTS(SELECT 1 FROM ai.insight_explanation WHERE month_start='{r['month_start']}'
                AND metric_name='sales_amount' AND comparison_type='MoM')""")
        db.commit()
    print('Processed',len(df),'trend explanations')
