## Thay đổi và lý do

Mô tả tính năng/lỗi và kết quả sau khi sửa. Liên kết issue nếu có.

## Phạm vi

- [ ] Backend/API/storage
- [ ] Frontend
- [ ] Deployment/load test/docs

## Kiểm chứng

Ghi lệnh đã chạy, kết quả và ảnh nếu thay đổi giao diện. Phân biệt local, fake Swift và OpenStack thật.

- [ ] Kiểm thử phù hợp đạt; không bỏ test chỉ để làm CI xanh
- [ ] Không có secret, `.env`, dump database hoặc dữ liệu người dùng trong diff
- [ ] Cập nhật tài liệu API nếu thay đổi contract
- [ ] Cập nhật cả requirements và lock nếu thay đổi dependency
- [ ] Có kế hoạch migration nếu thay đổi schema

## Ảnh hưởng tới thành viên khác

Endpoint/cấu hình/schema thay đổi, cách chạy mới hoặc ghi rõ không có.
