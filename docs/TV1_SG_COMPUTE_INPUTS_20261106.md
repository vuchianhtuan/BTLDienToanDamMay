# Đầu vào Compute Singapore — 06/11/2026

Đã kiểm tra trực tiếp trên Controller và Compute 3 đang chạy. Đây là đầu vào chuẩn bị, không phải bộ cài đã nghiệm thu. Singapore chưa có nova-compute/OVN hoạt động trong cụm. Không chạy stack/unstack/clean.sh trên Controller.

## Endpoint/catalog và cell

Catalog hiện chỉ có interface public, host `http://172.31.47.27`; dùng route /32 OpenVPN đã kiểm tra, không mặc định đổi toàn bộ catalog sang Tailscale hoặc OpenVPN IP.

| Service | Path trên host catalog |
|---|---|
| Keystone | /identity (auth nên dùng /identity/v3) |
| Nova | /compute/v2.1 |
| Placement | /placement |
| Neutron | /networking |
| Glance | /image |
| Cinder | /volume/v3 |
| Heat | /heat-api/v1/$(project_id)s |
| Octavia | /load-balancer |

RabbitMQ controller TCP5672; **compute dùng vhost `nova_cell1`**, không dùng `/`. Cell đang dùng: name `cell1`, UUID `d75f3d0d-6a70-48a1-b94a-6c09e19b491e`, disabled=0. Cell0 UUID toàn0, không map Compute vào đó. `/etc/nova/nova.conf` Controller dùng transport vhost `/` và database cell0; `/etc/nova/nova_cell1.conf` có cell1. Compute 3 thực tế dùng `/etc/nova/nova-cpu.conf` với transport cell1. Không cấp database root URL cho Compute; compute RPC tới conductor.

OVN SB đề xuất `tcp:10.253.239.1:6642`; metadata agent → `172.31.47.27:8775`; OVSDB local `tcp:127.0.0.1:6640`. Không public6640. Nova console hiện `http://172.31.47.27:6080/vnc_lite.html`; đây là đường tùy chọn chưa khảo sát console Singapore, chưa mở hàng loạt5900–5999/live migration.

## Pin mã và dependency

DevStack `9b0a00865c2537338f72ed5b9b44a0d6bff16eb4`; Nova `94de0576ca02e0668233bedfbe7e18b87316c708`; Neutron `0d3e8e65b0c5171c654dcf2fca78bdd1b09b6107`; Placement `8e91e4d7aad1c6a642f80ec6387ce08d86f7c26d`; requirements `9edc04289eca1a4c18ae86e4430416d82a5b07fa`.

Trên venv Compute3: nova34.1.0.dev1, neutron29.1.0.dev16, oslo.messaging18.3.0, oslo.config10.7.0, oslo.db18.1.1, SQLAlchemy2.0.52, os-vif5.2.1, libvirt-python10.0.0, ovsdbapp2.19.0, keystoneauth1 5.17.0, openstacksdk4.20.0, eventlet0.41.2. Python package **ovs3.7.1** khác phiên bản daemon **OVS3.3.9**; OVN24.03.8. Dùng Python3.12/Ubuntu24.04 như cụm. Danh sách này chưa là lock toàn bộ dependency: đối chiếu requirements constraints, pip check, package Ubuntu và binary/libvirtABI trước start; không pin ovs Python bằng phiên bản daemon.

## Compute-only: giá trị cần dùng

- Hostname riêng ổn định, đề xuất AZ `sg-test`; chưa tạo aggregate/map host trước khi node xác thực. Không tái sử dụng compute_id của Sydney.
- `my_ip=10.253.239.4`, libvirt.LibvirtDriver, `virt_type=kvm`; CPU mode chọn theo kiểm tra KVM thực tế, không sao chép CPU model custom của Sydney. Chưa làm live migration.
- `state_path=/opt/stack/data/nova`, `instances_path=/opt/stack/data/nova/instances` nếu giữ layout hiện tại. Tạo owner/quyền rootwrap/libvirt đúng; metadata state riêng `/opt/stack/data/neutron`.
- Keystone auth v3; region RegionOne; public interface; project service/Default. User riêng Singapore (chưa tạo), không dùng admin openrc làm credential Compute.
- Các section cần inject riêng: placement, neutron, service_user (`send_service_user_token=True`) và transport cell1. Không có password trong tài liệu.
- OVN geneve encap `10.253.239.4`, `ovn-remote=tcp:10.253.239.1:6642`; system-id riêng; không `enable-chassis-as-gw`, không bridge mappings/public provider nếu không được giao gateway.
- Metadata agent dùng SB trên, `nova_metadata_host=172.31.47.27`, root_helper/root_helper_daemon trỏ đúng venv Neutron/rootwrap. Cần HMAC shared secret khớp controller; đây là bí mật dùng chung, không thể giả vờ là credential riêng từng node. Không chia sẻ toàn bộ local.conf.
- Chỉ cài/enable dịch vụ compute cần thiết: Nova compute, libvirt, OVS, ovn-controller, OVN metadata; không Keystone/DB/Rabbit/API/scheduler. Đặt thứ tự start sau VPN và OpenVPN phải sẵn sàng, không chỉ active tiến trình. Mask/không start nova-compute/ovn-controller trước phiên.

## Quyền và cách cấp riêng

Đã đọc policy source: Placement có service_api role:service/admin_or_service; Neutron có service_api. User nova/placement hiện có cả admin và service trong project service; không coi đó là quyền tối thiểu bắt buộc cho node mới.

Đề xuất tài khoản Keystone `nova-sg` project service chỉ role service ban đầu; xác thực/token và kiểm tra API cụ thể trên policy đang chạy trước đăng ký. Nếu403, xác định đúng rule/operation; không tự thêm admin cho hết lỗi. Nếu policy cần quyền rộng hơn phải nêu phạm vi và thử có kiểm soát. Role service cũng là quyền nhạy cảm ở cấp dịch vụ, không giới hạn được mọi thao tác theo một hypervisor bằng cách đặt tên user.

RabbitMQ user riêng `nova-sg` chỉ được phép vhost nova_cell1; chưa có regex queue/exchange tối thiểu đã kiểm chứng, vì RPC dynamic cần publish/reply/conductor. Không cấp quyền vhost `/`, không dùng shared stackrabbit trên node mới. Chỉ cấp sau khi chốt quyền và kênh nhận. Không cần SQL credential trên Singapore.

Hiện **chưa tạo/cấp Keystone/Rabbit credential hay metadata HMAC cho TV3**. Quyền chia sẻ VPN trước đó không tự bao gồm secret dịch vụ OpenStack. Gói cấp riêng sau khi được cho phép: file0600 cấu hình Nova/metadata theo node, manifest hash, hướng dẫn inject; gửi qua SSH forced-command chỉ đọc đúng gói, keyTV3 và IPgiới hạn, rồi thu hồi sau nhận như lần VPN. Không Git/chat/log. Root/helper quyền trên Singapore do TV3 quản lý. Tài khoản tv3-audit không có shell/sudo; tv3-underlay đã thu hồi và không tái sử dụng ngầm.

## Quota/capacity và nghiệm thu

Project admin ID `ac47966097d240f9b3814ea839b00be6`: quota usage thực tế cores20/inuse3/reserved0, instances10/inuse3/reserved0, RAM51200MiB/inuse2304/reserved0. Đây gồm cả các guest SHUTOFF, không phải RAM available. Các cột networking=0 trong `quota show --compute` không phải quota Neutron; phải query riêng nếu tạo network.

Controller hiện khoảng867MiB RAM available và swap55MiB/2GiB; không cài thêm control service trên Controller. Resource Singapore theoTV3 ~3.2GiB available/26GiB trống là số đo trước, phải đo lại khi package/daemons lên. Hai hypervisorSydney up; AppB/CirrOS SHUTOFF, amphoraACTIVE. Đo riêng Singapore và Placement/quota ngay trước boot.

VM thử đề xuất CirrOS image active `67ee0ba4-6d26-4d28-992b-f0932b8fa202`, flavor cirros256 (1vCPU/256MiB/1GiB). Network IPv4-only riêng, CIDRứng viên10.250.17.0/24 kiểm tra lại trùng, MTU1442 trên underlay1500 đã đạt ởSydney; không dùng network/imageAppB hay thayMTU cũ. Tạo một VM mỗi hostSingapore/Sydney, SGgiới hạn đúngnguồn, config/userdata giả. Xác nhận DHCP IP/MTU/route, UUID metadata đúng, public key/userdata, pingDF/TCP/SHA256 VM-to-VM; chưa thêm DB/Swift/LB/autoscale trong nghiệm thu hạ tầng.

Đăng ký theo giai đoạn: cấp/xác thực credential → OVNagent/metadata → nova-compute với hostmới → TV1 discover_hosts đúngcell1 → xác nhận hypervisor/Placement → aggregate/AZ → VM test. Dừng nếu host trùng, cell sai, API403, endpoint route sai, MTUfail, agent/workloadcũ suy giảm, thiếuRAM/disk/quota.

Rollback nodeSingapore: dừng nova-compute/metadata/ovn-controller mới, giữdisk/log, thu hồi credential node; chỉ gỡ service/chassis/Placement đúngID sau khi không còn instance/allocations. Không xóa theo hostname, không đụng Compute2/AppB, không restore DB cho một lỗi đăng ký. Rollback underlay theo TV1_UNDERLAY_OPENVPN_20261106.md; database dump đã tạo nhưng chưa restore drill toàncụm. Mọi node mới phải giữ SSH dự phòng AWS.

Lệnh đã dùng: endpoint list; role assignment list (khôngtoken); mysql SELECT uuid,name,disabled FROM nova_api.cell_mappings qua filedefaultsprivate; rabbitmqctl list_vhosts/list_permissions; configparser chỉ chọn trường antoàn, transportURL được tách bỏpassword; importlib.metadata.version từ venvCompute3; quota show --compute --usage admin; hypervisor/server/networkagent list.

## Chuẩn bị credential riêng (06/11, chưa bàn giao)
Đã tạo Keystone user nova-sg ID8fb98900d77b44c4addf459fcc13fc6f trong project service, chỉ role service. Xác thực Keystone đạt, GET Placement/resource_providers và Neutron/v2.0/ports đều HTTP200 tạiController; chưa test mutation/compute workflow. Rabbit usernova-sg chỉ vhostnova_cell1 (configure/write/read .* trong vhost), AMQP authđạt; không có quyềnvhost/. Chưa thêmadmin.

Gói root-only /root/tv1-sg-service/singapore-compute-private.tar.gz đã đối chiếu byte archive, chứa nova-cpu.conf, metadata agentini và README-PRIVATE. Không có SQL/admin password. SHA2563c6ff4f8f1f59371b81a6a447f1b7ddd4de6804e05cbd73095e305a03a795030. Chưa chuyển gói choTV3, chưa mở lại tài khoản tải và chưa startSingapore.

Chưa tìm thấy metadata_proxy_shared_secret được đặt rõ trong fileNova/NeutronController; WSGImodule nova.wsgi.metadata:application. Gói không tự bịa hoặc đổi sharedsecret; cần đối chiếu effectiveWSGIconfig và metadataagent trước nghiệmthu. Đề xuất trước đó nói chuyển HMAC phù hợp chỉ áp dụng khi xác định rõ giá trị/cấu hình đang dùng. READMEgói ghiđiểm chặn này. Không coi gói là càiđặt productionhoànchỉnh.

Đã xin người dùng xác nhận riêng trước khi cấp credentialdịch vụ quaSSHkey/IPgiớihạn; xác nhận chia sẻ VPNtrước không tự mở phạmvi quyềnOpenStack.
