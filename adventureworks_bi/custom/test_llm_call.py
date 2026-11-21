import time
import requests
from mage_ai.data_preparation.shared.secrets import get_secret_value

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def test_llm_call(*args, **kwargs):
    api_key = get_secret_value('GEMINI_API_KEY')
    model = get_secret_value('GEMINI_MODEL')
    headers = {'x-goog-api-key': api_key, 'Content-Type': 'application/json'}
    base = 'https://generativelanguage.googleapis.com/v1beta'

    # 1. Kiểm tra kết nối và key: liệt kê các model dùng được
    t = time.time()
    r = requests.get(f'{base}/models?pageSize=200', headers=headers, timeout=(10, 30))
    print('Liệt kê model: HTTP', r.status_code, f'({time.time() - t:.1f}s)')
    r.raise_for_status()
    names = [m['name'].split('/')[-1] for m in r.json().get('models', [])
             if 'generateContent' in m.get('supportedGenerationMethods', [])]
    print('Các model flash dùng được:', [n for n in names if 'flash' in n][:15])
    print('GEMINI_MODEL đang đặt:', model, '->', 'HỢP LỆ' if model in names else 'KHÔNG có trong danh sách')

    # 2. Gọi thử sinh văn bản
    t = time.time()
    body = {'contents': [{'parts': [{'text': 'Trả lời đúng một câu tiếng Việt: pipeline ETL là gì?'}]}]}
    r = requests.post(f'{base}/models/{model}:generateContent',
                      headers=headers, json=body, timeout=(10, 120))
    print('Sinh văn bản: HTTP', r.status_code, f'({time.time() - t:.1f}s)')
    r.raise_for_status()
    parts = r.json()['candidates'][0]['content']['parts']
    print(''.join(p.get('text', '') for p in parts))