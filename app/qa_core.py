"""Logic lõi Q&A: câu hỏi TV -> SQL (kiểm duyệt) -> bảng (qa_reader) -> giải thích + đối chiếu số.

Không phụ thuộc Streamlit nên có thể test riêng. Prompt nằm ở qa_prompts.py.
"""
import json
import os
import re
import sys
import time

import pandas as pd
import pyodbc
import requests

# Repo được mount tại /home/src; thêm cả 2 thư mục để import được module của B
# lẫn qa_prompts dù chạy từ bất kỳ working directory nào.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_APP_DIR)
for _path in (_APP_DIR, _ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from adventureworks_bi.utils.business_ai import to_json, verify_claims  # noqa: E402
from qa_prompts import EXPLAIN_RULES, sql_prompt  # noqa: E402

# --- Cấu hình ---------------------------------------------------------------
DB_HOST = os.environ.get('MSSQL_HOST', 'host.docker.internal')
DB_NAME = 'BI_AdventureWorks'
DB_USER = 'qa_reader'                       # chỉ đọc, không dùng sa
DB_PASS = os.environ['MSSQL_PASSWORD']
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
GEMINI_URL = (
    'https://generativelanguage.googleapis.com/v1beta/models/'
    f'{GEMINI_MODEL}:generateContent'
)

ALLOWED_VIEWS = (
    'ai.v_kpi_monthly',
    'ai.v_kpi_by_dim',
    'ai.v_latest_summary',
    'ai.v_trend_explain',
)
_ALLOWED = {v.lower() for v in ALLOWED_VIEWS}

# Một phản hồi chung cho mọi từ chối / lỗi: không lộ từ khoá, câu gốc, SQL hay exception.
GENERIC_DENIAL = 'Yêu cầu không được hỗ trợ. Hệ thống chỉ trả lời câu hỏi về số liệu KPI.'
GENERIC_ERROR = 'Không thể xử lý yêu cầu lúc này. Vui lòng thử lại sau.'

_FENCE = re.compile(r'^\s*```(?:sql)?\s*|\s*```\s*$', re.I | re.M)
_BANNED = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC|EXECUTE|MERGE|'
    r'GRANT|REVOKE|CREATE|SHUTDOWN|SP_\w+|XP_\w+)\b', re.I
)
_TABLE_REF = re.compile(
    r'\b(?:FROM|JOIN)\s+(\[?[A-Za-z_]\w*\]?(?:\.\[?[A-Za-z_]\w*\]?)?)', re.I
)
_DESTRUCTIVE = re.compile(
    r'(xoá|xoá|xóa|delete|drop|truncate|huỷ|hủy|sửa|update|cập\s*nhật|'
    r'insert|thêm\s+mới|ghi\s+đè|alter|create\s+table|exec|grant|revoke|'
    r'mật\s+khẩu|password|\bsa\b|tài\s+khoản\s+sa)',
    re.I,
)
_NOTE = re.compile(r'(?i)(?:\*\*)?\s*Lưu\s*ý\s*(?:\*\*)?\s*:\s*')
_SELECT_HEAD = re.compile(r'^(\s*SELECT\s+(?:DISTINCT\s+)?)', re.I)
_HAS_TOP = re.compile(r'\s*TOP\s*\(?\s*\d+', re.I)


# --- Truy cập dữ liệu -------------------------------------------------------
def connect():
    conn_str = (
        'DRIVER={ODBC Driver 18 for SQL Server};'
        f'SERVER={DB_HOST},1433;DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASS};'
        'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str, autocommit=True)


def load_schema():
    """Lấy cột của 4 view để nhét vào prompt sinh SQL."""
    with connect() as cn:
        rows = cn.cursor().execute("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'ai' AND TABLE_NAME LIKE 'v_%'
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """).fetchall()
    schema = {}
    for table, column, dtype in rows:
        schema.setdefault('ai.' + table, []).append(f'{column} ({dtype})')
    return schema


def fetch(sql):
    """Chạy câu SELECT đã qua kiểm duyệt, trả DataFrame."""
    with connect() as cn:
        cur = cn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        return pd.DataFrame.from_records(cur.fetchall(), columns=cols)


# --- Gemini -----------------------------------------------------------------
def call_gemini(prompt, temperature=0.0, max_retries=3):
    """Gọi Gemini, retry 429/500/503 (cùng pattern với utils/ai_helpers.py của B)."""
    if not GEMINI_KEY:
        raise RuntimeError('Chưa cấu hình GEMINI_API_KEY')
    headers = {'x-goog-api-key': GEMINI_KEY, 'Content-Type': 'application/json'}
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperature, 'maxOutputTokens': 2048},
    }
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(GEMINI_URL, headers=headers, json=body, timeout=(10, 120))
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


# --- Guardrail --------------------------------------------------------------
def _deny():
    raise ValueError(GENERIC_DENIAL)


def check_intent(question):
    """Chặn ý định phá hoại TRƯỚC khi gọi LLM (đỡ quota, không lộ trạng thái)."""
    if _DESTRUCTIVE.search(question):
        _deny()


def validate_sql(raw_sql):
    """Chỉ chấp nhận 1 câu SELECT trên 4 view ai.v_*; tự ép TOP 100."""
    sql = _FENCE.sub('', raw_sql.strip()).strip().rstrip(';').strip()
    if not re.match(r'^\s*SELECT\b', sql, re.I):
        _deny()
    if _BANNED.search(sql) or any(c in sql for c in (';', '--', '/*')):
        _deny()
    for m in _TABLE_REF.finditer(sql):
        ref = m.group(1).replace('[', '').replace(']', '').lower()
        if ref not in _ALLOWED:
            _deny()
    head = _SELECT_HEAD.match(sql)
    if head and not _HAS_TOP.match(sql[head.end():]):
        sql = head.group(1) + 'TOP 100 ' + sql[head.end():]
    return sql


# --- Giải thích & kiểm chứng ------------------------------------------------
def split_explanation(text):
    """Tách đoạn 'Lưu ý:' ra khỏi thân chính để gom vào expander đóng."""
    text = (text or '').strip()
    m = _NOTE.search(text)
    if not m:
        return text, ''
    return (text[:m.start()].strip().rstrip('* ').strip(),
            text[m.end():].strip().lstrip('* ').strip())


def explain_result(question, sql, df):
    """Giải thích bảng rồi đối chiếu từng số với chính bảng đó.

    Dùng to_json (Decimal -> float, date -> ISO); default=str sẽ biến số thành
    chuỗi "Decimal('...')" khiến verify_claims đánh verified=0 oan.
    """
    payload = {
        'cau_hoi': question,
        'sql': sql,
        'so_dong': int(len(df)),
        'du_lieu': json.loads(to_json(df.head(20).to_dict('records'))),
    }
    text = call_gemini(
        EXPLAIN_RULES + '\nDỮ LIỆU (JSON):\n' + to_json(payload),
        temperature=0.0,
    )
    verified, note = verify_claims(text, payload)
    return text, bool(verified), note


# --- Entry point ------------------------------------------------------------
def ask(question):
    """Trả dict: sql, df, explanation, verified, verification_note, blocked, error."""
    result = {'sql': None, 'df': None, 'explanation': None,
              'verified': None, 'verification_note': None,
              'blocked': False, 'error': None}
    try:
        check_intent(question)
        sql = validate_sql(call_gemini(sql_prompt(question, load_schema())))
        result['sql'] = sql                      # chỉ gán sau khi đã qua kiểm duyệt
        result['df'] = fetch(sql)
        text, ok, note = explain_result(question, sql, result['df'])
        result.update(explanation=text, verified=ok, verification_note=note)
    except ValueError:
        result.update(blocked=True, error=GENERIC_DENIAL, sql=None)
    except Exception as e:
        print('[qa_core] internal error:', repr(e))   # log server, không đẩy ra UI
        result.update(error=GENERIC_ERROR, sql=None)
    return result
