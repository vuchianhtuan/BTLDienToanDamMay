# File Integrity System

Repository của nhóm: [BTLDienToanDamMay](https://github.com/vuchianhtuan/BTLDienToanDamMay). Thành viên mới bắt đầu từ [CONTRIBUTING.md](CONTRIBUTING.md), [API contract](docs/API_CONTRACT.md) và [kết quả kiểm chứng local](docs/VERIFICATION.md).

Ứng dụng bài tập lớn Điện toán đám mây: lưu tệp, tải xuống và kiểm tra SHA-256. Bản local chạy FastAPI + PostgreSQL thật + storage trên Docker volume. Adapter Swift dùng cùng API và được cấu hình riêng khi có OpenStack.

`requirements.txt` ghi các dependency trực tiếp; `requirements.lock.txt` ghi toàn bộ phiên bản đã chạy kiểm thử. Docker build dùng file lock để tránh tự thay dependency gián tiếp ở lần chạy sau.

## Chạy trên Windows

1. Mở Docker Desktop, chờ engine chạy.
2. Clone repo, mở PowerShell tại thư mục chứa `compose.yaml`.
3. Chạy:

```powershell
Copy-Item .env.example .env
docker compose up --build -d --wait --wait-timeout 180
```

Nếu `.env` đã có, giữ nguyên file đó. Hoặc dùng `./scripts/start.ps1` để tự tạo `.env` chỉ khi chưa tồn tại.

Mở http://localhost:8000 để dùng giao diện; http://localhost:8000/docs để xem API. Nếu cổng 8000 đang dùng, đặt `APP_PORT=8001` trong `.env`, chạy lại Compose và dùng cổng mới.

Upload một tệp rồi bấm Verify. Kết quả gồm SHA-256 gốc, SHA-256 tính lại từ nội dung và dung lượng. File rỗng cũng hợp lệ. Mặc định tối đa 25 MiB/tệp. Tên trùng không ghi đè tệp cũ.

## Kiểm thử và vận hành

```powershell
docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
docker compose exec -T app python tests/smoke_live.py
docker compose ps
docker compose logs --tail 100 app
docker compose stop
docker compose up -d --wait
```

`scripts/test.ps1` chạy cả hai bộ kiểm tra; `scripts/stop.ps1` dừng dịch vụ. Smoke test tạo một tệp có tiền tố `smoke-` và giữ lại để xem qua UI. Unit test dùng SQLite và thư mục tạm riêng; smoke test dùng API đang chạy và PostgreSQL của Compose.

Compose tạo hai named volume: `postgres-data` lưu metadata và `file-data` lưu nội dung. Dừng hoặc tạo lại container không xóa các volume. Không dùng `docker compose down -v` nếu cần giữ dữ liệu. Chưa có API xóa tệp trong phạm vi MVP.

## API

| Phương thức | Đường dẫn | Ý nghĩa |
|---|---|---|
| GET | `/health/live` | Tiến trình API phản hồi |
| GET | `/health/ready` | Kiểm tra database và storage |
| POST | `/api/files?filename=example.txt` | Body là byte tệp trực tiếp, không phải multipart |
| GET | `/api/files?offset=0&limit=50` | Danh sách phân trang, tối đa 200 mục/lần |
| GET | `/api/files/{id}/download` | Tải nội dung dưới dạng attachment |
| POST | `/api/files/{id}/verify` | Đọc lại nội dung từ storage và đối chiếu hash + size |

Ví dụ PowerShell (dùng `curl.exe` để tránh alias):

```powershell
curl.exe -X POST --data-binary '@C:\path\example.txt' 'http://localhost:8000/api/files?filename=example.txt'
curl.exe http://localhost:8000/api/files
```

`verify` trả HTTP 200 với `intact=false` nếu nội dung thay đổi. Tệp không có metadata trả 404; ID sai định dạng trả 422; storage không đọc được trả 503; vượt giới hạn trả 413. Lỗi dependency không được báo là xác minh thành công.

## Cấu hình và phạm vi bảo vệ

- `.env` là cấu hình riêng, được loại khỏi Git và Docker build context. `.env.example` không có credential thật.
- Mặc định local chỉ bind `127.0.0.1`, database không publish cổng ra Windows.
- `APP_API_KEY` tùy chọn là key chung của nhóm. Khi bật, mọi `/api/*` yêu cầu header `X-API-Key`; giao diện có ô nhập key. Đây chưa phải hệ thống tài khoản hoặc phân quyền từng người. Không đưa dịch vụ ra Internet khi chưa bổ sung TLS và xác thực phù hợp.
- Tên tệp chỉ là metadata; storage dùng UUID, tải xuống với `application/octet-stream` và `nosniff`.
- Upload ghi object trước, commit metadata sau; nếu commit thất bại ứng dụng cố xóa object và ghi log khi cần xử lý orphan. Hai storage không có transaction phân tán; cần đối soát sau sự cố/timeout hoặc process crash.
- Hash gốc nằm trong PostgreSQL. Nếu cả nội dung và metadata cùng bị sửa, cơ chế này không phát hiện được. Chưa có chữ ký số, lưu trữ bất biến hay quét malware.
- Schema phiên bản 1 được tạo ở startup. Chưa có framework migration cho thay đổi schema; không tự ý thay cấu trúc trên database chứa dữ liệu.
- `health/ready` kiểm tra database và storage; `health/live` chỉ kiểm tra tiến trình. Khi làm Octavia, chọn health check theo kịch bản cần chứng minh.

## Chuyển sang OpenStack

Xem [hướng dẫn triển khai](deploy/README.md). Cấu hình chạy app trên VM private có sẵn tại `deploy/compose.openstack.yaml`. Chưa có hạ tầng OpenStack thật trong phiên triển khai local; Swift, Cinder, Octavia, hai AZ và autoscaling cần kiểm thử tích hợp riêng.

**Không chạy nhiều App VM với storage local độc lập.** Các App VM phải cùng dùng Swift và cùng PostgreSQL; schema/storage không nằm trên từng app instance.

## Làm việc nhóm

```text
app/
  main.py           Ghép ứng dụng, không chứa logic tính năng
  config.py         Cấu hình từ môi trường
  database.py       Engine và session
  models.py         Schema dữ liệu
  routes/           HTTP API và health
  services/         Nghiệp vụ tệp
  storage/          Interface, local và Swift adapter
frontend/           HTML, CSS, JavaScript độc lập với backend
deploy/             Cấu hình App VM và runbook OpenStack
loadtest/           Kịch bản tải
tests/api/          Kiểm thử API
tests/storage/      Contract test adapter
.github/            CI, mẫu PR và issue
```

Ba vùng làm việc đề xuất: hạ tầng/tích hợp ở `deploy/`; backend/dữ liệu ở `app/`; UI và đo tải ở `frontend/` và `loadtest/`. Chi tiết nhánh, PR, reload và điểm phối hợp ở [hướng dẫn đóng góp](CONTRIBUTING.md).

1. Nhóm dùng cùng bộ mã nguồn, mỗi người có `.env` riêng.
2. Phát triển trên nhánh riêng; review trước khi merge như quy trình nhóm.
3. Chốt người phụ trách từng vùng và một người review; cấu trúc này không tự gán lại tên/vai trò của nhóm.
4. Trước khi tích hợp, ghi phiên bản OpenStack, IP/endpoint, dịch vụ đã hoạt động và kết quả kiểm tra vào tài liệu nhóm; không ghi secret.

## Tạo tải

TV3 xem [hướng dẫn workload và báo cáo](loadtest/README.md), [tiến độ và các mốc tích hợp](docs/TV3_PROGRESS.md).

Upload ít nhất một tệp trước. Chạy Locust trên host của container app:

```powershell
docker compose exec -T app locust -f loadtest/locustfile.py --headless -u 5 -r 1 -t 30s --host http://127.0.0.1:8000 --only-summary
```

Kịch bản tái sử dụng một tệp, không upload vô hạn. Kết quả chỉ là đo tải local, không chứng minh autoscaling. Nếu file nhỏ không tạo đủ CPU load, cần đo lại metric và chọn ngưỡng/workload thực tế; không giả lập alarm thành scale-out thật.

## Tài liệu công nghệ

- [FastAPI Request và streaming](https://www.starlette.io/requests/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- [Swift client](https://docs.openstack.org/python-swiftclient/latest/)
- [Octavia DevStack requirements](https://docs.openstack.org/octavia/latest/contributor/guides/dev-quick-start.html)
- [Aodh alarms](https://docs.openstack.org/aodh/latest/admin/telemetry-alarms.html)
