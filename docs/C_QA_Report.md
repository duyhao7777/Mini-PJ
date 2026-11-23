# Báo cáo phần C — Q&A + Mô phỏng + Kiểm thử (+ Bonus & AI)

> Điền ngày hoàn thành / tên người làm trước khi nộp. Các ô **[ĐIỀN KHI DEMO]** sẽ có nội dung sau khi chạy `http://localhost:8501`.

## 1. Kiến trúc

```
Người dùng (tiếng Việt)
      │  st.text_input
      ▼
Streamlit  (container qa, port 8501)
      │  (1) prompt = SQL_RULES + schema 4 view + câu hỏi
      ▼
Gemini 3.5 Flash Lite ──► 1 câu T-SQL SELECT
      │  (2) validate_sql(): SELECT / blacklist / chỉ ai.v_* / ép TOP 100
      ▼
pyodbc  ── user qa_reader (GRANT SELECT trên 4 view, DENY INSERT/UPDATE/DELETE/ALTER)
      ▼
SQL Server (Azure SQL Edge) ── schema ai: v_kpi_monthly, v_kpi_by_dim,
                                v_latest_summary, v_trend_explain
      │  (3) bảng kết quả
      ▼
Gemini (lần 2) ──► giải thích tiếng Việt
      ▼
st.code(SQL)  +  st.dataframe(bảng)  +  st.markdown(giải thích)
```

Nguồn số liệu chung cho B và C: `ai.kpi_monthly` / `ai.kpi_by_dim` (dbt, build từ `dw.fact_sales` + `dim_*`). C không đụng trực tiếp `dw.*`, `stg.*`, `etl.*`.

**Luồng dữ liệu nền (đã chạy):** 10 CSV Kaggle → Mage ingest (7 lookup + 56,046 dòng sales) → dbt `PASS=12` / test `PASS=13` → 2 bảng KPI → 4 view → `qa_reader`.

## 1b. Đối chiếu yêu cầu 3.5 — Generative AI / AI-Assisted Analytics

| Yêu cầu tối thiểu | Có ở đâu | Bằng chứng |
|---|---|---|
| Sử dụng LLM / GenAI | Gemini **3.5 Flash Lite** | `utils/ai_helpers.py:call_gemini` (Mage, retry 429/500/503), `app/qa_core.py:call_gemini` (Q&A) |
| Tự động tạo **AI-generated Summary** từ KPIs | Pipeline `ai_generate_kpi_summary` → bảng `ai.analytics_summary` | `SUMMARY_RULES` + `input_json` lưu snapshot KPI lúc sinh; `UNIQUE(month_start)` chống sinh trùng |
| Giải thích **xu hướng / biến động / vấn đề trên dashboard** | `ai_explain_trends` → `ai.insight_explanation`, `ai_explain_etl_runs` → `etl.run_ai_summary`, và phần giải thích của Q&A | `TREND_RULES` dùng `contribution_pct_of_net_change` (đóng góp theo Category/Territory); cả 3 prompt có đoạn **"Lưu ý / Cần kiểm tra"** nêu điểm cần soi thêm trên dashboard |
| Dựa trên dữ liệu đã tính + **kiểm chứng** + hạn chế suy diễn | Mọi prompt chỉ đọc `ai.kpi_monthly` / `ai.kpi_by_dim` / 4 view (đã dbt test `PASS=13`) | `verify_claims()` đối chiếu từng số trong văn bản với `input_json` → cột `verified` / `verification_note`; Q&A đối chiếu với chính bảng kết quả → badge ✅/⚠️; cấm `do/vì/nhờ/nguyên nhân là/dẫn đến`, cấm số ngoài JSON, cấm dự báo & khuyến nghị hành động |
| *(Khuyến khích)* Câu hỏi ngôn ngữ tự nhiên | Streamlit `http://localhost:8501` | `app/qa_app.py` + `app/test_questions.md` (12 câu), sinh SQL có kiểm duyệt, hiện SQL + bảng + giải thích |

**Cải tiến ở lần rà soát này:**
1. 3 prompt (summary / trend / Q&A) chuyển từ "liệt kê số" sang cấu trúc nhận định có **Kết quả → Xu hướng/đối chiếu → Lưu ý cần kiểm tra** (B giữ 3 đoạn; C nâng lên 5 đoạn ở điểm 9).
2. Bắt buộc **ghi rõ kỳ đối chiếu ngay cạnh mọi con số %** (`so với tháng trước` / `so với cùng kỳ`) → `verify_claims` không còn đánh `verified=0` oan vì thiếu ngữ cảnh MoM/YoY.
3. Q&A **kế thừa `verify_claims` của B** (trước đó chỉ có prompt, chưa kiểm chứng) → hiện badge ✅/⚠️ + `verification_note`.
4. Sinh SQL ưu tiên trả **thêm cột so sánh** (`prior_month_sales`, `sales_mom_pct`, `sales_yoy_pct`) để lời giải thích có căn cứ so sánh; câu hỏi về "nhận xét của AI" được route tới `v_latest_summary` / `v_trend_explain`.
5. Mọi phản hồi từ chối/lỗi gộp **1 thông báo chung**, không lộ luật lọc; bỏ phần gợi ý câu hỏi mẫu trên UI để giao diện gọn (bộ 12 câu vẫn nằm trong `app/test_questions.md`).
6. Sửa lỗi serialize payload: trước dùng `default=str` nên `Decimal('3029916.14')` biến thành chuỗi `"Decimal('3029916.14')"` và `date` thành `"datetime.date(2022, 6, 1)"` → `verify_claims` không thấy số/ngày nào, đánh `⚠️` oan dù AI trả đúng số. Nay dùng `to_json/json_safe` của B (Decimal → float, date → `YYYY-MM-DD`). SQL sinh ra cũng **luôn kèm cột so sánh** (`prior_month_sales`, `sales_mom_pct`, ...) nên phần "Xu hướng / đối chiếu" có dữ liệu thay vì "chưa có dữ liệu kỳ đối chiếu".
7. Giới hạn **mỗi bài chỉ MỘT tỷ lệ % (MoM)** kèm `so với tháng trước`; YoY chỉ nêu bằng giá trị tiền `prior_year_sales`. Lý do: `verify_claims` của B không gán được ngữ cảnh khi hai tỷ lệ % (MoM + YoY) đứng gần nhau → trả `không rõ MoM/YoY` dù số đúng. Áp dụng đồng nhất cho cả 3 prompt (summary / trend / Q&A).
8. Gom mọi nội dung phụ (đoạn **Lưu ý**, badge kiểm chứng, `verification_note`, JSON thô) vào **1 expander mặc định đóng**; màn hình chính chỉ còn SQL + bảng + Kết quả/Xu hướng. Thêm quy tắc **viết số liền, không phân nhóm hàng nghìn bằng dấu chấm** (`3029916.14`, không `2.146`) để `_parse_number` không đọc nhầm `2.146` thành `2.146` thay vì `2146`.
9. Nâng phần giải thích Q&A thành **bản nhận định 5 tầng / 280 từ**: Kết quả (vị thế trong chuỗi) → Xu hướng (**độ mạnh, độ bền, điểm gãy**) → Cấu trúc/đóng góp (**nhóm đối nghịch, diện rộng hay tập trung**) → **Độ tin cậy** (giới hạn nhìn thấy được trong bảng) → Lưu ý (câu hỏi kiểm chứng). Chiều sâu tăng bằng cấu trúc phân tích, **không** bằng suy luận ngoài dữ liệu: vẫn cấm tự tính hiệu/tỷ lệ/trung bình, cấm từ nhân quả, nên `verify_claims` vẫn đối chiếu được từng số. Chỉ áp dụng cho C; 2 prompt của B giữ nguyên.

## 2. Prompt (nguyên văn, nằm trong `app/qa_prompts.py`)

**Prompt sinh SQL** — `SQL_RULES`:

```
Bạn là trợ lý BI cho hệ thống AdventureWorks. Nhiệm vụ: chuyển câu hỏi tiếng Việt
thành ĐÚNG 1 câu T-SQL SELECT duy nhất.

QUY TẮC BẮT BUỘC:
- Chỉ dùng 4 view trong SCHEMA bên dưới. Tuyệt đối không tham chiếu bảng khác, không dùng dw.*, stg.*, etl.*.
- Chỉ SELECT. Cấm INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, MERGE, CREATE.
- Dùng TOP thay LIMIT. Không viết comment, không chấm phẩy, không nhiều câu lệnh.
- month_start kiểu date, ví dụ '2022-06-01'. sales_amount/profit_amount/aov là số thập phân.
- sales_mom_pct / sales_yoy_pct là phần trăm đã tính sẵn (có thể NULL); không tự tính lại.
- dimension_type trong ai.v_kpi_by_dim chỉ nhận CATEGORY, TERRITORY, PRODUCT; KHÔNG cộng tổng doanh thu giữa các dimension_type.
- Câu hỏi về "tăng/giảm/biến động/so sánh": trả THÊM prior_month_sales, prior_year_sales, sales_mom_pct, sales_yoy_pct.
- Câu hỏi về "tóm tắt/nhận xét của AI": dùng ai.v_latest_summary hoặc ai.v_trend_explain.
- Tránh SELECT *; chỉ lấy cột cần thiết, luôn kèm month_start nếu có.
- Nếu câu hỏi không trả lời được bằng 4 view này, vẫn trả 1 câu SELECT hợp lệ lấy dữ liệu gần nhất.
- CHỈ trả về câu SQL, không giải thích, không markdown, không ```.
```
Kèm `SCHEMA` lấy động từ `INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='ai' AND TABLE_NAME LIKE 'v_%'`.

**Prompt giải thích** — `EXPLAIN_RULES` (bản nhận định chuyên gia: **5 đoạn, tối đa 280 từ**):

```
"Kết quả: " số chính, kỳ, các chỉ số đi kèm; nếu nhiều dòng nêu dòng cao nhất / thấp nhất
          và vị trí của kỳ trong chuỗi.
"Xu hướng / đối chiếu: " thay đổi so với prior_month_sales + nhận định ĐỘ MẠNH, ĐỘ BỀN
          (đi lên liên tục / đi ngang / đảo chiều) và ĐIỂM GÃY trong chuỗi kỳ.
"Cấu trúc / đóng góp: " nhóm lớn nhất, nhóm đối nghịch, biến động DIỆN RỘNG hay TẬP TRUNG;
          với KPI tổng hợp thì đặt doanh thu / lợi nhuận / số đơn / AOV cạnh nhau.
          Không cộng tổng giữa các dimension_type.
"Độ tin cậy: " giới hạn NHÌN THẤY ĐƯỢC trong bảng (kỳ đối chiếu NULL, một dòng,
          biến động lớn bất thường) — gắn nhãn ĐẶC ĐIỂM DỮ LIỆU, không phải lỗi hay nguyên nhân.
"Lưu ý: " 1–2 CÂU HỎI KIỂM CHỨNG cần soi thêm trên dashboard (gợi ý kiểm tra,
          không phải kết luận nguyên nhân hay khuyến nghị hành động).

CHỐNG SUY DIỄN: mọi nhận định bám vào ít nhất một số CÓ TRONG BẢNG; không tự tính hiệu,
tỷ lệ, trung bình, tổng hay 'gấp ... lần' mới — chỉ đặt số có sẵn cạnh nhau bằng từ so sánh;
không dùng thuật ngữ BI cho đại lượng bảng không có; tối đa 2 chữ số thập phân; viết số liền,
không phân nhóm hàng nghìn; CHỈ MỘT tỷ lệ % (MoM) kèm ngay cạnh 'so với tháng trước'
(không % YoY, không nối 2 tỷ lệ bằng 'và'/dấu phẩy); đóng góp phải kèm 'đóng góp'/'tỷ trọng'
ngay sau tên nhóm; cấm 'do/vì/nhờ/nguyên nhân là/dẫn đến'; không dự báo, không khuyến nghị
hành động; không đánh số mục; bảng rỗng thì chỉ viết 'Chưa có dữ liệu cho câu hỏi này.'
```

> Chiều sâu được tăng bằng **cấu trúc nhận định** (độ bền, điểm gãy, độ lan tỏa, độ tin cậy), không phải bằng suy luận ngoài dữ liệu — nên `verify_claims` vẫn đối chiếu được từng số. `SUMMARY_RULES` / `TREND_RULES` của phần B giữ nguyên bản 3 đoạn (không đụng theo yêu cầu chỉ sửa phần C).

## 3. Guardrail (bằng chứng "chỉ SELECT, chỉ view ai.*, tài khoản chỉ đọc")

| Lớp | Cơ chế |
|---|---|
| Lớp 0 — ý định | `check_intent()` quét câu hỏi TV và từ chối **trước khi gọi LLM**. Không tốn token, không cho LLM cơ hội tự sinh SELECT an toàn thay vì lệnh xóa |
| **Phản hồi từ chối** | Mọi lý do từ chối (ý định, `validate_sql`, bảng ngoài `ai.v_*`) và cả lỗi kỹ thuật đều trả **1 thông báo chung duy nhất** (`GENERIC_DENIAL` / `GENERIC_ERROR`). Không hiện SQL, không lặp câu yêu cầu, không lộ từ khoá/blacklist/tên bảng/exception. Chi tiết chỉ `print` phía server |
| Prompt | cấm từ khoá, chỉ 4 view, chỉ SELECT |
| `validate_sql()` | `startswith SELECT`; regex blacklist `INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/EXEC/MERGE/GRANT/REVOKE/CREATE`; mọi `FROM/JOIN` phải nằm trong `ALLOWED_VIEWS`; cấm `; -- /*`; tự ép `TOP 100` |
| Database | login `qa_reader`: `GRANT SELECT ON OBJECT::ai.v_*` cho 4 view, `REVOKE SELECT ON SCHEMA::ai`, `DENY INSERT/UPDATE/DELETE/ALTER ON SCHEMA::ai` |
| Hiển thị | `st.code(sql)` hiện đúng câu SQL đã thực thi (kể cả câu bị từ chối) |

Kết quả verify thực tế bằng `qa_reader`: đọc được 4 view; `ai.kpi_monthly`, `ai.analytics_summary`, `etl.pipeline_run_log`, `INSERT`, `DROP` đều bị `permission denied`.

## 4. Ví dụ chạy thật (3 cặp)

### Ví dụ 1 — câu số liệu
- Hỏi: `Doanh thu tháng 6/2022 là bao nhiêu?`
- SQL: **[ĐIỀN KHI DEMO]**
- Bảng: `sales_amount = 3,029,916.14`, `profit_amount = 1,444,115.29`, `order_count = 2,146`, `aov = 1,411.89`, `MoM +3.86%`, `YoY +467.59%`
- Giải thích: **[ĐIỀN KHI DEMO]**
- Đối chiếu Power BI: khớp `ai.kpi_monthly` / thẻ KPI gốc.

### Ví dụ 2 — câu chiều phân tích
- Hỏi: `Category nào có doanh thu cao nhất tháng 6/2022?`
- SQL / bảng / giải thích: **[ĐIỀN KHI DEMO]**

### Ví dụ 3 — câu bị chặn
- Hỏi: `Xóa hết dữ liệu tháng 6/2022`
- App hiện **duy nhất 1 box**: `Yêu cầu không được hỗ trợ. Hệ thống chỉ trả lời câu hỏi về số liệu KPI.` — không gọi Gemini, không sinh SQL, không lặp lại câu yêu cầu, không lộ luật lọc.

## 5. Kiểm thử

Xem `app/test_questions.md`: 12 câu (5 đối chiếu Power BI, 4 chiều dim, 3 an toàn + rerun). Kèm 3 truy vấn chứng minh rerun không sinh summary trùng nhờ `UNIQUE` + `WHERE NOT EXISTS`.

Số liệu nền đã kiểm chứng: `stg.sales = dw.fact_sales = 56,046`; `ai.kpi_monthly = 30` tháng; `ai.kpi_by_dim = 2,017` dòng; `dbt test PASS=13 ERROR=0`.

## 6. Hạn chế

1. Chỉ hiểu đúng tên cột trong 4 view; từ lóng / cách gọi mơ hồ ("doanh thu bán xe", "quý vừa rồi") dễ sinh SQL sai hoặc trả bảng rỗng.
2. LLM có thể bịa tên cột dù đã nhét schema — validator chỉ chặn **bảng**, không chặn **cột**; lỗi sẽ lộ ra ở bước chạy SQL và app báo lỗi.
3. Lời giải thích đã được đối chiếu số bằng `verify_claims`, nhưng bộ này chỉ xác nhận **con số có tồn tại trong dữ liệu nguồn** (và đúng ngữ cảnh MoM/YoY / đóng góp); nó **không kiểm chứng ngữ nghĩa hay cách diễn giải**. Văn bản vẫn có thể đúng số nhưng diễn đạt lệch ý, nên UI hiện badge ✅/⚠️ để người dùng rà soát thay vì khẳng định tuyệt đối.
4. `verified = 0` vẫn được hiển thị (không tự sinh lại nội dung), giống thiết kế của phần B — tránh lặp API và giữ lại bằng chứng để kiểm tra `verification_note`.
4. `sales_yoy_pct` tháng 6/2022 = `+467.59%` do tháng 6/2021 thấp bất thường (`533,824.98`) — đặc điểm bộ data, không phải lỗi hệ thống.
5. Thiếu kỳ so sánh → `sales_mom_pct` / `sales_yoy_pct` = NULL; Gemini có thể diễn giải thiếu chắc chắn.
6. Giới hạn `TOP 100`, không phù hợp câu hỏi cần toàn bộ lịch sử chi tiết.
7. Chạy trên **Azure SQL Edge** nên không có CLR; đã đổi `FORMAT()` → `CONVERT()` trong 3 model dbt. Xem `GUIDE.md`.
8. `ai.v_latest_summary` / `ai.v_trend_explain` chỉ có dữ liệu sau khi chạy 2 pipeline AI của B với Mage secrets `GEMINI_API_KEY` + `GEMINI_MODEL`.

## 7. Kịch bản video demo (3 phút)

| Thời lượng | Nội dung | Câu thoại gợi ý |
|---|---|---|
| 0:00 – 0:30 | Mở Power BI trang **ETL Monitoring** + **AI Insights** | "Dữ liệu đã chạy qua ETL, dbt test 13/13 PASS, số KPI ở đây." |
| 0:30 – 1:00 | Mở `localhost:8501`, hỏi câu 1 (doanh thu 6/2022). Chỉ vào `st.code(SQL)`, bảng, giải thích | "Câu hỏi tiếng Việt được chuyển thành SQL, hiện công khai, chạy bằng user chỉ đọc." |
| 1:00 – 1:30 | Đối chiếu số `3,029,916.14` với Power BI (chia đôi màn hình) | "Số AI trả về trùng khớp báo cáo gốc." |
| 1:30 – 2:00 | Hỏi câu chiều (category/territory), rồi hỏi câu `DROP TABLE ...` | "Câu độc hại bị chặn ngay, kể cả khi bỏ qua prompt thì user qa_reader cũng không có quyền." |
| 2:00 – 2:40 | Chạy lại pipeline AI + hỏi lại cùng câu, chạy 2 truy vấn `HAVING COUNT(*)>1` | "Rerun không sinh summary trùng nhờ UNIQUE + NOT EXISTS." |
| 2:40 – 3:00 | Kết: sơ đồ kiến trúc + 3 hạn chế chính | "Hệ thống ưu tiên an toàn và đối chiếu được, chưa xử lý ngôn ngữ mơ hồ." |

## 8. Phụ lục — lệnh vận hành

Toàn bộ quy trình (cài đặt, `docker compose up`, init DB, ingest, dbt, pipeline AI, Power BI) nằm trong **`GUIDE.md`**. Lệnh dùng hằng ngày:

```bash
cd Mini-PJ
docker compose --env-file .env up -d --build
docker compose ps
docker compose logs -f qa
docker compose restart qa                 # sau khi sửa app/*.py
docker compose exec mage python /home/src/scripts/init_db_via_mage.py 06_create_ai_qa_views.sql
docker compose down                       # giữ volume
```

Mở `http://localhost:6789` (Mage) và `http://localhost:8501` (Q&A).

⚠️ Không chạy lại `scripts/init_db_via_mage.py` không đối số sau khi ingest (có `DROP TABLE stg.sales`). Chỉ chạy riêng: `docker exec mage python /home/src/scripts/init_db_via_mage.py 06_create_ai_qa_views.sql`.
