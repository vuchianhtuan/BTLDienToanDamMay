# Triển khai File Integrity System trên OpenStack

Ứng dụng đã được kiểm chứng với Swift, PostgreSQL trên Cinder, hai backend ở hai AZ và Octavia. Phiên 13/11/2026 nghiệm thu chu kỳ tự động **2 → 3 → 2** bằng Heat pilot, Gnocchi/Aodh trên staging và relay tạm. [Kết quả và giới hạn phép thử](../docs/evidence/autoscaling-acceptance-20261113.md)

Cấu hình trong repository gồm mẫu chạy ứng dụng, template hạ tầng và script dành cho lab đã có. Đây chưa phải bộ cài tự động toàn bộ OpenStack/DevStack.

## Điều kiện triển khai

1. Hai compute/AZ tạo được VM; Neutron và mạng liên node đã được kiểm tra.
2. PostgreSQL 16 chạy trên VM dữ liệu; Cinder volume được mount bền vững và data directory đặt trên volume. Tạo database/user riêng cho ứng dụng; cổng 5432 chỉ cho phép nguồn App cần thiết.
3. Swift có container `file-integrity`; Keystone application credential đúng project/role và đọc/ghi được object.
4. App VM có Docker + Compose, kết nối được PostgreSQL, Keystone và Swift. Image phải có sẵn hoặc VM có egress để build.
5. Octavia tới được cổng 8000 của App VM; security group giới hạn nguồn phù hợp. Mô hình truy cập phục vụ ứng dụng đi qua VIP; kiểm tra và ghi riêng mọi floating IP quản trị còn gắn.
6. Client demo có route tới VIP private hoặc tunnel/VPN đã kiểm chứng.

Các App VM phải dùng **cùng database và container Swift**. Storage local riêng trên từng App VM không đáp ứng mô hình dữ liệu chung.

## Cấu hình ứng dụng trên mỗi App VM

Chuyển mã nguồn sang VM. Trong thư mục `deploy/`, tạo file cấu hình nếu chưa tồn tại:

```sh
test -f app.env || cp app.env.example app.env
chmod 600 app.env
```

Điền các giá trị riêng trong `app.env`:

| Biến | Nội dung |
|---|---|
| `DATABASE_URL` | URL PostgreSQL private; URL-encode ký tự đặc biệt trong user/password |
| `APP_API_KEY` | Khóa chung cho API tệp |
| `OS_AUTH_URL` | Keystone v3 endpoint |
| `OS_APPLICATION_CREDENTIAL_ID`, `OS_APPLICATION_CREDENTIAL_SECRET` | Credential dành cho backend |
| `OS_REGION_NAME`, `OS_INTERFACE` | Region và interface của catalog có thể truy cập |
| `SWIFT_CONTAINER` | Container Swift dùng chung |
| `MAX_FILE_BYTES` | Giới hạn upload, mặc định 26214400 byte |

Compose đặt `STORAGE_BACKEND=swift` và publish cổng 8000 trên VM:

```sh
docker compose --env-file app.env -f compose.openstack.yaml up -d --build --wait
docker compose --env-file app.env -f compose.openstack.yaml ps
docker compose --env-file app.env -f compose.openstack.yaml logs --tail 100 app
```

Mật khẩu, private key, token và `app.env` thật nằm ngoài Git. Không sao chép volume local sang từng App VM để thay cho Swift. Tệp đã upload ở local không tự xuất hiện trên cloud.

## Cân bằng tải và autoscaling

Đọc [runbook elasticity](elasticity/README.md) trước khi chọn phương án:

- `baseline-lb.json`: LB cho hai App đã có.
- `autoscale.json` cùng `app-member.json`: LB riêng và hai nhóm App theo AZ; cấu hình mẫu, kiểm chứng offline.
- `templates/*.yaml`: phương án YAML riêng, dùng environment trong [YAML_RUNBOOK.md](elasticity/YAML_RUNBOOK.md).
- `octavia-pilot.yaml` cùng `octavia-pilot-member.yaml`: thêm tối đa một backend vào pool hiện có; đã được dùng cho nghiệm thu 13/11.

Không trộn tham số, environment hoặc quyền quản lý tài nguyên giữa các phương án. Tính cả VM đang có, PostgreSQL, amphora và dịch vụ OpenStack khi kiểm tra quota/RAM.

Pilot nghiệm thu đã được dọn. Muốn chạy lại tự động cần image app đã kiểm tra boot, credential DB/Swift riêng có thời hạn, hai mạng member/data, telemetry có metric CPU thật và đường callback Aodh → Heat. Mẫu không tự dựng lại staging hoặc relay. Tham số của phiên 13/11 được ghi trong biên bản; không suy ra từ các giá trị mặc định của bộ JSON.

## Kiểm tra sau triển khai

1. Kiểm tra `/health/ready` báo `ready` và storage `swift`; member Octavia `ONLINE`.
2. Upload một tệp giả qua VIP; ghi UUID, dung lượng và SHA-256; list/download/verify đúng cùng tệp.
3. Đối chiếu Swift object và row PostgreSQL. Kiểm tra `findmnt /srv/postgresql`, `SHOW data_directory;` và Cinder attachment.
4. Đọc/verify tệp qua các backend khác nhau; rút lần lượt một backend, khôi phục rồi kiểm tra pool.
5. Khi thử autoscaling, lưu metric, Aodh history, Heat event, mapping VM → AZ và member trước/sau. Tín hiệu Heat thủ công chỉ kiểm tra vòng đời tài nguyên.
6. Lưu toàn bộ lỗi/timeout và điều kiện đo. Kiểm tra lại tệp qua VIP sau scale-in.

[Lệnh vận hành và kiểm thử dữ liệu TV2](tv2/README.md); [bộ minh chứng dữ liệu 19/11](../docs/TV2_FINAL_EVIDENCE.md).

## Cập nhật và khôi phục phiên bản

Giữ bản mã/image đang chạy cùng cấu hình riêng trước khi cập nhật. Kiểm thử bản mới trước, cập nhật lần lượt App VM và theo dõi readiness/member. Nếu thất bại, khôi phục mã/image trước đó rồi tạo lại container với cùng `app.env`; kiểm tra download/verify qua VIP.

Không xóa volume hoặc thay schema để xử lý lỗi triển khai. Repository chưa có framework migration; thay đổi schema cần quy trình riêng. Backup metadata PostgreSQL và nội dung Swift phải được đối chiếu theo cùng UUID. Lab TV2 có lệnh backup/restore kiểm thử trong runbook; cần bản sao ngoài EC2 để bảo vệ trước sự cố mất host/EBS.

## Tài liệu hạ tầng

`infrastructure/` chứa script và systemd unit theo địa chỉ/topology của từng lab. Tài liệu có ngày trong `docs/` và `infrastructure/STATUS.md` là các mốc lịch sử. Kiểm tra interface, subnet, MTU, route, host/AZ và dependency trước khi áp dụng cho môi trường khác.
