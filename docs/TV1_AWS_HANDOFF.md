# TV1 → TV3: tiếp nhận cụm AWS ngày 31/10/2026

Controller và hai Compute đã chuyển sang AWS. Controller laptop `192.168.228.128` đã tắt; kiểm tra hạ tầng và App B sau đó đều đạt. Pull repo chỉ lấy tài liệu/code, không tự tạo hay cấu hình lại các máy đang chạy.

## Máy và AZ hiện tại

| Thành phần | Host/IP quản trị | Vai trò |
|---|---|---|
| Controller | `3.106.184.11`, private `172.31.47.27`, SSH user `ubuntu` | API/control plane; không chạy nova-compute |
| Compute 2 | `ip-172-31-1-199`, private `172.31.1.199` | KVM, AZ OpenStack `tv1-az2`, chạy App B |
| Compute 3 | `ip-172-31-9-62`, private `172.31.9.62` | KVM, AZ OpenStack `nova`, đang có CirrOS và amphora thử |

Controller: Ubuntu 24.04, 2 vCPU, khoảng 8 GiB RAM, root khoảng 40 GiB, swap 2 GiB. Mỗi Compute: 2 vCPU, khoảng 4 GiB RAM. Đo lại tài nguyên/quota trước khi thêm VM. Hai Compute cùng AWS AZ `ap-southeast-2a`: hai AZ OpenStack không phải hai miền lỗi AWS độc lập. Public IPv4 có thể đổi khi EC2 stop/start.

DevStack commit: `9b0a00865c2537338f72ed5b9b44a0d6bff16eb4`; Neutron dùng OVN/Geneve. Không chạy lại `stack.sh`, `unstack.sh` hoặc `clean.sh` để tiếp nhận cụm.

## Cấp quyền SSH và kiểm tra chỉ đọc

TV3 gửi public key và public IPv4 hiện tại cho TV1 qua kênh riêng. TV1 thêm key cho user `ubuntu` và giới hạn TCP 22 theo nguồn đã thống nhất. Private key vẫn ở máy TV3. Không dùng private key EC2 của TV1 để bàn giao.

Fingerprint ED25519 controller đã ghi nhận:

```text
SHA256:CMx1TwlMSxmM9P0RyZywvSQ/nRhK76I63G644Ms8i5E
```

Sau khi được cấp quyền, dùng private key riêng:

```bash
ssh -i /path/to/your-private-key ubuntu@3.106.184.11
sudo -iu stack
cd /opt/stack/devstack
source openrc admin admin
openstack hypervisor list
openstack compute service list --service nova-compute
openstack availability zone list --compute
openstack server list --all-projects --long
openstack network agent list
openstack quota show
free -h
df -h /
```

`openrc` chứa thông tin quản trị trên máy; không gửi nội dung/token cho nhóm hay đưa vào Git. Có một bản ghi nova-compute cũ `down` trùng hostname Compute 3 từ lần đăng ký nhầm cell; hai hypervisor hiện tại đều `up`. Không xóa bản ghi theo hostname khi chưa kiểm tra đúng service/cell.

## Mạng và App B

| Thành phần | Giá trị |
|---|---|
| Tenant network | `private`, ID `6ee39d5e-a790-465c-a46b-8152888957c7` |
| IPv4 subnet | `10.0.0.0/26`, ID `3aa08bc0-4833-4d34-b36a-163993b5a624`, gateway `10.0.0.1`, MTU 1442 |
| External network | `public`, ID `0e1559cb-4e90-4ea0-b91b-e3d1238d31b8`, IPv4 `172.24.4.0/24` |
| Egress | Controller `br-ex=172.24.4.1/24`, NAT qua `enp39s0`, unit `tv1-external-egress` |
| App B | `tv1-app-b-aws`, ID `37b64d69-046a-4888-8e87-a8ae448c26e4`, AZ `tv1-az2` |
| App B IP | Fixed `10.0.0.50`, floating `172.24.4.240`, VPN `100.85.65.41` |
| App B flavor | `ds1G`: 1 vCPU, 1024 MiB RAM, 10 GiB disk |
| App B security group | `tv1-app-private`; TCP 8000 từ `10.0.0.0/26`; SSH từ controller `172.24.4.1/32` |

Floating IP trên mạng external OpenStack chỉ truy cập qua đường quản trị đã cấu hình, không phải public IPv4 EC2. Chưa mở App B cổng 8000 ra Internet. SSH App B cần public key được cấp riêng và đường qua controller hoặc VPN được cho phép.

AWS security groups đã được bổ sung UDP 6081 giữa ba node; kiểm tra đầy đủ hai chiều khi thêm node/backend mới. DNS tenant hiện `1.1.1.1`, `8.8.8.8`.

App B dùng cùng DB/Swift với lab TV2 qua peer `tv2-lab-router` (`100.72.88.88`), quảng bá `10.42.0.22/32` và `172.31.4.101/32`. PostgreSQL: `10.42.0.22:5432`; Keystone: `http://172.31.4.101/identity/v3`; Swift: `172.31.4.101:8080`. Lab TV2 phải bật cả EC2/VPN và DB VM. Credential App B được giữ ngoài repo; TV2 cấp cấu hình phù hợp cho backend mới qua kênh riêng.

Image `tv1-app-b-migration-private` (`852b224c-e9a8-45fe-8390-ed4c9b13146d`) là bản di chuyển có dữ liệu cấu hình/credential và định danh VPN cũ. Giữ private; không dùng làm golden image hoặc nhân bản cho autoscaling. Không boot lại App B cũ đồng thời với bản hiện tại.

## Phần Heat/Octavia đã tồn tại để TV3 kiểm tra

Octavia commit ứng viên đã cài: `aef456859261fb37d5ff9206dfe4455f98fdfb2c`. `stack.sh` ban đầu dừng ở hook Octavia/OVN; dịch vụ được hoàn thiện thủ công. Không xem đây là bộ cài có thể tái chạy tự động.

- Heat API từng phản hồi kiểm tra template versions.
- Các unit Octavia: `tv1-o-mgmt`, `tv1-o-persistent-api`, `tv1-o-persistent-driver-agent`, `tv1-o-persistent-worker`, `tv1-o-persistent-housekeeping`, `tv1-o-persistent-health-manager`.
- Management network `lb-mgmt-net`, subnet `10.76.0.0/24`; worker → amphora TCP 9443, amphora → health-manager UDP 5555.
- LB thử `824a5092-34ff-4b01-a319-1ea43f79ccc2`; listener HTTP 80 `5e9b888a-7ad4-4e41-8cbe-2b8841f9a585` đã từng ACTIVE/ONLINE.
- Amphora VM `4aab99eb-127d-48c0-ad4d-551069085aa7` trên Compute 3; flavor `m1.amphora` 1 vCPU/1024 MiB/2 GiB.
- Chưa nghiệm thu hai backend qua VIP, failover, telemetry/Aodh hoặc autoscaling. TV3 kiểm tra trạng thái thực trước khi tiếp quản resource; không tạo trùng hay xóa resource chỉ theo tên.

## Kết quả và bước tiếp theo

Sau khi controller laptop tắt: hai hypervisor up, hai AZ available, sáu network agent Alive/UP. App B: cloud-init done, metadata đúng UUID, SSH và Internet hoạt động. Khi TV2 bật lại DB: TCP cả ba dịch vụ đạt, container healthy, readiness `ready / swift`, list file HTTP 200 và verify một file có sẵn HTTP 200 với `intact=true`.

TV3 tiếp nhận LB và chuẩn bị backend thứ hai; phối hợp TV2 về image/bootstrap và credential dùng chung. TV1 hỗ trợ mạng, SG và tài nguyên theo nguồn–đích thật. Chưa kiểm chứng đường trực tiếp giữa hai backend trên hai Compute bằng ứng dụng; chưa coi App A ở lab TV2 là backend LB khi chưa thử đường kết nối.

Chi tiết kết quả: [biên bản chuyển cụm](evidence/tv1-aws-controller-migration-20261031.md). Các hướng dẫn cũ dùng controller laptop, `tv1-test-network=10.73.0.0/...` hoặc AZ `tv1-az3` là lịch sử, không dùng để thao tác cụm AWS này.
