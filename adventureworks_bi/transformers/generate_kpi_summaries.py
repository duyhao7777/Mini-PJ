import time
import pandas as pd
from adventureworks_bi.utils.ai_helpers import call_gemini, get_model_name
from adventureworks_bi.utils.business_ai import to_json, json_safe, verify_claims, SUMMARY_RULES
if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

@transformer
def generate_kpi_summaries(df, *args, **kwargs):
    output=[]
    for row in df.to_dict('records'):
        payload={k:(None if pd.isna(v) else json_safe(v)) for k,v in row.items()}
        prompt=SUMMARY_RULES + '\nKPI (JSON):\n' + to_json(payload)
        try:
            result=call_gemini(prompt, temperature=0)
            verified,note=verify_claims(result,payload)
            output.append({'month_start': str(payload['month_start'])[:10],
                           'input_json':to_json(payload),'summary_text':result,
                           'model_name':get_model_name(),'verified':int(verified),
                           'verification_note':note})
        except Exception as e:
            print('Gemini failed for', payload['month_start'], str(e)[:200])
        time.sleep(2)
    return pd.DataFrame(output,columns=['month_start','input_json','summary_text','model_name','verified','verification_note'])
