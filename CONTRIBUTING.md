# Phát triển theo nhóm ba thành viên

Nhóm có thể phát triển local độc lập; chỉ cần cùng bật ba Ubuntu VM khi tích hợp OpenStack. Mỗi người giữ database, file demo và `.env` riêng.

## Khởi động lần đầu

```powershell
git clone https://github.com/vuchianhtuan/BTLDienToanDamMay.git
cd BTLDienToanDamMay
Copy-Item .env.example .env
docker compose up --build -d --wait --wait-timeout 180
```

Mở http://localhost:8000. Docker Desktop cần chạy Linux containers. Không cần cài Python/PostgreSQL riêng trên host. Repo không kèm dữ liệu đã upload, database, image đã build hoặc `.env` của người khác.

Để dùng bản Swift/Cinder đã triển khai trên lab TV2, không cần Docker: làm theo [cấu hình truy cập lab cho thành viên](deploy/tv2/README.md#1-mở-giao-diện-từ-windows), rồi chạy `./scripts/connect-lab.ps1`. Mỗi người dùng key và cấu hình riêng; EC2/App/DB phải đang chạy. Đây là bản đang triển khai trên lab; khi sửa code trên máy mình, tiếp tục dùng bản local để kiểm thử trước khi phối hợp triển khai lên cụm.

## Chọn chế độ làm việc

Chạy bản giống CI/demo:

```powershell
docker compose up --build -d --wait
```

Khi sửa backend/frontend thường xuyên, dùng chế độ dev có bind mount và reload Python:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Sửa frontend rồi refresh browser; sửa Python thì Uvicorn reload. Khi chuyển từ dev về bản thường, ép tạo lại app để bỏ các mount dev:

```powershell
docker compose up --build -d --force-recreate app --wait
```

Dependency thay đổi vẫn cần build lại. Nếu 8000 bận, sửa `APP_PORT` trong `.env`. Mỗi máy dùng project name mặc định được; nếu chạy nhiều clone đồng thời trên cùng máy, cần đổi cả `COMPOSE_PROJECT_NAME` và `APP_PORT` để tránh dùng chung container/volume/cổng.

## Chia vùng công việc

Đây là đề xuất chốt theo kỹ năng; không tự gán tên thành viên khi nhóm chưa thống nhất.

| Người/vùng | File chủ yếu | Có thể làm độc lập | Điểm cần phối hợp |
|---|---|---|---|
| TV1 Hạ tầng và tích hợp | `deploy/`, tài liệu hạ tầng, `compose*.yaml`, CI | Cấu hình VM/mạng, runbook, tự động hóa triển khai | Endpoint, secret injection, cổng/health check, ngân sách RAM |
| TV2 Backend và dữ liệu | `app/routes/`, `app/services/`, `app/storage/`, `app/models.py`, `tests/` | API, Swift adapter, truy vấn, kiểm thử | Contract API, schema/migration, môi trường Swift thật |
| TV3 Frontend và kiểm thử tải | `frontend/`, `loadtest/`, tài liệu kết quả | UI, hiển thị kết quả, kịch bản Locust | API contract và workload/metric cho elasticity |

TV3 có thể phối hợp TV1 phần Octavia/Heat/Aodh. Ai phụ trách một dịch vụ không bắt buộc cài dịch vụ đó trên laptop của mình. Một issue có một người chịu trách nhiệm chính, được người khác review.

`app/main.py` chỉ ghép các module. Đừng dồn tính năng mới vào đó. Storage có interface tại `app/storage/base.py`; frontend và load test chỉ gọi HTTP theo `docs/API_CONTRACT.md`.

## Nhánh và Pull Request

Đảm bảo working tree sạch hoặc commit các thay đổi đang làm trước khi đổi nhánh:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feat/file-search
```

Mỗi nhánh xử lý một chức năng nhỏ. Ví dụ `feat/swift-integration`, `feat/ui-search`, `infra/octavia`, `test/load-scenarios`. Khi xong:

```powershell
docker compose up --build -d --wait
docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
docker compose exec -T app python tests/smoke_live.py
git status
git add <cac-file-da-kiem-tra>
git diff --cached
git commit -m "Add file search"
git push -u origin feat/file-search
```

Thay `<cac-file-da-kiem-tra>` bằng đường dẫn file thật. Tạo PR vào `main`, có ít nhất một người khác review và CI đạt trước merge. GitHub CI build Docker, chạy pytest và smoke với PostgreSQL thật; CI không cần OpenStack credential. Người review phải kiểm tra hành vi và ảnh hưởng contract, không chỉ nhìn dấu xanh.

Khi main thay đổi trong lúc đang phát triển, lưu/commit công việc rồi:

```powershell
git fetch origin
git merge origin/main
```

Giải quyết conflict, chạy lại test, sau đó push nhánh của mình. Không force-push main. Không sửa file của người khác chỉ để né conflict; trao đổi ở PR khi cần đổi interface.

## Contract và thay đổi chung

- Chốt tên endpoint, request/response và mã lỗi trước khi frontend/backend phát triển song song. Upload hiện là raw bytes, không phải multipart.
- Giữ tương thích nếu có thể. Nếu bắt buộc thay API, cập nhật `docs/API_CONTRACT.md`, frontend, load test và test trong cùng PR hoặc thống nhất thứ tự merge các PR liên quan.
- `create_all()` chỉ tạo bảng mới, không tự đổi cột. PR thay schema phải có migration và hướng dẫn áp dụng/rollback; không xóa volume của thành viên khác để sửa lỗi schema.
- `requirements.txt` chứa dependency trực tiếp; Docker cài `requirements.lock.txt`. Người đổi thư viện cập nhật cả hai và tái tạo lock trong Python 3.12 Linux sạch. Không lấy `pip freeze` của máy Windows cá nhân làm lock Linux.
- `scripts/refresh-lock.ps1` dựng môi trường Linux riêng, xuất lock mới; kiểm tra diff và build/test lại trước commit. Lệnh này có thể cập nhật cả dependency gián tiếp, nên chỉ chạy khi có chủ đích.
- Chỉ dùng dữ liệu giả khi test. Không commit secret, openrc/clouds.yaml, khóa SSH, dump hoặc file upload thật. `.gitignore` không bảo vệ secret đã lỡ commit; cần báo nhóm, thu hồi/đổi secret và xử lý lịch sử.
- Không chạy DevStack, đổi IP/Tailscale/network hoặc sửa controller khi người khác đang kiểm thử; hẹn phiên tích hợp trước.

## Tiêu chí hoàn thành một công việc

Code/cấu hình đã review, test phù hợp đạt, có hướng dẫn chạy và minh chứng. Phân biệt test local/fake với kết quả OpenStack thật. Bật đủ ba máy chỉ khi cần thử cross-node hoặc dịch vụ phụ thuộc cụm.

## Thiết lập GitHub do chủ repo quản lý

Thêm hai tài khoản làm collaborator khi đã biết đúng username. Nếu gói repo hỗ trợ, bảo vệ main: yêu cầu PR, ít nhất một review, status check `Docker build and application tests`, không force-push. Nếu không có branch protection, nhóm vẫn tuân thủ quy ước review bằng tay. Workflow có trong source không tự bật các rule này hoặc cấp quyền collaborator.
