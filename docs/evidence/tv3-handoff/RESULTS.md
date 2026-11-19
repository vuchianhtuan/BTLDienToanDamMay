# Bản ghép TV3 — 28/10/2026

Nhánh bàn giao: `feat/tv3-handoff`. Giữ lịch sử nhánh cũ tại `a3fa8a0` và ghép UI `6bb92e9`, Locust `149ecaa`, elasticity `25a03c1`. Không push cập nhật vào `feat/cong-tuan-ui-loadtest` hoặc `main` trong đợt này.

## Kết quả local sau khi ghép

| Kiểm tra | Kết quả |
|---|---|
| Node: `node --test tests/frontend/*.test.cjs` | 17 đạt: 13 HTTP/clipboard test và 4 ca hồi quy DOM/transport harness cho bản ghép |
| App: `docker compose exec -T app python -m pytest tests -q -p no:cacheprovider` | 51 đạt, 1 cảnh báo deprecation Starlette/AnyIO |
| JSON: `python deploy/elasticity/kit.py lint` trong container | Đạt tham chiếu/nested contract/invariant offline |
| Smoke live PostgreSQL | Readiness, frontend/assets, upload/list/download và SHA-256 verify đạt |
| `tests/loadtest/smoke_workload.py` | Chọn fixture, download streaming đúng byte count, sửa nội dung, mất object, thiếu fixture và sai key đều xử lý đúng |
| `tests/smoke_locust.py` — API live | Exit 0; 12 request, 0 lỗi trong smoke ngắn |
| Locust HTTP fixture — danh sách rỗng | Exit 1; 2 request, 2 lỗi |
| Locust HTTP fixture — 401 | Exit 1; 2 request, 2 lỗi |
| Locust HTTP fixture — verify false dù HTTP 200 | Exit 1; 4 request, 2 lỗi |
| Locust HTTP fixture — download sai cùng kích thước | Exit 1; 6 request, 2 lỗi |
| Bộ YAML cũ: validator và unittest | 4 template đạt; 14 ca tooling đạt |

Chạy nhóm kiểm tra app/UI/JSON/workload bằng `scripts/test.ps1` sau khi Docker build thành công. YAML được thử bằng PyYAML 6.0.2 trong thư mục `/tmp/tv3-yaml` của container, không sửa application dependency lock. Các ca DOM dùng harness, không thay thế kiểm tra trình duyệt thực. Các HTTP fixture âm tính mô phỏng lỗi và không phải sự cố cloud thực.

## Các khác biệt đã xử lý khi ghép

- UI giữ tiến trình/hủy upload, thông báo chưa xác định kết quả lưu, khóa control, danh sách chống request cũ và lấy thêm một dòng để quyết định trang sau; bổ sung helper timeout/copy hash và panel verify.
- Locust giữ `LOADTEST_FILE_ID` và streaming download; bổ sung validator dùng chung, kiểm tra verify/download ngay lúc khởi tạo, dừng run lỗi fixture và summary cuối. Điều chỉnh smoke cũ cho hai request khởi tạo bổ sung.
- Giữ cả hai bộ cloud, tách hướng dẫn YAML cũ sang `YAML_RUNBOOK.md`; JSON là luồng bàn giao chính. Không trộn topology hoặc môi trường của hai bộ.
- Hợp nhất bước CI, không thay backend/API/schema/lock của nhóm. CI chạy khi push lên nhánh bàn giao.

## Chưa được xác nhận

Không có kết quả Heat server-side validation, boot Glance/cloud-init, Octavia failover, Gnocchi/Aodh, scale-out/scale-in hoặc tải qua hai AZ thực. Không dùng 12 request smoke làm benchmark hoặc chứng minh autoscale. Minh chứng UI/Locust/elasticity ở các thư mục cũ ghi nhận lần chạy riêng trước khi ghép; báo cáo này là kiểm chứng bản bàn giao.
