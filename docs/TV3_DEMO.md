# TV3: tập demo, thu chứng cứ và chuẩn bị báo cáo

## Có thể hoàn thành một mình

| Việc | Sản phẩm có thể tự chuẩn bị |
|---|---|
| Giao diện | Review PR #1, luyện upload/verify/copy hash; giữ ảnh và kết quả test |
| Tải | Review PR #2, chạy lại profile local; giải thích RPS, p95, lỗi và giới hạn phép đo |
| Elasticity | Kiểm tra/sửa template tại `deploy/elasticity/`, chạy offline test, hiểu ngưỡng/budget/boot contract |
| Khả dụng | Chạy sampler HTTP local, hiểu lỗi readiness và tập thu snapshot |
| Báo cáo | Điền phần đã có chứng cứ; để `NOT AVAILABLE` ở kết quả cloud chưa chạy |

PR #1: <https://github.com/vuchianhtuan/BTLDienToanDamMay/pull/1>. PR #2: <https://github.com/vuchianhtuan/BTLDienToanDamMay/pull/2>. Bộ elasticity nằm ở nhánh riêng, không chứa code của hai PR này khi chúng chưa merge. Muốn dùng chung, tích hợp các PR đã review vào nhánh thử nghiệm sau; không giả định checkout nhánh này sẽ có UI/Locust mới.

## Tập thu bằng chứng ngay trên máy cá nhân

Khởi động stack local theo README. Từ gốc repo:

```powershell
python deploy/elasticity/probe_http.py --url http://127.0.0.1:8000 --expected-storage local --samples 10 --interval 1 --out test-results/elasticity/local-ready.json
```

Sampler chỉ GET readiness, có giới hạn số mẫu/thời gian chờ, không retry và không theo redirect. Exit 0 khi tất cả mẫu đạt, 1 khi có mẫu lỗi, 2 khi tham số/output lỗi. Kết quả gồm timestamp UTC, status HTTP, latency, số mẫu lỗi và chuỗi lỗi liên tiếp dài nhất. Readiness local không chứng minh Swift hay tính sẵn sàng của OpenStack. Khi chạy qua VIP thật, dùng `--expected-storage swift`; mặc định cũng là `swift`. Luôn đặt tên output mới.

Muốn tập nhận diện lỗi mà không ảnh hưởng stack: unit test đã dùng HTTP server tạm trả 503, redirect, JSON hỏng và storage không khớp. Không cần tắt DB của nhóm để làm bài tập này. Upload/verify/download và hash vẫn cần kiểm tra riêng vì readiness chỉ kiểm tra DB/storage.

## Ma trận chấp nhận trên cloud

Không đánh dấu đạt chỉ dựa vào Heat `CREATE_COMPLETE` hoặc ảnh dashboard. Dùng file tổng hợp theo từng lần chạy:

| Hạng mục | Cách xác minh | Bằng chứng cần lưu | Hiện trạng trước tích hợp |
|---|---|---|---|
| Hai AZ | Mapping UUID App VM → AZ/host, mỗi AZ ít nhất 1 VM | Output Nova và ảnh không có secret | NOT AVAILABLE |
| App private | App chỉ có private IP, đường tới App:8000 từ Octavia | Port/floating-IP/SG đã lược thông tin nhạy cảm | NOT AVAILABLE |
| LB | Hai member ONLINE; truy cập VIP, upload/verify/download | Snapshot member + HTTP + UUID/hash tệp | NOT AVAILABLE |
| Shared data | Tạo qua VIP rồi đọc/verify qua App khác ở mạng quản trị | Hash và metadata trùng, Swift object, DB row | NOT AVAILABLE |
| Scale-out | CPU qua ngưỡng, Aodh có history, Heat event tạo VM, member ONLINE | Timeline UTC với cùng resource ID | NOT AVAILABLE |
| Scale-in | CPU dưới ngưỡng đủ cửa sổ/cooldown, giảm VM nhưng còn 1/AZ | Metric + history + events + members | NOT AVAILABLE |
| Không đủ mẫu | Alarm `insufficient data` không gọi policy | History và số VM không đổi | NOT AVAILABLE |
| Khả dụng khi đổi member | Sampler + Locust đang chạy qua VIP | Mọi mẫu, lỗi, p95; không bỏ khoảng lỗi khỏi báo cáo | NOT AVAILABLE |

Mẫu timeline (copy sang file của lần chạy; không điền thời gian giả):

| UTC | Sự kiện | UUID liên quan | Tệp minh chứng | Đã xác minh |
|---|---|---|---|---|
| NOT AVAILABLE | Baseline: 2 App, 2 member ONLINE | NOT AVAILABLE | NOT AVAILABLE | Chưa |
| NOT AVAILABLE | Bắt đầu Locust qua VIP | NOT AVAILABLE | NOT AVAILABLE | Chưa |
| NOT AVAILABLE | CPU vượt ngưỡng đủ periods | NOT AVAILABLE | NOT AVAILABLE | Chưa |
| NOT AVAILABLE | Aodh chuyển alarm và gửi action | NOT AVAILABLE | NOT AVAILABLE | Chưa |
| NOT AVAILABLE | Heat tạo App/member mới ONLINE | NOT AVAILABLE | NOT AVAILABLE | Chưa |
| NOT AVAILABLE | Giảm tải; Aodh/Heat scale-in hoàn tất | NOT AVAILABLE | NOT AVAILABLE | Chưa |

Giữ snapshot trước/sau bằng `kit.py collect` trong [runbook](../deploy/elasticity/README.md). Cần ảnh/raw log bổ sung cho metric và Aodh history; collector không tự chứng minh causal chain. Kiểm tra/che secret và dữ liệu người dùng trước khi đưa chứng cứ vào Git. Không commit thư mục `test-results` nguyên bản.

## Demo trình bày 10 phút

1. **0–1 phút:** Bài toán, sơ đồ hai AZ, vai trò Swift/Cinder/PostgreSQL, giới hạn lab.
2. **1–3 phút:** Upload tệp đã chuẩn bị, hiển thị metadata/SHA-256, verify/download qua VIP.
3. **3–5 phút:** Hai backend private và pool ONLINE; giải thích shared storage, không chỉ trình diễn hai bản app local.
4. **5–8 phút:** Chiếu timeline/video lần autoscale đã chạy thật cùng metric, Aodh history và Heat events; chỉ rõ thời gian chờ thực. Nếu làm live, chuẩn bị phần chờ trước giờ thuyết trình.
5. **8–9 phút:** Locust/sampler: RPS, p95, lỗi, cách xác nhận nguyên nhân; nêu giới hạn phép đo.
6. **9–10 phút:** Chi phí, phân công, kết quả đạt/chưa đạt.

**Thời gian chạy thử không bị giới hạn 10 phút.** Với metric 300 giây × 2 periods, cả tăng/giảm cộng boot có thể cần hàng chục phút. Kịch bản ứng dụng nhẹ có thể không tạo đủ CPU; ghi nhận và điều chỉnh workload/ngưỡng dựa trên số đo thật. Nếu dùng stress CPU tổng hợp để kiểm tra dây metric→alarm→Heat, ghi rõ đó là bài thử hạ tầng riêng, không gọi là tải người dùng thực tế. Nếu cloud chưa sẵn sàng, trình diễn local và nêu phần thiếu; không dùng mock test làm minh chứng triển khai thật.

## Bảng chi phí để tự hoàn thiện

Đơn vị VND; điền nguồn và thời điểm cho mọi số liệu. Chi phí phần cứng đã có là tài sản sẵn có, không tự tính bằng 0; trình bày riêng chi phí mua mới và chi phí vận hành phát sinh. Giấy phép OpenStack không đồng nghĩa tổng vận hành miễn phí.

| Hạng mục | Cách tính | Đầu vào thực tế | Thành tiền | Nguồn/minh chứng |
|---|---|---|---|---|
| Máy của nhóm | Thiết bị sẵn có; ghi cấu hình/khấu hao nếu tính | NOT AVAILABLE | NOT AVAILABLE | Kiểm kê nhóm |
| Điện chạy lab | Tổng công suất đo W / 1000 × giờ × đơn giá điện | NOT AVAILABLE | NOT AVAILABLE | Số đo/hóa đơn/biểu giá áp dụng |
| Thuê VM/GPU/cloud nếu dùng | Đơn giá × giờ + disk + network theo hóa đơn | NOT AVAILABLE | NOT AVAILABLE | Hóa đơn/console provider |
| Mạng/VPN/dịch vụ trả phí | Gói thực dùng × thời gian phân bổ | NOT AVAILABLE | NOT AVAILABLE | Hợp đồng/gói tài khoản |
| Dự phòng | Ghi cách ước lượng và tách khỏi khoản đã chi | NOT AVAILABLE | NOT AVAILABLE | Giả định ghi rõ |

Không lấy giá cũ trên mạng làm chi phí thực; không nhập số 0 cho khoản chưa biết. Tách **ước tính** và **đã thanh toán**, ghi khoảng thời gian đo, không cộng hai lần.

## Thông tin chỉ cần phối hợp khi tích hợp

TV1 bàn giao phiên bản cloud/plugin, AZ thật, network/subnet/SG, route tới VIP, quota và capacity còn trống kể cả amphora. TV2 bàn giao DB trên Cinder, Swift/container và application credential, cấu hình app, kiểm chứng shared data. TV3 tự chuẩn bị template/image procedure/test/demo trước; sau bàn giao mới điền cấu hình, validate Heat và chạy bài thử cloud. Cấp secret qua kênh riêng, không để trong issue/PR/chat công khai.
