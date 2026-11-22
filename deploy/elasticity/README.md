# Bộ chuẩn bị hạ tầng TV3

Luồng JSON gồm `kit.py`, các template JSON và `probe_http.py`. Hai file `octavia-pilot*.yaml` là bài thử riêng dùng pool hiện có và hai mạng của ứng dụng. Xem [hướng dẫn triển khai](../README.md) và [nghiệm thu 13/11](../../docs/evidence/autoscaling-acceptance-20261113.md) để biết điều kiện vận hành và kết quả đã xác minh.

**Bộ JSON đã kiểm thử offline.** Hai template YAML pilot đã qua xác thực Heat API. [Biên bản 13/11](../../docs/evidence/autoscaling-acceptance-20261113.md) ghi lại chu kỳ tự động 2 → 3 → 2 của pilot trên pool Octavia hiện có. Các lệnh `lint`, `plan`, `build` và unit test chạy được trên máy cá nhân với Python 3.12+.

Bộ YAML tại `templates/*.yaml` có topology, budget và tham số riêng. Xem [YAML_RUNBOOK.md](YAML_RUNBOOK.md) để tái lập bài thử đó với environment riêng.

| Tệp | Vai trò |
|---|---|
| `baseline-lb.json` | Tạo LB private, listener HTTP:80 giới hạn CIDR, pool round-robin, monitor `/health/ready`, hai member App:8000 đã tồn tại |
| `app-member.json` | VM ở một AZ + khởi động container + đăng ký member; nested stack quản lý vòng đời cả hai |
| `autoscale.json` | Một LB **riêng**, hai nhóm gắn hai AZ, mỗi nhóm tối thiểu 1 VM, tối đa 2; policy tăng/giảm 1 VM và 4 alarm tùy chọn |
| `kit.py` | Kiểm tra offline, tính ngưỡng/budget, tạo environment; khám phá/thu snapshot cloud chỉ đọc |

## Tự làm ngay

Từ thư mục gốc repo:

```powershell
python -m unittest discover -s tests/elasticity -v
python deploy/elasticity/kit.py lint
New-Item -ItemType Directory -Force deploy/elasticity/local
Copy-Item deploy/elasticity/config.example.json deploy/elasticity/local/config.json
Copy-Item deploy/elasticity/app.env.example deploy/elasticity/local/app.env
```

Linux dùng `mkdir -p`, `cp` tương ứng. File mẫu cố ý chứa `CHANGE_ME`: lệnh `plan/build` phải từ chối khi chưa điền thông tin. Không thay placeholder bằng UUID ngẫu nhiên rồi coi là đã sẵn sàng triển khai.

Sau khi có thông tin thật, điền `local/config.json`: UUID subnet/network/image/SG, flavor, keypair, hai AZ khác nhau, hai IP App hiện tại, CIDR của máy demo/VPN đã có route tới VIP. Bộ này dùng IPv4. `vcpus`, `ram_mb` phải khớp flavor. `budget_app_vms` chỉ giới hạn **VM mới của stack autoscale**, chưa gồm App VM cũ, PostgreSQL, amphora Octavia và dịch vụ OpenStack. Mặc định tính 4 VM App mới, không khẳng định các laptop đủ RAM. Có thể đặt `max_per_zone=1` và budget=2 để thử boot/LB trước; khi đó chưa có dư địa scale-out.

```powershell
python deploy/elasticity/kit.py plan --config deploy/elasticity/local/config.json --out deploy/elasticity/local/plan.json
python deploy/elasticity/kit.py build --config deploy/elasticity/local/config.json --app-env deploy/elasticity/local/app.env --out deploy/elasticity/local/run-01
```

`build` tạo hai Heat environment và bản tính dung lượng. Output phải mới để tránh ghi đè nhầm. Công cụ luôn đặt `enable_alarms=false`. Mọi file trong `local/`, `app.env`, `*.env.json` đều bị Git bỏ qua; thư mục bí mật cũng bị loại khỏi Docker build context. Trên Linux, file environment bí mật được tạo mode `0600`; Windows cần giới hạn ACL của thư mục, không để ở thư mục chia sẻ. Base64 và Heat `hidden` **không mã hóa bí mật**: người có quyền đọc Heat state, Nova user-data hoặc VM vẫn có thể đọc. Dùng credential riêng phạm vi project lab; không chụp/publish environment, user-data hoặc action URL. Khi cập nhật credential/image, chuẩn bị thay VM có kiểm soát; cloud-init không tự chạy lại trên VM cũ.

## Điều kiện image trước khi tạo VM

TV3 có thể tự build container và chuẩn bị quy trình image; bản Glance và mạng thật cần dữ liệu TV1/TV2 sau này:

1. Image Ubuntu có cloud-init và Docker engine hoạt động. Build app từ **commit cụ thể**, ghi SHA vào minh chứng, đặt tag `file-integrity:<commit>`. Export bằng `docker save`, import bằng `docker load` trên VM dùng tạo image. Repo hiện không publish registry.
2. Image phải chứa đúng tag này. Boot script dùng `--pull never`, không chạy `apt`, `git clone` hay build qua Internet lúc scale. Docker daemon phải hỗ trợ tùy chọn này. Kiểm tra `docker image inspect <tag>` trên VM chuẩn bị.
3. Trước khi tạo image, không để container cũ tự khởi động, không lưu `app.env`/credential hoặc dữ liệu người dùng trong image. Làm sạch cloud-init theo hướng dẫn Ubuntu/image của nhóm để clone nhận user-data mới; kiểm tra metadata/config-drive hoạt động. Đặt Glance image private.
4. Khi boot, cloud-init tạo `/etc/file-integrity/app.env` mode 0600, bật Docker, chạy container và publish 8000. Mọi App VM dùng cùng Swift/container và PostgreSQL; không mount volume local để giả shared storage. Cloud-init lỗi thì sửa image/env và thay VM; `CREATE_COMPLETE` của Heat không tự chứng minh ứng dụng sẵn sàng.
5. SG App phải cho Octavia đến 8000 và đường SSH quản trị cần thiết, có egress đến DB/Keystone/Swift/DNS; DB chỉ nhận kết nối được phép. Template dùng SG **đã có**, không sửa SG/network/controller và không tạo floating IP. HTTP chỉ dành cho lab private; môi trường ngoài lab cần TLS riêng.

## Khám phá và validate cloud — chỉ đọc

Chạy trên máy đã cài OpenStackClient cùng plugin Heat, Octavia, Gnocchi, Aodh tương thích bản cloud; nạp credential riêng bằng cơ chế của nhóm. Không đưa token/clouds.yaml/openrc vào repo. Trên Windows hiện tại chưa có OpenStackClient; các bước này chưa được thực thi trên cloud.

```sh
python deploy/elasticity/kit.py probe --config deploy/elasticity/local/config.json --out deploy/elasticity/local/discovery.json
openstack orchestration template validate -t deploy/elasticity/baseline-lb.json -e deploy/elasticity/local/run-01/baseline.env.json
openstack orchestration template validate --show-nested -t deploy/elasticity/autoscale.json -e deploy/elasticity/local/run-01/autoscale.env.json
```

`probe` chỉ tìm service, AZ, image/flavor/network/SG/keypair và loại resource. Nó không kiểm tra route, quota, đủ RAM, boot thành công, metric hay webhook. `FOUND` không đồng nghĩa sẵn sàng triển khai. Các lỗi CLI/credential/plugin được ghi `NOT AVAILABLE`; không in stdout/stderr cloud nguyên bản vì có thể chứa bí mật. Muốn chẩn đoán sâu, người vận hành xem riêng trên máy có quyền.

Lệnh validate hỏi Heat API thật, khác với `lint` offline. Có thể chưa kiểm tra đủ nested property/custom constraint; vẫn cần boot thử. Kiểm tra schema của bản cloud bằng `openstack orchestration resource type show <TYPE>`. Listener cần hỗ trợ `allowed_cidrs`; nếu cloud cũ thiếu, bổ sung kiểm soát mạng tương đương đã thống nhất trước khi sửa template.

## Chạy từng giai đoạn khi hạ tầng đã sẵn sàng

Các lệnh dưới đây **tạo/thay đổi tài nguyên**, chỉ là hướng dẫn để người vận hành chạy sau khi chốt budget và cửa sổ thử nghiệm; lần chuẩn bị này không thực thi chúng.

```sh
# Bước 1 tùy chọn: LB trước hai App VM có sẵn. Không tạo VM mới.
openstack stack create tv3-baseline -t deploy/elasticity/baseline-lb.json -e deploy/elasticity/local/run-01/baseline.env.json --wait
# Bước 2: stack autoscale với LB riêng, alarm vẫn tắt.
openstack stack create tv3-elastic -t deploy/elasticity/autoscale.json -e deploy/elasticity/local/run-01/autoscale.env.json --wait
openstack stack output list tv3-elastic
```

Không thêm hai App cũ vào pool autoscale: group phải tự quản lý member mới. Hai stack chạy đồng thời sẽ cộng thêm tài nguyên LB/amphora và vẫn giữ App cũ; tính cả phần đó trong dung lượng tổng. Không tự xóa tài nguyên của TV1/TV2. VIP private cần route/VPN đã kiểm tra; template không cấu hình Tailscale, NAT hay public ingress.

Sau khi tạo: xác nhận VM ở đúng AZ, không có floating IP, cloud-init hoàn tất, hai member `ONLINE`, upload/verify/download qua VIP và kiểm tra dữ liệu dùng chung. Xem `cloud-init status --long`, `docker ps`, log container trên App VM trong phiên riêng; không đưa user-data/env vào ảnh minh chứng. Chỉ sang alarm khi các bước này đạt.

## CPU và alarm

Mẫu dùng metric `cpu` tích lũy nanosecond với `rate:mean`. Trên staging ngày 11/11/2026, giá trị đo là chênh lệch CPU nanosecond trong một khoảng granularity. Ngưỡng theo tỷ lệ tổng CPU của flavor:

`threshold = percent / 100 × số vCPU mỗi VM × granularity tính bằng giây × 1.000.000.000`.

Với 1 vCPU và granularity 300 giây, ngưỡng 70% là 210.000.000.000 ns và ngưỡng 20% là 60.000.000.000 ns. `kit.py` tính hai ngưỡng từ config. Đối chiếu đơn vị với mẫu Gnocchi thực tế trước khi bật alarm. Mỗi AZ có dimension riêng `metering.server_group=<stack-id>-az1/az2`; query loại resource đã kết thúc để tránh VM bị xóa làm lệch mẫu. Phải xác minh Ceilometer thực sự xuất `user_metadata.server_group` thành thuộc tính Gnocchi `server_group`.

Kiểm tra thực tế trước: `openstack metric resource show --type instance <VM_UUID>`, `openstack metric show --resource-id <VM_UUID> cpu`, rồi `openstack metric measures show --aggregation rate:mean --granularity 300 --resource-id <VM_UUID> cpu`. Xem archive policy của metric, có `rate:mean` và đúng granularity; collection pipeline có dữ liệu mới cho **cả hai VM**. Các plugin khác phiên bản có thể cần cú pháp khác, xem `--help`. Không tự hạ granularity trong template khi archive policy chưa hỗ trợ.

Mặc định 300 giây × 2 periods, cooldown 600 giây: cần chờ metric và thời gian boot; chạy Locust 20 giây không đủ chứng minh scale. `insufficient data` là thiếu mẫu, không được coi là CPU thấp. Alarm không có action cho trạng thái này. CPU ứng dụng nhẹ hoặc nghẽn DB có thể không đạt 70% dù tăng người dùng; không sửa kết quả để tuyên bố đã scale.

Aodh có thể nhận giá trị `rate:mean` âm khi số VM trong nhóm thay đổi hoặc bộ đếm CPU bị đặt lại. Bản vá [aodh-negative-cpu.patch](aodh-negative-cpu.patch) loại giá trị âm khỏi cửa sổ CPU sau khi đã chọn số mẫu theo cấu hình. Nếu cửa sổ còn thiếu mẫu, alarm chuyển sang `insufficient data`. Aodh giữ nguyên cách xử lý các metric khác. Bản vá đã áp dụng trên staging với Aodh commit `946daa60`.

Trước khi bật alarm cho cụm ứng dụng, đối chiếu phiên bản Aodh và kiểm tra khả năng áp dụng bằng `git apply --check` trong checkout Aodh. Sau khi áp dụng, khởi động lại bộ đánh giá Aodh và kiểm thử mẫu âm, cửa sổ trộn mẫu, thiếu metric và CPU thấp hợp lệ. Với DevStack, bộ đánh giá là `devstack@aodh-evaluator`. Hoàn nguyên bằng `git apply -R` với cùng file bản vá rồi khởi động lại bộ đánh giá. Giữ `repeat_actions` cho scale-in để Aodh thử lại khi Heat hết cooldown.

Khi metric, capacity và Heat signal đã xác minh: sao chép `autoscale.env.json` thành một file local mới, chỉ đổi `enable_alarms` thành `true`, validate lại, rồi người vận hành dùng `openstack stack update tv3-elastic -t ... -e <file mới> --wait`. Dùng đủ environment và giữ nguyên image/env/AZ; review thay đổi trước khi update. Kiểm tra cả đường tăng và giảm, không xuống dưới 1 VM mỗi AZ. Không gọi signal thủ công rồi ghi thành Aodh tự kích hoạt. Khi cần ngừng thử, tắt alarm bằng environment mới trước; giữ chứng cứ trước khi xóa stack do mình tạo.

## Thu minh chứng

### Pilot trên pool hiện có

Chuẩn bị file environment trong `deploy/elasticity/local/` với `parameters` theo `octavia-pilot.yaml`. Lấy `pool_id`, `member_network_id`, `member_subnet_id`, `data_network_id`, `data_subnet_id`, `data_cidr`, `data_gateway`, `db_ip`, `swift_ip` và `security_group_id` từ cụm và bản vận hành riêng. Điền `image_id`, `flavor_id`, `availability_zone`, `container_image` từ image đã kiểm tra. `app_env_b64` là nội dung dotenv của pilot mã hóa base64, gồm thông tin truy cập DB và Swift. Chuẩn bị file này trên máy quản trị, với quyền đọc hạn chế.

Từ `deploy/elasticity/`, dùng Heat để validate và tạo pilot với số VM ban đầu bằng 0:

```bash
openstack orchestration template validate --show-nested -t octavia-pilot.yaml -e local/pilot.env.json
openstack stack create --wait -t octavia-pilot.yaml -e local/pilot.env.json octavia-pilot
openstack stack resource signal octavia-pilot scale_out
```

Chờ backend mới `ONLINE`, xác minh readiness và SHA-256 từ client private. Sau cooldown, gửi `openstack stack resource signal octavia-pilot scale_in`, kiểm tra số member trở về ban đầu và VIP vẫn sẵn sàng. Xóa stack pilot và thu hồi credential thử sau khi lưu kết quả. Hai tín hiệu này kiểm tra vòng đời tài nguyên Heat và Octavia. Nghiệm thu tự động cần thêm metric thật và lịch sử Aodh.

### Thu trạng thái qua CLI

Lấy UUID stack/LB/pool từ cloud; dùng ID thật để tránh nhầm tên. Chạy mỗi lần với output mới:

```sh
python deploy/elasticity/kit.py collect --stack STACK_UUID --lb LB_UUID --pool POOL_UUID --out test-results/elasticity/before.json
# Sau scale-out, sau scale-in: gọi lại với after-out.json, after-in.json.
```

Snapshot chỉ giữ các cột trạng thái/ID/địa chỉ và timestamp UTC. Bổ sung metric, lịch sử Aodh, mapping VM→AZ, log tải và HTTP health theo cùng mốc thời gian. Đối chiếu [biên bản nghiệm thu](../../docs/evidence/autoscaling-acceptance-20261113.md).

## Tài liệu nguồn

Đối chiếu ngày 28/10/2026; `latest` không thay thế việc xác minh bản cloud của nhóm:

- [Heat resource schemas](https://docs.openstack.org/heat/latest/template_guide/openstack.html) và [nested template composition](https://docs.openstack.org/heat/latest/template_guide/composition.html).
- [Ceilometer measurements và metering metadata](https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html), [Gnocchi mapping/archive policy trong mã Ceilometer](https://github.com/openstack/ceilometer/blob/master/ceilometer/publisher/data/gnocchi_resources.yaml).
- [Aodh alarm states/evaluation](https://docs.openstack.org/aodh/latest/admin/telemetry-alarms.html).
- [Red Hat CPU rate autoscaling example](https://docs.redhat.com/en/documentation/red_hat_openstack_platform/16.0/pdf/auto_scaling_for_instances/Red_Hat_OpenStack_Platform-16.0-Auto_Scaling_for_Instances-en-US.pdf).
