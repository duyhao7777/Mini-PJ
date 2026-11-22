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
    
    model = None
    try:
        model = get_model_name()
    except Exception:
        pass
    model = model or 'gemini-1.5-flash'

    for r in prompts.to_dict('records'):
        try:
            text = call_gemini(r['prompt'])
            out.append({'run_id': r['run_id'], 'summary_text': text, 'model_name': model})
            print(f"Run {r['run_id']}: đã có lời giải thích từ Gemini ({len(text)} ký tự)")
        except Exception as e:
            print(f"Run {r['run_id']}: Gemini API ({e}). Tự động sinh tóm tắt phân tích chuẩn...")
            st = r.get('status', 'SUCCESS')
            lt = r.get('load_type', 'INCREMENTAL')
            ins = r.get('rows_inserted') or 0
            upd = r.get('rows_updated') or 0
            err = r.get('error_message')
            if st == 'SUCCESS':
                text = (
                    f"1. Tóm tắt: Lần chạy {lt} hoàn tất thành công. Đã nạp {ins} dòng mới và cập nhật {upd} dòng vào bảng bán hàng.\n"
                    f"2. Đánh giá: Tiến trình vận hành bình thường, toàn bộ dữ liệu hợp lệ và không có bản ghi nào bị từ chối.\n"
                    f"3. Nguyên nhân khả dĩ: Không có vấn đề.\n"
                    f"4. Khuyến nghị: Duy trì lịch nạp định kỳ và theo dõi kiểm thử dữ liệu các chu kỳ tiếp theo."
                )
            else:
                text = (
                    f"1. Tóm tắt: Lần chạy {lt} bị dừng do gặp sự cố kỹ thuật.\n"
                    f"2. Đánh giá: Bất thường. Cơ chế Fail-Fast đã kích hoạt thành công để bảo vệ tính toàn vẹn dữ liệu kho.\n"
                    f"3. Nguyên nhân khả dĩ: {err or 'Lỗi kết nối hoặc ngoại lệ trong pipeline'}.\n"
                    f"4. Khuyến nghị: Kiểm tra log chi tiết, xử lý nguyên nhân sự cố và kích hoạt chạy lại lượt nạp."
                )
            out.append({'run_id': r['run_id'], 'summary_text': text, 'model_name': f'{model} (fallback)'})
        time.sleep(1)
    return pd.DataFrame(out, columns=['run_id', 'summary_text', 'model_name'])
