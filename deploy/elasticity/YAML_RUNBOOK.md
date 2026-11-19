# TV3 - Octavia, Heat, Aodh va minh chung

Phu trach: Dinh Kieu Cong Tuan (23020875). Day la bo cau hinh chuan bi de tich hop, **chua duoc deploy/xac minh tren cum OpenStack that**. Khong chay lai DevStack lab cu de bat dich vu khi chua thong nhat voi TV1. TV1 chu tri Controller/Compute/network; TV2 cung cap app image va Swift/PostgreSQL dung chung; TV3 so huu LB, elasticity va kiem thu.

## 1. Dau vao can nhan, khong can doi toan bo du an hoan tat

| Nguoi | Dau vao can chot |
|---|---|
| TV1 | Ban OpenStack/DevStack/plugin; scope project va CLI co quyen; 2 AZ khac nhau; image/flavor/keypair; private network/subnet; security group; quota cho toi da 3 App VM va Octavia provider. |
| TV1 | Octavia provider ho tro HTTP, ROUND_ROBIN va HTTP health monitor (mau dung amphora); Heat + Aodh + Gnocchi; Aodh trust notifier den Heat; Ceilometer tren cac compute. OVN networking khong dong nghia Octavia provider OVN ho tro cac tinh nang HTTP nay. |
| TV1 + TV3 | Cach may tao tai di toi private VIP, duong den backend, MTU; metric/aggregation/granularity, resource attribute server_group, chu ky lay mau; du RAM cho App VM va amphora. |
| TV2 | Hai App VM test hoac prebuilt app image; tat ca dung cung PostgreSQL + Swift; /health/ready tra 200; thong tin secret cap rieng. Khong dung storage local tren nhieu app. |

Chi mo cong 8000 cua App VM tu duong traffic/health monitor Octavia da xac minh. Khong mac dinh mo ca subnet hay Internet. App VM khong co floating IP. VIP private cung chua tu truy cap duoc qua Tailscale: TV1 phai cap routing/jump host phu hop. HTTP trong mau chi danh cho mang lab/VPN; public access can TLS rieng.

## 2. Kiem tra offline truoc (khong can OpenStack)

Tu thu muc goc repo, voi Python co dependencies ung dung:

```powershell
.\.venv\Scripts\python.exe -m pip install -r deploy/elasticity/requirements-check.txt
.\.venv\Scripts\python.exe deploy/elasticity/validate.py
.\.venv\Scripts\python.exe -m unittest discover -s deploy/elasticity/tests -v
```

Validator bat YAML trung key, tham chieu sai, nested interface sai va gia tri moi truong nguy hiem/de trong. Day KHONG phai Heat schema validation, khong xac nhan provider/metric/network/cloud-init that.

## 3. Kiem tra cum chi doc

Tren terminal co OpenStack CLI va cac plugin Heat/Octavia/Aodh/Gnocchi da duoc TV1 cai theo phien ban cum, nap openrc/clouds.yaml rieng cua nhom. Khong commit file nay.

Tu `deploy/elasticity`:

```bash
python3 cloud_check.py preflight --output evidence/preflight-01.json
openstack loadbalancer provider list
openstack availability zone list --compute
```

Tool chi goi lenh list/show, co timeout va bao INCOMPLETE neu lenh thieu/quyen thieu/dich vu loi. `compute service list` co the can admin; nho TV1 chay phan nay, khong cap admin chi de vuot preflight. QUERIES OK chi chung minh truy van duoc, can doc ket qua va xac nhan co 2 AZ va du tai nguyen. Preflight yeu cau ca Aodh, nen co the INCOMPLETE nhung van thu LB khi TV1 da kiem tra rieng Octavia/Heat hoat dong.

## 4. Giai doan 1: LB voi 2 App VM co san

1. TV2 chuan bi hai App VM co private IP KHAC NHAU tren cung subnet chi dinh; cung DB/Swift, khac AZ; kiem tra truc tiep tu duong mang Octavia. UI/verify/download phai hoat dong truoc khi them LB.
2. Tao `private/`, copy `lb.env.example.yaml` thanh `private/lb.env.yaml`, dien subnet UUID va 2 IP that. Thu muc `private/` va `evidence/` duoc Git bo qua. Tren Linux: `chmod 700 private` va `chmod 600 private/*` sau khi tao file.
3. Kiem tra va tao stack RIENG (lenh create co tao tai nguyen/tieu quota; chi chay trong phien tich hop da thong nhat):

```bash
python3 validate.py --kind lb --environment private/lb.env.yaml
openstack orchestration template validate -t templates/lb-existing.yaml -e private/lb.env.yaml
openstack stack create tv3-lb -t templates/lb-existing.yaml -e private/lb.env.yaml --wait
openstack stack output show tv3-lb loadbalancer_id -f value -c output_value
openstack stack output show tv3-lb pool_id -f value -c output_value
openstack stack output show tv3-lb vip_address -f value -c output_value
```

Ghi LB_ID, POOL_ID, VIP vao bien shell rieng. Doi provisioning ACTIVE va ca 2 member ONLINE. Neu member ERROR/OFFLINE, kiem tra app, security group, routing, port va provider; khong bo health monitor de che loi. HTTP monitor kiem tra `/health/ready`, co the lam ca 2 backend OFFLINE khi DB/Swift chung hong: day la dependency that.

4. Upload 1 fixture 1-10 MiB qua VIP, luu UUID, size va SHA-256 goc. Kiem tra download/verify qua VIP va tu tung backend trong mang private. Hai member ONLINE chua chung minh ca hai nhan request: doi chieu access log cua hai App VM khi goi qua VIP (connection moi); ung dung hien chua tra backend identity header.
5. Chay workload nho theo `../../loadtest/README.md`, va probe ben duoi. TV2 dung **container app cua mot backend** trong phien test da hen; khong dung database/Swift/Controller va khong xoa VM. Ghi thoi diem UTC dung/khoi phuc, member ONLINE -> OFFLINE -> ONLINE, log backend va ket qua probe. Doi health monitor hoi tu truoc khi danh gia. Request dang xu ly co the loi trong luc chuyen; giu nguyen CSV, bao cao so loi/thoi gian phuc hoi, khong sua du lieu de ghi zero downtime.

```bash
# APP_API_KEY cap qua moi truong rieng, khong dua key vao CLI/history.
python3 probe.py --host http://VIP --file-id FIXTURE_UUID --sha256 ORIGINAL_SHA256 --size ORIGINAL_BYTES --seconds 120 --output evidence/failover-01.csv
```

Probe chi goi readiness, verify va streamed download cua tep co san; khong upload, khong dung backend. `roundtrip_ms` la tong 3 thao tac, khong phai latency mot endpoint. Code 1 neu co bat ky loi nao; 0 neu moi lan deu dat. Probe khong chung minh can bang tai: phai ket hop log cua tung backend va Octavia status. Dung TCP/HTTP moi request trong Locust de tranh suy dien tu 1 ket noi giu lau.

6. Chup snapshot truoc/sau, bang ID THAT, file moi cho moi moc:

```bash
python3 cloud_check.py snapshot --stack tv3-lb --loadbalancer LB_ID --pool POOL_ID --output evidence/lb-before.json
python3 cloud_check.py snapshot --stack tv3-lb --loadbalancer LB_ID --pool POOL_ID --output evidence/lb-after.json
```

Khong commit evidence chua review: co IP/project/resource ID va co the co error cua dich vu. Tool khong dump token, user-data, signal URL hoac stack parameters.

## 5. Giai doan 2: Image/bootstrap + autoscaling

Tao stack `tv3-elastic` RIENG; khong update `tv3-lb` sang template autoscaling. Hai stack tao LB rieng, va stack autoscaling tao App VM moi, nen can du quota/RAM khi cung ton tai. Thong nhat viec don stack test truoc neu thieu tai nguyen.

### Hop dong app image voi TV2

- Image Ubuntu co cloud-init, Docker va Docker Compose; repo o `/opt/file-integrity`, dung commit da review, container image cua `deploy/compose.openstack.yaml` da build (`file-integrity-cloud-app-app` voi Compose mac dinh nay). Thu lenh `up --no-build` tren VM mau truoc khi chup image. Khong git clone/cai package/build container khi autoscale.
- Image KHONG chua `.env`, credential, DB/upload local, SSH private key hay cloud-init cache cua VM mau. TV2 chuan bi golden image va reset cloud-init/machine identity theo quy trinh image, khong dung image chua secret.
- Copy `bootstrap.example.yaml` thanh `private/bootstrap.yaml`, dien endpoint/credential rieng, cung Swift/DB/key tren moi App VM. Ma hoa URL database neu mat khau co ky tu dac biet. Khong dua secret vao command history, log/screenshots hoac Git.
- `hidden: true` chi an parameter trong output thong thuong, KHONG la secret vault: cloud-init/user-data/config-drive va admin Heat/Nova co the doc. Mau nay dung credential scope rieng cho lab. Neu nhom co secret manager, thay bootstrap bang lay secret luc boot.
- Thu boot mot App VM bang image/bootstrap nay va `cloud-init status --wait`; can log cloud-init hoan tat, container ready, Swift/DB dung chung that. `CREATE_COMPLETE` cua Heat KHONG doi app ready; member chi ONLINE khi health monitor dat.

### Chot metric truoc khi bat alarm

Mau su dung Gnocchi `instance`, filter `server_group` bang stack UUID, voi metadata `metering.server_group` tren TAT CA app VM. TV1 phai xac nhan Ceilometer/Gnocchi map metadata nay sang resource attribute; khong tu gia dinh co san.

```bash
openstack metric resource show --type instance APP_VM_UUID
openstack metric measures show CPU_METRIC_UUID --aggregation rate:mean --granularity 60
```

Kiem tra resource thuoc dung project/group va co nhieu sample moi lien tuc, archive policy co aggregation/granularity da chon. Neu khong co metric hoac stale: dung o day, khong ep alarm state de gia lap autoscaling.

Ceilometer `cpu` la cumulative **nanoseconds**, KHONG phai %. `rate:mean` la ns CPU/giay. Voi N vCPU cung flavor, moc P% la `(P/100) * N * 1e9`; so trong env mau chi minh hoa cho 1 vCPU. Khong mac dinh co `cpu_util`. Chon metric/workload theo do thuc, va ghi don vi vao bao cao. Workload verify/download co the bi gioi han DB/Swift/client, chua chac tang CPU App VM; khi do khong duoc tu ket luan autoscale hong hay tao alarm gia.

### Tao va bat autoscaling

Copy `autoscaling.env.example.yaml` thanh `private/autoscaling.env.yaml`, dien ID/AZ that, az_a KHAC az_b; thiet lap threshold_low < threshold_high, granularity co that va cooldown lon hon thoi gian boot + health convergence da do. Alarms mac dinh false. Bo chi tao toi da **3 app**: 1 baseline AZ-1 va 1-2 app trong ASG AZ-2. Scale-in chi giam AZ-2 ve 1, nen van co 2 AZ; day khong phai scale ca Compute host. LB amphora co quota/RAM rieng.

```bash
python3 validate.py --kind autoscaling --environment private/autoscaling.env.yaml --bootstrap private/bootstrap.yaml
openstack orchestration template validate -t templates/autoscaling.yaml -e private/autoscaling.env.yaml --parameter bootstrap_user_data=VALIDATION_ONLY
openstack stack create tv3-elastic -t templates/autoscaling.yaml -e private/autoscaling.env.yaml --parameter-file bootstrap_user_data=private/bootstrap.yaml --wait
```

`VALIDATION_ONLY` chi dung lenh validate, khong dung de create VM. Doi ca 2 backend ONLINE, kiem tra shared data, 2 AZ va metering group/sample moi. Chup snapshot baseline va lay output high_alarm_id/low_alarm_id. Sau khi nhom chot metric, bat alarm:

```bash
openstack stack update tv3-elastic --existing --parameter alarms_enabled=true --wait
```

Khong can xuat signal URL ra output; Aodh su dung `trust+` Heat signal URL trong template. TV1 phai cau hinh trusts/notifier/endpoint access theo phien ban cum. Neu cloud dung telemetry khac (Prometheus, khong Gnocchi), can doi alarm resource va query, khong chay nguyen mau nay.

## 6. Thu scale-out/scale-in va thu bang chung

1. Tao fixture qua VIP cua `tv3-elastic`; luu UUID/size/SHA-256. Chay probe va Locust tu may tao tai rieng, key qua environment; 5 users truoc, tang tung muc da hen voi nhom, theo doi CPU/RAM/network cua ca client va app.
2. Ghi UTC tai tang -> sample vuot nguong du evaluation periods -> Aodh ALARM -> Heat event tao app -> Nova ACTIVE -> cloud-init xong -> member ONLINE -> backend moi nhan request. Phai thay server ID moi va member moi, khong chi alarm doi state.
3. Lay history va snapshot co --high-alarm/--low-alarm, CSV/HTML Locust. So sanh truoc/tai dinh/sau; ghi p50/p95/p99, throughput, failures, fixture, commit, flavor/vCPU, aggregation/units/granularity, nguong va cooldown.
4. Giam/dung Locust. Doi sample thap du periods va cooldown, xac nhan AZ-2 ve 1 app/member, AZ-1 van con. Verify/download fixture cu qua VIP, chung minh data khong nam tren App VM bi xoa.
5. Snapshot can ID LB/pool cua stack MOI, khong dung lai stack LB phase 1:

```bash
python3 cloud_check.py snapshot --stack tv3-elastic --loadbalancer LB_ID --pool POOL_ID --high-alarm HIGH_ALARM_ID --low-alarm LOW_ALARM_ID --output evidence/scale-peak.json
```

Tool chi chup tai mot thoi diem, khong tu poll va khong tu tao load; lap lai voi ten file khac o tung moc. Khong ghi de bang chung.

## 7. Dung phien / xu ly loi

- Neu dang scale loi: dung Locust, tat ca hai alarm bang stack update --existing --parameter alarms_enabled=false; thu snapshot/error events, thong bao TV1. Khong thay metric/nguong ngam khi dang quay demo.
- Thu scale bang `openstack stack resource signal` chi la test plumbing co chu dich; neu dung, ghi ro manual signal, KHONG tinh la metric-driven scale. Khong co lenh signal tu dong trong bo nay.
- Khi can don tai nguyen, nhom kiem tra dung stack ID va thong nhat truoc khi chay `openstack stack delete --wait STACK_NAME`. Xoa stack autoscaling se XOA App VM/ports/members/LB thuoc stack, nhung khong xoa DB/Swift ngoai stack. Xoa stack LB phase 1 chi xoa LB/members do stack tao, khong xoa App VM co san. Khong xoa Controller, volume/database hay stack nguoi khac.
- Luu ban report da che secret theo `EVIDENCE.md`; khong tu dong upload evidence.

## Tai lieu chinh thuc dung de chuan bi

- [Heat resource schemas](https://docs.openstack.org/heat/latest/template_guide/openstack.html): Nova/Neutron, Octavia, ASG/ScalingPolicy, Aodh Gnocchi alarm. Can doi chieu lai ban dang cai.
- [Octavia cookbook](https://docs.openstack.org/octavia/latest/user/guides/basic-cookbook.html): HTTP pool/monitor va duong mang backend.
- [Ceilometer measurements](https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html): cpu cumulative ns va metadata metering.
- [Heat client stack commands](https://docs.openstack.org/python-heatclient/latest/cli/stack.html): parameter-file, create/update --existing.

## Trang thai kiem chung

Chi ghi ket qua that vao `docs/TV3_PROGRESS.md`. Offline tests khong chung minh Heat service chap nhan schema, plugin co san, app image boot duoc, hay scale that. Chua co endpoint/credential cum nhom trong repo; chua deploy tai nguyen cloud trong dot nay.
