# Kế hoạch chốt bài cuối kỳ File Integrity System

Cập nhật ngày 13/11/2026, giờ Việt Nam. Kế hoạch lấy ngày 16/11 trong đề xuất của nhóm làm mốc bảo vệ. TV1 xác nhận lịch chính thức, hạn nộp và định dạng với lớp trước khi chốt lịch nội bộ.

[Biên bản nghiệm thu 13/11](evidence/autoscaling-acceptance-20261113.md) ghi nhận hai backend ở hai AZ, chu kỳ tự động 2 → 3 → 2 và SHA-256 qua VIP. Telemetry dùng Gnocchi/Aodh trên staging cùng relay tạm. Lượt thử có 56/60 phản hồi HTTP 200, 4 timeout ở 4 giây và p95 2,42 giây trên các phản hồi thành công. Giữ các điều kiện và giới hạn này trong báo cáo.

## Lịch và người phụ trách

| Hạn nội bộ | Người chính | Việc cần làm | Đầu ra cần có |
| --- | --- | --- | --- |
| 14/11, 12:00 | TV1 | Chốt kiến trúc thực tế, vẽ sơ đồ Controller Sydney, các Compute, hai AZ, Octavia và đường tới lab TV2. Kiểm tra lại port, floating IP và Keystone RBAC. | Sơ đồ và ảnh/CLI cho mục 1, 2, 5. Ghi rõ floating IP quản trị của App B nếu còn gắn, nguồn được phép và kết quả thử thiếu quyền. |
| 14/11, 18:00 | TV2 | Chuẩn bị bằng chứng upload/list/download/verify, Swift object, PostgreSQL metadata và Cinder volume đính vào VM database. Xác nhận thu hồi credential pilot khi không cần chạy lại. | Một tệp mẫu, UUID/hash và ảnh đã che cấu hình nhạy cảm. |
| 15/11, 12:00 | TV3 | Hoàn thiện timeline autoscaling từ log, chuẩn bị demo và bảng chi phí tháng. | Timeline CPU → Aodh → Heat → Octavia, số đo VIP, bản trình bày và bảng chi phí có nguồn. |
| 15/11, 18:00 | Cả nhóm | Hợp nhất báo cáo, rà tám tiêu chí, diễn tập 10 phút và quay bản dự phòng. Mỗi người giải thích được phần mình và luồng chung. | Báo cáo đã review, video demo, checklist có minh chứng cho từng mục và nhánh/commit giao nộp. |
| Trước giờ nộp/bảo vệ | TV1 điều phối | Kiểm tra quyền xem link, phiên bản file và biên nhận nộp. Nếu demo live, bật lab theo hướng dẫn và xác nhận readiness trước giờ trình bày. | Gói nộp mở được, video chạy được và một lượt upload → download → verify qua VIP. |

## Checklist tám tiêu chí

| # | Tiêu chí | Minh chứng cần có trong báo cáo |
| --- | --- | --- |
| 1 | Mạng và hai AZ | Neutron public/private, Nova compute và ánh xạ App VM → host/AZ `tv1-az2`, `sg-test`. |
| 2 | App private | Địa chỉ private, port/SG và luồng client → VIP → backend. Đối chiếu yêu cầu không có floating IP với thực tế: App B từng có floating IP quản trị. Nếu tiêu chí yêu cầu gỡ, kiểm tra SSH qua đường riêng trước rồi ghi lại kết quả sau đổi. |
| 3 | Swift và Cinder | Swift object của tệp mẫu và Cinder volume đang gắn VM PostgreSQL. |
| 4 | PostgreSQL | Row metadata gồm UUID, SHA-256 của cùng tệp mẫu. |
| 5 | Phân quyền | Keystone role/quyền ứng dụng và một phép thử hành động thiếu quyền. Có thể kèm HTTP 401 khi thiếu API key để minh họa quyền ở tầng ứng dụng. |
| 6 | Load balancing và autoscaling | Hai member gốc ONLINE, Heat hoàn tất hai tín hiệu tự động, member mới ONLINE rồi bị rút và SHA-256 qua VIP khớp. |
| 7 | Monitoring và alarm | Mẫu CPU cao/thấp, chuyển trạng thái Aodh và thời điểm callback. Ghi nguồn metric libvirt, cấu hình alarm và staging. |
| 8 | Chi phí tháng | Bảng gồm EC2 theo region và giờ chạy, EBS theo dung lượng và IPv4/network nếu phát sinh. Ghi nguồn, ngày lấy đơn giá, tỷ giá nếu quy đổi và tách credit/hóa đơn thực khỏi ước tính tháng. |

## Kịch bản demo 10 phút

1. **0–2 phút, TV1.** Mở sơ đồ, chỉ hai AZ, App VM, mạng và pool Octavia.
2. **2–4 phút, TV2.** Upload tệp mẫu qua VIP, xem danh sách, tải xuống và verify SHA-256. Đối chiếu Swift object và PostgreSQL metadata trên Cinder.
3. **4–5 phút, TV1.** Trình bày quyền Keystone và một thao tác bị từ chối bằng danh tính thiếu quyền.
4. **5–8 phút, TV3.** Chiếu timeline hoặc video trích lại lần chạy thật 2 → 3 → 2. Chỉ ra CPU vượt ngưỡng, Aodh gọi Heat, member mới ONLINE và kết quả verify sau scale-in.
5. **8–10 phút, TV3.** Trình bày p95, 4 timeout, giới hạn tải thử và bảng chi phí. Chốt kết quả tám tiêu chí.

## Chuẩn bị và chốt nộp

- **Mặc định demo kết hợp.** Chạy live topology và upload/verify. Trình bày autoscaling bằng log hoặc video đã thu. Pilot, alarm và relay của lần nghiệm thu đã được dọn. Nếu nhóm chọn chạy autoscaling live, dựng lại pilot, xin credential mới có thời hạn và bắt đầu lượt thử trước phần trình bày.
- **Kiểm tra lab trước demo.** TV2 xác nhận DB/Swift và VPN sẵn sàng. TV1 kiểm tra Nova, hai backend, Octavia và VIP readiness. Nếu phần live lỗi, dùng video dự phòng có thời điểm ghi và log đi kèm. [Hướng dẫn khởi động lab](HANDOFF-20261112.md)
- **Rà gói nộp.** Báo cáo có sơ đồ thực tế, tám tiêu chí kèm nguồn, chi phí, bảng phân công và giới hạn kết quả. Repo có mã/cấu hình mẫu và biên bản nghiệm thu. Video và tài liệu mở được bằng quyền người chấm. Người điều phối lưu commit nộp và biên nhận.
