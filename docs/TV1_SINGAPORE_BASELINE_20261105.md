# TV1 — baseline khảo sát Compute Singapore, 05/11/2026

Thời điểm thu thập: 23:14–23:16 giờ Việt Nam. Thông tin động cần đo lại trước phiên. Đây là khảo sát; chưa đăng ký Singapore, chưa đổi OVN encap/MTU, chưa khởi động App B. Không có secret trong tài liệu này.

## 1. Cụm và tài nguyên

| Node | OpenStack / tình trạng | CPU | RAM khả dụng | Disk `/` còn trống |
|---|---|---:|---:|---:|
| Controller Sydney | control plane; 172.31.47.27 | 2 vCPU | 1,0 GiB / 7,6 GiB | 14 GiB / 38 GiB |
| Compute 2 Sydney | ip-172-31-1-199, `tv1-az2`, up | 2 vCPU | 2,5 GiB / 3,7 GiB | 14 GiB / 29 GiB |
| Compute 3 Sydney | ip-172-31-9-62, `nova`, up | 2 vCPU | 1,9 GiB / 3,7 GiB | 21 GiB / 29 GiB |

Nova báo hai hypervisor up; tổng inventory RAM 7624 MiB, free_ram_mb 4296, 4 vCPU và vcpus_used 3, local disk 56 GiB, free_disk_gb 43. Đây là inventory/đặt chỗ, không đồng nghĩa RAM vật lý `available`; các trường tổng không thay thế kiểm tra từng host, overcommit hoặc Placement allocations.

Hai agent OVN controller, hai metadata agent của Compute, gateway và Neutron OVN agent của Controller đều Alive/UP. AZ `nova`, `tv1-az2` available. App B `tv1-app-b-aws` SHUTOFF, CirrOS thử SHUTOFF, amphora ACTIVE. Hai Compute Sydney cùng AWS AZ ap-southeast-2a.

Service cũ `40550043-1be5-4f47-9a1e-f2c506c052eb` trên hostname Compute 3 `enabled/down`, heartbeat 31/10; service thực đang dùng `3e6590b7-0bc4-4213-8d50-6060a15a6a82` `up`. Không xóa theo hostname; chưa kiểm chứng database/cell của service cũ.

Quota `admin` được CLI báo cores 20, instances 10, RAM 51200 MiB, networks/subnets 100, ports 500, security groups 100; output cột project_id None nên cần xác minh đúng project ID và usage/đặt chỗ thực tế trước khi tạo VM. Không coi quota limit là tài nguyên còn trống.

## 2. Phiên bản và compute-only

| Thành phần | Commit/phiên bản |
|---|---|
| DevStack | `9b0a00865c2537338f72ed5b9b44a0d6bff16eb4` |
| Nova | `94de0576ca02e0668233bedfbe7e18b87316c708` |
| Neutron | `0d3e8e65b0c5171c654dcf2fca78bdd1b09b6107` |
| Placement | `8e91e4d7aad1c6a642f80ec6387ce08d86f7c26d` |
| requirements | `9edc04289eca1a4c18ae86e4430416d82a5b07fa` |
| OVS / OVN | 3.3.9 / 24.03.8 trên cả ba node |

Compute-only hiện chạy `devstack@n-cpu` (nova-compute dùng `/etc/nova/nova-cpu.conf`), `ovn-controller`, OVS và `devstack@q-ovn-metadata-agent` (dùng `/etc/neutron/neutron_ovn_metadata_agent.ini`). Dịch vụ đều active trên hai Compute. Node mới phải dùng cell transport, Keystone/Placement/Glance/Neutron, metadata và OVN SB tương thích, endpoint địa chỉ có thể tới được qua VPN. Chưa pin được toàn bộ dependency, chưa có local.conf hoàn chỉnh và chưa chứng minh khả năng cài máy Singapore. Không chép nguyên cấu hình có secret hoặc đổi endpoint khi chưa kiểm tra.

## 3. Kết nối và quyền

| Node | IP Tailscale | IP AWS hiện tại | Encap OVN hiện tại |
|---|---|---|---|
| Controller | 100.127.44.18 | 172.31.47.27/20 | 172.31.47.27 |
| Compute 2 | 100.102.196.94 | 172.31.1.199/20 | 172.31.1.199 |
| Compute 3 | 100.102.48.51 | 172.31.9.62/20 | 172.31.9.62 |
| Singapore | 100.108.40.36 | 172.31.36.23/20 | chưa cấu hình |

VPC Singapore 172.31.0.0/16, subnet 172.31.32.0/20 trùng VPC/subnet phía Controller. `ip route get 172.31.36.23` trên Controller chọn enp39s0 nội bộ; không dùng các IP AWS trùng dải làm địa chỉ liên vùng. Route Tailscale 100.108.40.36 từ hai Compute đi tailscale0/table 52. Không quảng bá subnet route.

| Nguồn → đích | Giao thức/cổng | Trạng thái |
|---|---|---|
| Singapore → Controller | TCP 80, 5672, 6642, 8775 | TV3 báo bắt tay TCP đạt; chưa xác thực dịch vụ |
| Singapore ↔ Compute 2/3 | UDP 6081 | TV1 thấy 3/3 gói thử vào mỗi Compute; TV3 xác nhận hai chiều. Chỉ là UDP giả, chưa chứng minh Geneve/OVN |
| Singapore ↔ Compute 2/3 | ICMP | 1280-byte IPv4 DF đạt 2/2 từ Sydney, TV3 báo chiều ngược 3/3 |
| Compute Singapore → Controller | SSH quản trị, Neutron/Nova/Placement/Glance/Keystone và RabbitMQ | cần chốt endpoint thực tế, danh tính và ACL; không public các control-plane port |
| Mọi chassis tham gia cùng logical network | Geneve UDP 6081 các cặp node | chưa cấu hình/test thực tế, cần chính sách tailnet và firewall hai chiều |
| VM test → metadata | 169.254.169.254 qua OVN metadata; agent → Controller TCP 8775 | cần thử sau khi có node/mạng test |

Hai Compute có iptables INPUT nhảy `ts-input` trước các rule cũ cho IP tailnet trường và DROP tailscale0; trong `ts-input` có ACCEPT `-i tailscale0` nên không thể suy luận rule DROP sau đó bảo vệ mọi cổng. Cần kiểm tra ACL Tailscale, thứ tự netfilter, IPv6/nftables và security group thực tế theo nguồn–đích trước phiên; tcpdump chỉ chứng minh tới interface trước firewall. Chưa kiểm chứng quyền SSH Singapore tới Sydney hay policy hai chiều đầy đủ. Tailscale ACL giới hạn peer/cổng; AWS SG chỉ cần cổng underlay Tailscale phù hợp và SSH quản trị theo nguồn; không mở trực tiếp 5672/6642/6081 ra Internet.

Quan trọng: mỗi chassis hiện quảng bá một encap IP AWS; Singapore không định tuyến được các địa chỉ trùng VPC. Một tenant network mới không tự làm các chassis cũ có đường tunnel Tailscale: phải có giải pháp underlay tới **tất cả** node mang port, và xét ảnh hưởng workloads hiện có. Phương án re-encap các chassis sang VPN sẽ tác động cả mạng hiện tại và cần phiên riêng cùng backup/rollback được chứng minh; không thực hiện trong bước khảo sát.

## 4. MTU và đề xuất thử

Tailscale MTU 1280; tenant `private` và `lb-mgmt-net` 1442, đều Geneve. ML2 `overlay_ip_version=4`, `max_header_size=38`; giá trị 38 là thông số Neutron, không được trừ hai lần các header. Lấy ví dụ cấu hình hiện tại 1500 → 1442 (58 byte) thì 1280 − 58 = **1222 byte** là ước lượng ban đầu, cần đối chiếu cách tính và bắt gói trên kernel/OVS thực tế. Đề xuất network test **IPv4-only MTU 1200**, không coi là giá trị đã xác nhận. IPv6 có minimum MTU 1280 nên không gắn IPv6 subnet vào network thử 1200; muốn IPv6 cần underlay phù hợp hoặc thiết kế khác và kiểm thử riêng. Không thay MTU tenant/amphora đang có.

Chỉ sau khi có underlay mesh và quyền, tạo network Geneve IPv4 thử riêng, CIDR ứng viên `10.250.17.0/24` (kiểm tra trùng toàn bộ VPC/tenant/VPN trước), MTU 1200, DHCP, không nối router/public mặc định. SG test chỉ cho ICMP/SSH từ nguồn quản trị và lưu lượng cần thiết giữa các VM; tạo tên/ID độc lập. Dùng 2 VM CirrOS image `67ee0ba4-6d26-4d28-992b-f0932b8fa202` active và flavor `cirros256` 1 vCPU/256 MiB/1 GiB, một node Singapore và một Sydney; cần xác nhận quota/capacity và chỉ định host/AZ đúng. Test hai chiều DHCP, metadata UUID/user-data giả, ICMP DF phù hợp MTU, TCP + payload SHA-256, liên tục theo dõi app/LB hiện có. Lưu ý metadata OVN cần route agent tới controller.

## 5. Baseline và rollback

Đã đọc `ip -br addr`, `ip route`, `ip rule`, `ovs-vsctl get ... external-ids`, iptables `-S`, FORWARD/NAT trên controller, `systemctl is-active`, `virsh list --all`, network agents, VM/AZ/quota, `free -h`, `df -h`, MTU. Đây là baseline quan sát; chưa có bản sao lưu cấu hình/database nhất quán và chưa thử khôi phục.

Đã chạy [scripts/tv1_capture_baseline.py](../scripts/tv1_capture_baseline.py) trên ba host lúc 23:19. Script chỉ đọc trạng thái và tạo file root-only; không đổi route/firewall/OVN. Các thư mục sau có file command output, archive cấu hình Nova/Neutron/systemd/netplan và manifest SHA-256:

| Host | Thư mục root-only | Số file cấu hình đã kiểm tra |
|---|---|---:|
| Controller | `/root/tv1-sg-baselines/ip-172-31-47-27-20261105T161909Z` | 47 |
| Compute 2 | `/root/tv1-sg-baselines/ip-172-31-1-199-20261105T161914Z` | 15 |
| Compute 3 | `/root/tv1-sg-baselines/ip-172-31-9-62-20261105T161922Z` | 17 |

Archive được đọc lại và đối chiếu từng file bằng SHA-256 thành công. Controller không có `virsh` (không chạy nova-compute), script ghi nhận thiếu lệnh này thay vì coi là lỗi guest. Không tải archive có secret về local/Git. Đây **chưa** là backup database nhất quán hay diễn tập phục hồi. Chưa chụp ACL tailnet/AWS security groups/Placement allocations đầy đủ. Những phần này và restore drill trên lab tách riêng vẫn là điều kiện trước thay đổi ảnh hưởng cụm.

Đường dự phòng đã kiểm tra: Controller public SSH (host key đã đối chiếu), Compute 2 public SSH và Compute 3 SSH qua controller/private IP; không phụ thuộc VPN trường. Trước phiên cần thử lại vì IP public và rule My IP có thể thay đổi.

Rollback cụ thể phải gắn theo thao tác thực sự: dừng tạo mới; giữ App B và workload; chỉ xóa VM/port/network thử xác định bằng ID sau khi xác nhận không còn dùng; gỡ cấu hình/node Singapore theo runbook và kiểm tra cell/Placement trước khi xóa service; phục hồi giá trị encap, routes, firewall, MTU và config từ bản lưu nếu đã thay, theo thứ tự được thử trên lab riêng. Kiểm tra OVN chassis/bindings, agents, hai compute up, VM hiện có, DHCP/metadata và đường ứng dụng/DB/Swift. Không chạy `stack.sh`, `unstack.sh`, `clean.sh` trên Controller. Chưa có rollback được kiểm chứng: điều kiện chặn phiên thay đổi ảnh hưởng cụm.

## 6. Đầu vào/điều kiện dừng

TV3 cung cấp commit/dependency thực tế node, subnet/route/SG, quyền cài và SSH public key; TV1 cấp danh tính/cấu hình cần thiết qua kênh an toàn hạn chế quyền; TV2 cung cấp credential riêng chỉ khi cần App. Không gửi `local.conf`, token, mật khẩu, private key hay bản sao VM có credential lên Git/chat. Tài khoản `tv3-audit` chỉ trả snapshot, không đủ quyền triển khai.

### Thứ tự thực hiện đề xuất cho phiên tới

1. Đối chiếu và pin dependency Compute Singapore trên máy mới; chỉ cài package/code, không start nova-compute/ovn-controller để tránh đăng ký sớm. Mẫu DevStack multinode trong tài liệu chỉ dùng làm tham khảo, không chạy nguyên mẫu trên Controller.
2. Trong lab mạng tách biệt (network namespace/OVS thử, không đụng br-int/OVN hiện tại), kiểm tra Geneve với payload thật MTU 1200 qua Tailscale. Chỉ thực hiện khi có quyền trên cả hai đầu và đã xác nhận cách cô lập. Kết quả UDP chữ vừa rồi không thay thế bước này.
3. Chốt một phương án underlay cho tất cả chassis trước khi tạo logical network test. Phương án đơn giản là chuyển encap các chassis sang IP VPN trong phiên bảo trì, nhưng sẽ chạm cụm đang có và không được duyệt trong khảo sát này; phương án giữ encap cũ cần thiết kế underlay khác giải quyết trùng VPC. Không quảng bá 172.31.0.0/16 qua VPN để né vấn đề.
4. Khi có backup/restore drill và đồng ý cho phiên bảo trì, thử node/mạng IPv4 riêng với CirrOS, canary trên đúng host; ghi rõ ID resource mới. Chưa boot image App B vì chứa credential và định danh VPN của máy cũ.
5. Nghiệm thu rồi mới bàn thay Compute 2/chuyển App B với TV2. Không xóa Compute 2 hoặc bản ghi cũ để giải phóng quota trong lúc khảo sát.

Dừng nếu không có mesh và MTU được test, baseline/khôi phục chưa chứng minh, controller thiếu RAM/disk/quota, Agent hoặc workload hiện hữu lỗi, tunnel/metadata không ổn định, CIDR trùng, policy/credential không rõ, chi phí chưa chốt. Đo lại đường trực tiếp/DERP, MTU và ping trước phiên; việc chuyển node sang Tailscale có thể đổi đường quản trị và ảnh hưởng cả tenant/amphora.

Tham khảo: [cấu hình Geneve Neutron](https://docs.openstack.org/neutron/2025.1/configuration/ml2-conf.html), [DevStack multinode](https://docs.openstack.org/devstack/2026.1/guides/multinode-lab.html).

## Geneve cách ly đã chuẩn bị

Bộ thử: `scripts/tv1_geneve_probe.py`. Tạo đúng một interface kernel `gnv-tv1-test`, VNI 730017, UDP6082, CIDR benchmark 198.18.173.0/30, MTU1200; không gắn bridge/OVS hay sửa cấu hình Nova/OVN. Từ chối interface/CIDR trùng; finally thu dọn, bắt SIGTERM/SIGINT. Nếu tiến trình bị SIGKILL hay host mất điện thì finally không chạy; phải kiểm tra và dọn interface có đúng quyền sở hữu trước khi thử lại.

Chạy trước giữa Compute 2 và 3 trên Tailscale: mỗi chiều hai vòng đầu ping 3/3 gói IPv4 DF tổng 1200 byte; vòng cuối C2→C3 3/3, chiều C3→C2 2/3 khi hai phía kết thúc lệch giờ. Cả hai cleanup trả 0. Không kết luận mất gói do mạng hay kết luận benchmark ổn định; script được bổ sung thời gian giữ tunnel cuối phiên để tránh peer dọn sớm. Chưa chạy Singapore và không dùng kết quả này thay cho Geneve OVN/UDP6081.

Trên Singapore, sau khi đối chiếu route/CIDR không trùng, thực hiện trong phiên cùng TV1 (TV1 chạy đầu đối ứng):
```bash
sudo python3 scripts/tv1_geneve_probe.py --peer 100.102.196.94 --side b
```
Đầu Sydney C2 dùng `--peer 100.108.40.36 --side a`. Chỉ chạy một cặp mỗi lần; khi kết thúc kiểm tra `ip link show gnv-tv1-test` không còn. Sau C2 mới thử C3 với IP 100.102.48.51. Không đổi port sang 6081 trên host đang có OVN. UDP6082 cần được policy cho phép ở cả hai đầu; bài UDP6081 trước không chứng minh quyền UDP6082.

### Lượt Compute 2 ↔ Singapore khoảng 23:35–23:37
- TV1 chạy đầu C2 20 vòng; vòng 7 đạt 3/3 nhưng RTT cao, vòng 8–13 mỗi vòng 3/3 với RTT khoảng 94–95 ms; vòng 1–6 và 14–20 không nhận trả lời.
- TV3 báo journal Singapore READY 23:35:27, kết thúc 23:36:05; 3 vòng × 3/3 gói IPv4 DF 1200 byte, cleanup 0, interface/route đã dọn.
- Script TV1 lúc chạy chưa ghi timestamp mỗi vòng. Không có căn cứ đối chiếu chính xác vòng lỗi với khoảng overlap; không kết luận các lỗi đều ngoài thời gian overlap, không tái dựng timestamp từ độ dài sleep/ping.
- TV1 quan sát tunnel còn tồn tại lúc 23:36:50, sau đó cleanup 0; kiểm tra lúc 23:37:33 interface đã mất, Nova/OVN active.
- Đã chứng minh một số vòng Geneve thật UDP6082/MTU1200 hai chiều; chưa chứng minh ổn định toàn phiên, chưa phải Geneve OVN hay VM-to-VM.
- Script mới có READY_UTC, START_UTC/END_UTC từng vòng và CLEANUP_UTC; hỗ trợ --rounds 1..20 thay vì sửa code tạm. Hai bên phải cập nhật cùng commit trước lượt tiếp; dùng journal hoặc tee ở thư mục private, đối chiếu UTC/NTP và lưu log đủ.
