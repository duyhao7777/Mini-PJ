"""Streamlit UI cho Q&A tiếng Việt — phần C."""
import json

import streamlit as st

from qa_core import ALLOWED_VIEWS, ask, load_schema, split_explanation, to_json

st.set_page_config(page_title='AdventureWorks Q&A', page_icon='📊', layout='wide')
st.title('📊 Hỏi đáp dữ liệu AdventureWorks (tiếng Việt)')
st.caption('LLM sinh SQL → kiểm duyệt → chạy bằng tài khoản chỉ đọc → trả bảng + giải thích')

with st.sidebar:
    st.subheader('🔒 Giới hạn truy cập')
    st.code('user: qa_reader\nquyền: SELECT trên 4 view ai.v_*', language='text')
    for view in ALLOWED_VIEWS:
        st.write('•', view)
    st.divider()
    st.caption('Kiểm chứng: mọi số trong lời giải thích được đối chiếu với bảng kết quả.')
    if st.button('Xem schema các view'):
        try:
            st.json(load_schema())
        except Exception:
            st.error('Không thể xử lý yêu cầu lúc này. Vui lòng thử lại sau.')


def render(result):
    if result['blocked'] or result['error']:
        st.error(result['error'])          # 1 phản hồi chung duy nhất
        return

    main, note = split_explanation(result['explanation'])
    st.subheader('1️⃣ Câu SQL được thực thi')
    st.code(result['sql'], language='sql')
    st.subheader(f'2️⃣ Kết quả ({len(result["df"])} dòng)')
    st.dataframe(result['df'], use_container_width=True)
    st.subheader('3️⃣ Giải thích')
    st.write(main)

    # Mọi nội dung phụ gom vào 1 gốc, mặc định đóng.
    with st.expander('🔎 Lưu ý & kiểm chứng', expanded=False):
        if note:
            st.markdown('**Lưu ý:** ' + note)
        if result.get('verified'):
            st.success('Đã đối chiếu: các số trong lời giải thích khớp bảng kết quả.')
        else:
            st.warning('Cần rà soát: một số con số chưa đối chiếu được với bảng.')
        if result.get('verification_note'):
            st.caption(result['verification_note'])
        st.caption('Dữ liệu thô')
        st.json(json.loads(to_json(result['df'].head(20).to_dict('records'))))


question = st.text_input(
    'Nhập câu hỏi tiếng Việt',
    placeholder='Ví dụ: Doanh thu tháng 6/2022 là bao nhiêu?',
)

if st.button('Hỏi', type='primary') and question.strip():
    with st.spinner('Đang sinh SQL, chạy truy vấn và giải thích...'):
        render(ask(question.strip()))
