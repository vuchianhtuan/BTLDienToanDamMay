# Kết quả kiểm chứng local ngày 22 tháng 10 năm 2026

## Môi trường

- Windows host, Docker Desktop với Linux engine 29.7.2, Compose 5.3.1.
- FastAPI, Python 3.12 và PostgreSQL 16 trong hai container riêng.
- PostgreSQL và nội dung tệp nằm trên hai Docker named volume riêng; đây không phải Swift/Cinder.
- Các phiên bản Python package cụ thể nằm trong `requirements.lock.txt`.

## Kết quả đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Bộ pytest | 16 passed, gồm 15 ca ứng dụng và 1 ca Swift adapter với fake transport |
| Round trip qua API đang chạy | Upload, row PostgreSQL, list, download và SHA-256 đều đạt |
| Nội dung bị sửa, cùng số byte | Verify trả `intact=false` |
| Mất object | Verify/download trả 503 |
| Giới hạn upload | Chặn cả Content-Length vượt ngưỡng và body stream vượt ngưỡng |
| Ghi metadata thất bại | Trả 503 và dọn object đã ghi |
| API key | Thiếu/sai key bị từ chối; đúng key được truy cập |
| Khởi động lại cả database và app | Hai tệp smoke còn metadata và verify vẫn toàn vẹn |
| Giao diện browser | Hiển thị sẵn sàng, danh sách tệp; bấm Verify nhận TOÀN VẸN |
| Locust local, 5 users, 30 giây | 81 requests, 0 failures; trung bình khoảng 5 ms/request |

Logs gốc được lưu tại `test-results/pytest.txt`, `smoke.txt`, `persistence.txt`, `locust.txt`; ảnh tại `test-results/interface.png`. Thư mục này được bỏ qua khi đưa lên Git. Cảnh báo pytest hiện có là deprecation từ thư viện Starlette/AnyIO; không có ca kiểm thử thất bại trong bộ kết quả cuối.

## Giới hạn của bằng chứng

Locust chạy cùng container với ứng dụng, file fixture chỉ 33 byte; kết quả không phải benchmark WAN, công suất tối đa hoặc minh chứng autoscaling. Test Swift dùng fake transport để kiểm tra code adapter và vòng đời kết nối, không gọi Keystone/Swift thật.

Chưa triển khai hoặc kiểm chứng trên OpenStack: DevStack multi-node, Tailscale/Neutron, nested KVM, hai AZ, Swift, Cinder, Keystone RBAC, Octavia, Heat, Aodh và telemetry. Không suy ra đạt 8/8 hạng mục từ kết quả local này.

## Chuẩn bị repository cho nhóm

Đã tách `app` thành config/database/models/routes/services/storage và tách frontend thành HTML/CSS/JavaScript trong `frontend/`. Backend và UI giữ nguyên HTTP contract; smoke test kiểm tra cả các asset frontend. Bổ sung test xử lý mật khẩu database có ký tự đặc biệt, đưa tổng bộ pytest lên 17 ca. Kết quả build/clone sau khi tách được kiểm tra riêng trước khi push.

Workflow GitHub Actions build Docker, chạy pytest và smoke PostgreSQL khi push main hoặc tạo PR. Việc có workflow trong repo không đồng nghĩa đã bật branch protection; trạng thái từng lần CI cần xem trên GitHub Actions.
