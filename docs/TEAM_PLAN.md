# Kế hoạch phát triển độc lập

Các vai trò dưới đây cần được nhóm chốt theo người; không phải thay đổi bắt buộc bản phân công đã thống nhất. Mỗi hàng là một issue/PR gợi ý, chưa được tạo tự động trên GitHub.

| Vai trò | Đầu việc đầu tiên | Cách kiểm chứng độc lập | Đầu ra chuyển cho người khác |
|---|---|---|---|
| Hạ tầng/tích hợp | Kiểm tra Ubuntu/nested KVM, kết nối và tài nguyên ba node; chốt phiên bản DevStack/plugin | Audit chỉ đọc và log trên từng máy; không cần sửa ứng dụng | Danh sách endpoint/mạng và runbook, không chứa secret |
| Backend/dữ liệu | Tăng test adapter, thử Swift thật khi endpoint có sẵn; thiết kế migration trước khi thêm cột | `pytest tests/storage tests/api`; fake transport dùng khi chưa có OpenStack | API contract, schema và cách cấu hình Swift/DB |
| Frontend/đo tải | Trạng thái chờ/lỗi rõ hơn, tiến trình upload, tìm kiếm sau khi chốt API; workload Locust | UI với backend local trên máy mình; tạo tải nhỏ có kiểm soát | Ảnh, kịch bản và metric cần theo dõi |

## Các mốc tích hợp

1. Mỗi người clone, build và chạy smoke local thành công. Không dùng database hoặc `.env` của người khác.
2. Tích hợp Swift/PostgreSQL trên VM private. Cinder gắn vào VM database; mọi app dùng cùng DB và Swift.
3. Hai App VM qua Octavia. Kiểm tra app không có floating IP và dữ liệu dùng chung.
4. Nối metric thật, Aodh và Heat; app mới boot phải nhận đúng cấu hình, credential và tham gia pool.
5. Demo và thu bằng chứng đủ tiêu chí. Không dùng kết quả fake/local thay thế minh chứng cloud.

## Điểm phối hợp tối thiểu

- UI chỉ phụ thuộc HTTP contract, không import Python hoặc truy cập trực tiếp DB/Swift.
- Backend chỉ phụ thuộc storage interface và cấu hình môi trường, không hard-code IP của thành viên.
- Hạ tầng chỉ phụ thuộc image/lệnh chạy, port 8000, health endpoint, DB/Swift configuration contract.
- Thêm tính năng mới bằng module/PR nhỏ, thông báo trước khi thay contract hoặc schema. Người sửa file chung như Dockerfile/requirements/Compose chịu trách nhiệm test cả stack.
- Đổi cấu hình cụm chung phải hẹn phiên tích hợp. Một thành viên đang làm UI không cần cả ba Ubuntu VM cùng bật.
