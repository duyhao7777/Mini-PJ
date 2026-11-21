import time
import requests
from mage_ai.data_preparation.shared.secrets import get_secret_value

BASE = 'https://generativelanguage.googleapis.com/v1beta'


def get_model_name():
    return get_secret_value('GEMINI_MODEL')


def call_gemini(prompt, max_retries=3, temperature=0.2):
    """Gọi Gemini API. Thử lại khi quá tải (429, 500, 503); lỗi khác thì dừng ngay."""
    headers = {'x-goog-api-key': get_secret_value('GEMINI_API_KEY'),
               'Content-Type': 'application/json'}
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperature, 'maxOutputTokens': 2048},
    }
    url = f'{BASE}/models/{get_model_name()}:generateContent'
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=(10, 120))
        except requests.RequestException as e:
            last_error = str(e)[:200]
            time.sleep(3 * attempt)
            continue
        if r.status_code in (429, 500, 503):
            last_error = f'HTTP {r.status_code}'
            time.sleep(5 * attempt)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f'HTTP {r.status_code}: {r.text[:200]}')
        parts = r.json()['candidates'][0]['content']['parts']
        text = ''.join(p.get('text', '') for p in parts).strip()
        if text:
            return text
        last_error = 'phản hồi rỗng'
    raise RuntimeError(f'Gọi AI thất bại sau {max_retries} lần: {last_error}')