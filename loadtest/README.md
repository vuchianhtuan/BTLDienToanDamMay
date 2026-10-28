# Phần Locust của TV3

Kịch bản kiểm tra list, verify và download với một tệp có sẵn. HTTP 200 chưa được coi là thành công nếu payload sai. Các request có timeout 15 giây và được gom tên cố định để báo cáo không phình theo UUID.

## Chuẩn bị và chạy

Sau khi build app từ nhánh chứa phần Locust:

```powershell
docker compose up --build -d --wait
docker compose exec -T app python loadtest/prepare_fixture.py --size-mib 1
docker compose exec -T app python -m locust -f loadtest/locustfile.py --headless -u 5 -r 1 -t 30s --host http://127.0.0.1:8000 --only-summary --exit-code-on-error 1
```

Lệnh prepare tạo đúng một tệp giả (mặc định 1 MiB), trả UUID/hash và không lặp upload trong workload. Locust chọn tệp mới nhất ở thời điểm mỗi user bắt đầu. Để so sánh công bằng, chuẩn bị fixture một lần, không upload thêm hoặc đổi nội dung trong lúc đo; ghi UUID/kích thước vào kết quả. Nếu cần dùng tệp khác, upload nó trước lượt đo. `APP_API_KEY` được lấy từ môi trường container, không ghi vào code hoặc báo cáo.

## Kịch bản và tiêu chí

- Metadata phải là mảng JSON có UUID, SHA-256 hợp lệ và size không âm. Không có fixture hoặc fixture hỏng/sai quyền thì dừng run với exit code 1.
- Mỗi user kiểm tra verify và download fixture trước khi chạy workload ngẫu nhiên: list : verify : download có trọng số 3 : 1 : 1, thời gian nghỉ 1–3 giây.
- Verify phải có `intact=true` đúng kiểu boolean, đúng ID, hai hash và hai size khớp metadata đã chọn.
- Download phải có đúng số byte và SHA-256; nội dung bị sửa cùng kích thước vẫn là lỗi.
- Khi đang đo, lỗi request vẫn được đếm để phản ánh tỷ lệ lỗi. Lỗi fixture ở bước khởi tạo khiến run dừng sớm, không tạo kết quả xanh không có workload.

## Các mức tải gợi ý

| Profile | Users | Tăng users mỗi giây | Thời gian mặc định |
|---|---:|---:|---:|
| light | 5 | 1 | 30 giây |
| medium | 10 | 2 | 30 giây |
| higher | 20 | 2 | 30 giây |

Đây là mức thử ban đầu trên máy lab, không phải tải tối đa hoặc ngưỡng autoscaling. Tăng từng mức sau khi kiểm tra RAM/CPU, độ trễ và tỷ lệ lỗi. File nhỏ và các tác vụ I/O có thể không làm CPU đủ cao để kích hoạt alarm; cần chốt metric/ngưỡng với TV1 theo số liệu thật.

Xuất báo cáo CSV/HTML bằng PowerShell:

```powershell
./scripts/run-loadtest.ps1 -Profile light
./scripts/run-loadtest.ps1 -Profile medium
```

Script dùng fixture đã có; hãy chạy prepare trước. Báo cáo được copy về `test-results/locust/<profile>-<id>/` và không đưa vào Git tự động. Chỉ commit bản tóm tắt đã kiểm tra dữ liệu nhạy cảm vào `docs/evidence/`. Không chạy đồng thời các profile trên cùng máy nếu muốn so sánh từng mức.

Mỗi profile có `summary.json` chụp bộ đếm cuối khi Locust thoát. Dùng file này cho tổng requests/failures, đặc biệt khi lỗi fixture làm run kết thúc trước lần cập nhật CSV tiếp theo. CSV/HTML vẫn hữu ích để xem lịch sử và từng endpoint.

## Kiểm thử

Chạy offline, không cần Docker hoặc Locust:

```powershell
python -m unittest discover -s tests/loadtest -v
```

Chạy toàn bộ pytest và Locust CLI integration khi app/PostgreSQL đã sẵn sàng:

```powershell
docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
docker compose exec -T app python tests/smoke_live.py
docker compose exec -T app python tests/smoke_locust.py
```

Integration chạy Locust thật trên ứng dụng thật cho trường hợp khỏe, rồi dùng HTTP fixture có kiểm soát cho các trường hợp: không có tệp, 401, verify trả false dù HTTP 200 và download hỏng cùng kích thước. Mỗi ca lỗi phải có failure được ghi nhận và exit code 1; lỗi import hoặc run không tạo request không được tính là test đạt.

## Giới hạn đo local

Locust chạy trong cùng container với app ở cấu hình này, nên các con số chịu ảnh hưởng máy tạo tải và không đo đường truyền Tailscale/WAN. Download được giữ trong bộ nhớ của mỗi user để tính hash; cân nhắc kích thước fixture khi tăng số users. Khi có cụm thật, chạy máy tạo tải riêng, dùng URL Octavia, cùng DB/Swift và thu metric/alarm/Heat cùng mốc thời gian. Thành công local không chứng minh autoscaling hoặc OpenStack đã hoạt động.
