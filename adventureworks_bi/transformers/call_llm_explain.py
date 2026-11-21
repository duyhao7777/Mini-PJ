import time
import pandas as pd

from adventureworks_bi.utils.ai_helpers import call_gemini, get_model_name

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def call_llm_explain(prompts, *args, **kwargs):
    out = []
    if prompts.empty:
        return pd.DataFrame(columns=['run_id', 'summary_text', 'model_name'])
    model = get_model_name()
    for r in prompts.to_dict('records'):
        try:
            text = call_gemini(r['prompt'])
            out.append({'run_id': r['run_id'], 'summary_text': text, 'model_name': model})
            print(f"Run {r['run_id']}: đã có lời giải thích ({len(text)} ký tự)")
        except Exception as e:
            # Lỗi AI không làm hỏng pipeline; lần chạy này sẽ được thử lại ở lượt sau
            print(f"Run {r['run_id']}: bỏ qua do lỗi AI: {e}")
        time.sleep(2)   # giãn cách để không vượt giới hạn tốc độ của gói miễn phí
    return pd.DataFrame(out, columns=['run_id', 'summary_text', 'model_name'])