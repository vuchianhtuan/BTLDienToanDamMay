# Kết quả chuyển cụm TV1 lên AWS — 31/10/2026

Đây là biên bản kiểm tra thực tế cụm TV1, không phải benchmark hay minh chứng autoscaling. Trạng thái tiếp nhận và lệnh kiểm tra nằm trong [TV1_AWS_HANDOFF.md](../TV1_AWS_HANDOFF.md).

## Hạ tầng sau chuyển

- Controller AWS: 3.106.184.11 / 172.31.47.27, DevStack 9b0a00865c2537338f72ed5b9b44a0d6bff16eb4, OVN/Geneve.
- Compute 2 ip-172-31-1-199 đã chuyển Nova, OVN và metadata sang controller AWS; AZ tv1-az2.
- Compute 3 ip-172-31-9-62 đã chuyển sang controller AWS; AZ nova.
- Hai hypervisor up, hai AZ available, sáu OVN/metadata/gateway agent Alive/UP khi kiểm tra sau khi controller laptop tắt.
- Hai Compute cùng AWS AZ ap-southeast-2a. Không coi hai AZ OpenStack là khả năng chịu lỗi giữa hai AWS AZ.
- Controller laptop 192.168.228.128 đã systemctl poweroff. Sau đó SSH controller cũ timeout, còn SSH App B qua controller AWS vẫn hoạt động.
- Có một bản ghi nova-compute cũ down trùng hostname Compute 3 từ lần đăng ký nhầm cell; hai dịch vụ/hypervisor đang sử dụng đều up.

## Bảo toàn và khôi phục App B

- Bốn đăng ký libvirt cũ trên Compute 2 đã được undefine với xác nhận riêng của người dùng, giữ disk, XML và bản sao cấu hình.
- Bản sao qcow2 độc lập qua qemu-img check và qemu-img compare; SHA-256 nguồn/đích cùng giá trị 523be42ac23470d8206b844b21f93940e6433cb56a446b8435cdaf45409dc78d.
- Image Glance 852b224c-e9a8-45fe-8390-ed4c9b13146d active/private, 3351773184 byte. Đây là image di chuyển có cấu hình/credential/VPN, không dùng làm golden image hay boot bản sao đồng thời.
- App B mới 37b64d69-046a-4888-8e87-a8ae448c26e4 ACTIVE trên Compute 2/tv1-az2, ds1G, private IP 10.0.0.50, floating IP 172.24.4.240.
- Cloud-init done; metadata trả đúng UUID; fingerprint SSH được đối chiếu với console trước khi đăng nhập.
- Bản rollback cũ có chốt từ chối nếu tên libvirt đã được VM cụm mới tái sử dụng. Chưa thử phục hồi toàn bộ; không chạy rollback trong khi guest mới đang hoạt động.

## Kiểm tra mạng

- Egress controller br-ex 172.24.4.1/24, forwarding và NAT giới hạn nguồn 172.24.4.0/24 qua enp39s0; người dùng xác nhận trước khi áp dụng. Unit tv1-external-egress active.
- UDP 6081 đã được người dùng bổ sung giữa ba node. Sau đó controller ping floating IP App B đạt 2/2 và SSH thành công.
- App B nhận DNS 1.1.1.1/8.8.8.8 sau DHCP renew; HTTPS Internet HTTP 200, kể cả sau khi laptop VM tắt.
- SSH Compute 2 dùng VPN trực tiếp; Compute 3 qua controller AWS. Không cần ProxyJump qua controller laptop.
- Chưa đo đầy đủ MTU xuyên mọi đường tenant/VPN và chưa nghiệm thu kết nối ứng dụng trực tiếp giữa hai Compute.

## Dữ liệu chung TV2

Lúc TV2 bật EC2 nhưng DB VM còn tắt, PostgreSQL timeout; Keystone và Swift nhận TCP. Sau khi TV2 khởi động DB/App VM:

- VPN tv2-lab-router online; App B tailscale0 100.85.65.41, route DB qua VPN.
- TCP App B → 10.42.0.22:5432, 172.31.4.101:80 và :8080 đều thành công.
- Container App B healthy; /health/ready trả status=ready, storage=swift.
- GET /api/files trả HTTP 200, có dữ liệu.
- POST verify một file có sẵn trả HTTP 200, intact=true.
- Credential chỉ được dùng trong container, không in ra log hay đưa vào Git.
- Sau di chuyển chưa chạy lại bài upload chéo hai chiều A/B hoặc kiểm thử tải.

## Phần TV3 tiếp nhận

Heat API đã được kiểm tra phản hồi. LB thử 824a5092-34ff-4b01-a319-1ea43f79ccc2 và listener HTTP từng ACTIVE/ONLINE, amphora trên Compute 3. Cài Octavia có phần hoàn thiện thủ công sau lỗi hook DevStack. Đây chưa phải minh chứng backend, failover, telemetry hoặc autoscaling; TV3 kiểm tra lại trước khi tích hợp.
