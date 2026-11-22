import json
import pandas as pd

from adventureworks_bi.utils.etl_helpers import PIPELINE_NAME, get_connection

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

RULES = """Bạn là kỹ sư dữ liệu đang giám sát pipeline ETL của hệ thống BI bán hàng AdventureWorks.
Hãy giải thích kết quả MỘT lần chạy ETL bằng tiếng Việt, ngắn gọn (tối đa 140 từ), để người không chuyên kỹ thuật cũng hiểu.
Quy tắc: chỉ dùng số liệu trong dữ liệu được cung cấp, không bịa nguyên nhân hay số liệu; nếu không đủ thông tin thì nói rõ.
Trình bày đúng 4 mục, mỗi mục một dòng bắt đầu bằng nhãn:
1. Tóm tắt: chuyện gì đã xảy ra trong lần chạy.
2. Đánh giá: bình thường hay bất thường, nêu căn cứ bằng số liệu (so với các lần chạy trước nếu có).
3. Nguyên nhân khả dĩ: chỉ khi trạng thái là FAILED hoặc có dòng bị loại; còn lại ghi "Không có vấn đề."
4. Khuyến nghị: việc cần làm tiếp theo.
- Không giả định hệ thống đã có lịch chạy tự động hay công cụ nào ngoài những gì được nêu trong dữ liệu.
- Khuyến nghị phải cụ thể, khả thi và dựa trên dữ liệu, ví dụ: chạy dbt run và dbt test để cập nhật Data Warehouse; nếu FAILED thì đọc thông báo lỗi, sửa nguyên nhân rồi chạy lại.
- Phân biệt rõ rows_read (số dòng đọc trong cửa sổ) với rows_inserted (số dòng thật sự được thêm mới).

Giải thích dữ liệu:
- LSET là mốc trích xuất thành công gần nhất; CET là mốc của lần chạy này. FULL là lần nạp đầu (LSET = 1900-01-01), INCREMENTAL chỉ xử lý dòng có ngày đặt hàng từ LSET đến CET.
- rows_inserted là dòng mới; rows_updated là dòng đã có nhưng nội dung thay đổi; rows_unchanged là dòng đã có và không đổi
  (ở lần INCREMENTAL, rows_unchanged thường gồm các đơn của đúng ngày LSET được đọc lại, đây là bình thường).
- rows_rejected là dòng bị loại vì thiếu hoặc trùng khoá. Nếu status là FAILED thì LSET không tiến và lần sau sẽ trích lại.
"""


@transformer
def build_ai_prompts(runs, *args, **kwargs):
    if runs.empty:
        return pd.DataFrame(columns=['run_id', 'prompt'])

    rows = []
    with get_connection() as loader:
        for r in runs.to_dict('records'):
            hist = loader.load(f"""
                SELECT TOP 5 run_id, load_type, status, rows_read, rows_inserted,
                       rows_updated, rows_unchanged, rows_rejected
                FROM etl.pipeline_run_log
                WHERE pipeline_name = '{PIPELINE_NAME}' AND run_id < {int(r['run_id'])}
                ORDER BY run_id DESC
            """)
            current = {k: (None if pd.isna(v) else (v.item() if hasattr(v, 'item') else v))
                       for k, v in r.items()}
            history = hist.astype(object).where(hist.notna(), None).to_dict('records')
            prompt = (RULES + '\nLẦN CHẠY CẦN GIẢI THÍCH (JSON):\n'
                      + json.dumps(current, ensure_ascii=False, default=str)
                      + '\n\nCÁC LẦN CHẠY TRƯỚC (mới nhất trước, có thể rỗng):\n'
                      + json.dumps(history, ensure_ascii=False, default=str))
            rows.append({
                'run_id': int(r['run_id']),
                'prompt': prompt,
                'status': r.get('status'),
                'load_type': r.get('load_type'),
                'rows_inserted': r.get('rows_inserted'),
                'rows_updated': r.get('rows_updated'),
                'error_message': r.get('error_message')
            })
    print(f'Đã tạo {len(rows)} prompt')
    return pd.DataFrame(rows)
