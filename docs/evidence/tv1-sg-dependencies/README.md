# Dependency/rootwrap thực tế Compute 3 — 06/11/2026

## Kết luận libvirt

TV3 phát hiện đúng: requirements HEAD `9edc04289eca1a4c18ae86e4430416d82a5b07fa` ghim libvirt-python===12.6.0. Worktree Compute 3 sửa cục bộ upper-constraints: về mặt nội dung **chỉ bỏ dòng libvirt-python**, các dòng khác giữ phiên bản (file còn bị sắp xếp lại). Không thể tái tạo venv bằng mỗi commitHEAD. Xem `compute3-constraints-semantic.json`; patchraw được lưu để đối chiếu lịch sử, không khuyến nghị áp dụng nguyênpatch làm chính sách cài mới.

Thực tế đang chạy:
- Python3.12.3, pip26.2.2, venv `/opt/stack/data/venv`, base `/usr`.
- Python binding trong venv: libvirt-python10.0.0; system python3-libvirt10.0.0-1build1 là gói khác, không chứng minh venv tự dùng binding hệ thống.
- libvirt0/libvirt-dev/libvirt-daemon-system/libvirt-clients10.0.0-2ubuntu8.19; virsh báo compiled/using/API libvirt10.0.0; QEMU8.2.2, package1:8.2.2+ds-0ubuntu1.18.
- OVS daemon3.3.9/OVN24.03.8; Python ovs3.7.1 là package riêng.

`compute3-pip-list-20261106.txt` là toàn bộ **211 distributions** lấy bằng pip list --format=freeze (không URL/credential). Đây là snapshot tên/phiên bản, không phải requirements hay lock đã kiểm chứng sạch; không pip install cả211gói lên Singapore. Các editable Nova/Neutron cần commit đã ghi ở tài liệu đầu vào.

**pip check hiện FAIL**: service-identity24.1.0 cần pyasn1-modules nhưng chưa cài. Không được báo baseline dependency sạch. Chưa sửa venvSydney trong bước đọc này.

## Quyết định cho Singapore

Giữ libvirt hệ thống Ubuntu10.0.x và dùng **binding venv libvirt-python10.0.0** làm ứng viên tương thích baseline, không nâng libvirt hệ thống chỉ để khớp binding12.6.0. Tạo constraints file local có ghi nhận ngoại lệ: lấy upper-constraints đúngHEAD, thay dòng libvirt-python===12.6.0 bằng libvirt-python===10.0.0; không vừa truyền constraint12.6 vừa truyền10.0. Không làm bẩn repo requirements để che ngoại lệ.

Cài dependency của đúng Nova/Neutron source với constraints đã sửa trong venv riêng của Singapore, để resolver cài cả các dependency còn thiếu như pyasn1-modules theo constraints. Đây là chỉ dẫn tái hiện ứng viên, chưa chứng minh full resolver/build/start trên Singapore. Trước đăng ký phải có:
1. pip check exit0, ghi full piplist/constraints hash/commit.
2. Import libvirt trong đúngvenv và in getVersion()/getLibVersion; kiểm tra compiled/systemABI, virsh version, /dev/kvm và quyền libvirt.
3. Kiểm tra rootwrap/privsep, cấu hình và quyền file rồi mới start theo phiên đã thống nhất.
4. Giữ Nova/OVN inactive nếu build, ABI hoặc quyền thất bại; không ép --no-deps hoặc sửa test để bỏ qua.

## Rootwrap/sudoers rút gọn

Compute3 thực tế có các rule dưới; đây là phạm vi helper, **chưa chứng minh tối thiểu cho mọi operation**:
```sudoers
stack ALL=(root) NOPASSWD: /opt/stack/data/venv/bin/nova-rootwrap /etc/nova/rootwrap.conf *
stack ALL=(root) NOPASSWD: /opt/stack/data/venv/bin/nova-rootwrap-daemon /etc/nova/rootwrap.conf
stack ALL=(root) NOPASSWD: /opt/stack/data/venv/bin/neutron-rootwrap /etc/neutron/rootwrap.conf *
stack ALL=(root) NOPASSWD: /opt/stack/data/venv/bin/neutron-rootwrap-daemon /etc/neutron/rootwrap.conf
```

Tạo bằng visudo -f file riêng và visudo -cf; sudoers root:root0440. Không cấp sudo ip/bash/python/ovs-vsctl tùy ý, không chép `/etc/sudoers.d/stack` chứa NOPASSWD:ALL từ DevStack. Rootwrap config root:root0644, filters_path chỉ `/etc/nova/rootwrap.d` hoặc `/etc/neutron/rootwrap.d` tương ứng, thư mục root:root0755 và filterroot:root0644. Không cho daemon đọc filter user có thể sửa.

Nova `compute.filters` của baseline cho context privsep os_brick.privileged.default và nova.privsep.sys_admin_pctxt. Neutron rootwrap.filters có context neutron.privileged.default, ip/netns/haproxy và nhiều helper agent khác. Lấy filter từ đúng source commit, không tự xóa theo phỏng đoán; thu hẹp sau khi audit operation cần thiết. Metadata agent config dùng root_helper và root_helper_daemon đúng đường dẫn trên; runtimeHAProxy/namespace cần rootprivileges phù hợp.

**Giới hạn an toàn baseline:** hiện helper executable và venv/source trên Compute3 do stack sở hữu. Cho user sudo rootwrap/privsep trong khi user sửa được helper hoặc module Python có thể tương đương quyềnroot; bốn rule không biến DevStack thành môi trường least-privilege cứng. Phải coi stack là tài khoản vận hành tin cậy, hoặc thiết kế helper/runtime/module path root-owned riêng rồi kiểm thử trước khi cho user không tin cậy dùng. Không chown hàng loạt venv/sourceSydney đang chạy trong bước này.

Khi đặt file Singapore, dùng install -o root -g root -m0644 cho rootwrap/filter, file config chứasecret0600 đọc được bởi userdịchvụ theo mô hình đã chọn. Tạo group/perms /dev/kvm/libvirt theo gói distro và xác nhận userdịchvụ thực, không chmod666 socket/device. Khóa file/module path trước khi đánh giá privilege boundary.

## Phạm vi nghiệm thu

Đã kiểm tra hệ thốngSydney đang chạy, virsh/libvirt và snapshotdependency. Chưa kiểm chứng buildlibvirt10.0.0 với constraints mới trênSingapore, chưa có pip check sạch, chưa nghiệmthu sudoers rútgọn độc lập với rule DevStackALL, chưa đăng ký node. Không có secret trong các artifact; credential dùnggói riêng đã bàn giao.
