# Underlay MTU1500 cho Singapore — 06/11/2026

> Cập nhật sau bàn giao: Singapore đã kết nối10.253.239.4. Tài khoản tải `tv3-underlay` đã bị khóa/hết hạn, gỡ authorized_keys và sudoers sau khiTV3 xác nhận checksum; các lệnh tải bên dưới chỉ ghi lịch sử, không còn dùng được. Chứng chỉ VPN không bị thu hồi.

TV1 xác nhận từ Controller, Compute2 và Compute3 tới Singapore: mỗi nguồn ping DF1500 đạt3/3, RTT khoảng94–108ms. TV3 xác nhận chiều ngược mỗi đích3/3, route172.31.47.27/32 qua VPN, default route/SSH vẫn qua AWS; TCP80/5672/6642/8775 bắt tay được nhưng chưa xác thực dịch vụ. Hai ComputeSydney up, LB ACTIVE/ONLINE. Singapore VPN active nhưng chưa enable khi boot; chưa có Nova/OVN, DHCP/metadata/VM-to-VM tạiSingapore.

## Trạng thái đã thay đổi
OpenVPN/TCP chạy bên trong Tailscale, tun MTU1500. Server chỉ bind `100.127.44.18:1194/TCP`, không mở1194 ra Internet. TLS/chứng chỉ riêng từng client, client-to-client bật, không push default route hay DNS. Đây là hub: server giải mã/định tuyến giữa client, không phải mesh end-to-end. Có double encryption/head-of-line blocking; chưa benchmark dài hạn.

| Node | Tailscale | OpenVPN/OVN encap hiện tại |
|---|---|---|
| Controller | 100.127.44.18 | 10.253.239.1 |
| Compute 2 | 100.102.196.94 | 10.253.239.2 |
| Compute 3 | 100.102.48.51 | 10.253.239.3 |
| Singapore | 100.108.40.36 | 10.253.239.4 dành riêng, chưa kết nối |

OVN encap ba node Sydney đã đổi sang IP OpenVPN. Tenant/amphora MTU1442 giữ nguyên. Ping DF1500 C3→Controller/C2 đạt3/3; OVN thật Controller→amphora DF1442 đạt5/5, TCP9443 đạt, LB ACTIVE/ONLINE, hai hypervisor up, sáu agent Alive/UP, App B SHUTOFF. OpenVPN enable tự khởi động; ovn-controller có After/Wants OpenVPN. Chưa thử reboot/recovery hoặc load/failoverVPN. Timer rollback tạm đã dừng sau test.

Thử trước đó dùng encap Tailscale1280 trực tiếp thất bại gói1442; `ovn-encap-df_default=false` vẫn không giải quyết PMTU của OVN. Các thay đổi đó đã hoàn tác, tùy chọn DF đã gỡ; không tiếp tục dùng cấu hình thử này.

## TV3 lấy file riêng
TV1 đã cho phép rõ cấp cấu hình OpenVPN riêng Singapore (có keyVPN mới, không có private keyAWS). Account `tv3-underlay` chỉ forced-command đọc đúng file, không shell/PTY/forwarding; public keyTV3 đã cung cấp, giới hạn nguồn `1.55.109.159` hoặc `100.108.40.36`. `tv3-audit` vẫn chỉ trả snapshot cũ. Chưa kiểm chứng đăng nhập từ máyTV3.

Controller SSH `15.135.67.242`, ED25519 fingerprint:
`SHA256:CMx1TwlMSxmM9P0RyZywvSQ/nRhK76I63G644Ms8i5E`

Từ máy giữ private keyTV3, lưu file trực tiếp ngoài repo. Bash:
```bash
umask 077
ssh -T -i /path/to/tv3-private-key tv3-underlay@15.135.67.242 > singapore.ovpn
sha256sum singapore.ovpn
```
SHA256 file nguồn:
`df9fe73e50c7b24e8d0527442fe6d2f5e54b5df788951a886d674af37a35c5cc`

PowerShell5.1 redirection có thể đổi encoding/newline: dùng công cụ giữ nguyên byte hoặc Python subprocess ghi stdout binary. File chứa private keyVPN; không commit/in nội dung/chat/chụp ảnh. Chuyển file sang Singapore bằng kênh riêng đã xác thực; không cần chuyển private keySSH quản trị laptop lên server.

Sau khi kiểm tra không trùng10.253.239.0/24, trên Singapore:
```bash
sudo env NEEDRESTART_MODE=l apt-get install -y openvpn
sudo install -m 0600 singapore.ovpn /etc/openvpn/client/tv1.conf
sudo systemctl start openvpn-client@tv1
ip -br addr show tun-tv1ovpn
ping -c 3 -M do -s 1472 10.253.239.1
ping -c 3 -M do -s 1472 10.253.239.2
ping -c 3 -M do -s 1472 10.253.239.3
ip route get 172.31.47.27
```
Singapore được push route **172.31.47.27/32 qua VPN** để endpoint controller không đi nhầm subnet Singapore; không route cả172.31.0.0/16. Phải kiểm tra thật sau kết nối; chưa chứng minh API auth. Chưa enableVPN Singapore khi chưa nghiệm thu.

Chỉ sau khi test đường mới đạt, chuẩn bị compute-only theo baseline commit; encapSingapore10.253.239.4, OVN SB controller10.253.239.1:6642; endpoint cell/Keystone/Placement/metadata phải kiểm tra. CredentialOpenStack là bước riêng chưa cấp. Chưa đăng ký Nova/OVN Singapore. Thử networkIPv4/VM DHCP/metadata/VM-to-VM trước khi bàn chuyển App B.

## Bản sao và rollback
MySQL dump root-only `/root/tv1-sg-integration-20261106/databases-private.sql.gz` tạo bằng `--single-transaction --quick --routines --events --triggers`, gzip-t đạt. Không chứng minh nhất quán bảng nontransactional hoặc restoreDB. PKI/serverconfig nằm root-only `/root/tv1-underlay-pki`, `/etc/openvpn`; không đưa vào Git.

Rollback encap đã thực hiện và kiểm tra1442 trở lại trước phiên OpenVPN. Khi cần về underlayAWS:
1. Dùng SSH dự phòng AWS tới đủ3máy.
2. Chạy đúng `/root/tv1-sg-encap-20261106/rollback.sh` trên từng node, trả172.31.47.27/172.31.1.199/172.31.9.62. Script chỉ đổi encap.
3. Nếu dừng underlay lâu dài, bỏ đúng dropin `/etc/systemd/system/ovn-controller.service.d/tv1-underlay.conf` tạo trong phiên và daemon-reload.
4. Chỉ dừng/disable `openvpn-client@tv1` và `openvpn-server@tv1` sau khi OVN đã về mạngAWS, không dừng VPN khi encap còn10.253.239.x.
5. Flush PMTU cache Controller nếu cần, kiểm tra DF1442 tới10.76.0.157, TCP9443, LB/agents/hypervisors, giữ App B nguyên trạng.
Không restore toàn DB để rollback encap, không clean/unstack/stack.sh. Thu hồi account tải config sau khiTV3 nhận file và xác nhận không còn cần. Chưa diễn tập phục hồi toàn cụm/database.
