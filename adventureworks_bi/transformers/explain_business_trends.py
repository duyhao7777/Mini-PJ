import time
import pandas as pd
from adventureworks_bi.utils.ai_helpers import call_gemini, get_model_name
from adventureworks_bi.utils.etl_helpers import get_connection
from adventureworks_bi.utils.business_ai import to_json, json_safe, verify_claims, TREND_RULES
if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

@transformer
def explain_business_trends(df, *args, **kwargs):
    output=[]
    for r in df.to_dict('records'):
        month=str(r['month_start'])[:10]
        with get_connection() as db:
            contributions=db.load(f"""WITH d AS (
                 SELECT dimension_type,dimension_key,dimension_name,sales_amount,prior_month_sales,
                        sales_mom_delta
                 FROM ai.kpi_by_dim WHERE month_start='{month}'
                   AND dimension_type IN ('CATEGORY','TERRITORY')
                 ), ranked AS (
                    SELECT *,ROW_NUMBER() OVER (PARTITION BY dimension_type
                                    ORDER BY ABS(sales_mom_delta) DESC) AS rn FROM d
                 ) SELECT dimension_type,dimension_name,sales_amount,prior_month_sales,
                          sales_mom_delta FROM ranked WHERE rn<=3
                   ORDER BY dimension_type,rn""")
        payload={k:(None if pd.isna(v) else json_safe(v)) for k,v in r.items()}
        payload['contributors']=[{k:json_safe(v) for k,v in row.items()} for row in contributions.to_dict('records')]
        # contribution share calculated against net monthly delta (can exceed 100% when offsets occur)
        total_delta=float(payload['sales_amount'])-float(payload['prior_month_sales'])
        for c in payload['contributors']:
            c['contribution_pct_of_net_change']=round(100*float(c['sales_mom_delta'])/total_delta,2) if total_delta else None
        try:
            result=call_gemini(TREND_RULES+'\nDỮ LIỆU (JSON):\n'+to_json(payload),temperature=0)
            verified,note=verify_claims(result,payload)
            output.append({'month_start':month,'metric_name':'sales_amount','comparison_type':'MoM',
              'change_pct':payload['sales_mom_pct'],'input_json':to_json(payload),
              'explanation_text':result,'model_name':get_model_name(),
              'verified':int(verified),'verification_note':note})
        except Exception as e:
            print('Gemini failed for trend',month,str(e)[:200])
        time.sleep(2)
    return pd.DataFrame(output,columns=['month_start','metric_name','comparison_type','change_pct',
      'input_json','explanation_text','model_name','verified','verification_note'])
