# Báo cáo Pha 1 — 2026-10-29

## Kết quả có bằng chứng

- `python -m core.run --claim P1 --no-cache`: CONFIRMED, 39/39 query đúng. Bằng chứng SQL và output từng mục: `artifacts/results/P1.json`.
- `CH_TEST=1 python -m pytest -q`: .........                                                                [100%]
9 passed in 3.02s
- `curl --fail http://127.0.0.1:8501/_stcore/health`: `ok`; AppTest kiểm summary và bấm Chạy trên trang P1.
- Cố tình đổi oracle → REFUTED (integration test). Không chỉnh test thành xanh.
- `core.run.run('P1', timeout=0.001, force=True)`: SKIPPED_RESOURCE / TIMEOUT, chi tiết `artifacts/timeout-probe.json`.
- `CH_PORT=1 python -m core.run --claim P1 --no-cache`: UNVERIFIED / FAILED_TO_RUN, lỗi kết nối trong `artifacts/connection-failure-probe.log`.
- Chạy P1 lần nữa cùng input: CACHE HIT, `artifacts/cache-probe.log`.

Version đã chạy (không khẳng định là mới nhất): `{'python': '3.12.14', 'clickhouse-connect': '0.9.2', 'polars': '1.34.0', 'streamlit': '1.50.0', 'PyYAML': '6.0.3', 'clickhouse': '25.8.33.6'}`.

## Chưa kiểm được

NHTSA: `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>`. Draft đã thêm hostname static.nhtsa.gov; chưa áp dụng runtime, chưa tải được nguồn, dữ liệu hoàn toàn tổng hợp. Các claim A/B và chức năng công cụ ở Pha 2–4 đều UNVERIFIED / NOT_RUN. Không dùng kết quả P1 để xác nhận Bảng chốt. Chưa chạy model, không có chi phí token đo được. Chưa kiểm thử máy/task mới sau publish.

## Vị trí sản phẩm

- `core/`: result contract, registry, CLI subprocess/deadline/cache/log.
- `ui/app.py`: Streamlit multipage, 7 khối/trang, verdict riêng.
- `data/`: Compose pin digest, seed + oracle + public-source fetcher.
- `PLAYGROUND.md`: hướng dẫn chạy, giới hạn và các pha tiếp theo.

## Tái lập và cấu hình đã lưu

`python -m data.seed --rows 200000 --generate-only`: exit 0, 3,05 giây; ground truth và checksum cả 5 file Parquet giống hệt lần trước. Chi tiết đo trong `artifacts/phase1_environment.json`. `python -m data.ensure` chạy lại bảo toàn dữ liệu; P1 sau đó vẫn đúng. 49 package khóa (bao gồm project và dev dependency), không coi là số dependency của tool ở các pha sau.

Đã lưu `install_script` (uv sync frozen), `start_skill` (Docker + readiness + nạp/giữ dữ liệu + CLI + Streamlit), và thêm đúng `static.nhtsa.gov` vào allowlist draft. Đây là lưu cấu hình, không phải áp dụng mạng hay publish. Người dùng review/lưu environment settings rồi publish nếu muốn snapshot dùng lại. Chưa kiểm khôi phục trong task mới.
