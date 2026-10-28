# Đối chiếu yêu cầu và kết quả TV2

Phạm vi TV2 theo tài liệu phân công của nhóm là FastAPI, Swift, PostgreSQL trên Cinder, xử lý lỗi, kiểm thử, sao lưu và migration khi đổi schema. Kết quả kiểm tra ngày 28/10/2026 cho thấy phần backend/dữ liệu trên lab một compute đủ điều kiện bàn giao để nhóm tích hợp. Schema không thay đổi trong phần bàn giao này nên không phát sinh migration.

| Yêu cầu TV2 | Bằng chứng | Kết quả |
|---|---|---|
| Upload/list/download/verify, giữ HTTP contract | Pytest, smoke live và báo cáo tích hợp ngày 28/10 | Đạt |
| Nội dung tệp ở Swift thật | Đọc trực tiếp object, đối chiếu API download và SHA-256 | Đạt |
| Metadata ở PostgreSQL trên Cinder | Truy vấn ID/size/hash, `SHOW data_directory`, `findmnt` | Đạt; `/srv/postgresql/data` trên `/dev/vdb` |
| Xử lý lỗi và dữ liệu sai | Sửa object cùng kích thước, mất object, vượt 25 MiB, tệp rỗng/tên trùng | Đạt ngày 28/10 |
| Hạn chế truy cập | Thiếu/sai API key, Swift không token, sai project, cổng DB ngoài App security group | Đạt ngày 28/10 |
| Lỗi DB và dọn object mồ côi | Liveness/readiness, ghi metadata thất bại, phục hồi DB | Đạt trong phiên 26/10 |
| Backup và restore | Dump DB, lưu Swift object, restore vào DB tạm riêng | Đạt trong phiên 26/10 |
| Độ bền dữ liệu | Reboot DB VM, mount lại Cinder, reboot App VM, hash fixture giữ nguyên | Có bằng chứng phiên trước tại `persistence.json` |

## Các lần kiểm tra

- [verification-20261028.json](verification-20261028.json): báo cáo gốc lấy từ EC2 sau `btl-tv2 check`, lúc **09:58:30 UTC ngày 28/10/2026** (16:58:30 UTC+7), **22 ca đạt**. Các thay đổi/sửa/xóa object chỉ áp dụng lên fixture mới tạo và script phục hồi object đó.
- [application-tests-20261028.txt](application-tests-20261028.txt): kết quả pytest **17 passed, 1 warning** và smoke API/frontend chạy trong container trên App VM ngay sau phiên tích hợp trên. Cảnh báo là deprecation của Starlette/AnyIO.
- [verification-20261026.json](verification-20261026.json): báo cáo lịch sử lúc **16:58:08 UTC ngày 26/10/2026**, **28 ca đạt**, gồm 6 ca lỗi DB và backup/restore bổ sung. Không chạy lại các ca dừng DB trong phiên 28/10.
- [persistence.json](persistence.json): bản sao bằng chứng reboot lưu từ phiên trước; file gốc không có timestamp nên không dùng nó để khẳng định đã reboot trong phiên 28/10.
- [source-sha256.txt](source-sha256.txt): hash các file `app/`, `frontend/`, `tests/` và script kiểm tra. Đã đối chiếu với file trên App VM/EC2; nội dung khớp repo sau chuẩn hóa CRLF thành LF.

Báo cáo JSON chứa endpoint, địa chỉ private và ID tài nguyên lab để đối chiếu; không chứa token, mật khẩu, API key hoặc nội dung tệp upload. Credential, khóa SSH, dump DB, dữ liệu upload và backup thật được giữ ngoài Git. Báo cáo là ảnh chụp kết quả tại thời điểm chạy, không đảm bảo lab luôn bật.

## Phần còn cần tích hợp

Hai compute/hai AZ thuộc TV1; Octavia, Heat/Aodh, metric và kiểm thử scale theo tải thuộc TV3 phối hợp TV1. Khi có App VM thứ hai, TV2 cần phối hợp kiểm tra hai backend cùng dùng DB/Swift: upload qua backend A rồi download/verify qua backend B.

Swift hiện có một replica; Swift, Cinder và backup dùng chung EC2/EBS. Kết quả này chưa chứng minh HA hoặc backup ngoài host. API key là khóa dùng chung; Keystone scope không thay thế tài khoản/phân quyền từng người ở ứng dụng. BTL toàn nhóm vẫn cần các minh chứng tích hợp, monitoring và chi phí theo [checklist triển khai](../../README.md).
