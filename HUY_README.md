# Phần Huy — AI Business Analytics

## Thứ tự chạy (PowerShell trong thư mục Mini-PJ)

1. Chạy file `sql/05_create_ai_analytics.sql` trong SSMS kết nối database BI_AdventureWorks.
2. Đảm bảo staging và DW đã nạp dữ liệu thành công. Trong thư mục `adventureworks_dw`:
   ```powershell
   $env:DBT_SA_PASSWORD = "<mật khẩu SQL Server>"
   dbt run --profiles-dir . --select +kpi_monthly +kpi_by_dim
   dbt test --profiles-dir . --select kpi_monthly kpi_by_dim
   dbt test --profiles-dir . --select assert_ai_kpi_monthly_reconcile assert_ai_by_dim_reconcile assert_ai_by_dim_unique
   ```
3. Trong Mage.ai đã chạy trên Docker, cấu hình secrets `GEMINI_API_KEY`, `GEMINI_MODEL` theo mẫu sẵn có của nhóm.
   Kiểm tra Mage có quyền truy cập `adventureworks_bi` mới, restart container Mage nếu cần.
4. Mở pipeline `ai_generate_kpi_summary`, chạy 3 block theo thứ tự; sau đó chạy `ai_explain_trends`.
5. Kiểm tra kết quả bằng SQL:
   ```sql
   SELECT * FROM ai.kpi_monthly ORDER BY month_start DESC;
   SELECT TOP 20 * FROM ai.kpi_by_dim ORDER BY month_start DESC;
   SELECT month_start, verified, verification_note, summary_text FROM ai.analytics_summary ORDER BY month_start DESC;
   SELECT month_start, change_pct, verified, verification_note, explanation_text FROM ai.insight_explanation ORDER BY month_start DESC;
   ```
6. Chạy lại pipeline: mỗi tháng chỉ lưu 1 summary và 1 trend cho `sales_amount/MoM` nhờ UNIQUE và NOT EXISTS.

## Tích hợp với repo

- Hai model dùng các fact/dimension hiện có. Macro `generate_schema_name` đưa model AI vào schema `ai`, giữ marts trong `dw` và staging trong `dw_staging` với profile `dev` hiện tại.
- Pipeline dùng lại `utils/ai_helpers.py` và `utils/etl_helpers.py`; kết nối lấy từ `io_config.yaml`, API key/model lấy từ Mage secrets.
- Mỗi lần chạy lấy tối đa 10 tháng chưa có kết quả, từ mới đến cũ. Chạy lại đến khi hết dữ liệu chờ nếu muốn xử lý toàn bộ lịch sử.
- Kết quả có `verified = 0` vẫn được lưu và không tự sinh lại. Kiểm tra `verification_note` trước khi sử dụng nội dung AI.
- Các bảng kết quả lưu snapshot KPI lúc sinh nội dung. Nếu nạp lại dữ liệu lịch sử, cần kiểm tra và xoá kết quả của các tháng bị thay đổi trước khi chạy lại pipeline.

## Lưu ý

- Dùng ngưỡng `ABS(sales_mom_pct) >= 20` (%). Có thể sửa thành 10 hoặc 30 trong `load_trend_candidates.py`.
- Với dữ liệu AdventureWorks hiện có, biến động MoM dùng **một tháng có bán hàng** trước đó đúng lịch, không lấy tháng trước gần nhất bất kể khoảng cách.
- Các nhóm dimension trong `ai.kpi_by_dim` là các góc nhìn khác nhau; tuyệt đối không cộng tổng doanh thu giữa CATEGORY, TERRITORY và PRODUCT.
- Mỗi nhóm đóng góp được tính theo biến động nhóm chia biến động toàn hệ thống, nên tỷ lệ có thể âm hoặc vượt 100% khi các nhóm triệt tiêu nhau.
- Bộ kiểm chứng chỉ xác nhận **con số trong văn bản tồn tại trong JSON**; không thể tự khẳng định tính đúng đắn của cách diễn giải, không phải semantic fact checker.
- Thêm 2 model vào `dbt` trước, không cần tự tạo `ai.kpi_monthly` và `ai.kpi_by_dim` bằng SQL.
- Không đưa API key hay mật khẩu vào repo.
