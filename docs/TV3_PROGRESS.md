# Công việc TV3 Đinh Kiều Công Tuấn

Nhánh làm việc: feat/cong-tuan-ui-loadtest. Đợt đầu hoàn thiện trải nghiệm upload và độ tin cậy của workload; phần cloud cần endpoint thật từ TV1/TV2.

## Đã thực hiện ngày 22 tháng 10 năm 2026

- Upload hiển thị tiến trình truyền; sau 100% vẫn chờ server lưu xong. Có nút hủy, khóa chọn tệp trong lúc gửi, chặn kéo nhiều tệp cùng lúc.
- Hủy/mất kết nối/timeout thông báo kết quả lưu có thể chưa xác định; người dùng làm mới trước khi upload lại để tránh trùng tệp.
- Lỗi API key, quá dung lượng và dependency chưa sẵn sàng có thông báo tiếng Việt. Download/verify có trạng thái chờ trên nút.
- Danh sách có trạng thái tải/lỗi, bỏ kết quả request cũ khi có request mới. Lấy thêm một dòng để tránh nút Sau dẫn đến trang trống khi trang cuối đủ 20 tệp. Bảng cuộn ngang trên mobile.
- Locust chọn fixture cố định tùy chọn qua LOADTEST_FILE_ID, kiểm tra nội dung verify/download; dừng user khi không có fixture hoặc sai key. Thêm smoke workload với API/storage/database tạm.

## Kiểm chứng đã chạy

Môi trường đợt này là Windows, Python 3.13 trong .venv, FastAPI với SQLite và local storage; chưa có Docker trong PATH. Dependency trực tiếp theo phiên bản repo, dependency gián tiếp do pip giải quyết trên Windows; không thay requirements.lock.txt của Python 3.12 Linux.

- Pytest: 17 passed, một cảnh báo deprecation Starlette/AnyIO.
- Edge headless: upload/verify/download round trip, lỗi API key, hủy upload, trang cuối đúng 20 tệp, mobile 390 px và không có lỗi JavaScript.
- Smoke workload: tệp hợp lệ, đối chiếu byte count, dữ liệu bị sửa cùng kích thước, mất object, thiếu fixture và sai key.
- Locust 3 users, spawn rate 3/s, 15 giây, fixture 22 byte: 27 request, 0 failure. Đây là smoke local, không phải benchmark cloud. Log/CSV/HTML và ảnh được giữ local trong test-results, không commit.

CI được bổ sung bước smoke workload. Chưa xác nhận kết quả Docker/PostgreSQL hoặc GitHub Actions cho commit này từ máy hiện tại.

## Các mốc còn lại

1. TV1 cung cấp Controller/Compute 2, nested KVM, mạng và AZ-2; TV3 phối hợp kiểm tra compute của mình đăng ký được. Chốt endpoint, quyền truy cập và phiên bản với TV1 trước khi cấu hình dịch vụ chung.
2. TV2 cung cấp App VM dùng chung Swift/PostgreSQL. TV3 cấu hình Octavia với hai backend, health monitor, kiểm tra một backend dừng thì backend còn lại phục vụ được; App VM không có floating IP.
3. Cùng TV1 chốt nguồn metric, đơn vị, khoảng đo và tài nguyên khả dụng. Viết cấu hình Heat/Aodh theo phiên bản cụm; App VM mới phải nhận cấu hình/credential và tự vào pool.
4. Chạy workload từ máy riêng qua Octavia, thu bằng chứng scale-out/scale-in thật và kiểm tra lại tính toàn vẹn sau scale. Thực hiện theo loadtest/README.md.
5. Tổng hợp số liệu chi phí theo thực tế, ảnh/log, video demo và nội dung báo cáo hạng mục 6/7/8.

Chưa triển khai Octavia/Heat/Aodh hay tuyên bố hoàn tất phần TV3 trên OpenStack. Cần endpoint, tài nguyên và cấu hình cụm thật để tiếp tục các bước này.
