# Bàn giao code TV3 cho thành viên và agent

**Nhánh lấy code: `feat/tv3-handoff`.** Đây là bản ghép UI, Locust và bộ chuẩn bị elasticity. Nhánh gốc `feat/cong-tuan-ui-loadtest` được giữ tại `a3fa8a0`, không nhận đợt cập nhật này. Các PR #1/#2/#3 vẫn là các phần review riêng; bản bàn giao đã chứa phần của cả ba, không cần merge lại từng PR vào bản này.

## Lấy về để chạy thử

Clone mới:

```sh
git clone --branch feat/tv3-handoff --single-branch https://github.com/vuchianhtuan/BTLDienToanDamMay.git BTLDienToanDamMay-TV3
cd BTLDienToanDamMay-TV3
```

Repo đã có trên máy và working tree sạch/đã lưu công việc:

```sh
git fetch origin
git switch --track origin/feat/tv3-handoff
```

Nếu nhánh local này đã tồn tại: `git switch feat/tv3-handoff`, rồi `git pull --ff-only origin feat/tv3-handoff`. Giữ `.env` riêng; chỉ copy `.env.example` thành `.env` nếu chưa có. Chạy:

```sh
docker compose up --build -d --wait --wait-timeout 180
```

Mở `http://localhost:8000`. Khi chạy hai clone trên cùng laptop, đặt `COMPOSE_PROJECT_NAME` và `APP_PORT` khác trong `.env`; kiểm tra bằng `docker compose config --format json` trong phiên riêng nếu cần, không đưa output có secret vào repo/chat công khai. Không xóa volume của clone đang dùng.

## Ghép vào nhánh của TV1/TV2

Commit/lưu công việc của mình trước. Từ nhánh thành viên, tạo nhánh tích hợp để review:

```sh
git fetch origin
git switch -c integration/tv3-handoff
git merge --no-ff origin/feat/tv3-handoff
```

Nhánh mới được tạo từ nhánh đang đứng; phải xác nhận đúng nhánh nền trước khi chạy. Nếu tên integration đã tồn tại, dùng tên mới hoặc mở nhánh đó theo chủ đích. Giải quyết conflict theo bảng dưới rồi chạy kiểm thử. Nếu cần hủy một merge chưa commit, `git merge --abort` trên nhánh tích hợp. Không checkout toàn bộ phiên bản TV3 đè lên backend/Compose của thành viên. Không cherry-pick các merge commit một cách tùy ý; merge nhánh giữ được lịch sử và tránh thiếu file phụ thuộc.

## Phạm vi và những tính năng cần giữ

| Vùng | Đã bàn giao | Lưu ý khi tích hợp |
|---|---|---|
| `frontend/` | Upload có tiến trình/hủy; cảnh báo kết quả chưa xác định khi đứt kết nối; khóa thao tác; danh sách tránh request cũ/không đi sang trang trống; verify chi tiết, copy SHA-256 | Giữ `api-client.js` trước `app.js` trong HTML và toàn bộ ID của các control; app không cần build JS |
| `loadtest/` | Chọn fixture bằng `LOADTEST_FILE_ID` hoặc tệp mới nhất, tìm qua trang metadata; verify/download trước workload; streaming hash/size; lỗi semantic được đếm; final JSON | `APP_API_KEY` lấy từ env; không upload lặp trong task; giữ chung `validation.py` với `locustfile.py` |
| `scripts/` | Test tổng hợp, chạy profile tải và xuất báo cáo | Node chạy trên host; pytest/smoke/Locust trong app container; báo cáo raw bị Git bỏ qua |
| `deploy/elasticity/` JSON | LB private, hai ASG theo AZ; ngưỡng/budget, build env, đọc trạng thái cloud, sampler HTTP | Luồng bàn giao chính; alarm tắt, tối đa cấu hình 2 VM/nhóm. Phải tính thêm App cũ/DB/amphora khi kiểm tra dung lượng |
| `deploy/elasticity/` YAML cũ | Validator, preflight/probe, template và test đã có từ nhánh gốc | Giữ để người đang dùng không mất code. Xem `YAML_RUNBOOK.md`; topology baseline + một ASG cho tổng 2–3 App, khác JSON |
| `tests/`, CI, `docs/` | Bộ test ghép, bằng chứng các lần chạy và hướng dẫn | Hợp nhất các bước CI thay vì chọn toàn bộ workflow của một phía |
| `app/`, API/schema, dependency lock | Giữ contract nền của nhóm | Không có migration/API mới trong bàn giao TV3; TV2 có thể phát triển riêng theo contract |

JSON và YAML là hai phương án riêng, không phải hai bước nối tiếp. Chọn một phương án phù hợp capacity sau khi thống nhất với TV1; không trộn secret, parameter, stack output hoặc resource ownership giữa hai bộ.

## Kiểm tra sau khi ghép

Node 20+ trên host; Python/Docker như README:

```sh
node --test tests/frontend/*.test.cjs
docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
docker compose exec -T app python deploy/elasticity/kit.py lint
docker compose exec -T app python tests/smoke_live.py
docker compose exec -T app python tests/loadtest/smoke_workload.py
docker compose exec -T app python tests/smoke_locust.py
```

PowerShell có thể dùng `./scripts/test.ps1` để chạy các kiểm tra này. Bộ YAML tách riêng:

```sh
python -m venv .venv-tools
# Kích hoạt .venv-tools theo hệ điều hành trước khi cài.
python -m pip install -r deploy/elasticity/requirements-check.txt requests==2.34.2
python deploy/elasticity/validate.py
python -m unittest discover -s deploy/elasticity/tests -v
```

Không cài dependency tooling vào lock app. CI có job riêng cho YAML và kiểm tra app/UI/JSON/Locust trên nhánh bàn giao. Smoke live tạo một tệp giả có tên `smoke-`; smoke workload dùng API/database/storage tạm. Bộ CLI Locust có các HTTP server giả để thử lỗi, không phải kết quả cloud.

## Trạng thái và đầu vào còn thiếu

Các kết quả cũ trong `docs/evidence/tv3-ui`, `tv3-locust`, `tv3-elasticity` thuộc các nhánh/commit riêng đã ghi trong báo cáo. Xem `docs/evidence/tv3-handoff/RESULTS.md` cho lần kiểm thử **bản ghép**. Không lấy số đo lịch sử làm kết quả benchmark của commit mới.

Chưa có Heat API validation, boot image, Octavia, Gnocchi/Aodh hoặc autoscale thật trên cụm nhóm. TV1 cung cấp phiên bản/plugin/AZ/network/SG/quota/capacity và route tới VIP. TV2 cung cấp app image, DB trên Cinder, Swift/container và credential riêng. Endpoint/secret thật để trong file local bị ignore và chia sẻ qua kênh riêng. Agent không được tự bịa UUID/metric/kết quả để điền vào báo cáo.

## Gợi ý giao việc cho agent của thành viên

Cho agent đọc `AGENTS.md`, tài liệu này, `docs/API_CONTRACT.md`, rồi yêu cầu: “Đọc phạm vi TV3 trên origin/feat/tv3-handoff, ghép vào nhánh tích hợp từ nhánh công việc hiện tại, giữ thay đổi backend/hạ tầng của tôi, xử lý conflict theo contract và chạy đủ kiểm thử; báo rõ phần chưa thể xác minh trên OpenStack.” Quyền push/merge/cấu hình cloud phải do người dùng của agent đó quyết định.
