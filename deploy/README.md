# Triển khai ứng dụng lên OpenStack sau giai đoạn local

Đây là cấu hình ứng dụng, chưa phải bộ cài DevStack hoặc minh chứng hạ tầng. Chỉ thực hiện sau khi nhóm có VM và endpoint thật. Không chạy các thay đổi controller/network khi thành viên khác đang kiểm thử.

## Điều kiện

1. Hai Compute/AZ đã tạo được VM và mạng Neutron liên node hoạt động.
2. PostgreSQL chạy trên một VM private; dữ liệu đặt trên Cinder volume đã mount bền vững. Database `integrity` và user chuyên dụng đã được tạo. Chỉ App VM được kết nối cổng 5432.
3. Swift có container `file-integrity`; Keystone application credential được cấp đúng project/role và đã thử đọc/ghi object. Credential là của dịch vụ backend, không tự tạo ra phân quyền người dùng của ứng dụng.
4. App VM có Docker + Compose, đủ egress để build image hoặc được cấp image đã build trước; truy cập được PostgreSQL, Keystone và Swift endpoint đã chọn.
5. Security group của App VM cho phép cổng 8000 từ đường đi của Octavia; không gắn floating IP cho App VM.

## Chạy trên mỗi App VM

Chuyển cả thư mục mã nguồn sang VM bằng Git clone hoặc SCP. Trên VM, vào thư mục `deploy`, sao chép `app.env.example` thành `app.env`, điền endpoint và secret thật, giới hạn quyền đọc:

```sh
cp app.env.example app.env
chmod 600 app.env
docker compose --env-file app.env -f compose.openstack.yaml up -d --build --wait
docker compose --env-file app.env -f compose.openstack.yaml logs --tail 100
```

Mọi App VM dùng cùng database và container Swift. Cấu hình publish cổng 8000 trên VM để Octavia kết nối; giới hạn truy cập bằng security group. TLS termination và routing public/VPN phải được nhóm cấu hình riêng.

Không copy volume `file-data` local lên từng App VM để giả lập shared storage. Tệp demo local không tự xuất hiện trên Swift; cần upload lại sau khi đổi môi trường.

## Checklist minh chứng 8 hạng mục

| Hạng mục | Cần xác minh trên cụm thật |
|---|---|
| Mạng và 2 AZ | Nova host aggregate/AZ, VM trên từng compute; traffic Neutron liên node |
| App private | Không có floating IP trên App VM; truy cập ứng dụng qua Octavia |
| Hai storage | Nội dung ở Swift; PostgreSQL data directory ở mount Cinder |
| Database | Row metadata khớp UUID, kích thước, SHA-256; vẫn còn sau restart |
| Phân quyền | Keystone credential có scope; thử thao tác ngoài quyền bị từ chối |
| LB và autoscaling | Hai backend hoạt động; alarm gây Heat tạo/xóa App VM và cập nhật pool |
| Monitoring | Metric thật, ngưỡng, khoảng lấy mẫu, Aodh history và thời điểm scale |
| Chi phí | Phần mềm/hạ tầng/thuê dịch vụ theo thực tế; ghi rõ phần không tính |

## Các phần hạ tầng còn phải triển khai

Bộ chuẩn bị TV3 nằm trong [elasticity/](elasticity/README.md): template LB, hai nhóm VM theo AZ, alarm tùy chọn, kiểm tra offline và công cụ thu snapshot chỉ đọc. Các template này chưa được chạy trên OpenStack; dùng runbook để validate và triển khai từng bước sau khi có môi trường thật.

- Chốt bản DevStack/OpenStack và plugin đồng bộ trên cả ba node.
- Thử nested KVM, Tailscale, MTU và đường đi của floating IP tới người xem demo.
- Dựng Swift/Cinder/PostgreSQL, Nova AZ, Octavia và health monitor.
- Chốt nguồn metric (ví dụ Ceilometer/Gnocchi), cấu hình Aodh và Heat autoscaling, cooldown, giới hạn VM; kiểm tra App VM mới nhận được cấu hình/secret và tham gia pool.
- Thu log/ảnh/video thật. Chưa có kết quả OpenStack nào được khẳng định chỉ từ bộ mã local này.
