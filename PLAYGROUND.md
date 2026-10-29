# Playground kiểm chứng OSS — Pha 1

Ngày tham chiếu: 2026-10-29. Pha 1 chuẩn bị nền; không xác nhận các kết luận của Bảng chốt. Repository này chỉ chứa playground Python; không chép website demo HTML/npm cũ.

## Chạy

Yêu cầu: Python 3.12, uv, Docker daemon + Compose; khoảng 4 GiB cho ClickHouse và RAM thêm cho Python/UI. Dependency Python pin chính xác trong `pyproject.toml`, dependency bắc cầu và hash trong `uv.lock`. Image ClickHouse được pin theo digest trong `data/compose.yaml` (version thực đã chạy: 25.8.33.6).

```bash
cd /workspace/OSS-tool
uv sync --frozen
# Trên cloud này, luôn chọn đúng daemon local:
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock compose -f data/compose.yaml up -d
# Đợi healthcheck container healthy rồi chạy:
uv run --frozen python -m data.ensure
uv run --frozen python -m core.run --claim P1 --no-cache
uv run --frozen streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

CLI độc lập UI:

```bash
uv run --frozen python -m core.run --claim B5 --params '{"few_shot":true}' --timeout 60
# B5 hiện trả UNVERIFIED / NOT_RUN: chưa triển khai Pha 3, không giả lập LLM.
CH_TEST=1 uv run --frozen pytest -q
```

Ở môi trường sandbox, kết nối Docker/loopback có thể cần quyền thực thi bổ sung. Không đổi proxy, tắt TLS hoặc dùng host networking để vượt chính sách mạng. Mặc định `core.db.client()` là `vf_reader`, SELECT-only và `readonly=1`; quyền admin chỉ dùng khi gọi rõ `admin=True` trong seed. Mặc định không mật khẩu **chỉ dành cho mock loopback**. Không triển khai cấu hình này lên mạng công khai. B12 chưa kiểm row policy/quota/masked view.

Override kết nối qua `CH_HOST`, `CH_PORT`, `CH_READONLY_USER`, `CH_READONLY_PASSWORD`, `CH_ADMIN_USER`, `CH_ADMIN_PASSWORD`. Không đặt giá trị bí mật vào file hoặc tham số CLI. Chưa có API/model nào được gọi. Token và chi phí: chưa đo.

## Dữ liệu và oracle

- Seed 20261029; mặc định 200.000 claim + 200.000 dòng part, 40.000 xe, 20 part, 10 đại lý. Mỗi claim có một part; dùng `row_id` cho quan hệ 1:1. `ma_yc_bh` có trùng cố ý nên join chỉ bằng mã này có thể fan-out.
- 46 tháng, 2023-01 đến 2026-10 (tháng hiện tại được sinh đầy tháng; không coi là dữ liệu quan sát thực đến ngày 29). Trọng số mùa hè 1,8 lần.
- Lô `LOT-DAMPER-2026-08`: 10.000 claim tăng thêm theo cohort DL03, VF8, giảm chấn sau trái. Là anomaly cài sẵn, không chứng minh quan hệ nhân quả.
- 100 dòng bẩn có nhãn: null km, km âm, null chi phí, quantity âm, mã claim trùng (20 mỗi loại). Null được giữ nguyên. Các phép tổng hợp chuẩn bao gồm cả dữ liệu bẩn theo semantics nêu trong SQL.
- PII hoàn toàn giả. Có CCCD 12 số, biển số VN, SĐT, tên giả; `ma_pt` dạng PT + 12 số, `so_hd` 12 số là đối chứng false positive. Chưa đo precision/recall Presidio.
- `data/generated/ground_truth.json`: 39 câu SQL tiếng Việt, đáp án Python độc lập, mapping nhóm viết tắt/có dấu/không dấu, dòng bẩn và cohort bất thường. Đây là oracle dataset, **không phải** accuracy của agent. B5 cần bổ sung benchmark theo độ khó, promptfoo và LLM ở Pha 3.
- `data/generated/manifest.json`: SHA-256 Parquet để kiểm tra tái lập. Seed ghi Parquet trước rồi nạp CH. `data.ensure` bảo toàn DB đã có; không tự reset dữ liệu dở dang.

Tăng lên 1 triệu hoặc reset **chỉ database mock chuyên dụng** bằng `python -m data.seed --rows 1000000 --replace`. `--replace` xóa đúng 5 bảng mock; không dùng khi cần giữ phiên dữ liệu cũ. Chưa benchmark Pandera/1 triệu dòng.

## NHTSA

`python -m data.fetch_nhtsa` tải recall flat file từ `https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL.zip`, lọc component SUSPENSION, lưu ngày tải/checksum/trích đoạn hoặc lỗi thật vào `data/generated/nhtsa_source.json`.

Phiên này: proxy trả HTTP 403. Host `static.nhtsa.gov` đã được thêm vào draft, chưa áp dụng runtime. Sau khi cấu hình mạng được lưu/áp dụng, chạy lại lệnh; không coi save draft là download thành công. Dataset hiện **chỉ tổng hợp**, không được hiệu chỉnh phân bố hay mô tả theo NHTSA. Parser flat-file và layout cột vẫn cần đối chiếu docs chính thức khi có truy cập. Không dùng mẫu web hoặc số liệu giả làm nguồn công khai thay thế.

## Runner, UI và bằng chứng

`core.checks.run(claim, params) -> Result` không import UI. `core.run` chạy worker subprocess, có deadline, kết thúc process group khi timeout, log live, redaction secret từ environment, phiên bản, thư mục mỗi run, cache theo claim/input/code/lockfile/ground truth và kết nối không bí mật. `--no-cache` bắt buộc khi dữ liệu server bị thay đổi ngoài seed; cache chưa tự phát hiện thay đổi remote DB hoặc model endpoint. Không cache lỗi hay claim NOT_RUN.

Mọi verdict thuộc đúng 5 trạng thái. `FAILED_TO_RUN`, `TIMEOUT`, `NOT_RUN`, `COMPLETED` là trường `execution`, không thêm trạng thái verdict. Lỗi môi trường không phải bằng chứng bác bỏ tính năng tool. CLI trả exit 1 khi FAILED_TO_RUN, TIMEOUT hoặc REFUTED.

`artifacts/results/` là kết quả mới nhất; `artifacts/runs/` giữ từng run, input, log, kết quả; không stage artifact/dữ liệu PII giả lên Git. UI lưu ghi chú và phán quyết độc lập vào `artifacts/verdicts.json`, có cảnh báo lệch. Các trang A/B hiện là **khung**, chưa có mapping benchmark, SQL agent, duyệt HITL, tấn công hay trace thực. Không có biểu đồ với số liệu giả. Nút bật dịch vụ nặng chưa khởi động service.

Dashboard dùng Streamlit multipage: tổng hợp, dữ liệu P1, nhóm A, rủi ro và 15 trang theo bước. Tổng hợp ban đầu có A1–A11, B1–B14 UNVERIFIED. P1 là check hạ tầng riêng. `data/claims_source.tsv` giữ nguyên các dòng bảng người dùng; A11 inventory gồm tool chính, dự phòng và bị loại. Chưa tra license/latest release/maintain.

## Các pha còn lại

2: Nhóm A, X1, 3b, 3c, 4c, X2. 3: 2b, 3a, 4a/4b, metric YAML. 4: catalog, báo cáo/biểu đồ đối tượng kiểm chứng, Prefect, quan sát, E2E, xuất báo cáo. Dừng sau Pha 1 theo yêu cầu; không tự coi placeholder là test đã thực hiện.
