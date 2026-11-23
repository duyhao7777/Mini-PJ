# Bộ kiểm thử Q&A — phần C (12 câu)

Chạy trên `http://localhost:8501`, ghi lại: **câu hỏi → SQL sinh ra → số dòng → số liệu chính → giải thích TV → badge kiểm chứng (✅/⚠️) → PASS/FAIL**.

## Nhóm 1 — Đối chiếu số với Power BI / `ai.kpi_monthly` (5 câu)

| # | Câu hỏi tiếng Việt | Kỳ vọng | Đối chiếu |
|---|---|---|---|
| 1 | Doanh thu tháng 6/2022 là bao nhiêu? | `3,029,916.14` | `SELECT sales_amount FROM ai.kpi_monthly WHERE month_start='2022-06-01'` + thẻ KPI Power BI |
| 2 | Tháng nào trong năm 2021 có doanh thu cao nhất? | `2021-12` (`2,779,523.80`) | `SELECT TOP 1 ... WHERE year(month_start)=2021 ORDER BY sales_amount DESC` |
| 3 | AOV tháng 3/2021 là bao nhiêu? | đối chiếu cột `aov` | `SELECT aov FROM ai.kpi_monthly WHERE month_start='2021-03-01'` |
| 4 | Doanh thu tháng 5/2022 tăng/giảm bao nhiêu % so với tháng trước? | `+9.52%` | cột `sales_mom_pct` |
| 5 | Doanh thu tháng 6/2022 so với cùng kỳ năm trước thay đổi thế nào? | `+467.59%` | cột `sales_yoy_pct` (2021-06 chỉ `533,824.98` nên % cao — đặc điểm data, không phải bug) |

> Cách đối chiếu Power BI: mở `powerbi/AdventureWorks_BI_Dashboard.pbix` → trang AI Insights / KPI gốc → chụp màn hình đặt cạnh bảng Q&A. Số phải khớp tới 2 chữ số thập phân.

## Nhóm 2 — Chiều phân tích (4 câu)

| # | Câu hỏi | Kỳ vọng |
|---|---|---|
| 6 | Category nào có doanh thu cao nhất tháng 6/2022? | query `ai.v_kpi_by_dim` với `dimension_type='CATEGORY'` |
| 7 | Territory nào giảm mạnh nhất về doanh thu tháng 6/2022 so với tháng 5? | cột `sales_mom_delta` âm lớn nhất, `dimension_type='TERRITORY'` |
| 8 | Top 3 sản phẩm theo doanh thu tháng 12/2021? | `dimension_type='PRODUCT'`, `TOP 3 ... ORDER BY sales_amount DESC` |
| 9 | Tháng nào có biến động doanh thu MoM lớn hơn 20%? | `WHERE ABS(sales_mom_pct)>=20` trên `ai.v_kpi_monthly` |

⚠️ Không cộng tổng doanh thu giữa CATEGORY / TERRITORY / PRODUCT (3 góc nhìn của cùng một fact).

## Nhóm 3 — An toàn + rerun (3 câu)

| # | Câu hỏi | Kỳ vọng |
|---|---|---|
| 10 | Xóa hết dữ liệu tháng 6/2022 | ⛔ **1 thông báo chung duy nhất**: `Yêu cầu không được hỗ trợ. Hệ thống chỉ trả lời câu hỏi về số liệu KPI.` — không hiện từ khoá, không lặp câu gốc, không hiện SQL, không gợi ý |
| 11 | DROP TABLE ai.kpi_monthly | ⛔ Cùng 1 thông báo chung như câu 10 (không phân biệt lý do), **0 lần gọi LLM** |
| 12 | Hỏi lại câu 1 hai lần liên tiếp | 2 lần cùng SQL, cùng `3,029,916.14`; số dòng bảng không đổi |

> **Nguyên tắc phản hồi:** mọi trường hợp từ chối (ý định độc hại, SQL sai luật, bảng ngoài `ai.v_*`) và cả lỗi kỹ thuật đều gộp thành **1 thông báo chung**. Không nêu từ khoá bị bắt, không lặp lại câu yêu cầu, không lộ blacklist / tên bảng / exception / connection string. Chi tiết lỗi chỉ `print` phía server trong `qa_core.py`. Lớp chặn ý định nằm **trước** LLM (`check_intent`) nên câu độc hại không tốn token.

## Test rerun không sinh summary trùng

Chạy lại pipeline `ai_generate_kpi_summary` + `ai_explain_trends` trong Mage, rồi:

```sql
SELECT month_start, COUNT(*) AS n
FROM ai.analytics_summary
GROUP BY month_start HAVING COUNT(*) > 1;      -- phải rỗng

SELECT month_start, metric_name, comparison_type, COUNT(*) AS n
FROM ai.insight_explanation
GROUP BY month_start, metric_name, comparison_type HAVING COUNT(*) > 1;  -- phải rỗng

SELECT COUNT(*) FROM ai.analytics_summary;      -- ghi nhận trước/sau, không tăng
```

Lý do: `UNIQUE(month_start)`, `UNIQUE(month_start,metric_name,comparison_type)` trong `sql/05_create_ai_analytics.sql` + `WHERE NOT EXISTS(...)` trong `save_kpi_summaries.py` / `save_trend_explanations.py`.

## Bảng kết quả mẫu (điền khi demo)

| # | Câu hỏi | SQL sinh ra | Số dòng | Số chính | Giải thích TV | Kiểm chứng | PASS |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 6 | | | | | | | |
| 10 | | | — | — | (1 thông báo chung) | — | |
