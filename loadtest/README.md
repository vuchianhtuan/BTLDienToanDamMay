# Kiểm thử tải phần TV3

Phụ trách: Đinh Kiều Công Tuấn. Workload gọi HTTP theo docs/API_CONTRACT.md, không sửa API hay schema. Không upload lặp trong lúc đo tải.

## Chuẩn bị fixture

1. Chạy app bằng Docker Compose theo README ở thư mục gốc.
2. Upload một tệp demo qua UI. Dùng tệp khoảng 1–10 MiB khi đo, ghi lại kích thước và SHA-256; tệp vài byte chỉ phù hợp smoke test.
3. Mặc định mỗi user chọn tệp mới nhất khi khởi tạo. Đặt LOADTEST_FILE_ID thành UUID của cùng một tệp nếu cần kết quả có thể so sánh; không upload tệp mới trong lúc đo. UUID lấy từ JSON trả về của API upload/list.
4. Khi bật API key, Locust đọc APP_API_KEY từ môi trường. Không ghi key vào lệnh, báo cáo hoặc Git. Compose đã truyền key của app vào container.

## Chạy baseline local

Chạy tại thư mục gốc repo, trong PowerShell:

~~~powershell
docker compose exec -T app locust -f loadtest/locustfile.py --headless -u 5 -r 1 -t 30s --host http://127.0.0.1:8000 --only-summary
~~~

Kịch bản gồm list:verify:download theo trọng số 3:1:1; mỗi user nghỉ ngẫu nhiên 1–3 giây giữa các task. Chuẩn bị fixture nằm trong thống kê riêng với tên fixture metadata. Thiếu fixture hoặc lỗi xác thực làm dừng user và ghi failure; không tiếp tục chạy chỉ list rồi báo toàn bộ workload thành công.

Verify HTTP 200 nhưng intact=false, hash/size không khớp vẫn là failure. Download được đọc theo chunk, đối chiếu SHA-256 và số byte; thời gian gồm nhận/kiểm tra toàn bộ nội dung. Vì client tính hash, cần theo dõi CPU của máy tạo tải để tránh nhầm nút thắt client với server.

## Đo qua Octavia và xuất báo cáo

Chỉ chạy khi TV1 đã cung cấp endpoint và nhóm thống nhất phiên tạo tải. Ví dụ PowerShell dưới đây yêu cầu Python/Locust đã cài trên máy đo riêng:

~~~powershell
$fixtureId = Read-Host 'UUID tep demo'
$targetUrl = Read-Host 'URL cua Octavia'
$env:LOADTEST_FILE_ID = $fixtureId
New-Item -ItemType Directory -Force test-results | Out-Null
python -m locust -f loadtest/locustfile.py --headless -u 5 -r 1 -t 60s --host $targetUrl --only-summary --csv test-results/baseline --html test-results/baseline.html
~~~

Nếu ứng dụng yêu cầu key, cấp APP_API_KEY cho tiến trình qua môi trường riêng trước khi chạy. Thử 5 users trước, sau đó tăng từng mức đã thống nhất; dừng khi lỗi tăng mạnh hoặc ảnh hưởng thành viên khác. CSV/HTML chứa tên và kết quả endpoint, lưu trong test-results đã được Git bỏ qua. Không đưa dữ liệu nhạy cảm vào fixture.

Với Compose có thể cố định fixture bằng docker compose exec -T -e LOADTEST_FILE_ID=$fixtureId app locust ... và giữ các tham số workload như trên. Báo cáo tạo trong container cần được sao chép ra host trước khi tạo lại container.

## Kiểm tra chính kịch bản tải

~~~powershell
docker compose exec -T app python tests/loadtest/smoke_workload.py
~~~

Hoặc dùng Python có dependency trong requirements.txt: python tests/loadtest/smoke_workload.py. Script tạo API subprocess, SQLite và storage tạm riêng, chạy các task qua HTTP thật rồi dọn môi trường. Các ca: tệp hợp lệ, download đủ byte, sửa nội dung cùng kích thước, mất object, UUID fixture không tồn tại và sai API key. Không dùng dữ liệu trong stack đang chạy.

## Bằng chứng cần ghi cho mỗi lượt đo

- Commit, môi trường, storage/DB, endpoint app trực tiếp hay LB, số App VM.
- UUID, dung lượng và SHA-256 fixture; users, spawn rate, thời gian chạy.
- Request/failure, throughput, p50/p95/p99; CPU/RAM/network của app và máy tạo tải.
- Khi thử autoscaling: metric/đơn vị/chu kỳ, ngưỡng, cooldown, min/max VM, alarm history, Heat events và Octavia pool member trước/sau.
- Mốc thời gian tải tăng, alarm, VM tạo xong, member HEALTHY; sau giảm tải kiểm tra scale-in và dữ liệu còn đọc/verify được.

Bài tải local không chứng minh autoscaling. Không kết luận scale-out chỉ vì alarm đổi trạng thái; phải có VM thật và member mới nhận traffic.
