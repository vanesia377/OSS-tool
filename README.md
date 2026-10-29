# OSS-tool

Playground kiểm chứng công cụ OSS cho dữ liệu bảo hành/phụ tùng ô tô trên ClickHouse. Hiện mới có **Pha 1**: dữ liệu giả, ground truth, CLI runner và khung dashboard Streamlit. Các claim A/B chưa được kiểm chứng.

## Chạy trên Linux

Yêu cầu Python 3.12, uv, Docker daemon và Docker Compose. Thực hiện trong thư mục repository vừa clone:

```bash
uv sync --frozen
docker compose -f data/compose.yaml up -d --wait
uv run --frozen python -m data.ensure
uv run --frozen python -m core.run --claim P1 --no-cache
uv run --frozen streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Kết quả P1 mong đợi: `CONFIRMED`, 39/39 truy vấn đúng. Khi chạy trên máy cá nhân, xem dashboard bằng trình duyệt tại `localhost:8501`. Server trên máy cloud cần cơ chế truy cập/forward cổng do môi trường đó cung cấp.

## Kiểm thử

Sau khi khởi động ClickHouse và sinh/nạp dữ liệu:

```bash
CH_TEST=1 uv run --frozen pytest -q
```

Không đưa `.venv`, `node_modules`, log, phán quyết hoặc Parquet/PII giả sinh ra lên GitHub. `data.ensure` tạo lại dữ liệu seed 200.000 claim khi database mới; không xóa database đã có. Nếu dùng lại volume ClickHouse từ checkout khác, chạy thêm `uv run --frozen python -m data.seed --rows 200000 --generate-only` để có oracle cục bộ.

Xem [hướng dẫn chi tiết](PLAYGROUND.md) và [báo cáo Pha 1](PHASE1_REPORT.md). Báo cáo lịch sử mô tả lượt chạy trước khi chuyển repository; các file runtime evidence được nhắc đến không nằm trong Git. Có thể tạo evidence mới bằng runner.

**Giới hạn:** Pha 2–4 chưa triển khai; các trang tool trả `UNVERIFIED / NOT_RUN`. Nguồn NHTSA chưa tải thành công ở Pha 1. Cấu hình ClickHouse không mật khẩu chỉ dành cho mock trên loopback, không dùng cho triển khai công khai.
