# Nghiệm thu autoscaling trên cụm ứng dụng ngày 13/11/2026

Lượt thử xác minh chuỗi **CPU App B → Gnocchi → Aodh → Heat → Octavia** trên ứng dụng File Integrity System. Pool bắt đầu với hai backend tại `tv1-az2` và `sg-test`, tăng lên ba rồi trở lại hai. Bản container kiểm thử là `file-integrity:4650bd0` từ commit `4650bd0999c892bd268ebb3302e324d54c834b2b`.

## Điều kiện thử

- Đọc CPU của App B từ chênh lệch bộ đếm libvirt trên một vCPU. Dùng tải CPU tổng hợp có giới hạn trong năm phút.
- Gnocchi và Aodh chạy trên staging. Aodh xét hai cửa sổ 60 giây với ngưỡng tăng trên 70% và ngưỡng giảm dưới 25%. Callback đi qua đường hầm SSH tới relay tạm trên Controller, giới hạn ở hai policy của Heat pilot.
- Heat pilot quản lý tối đa một backend bổ sung. Hai backend gốc ở hai AZ vẫn thuộc pool Octavia trong cả lượt thử.

## Dòng thời gian đã xác minh

Ngày 13/11/2026, theo UTC. Các dòng bên dưới tóm tắt log Gnocchi, Aodh, Heat, Octavia và phép thử VIP.

| Thời điểm UTC | Quan sát |
| --- | --- |
| 15:29, 15:30 | Gnocchi ghi CPU trung bình **92,78%** và **93,36%**. |
| 15:30:58 | Aodh chuyển alarm scale-out sang `alarm`. |
| 15:31:00 | Relay nhận callback scale-out và gửi tín hiệu Heat thành công. |
| 15:31:15 | Heat ghi `scale_out SIGNAL_COMPLETE`. |
| 15:32:59 | Octavia chuyển backend mới sang `ONLINE` sau khi ứng dụng khởi động. Pool có **3 member ONLINE**. |
| 15:35, 15:36 | Gnocchi ghi CPU trung bình **2,69%** và **2,49%** sau khi tải kết thúc. |
| 15:36:58 | Aodh chuyển alarm scale-in sang `alarm`. |
| 15:37:00 | Relay nhận callback scale-in và gửi tín hiệu Heat thành công. |
| 15:37:08 | Heat ghi `scale_in SIGNAL_COMPLETE`. Octavia trở về **2 member ONLINE** ở hai AZ gốc. |

ID đối chiếu khi kiểm tra hạ tầng:

- Heat stack `c5a561c5-d160-4efe-912d-d30616ff055e`
- Aodh scale-out `a5e914ca-461b-41db-ba52-2a740001758a`, scale-in `b324f486-a52c-44ee-be05-cdb1a8a07ff9`
- VM mới `c19b596e-a302-4693-911d-0e02190f8399`, member Octavia `6a426aa3-1e08-4c74-9822-5df825bcf01d`

## Kiểm tra dữ liệu và khả dụng

Backend mới và VIP trả readiness `ready` với Swift. SHA-256 của tệp mẫu tải trực tiếp từ backend mới, qua VIP sau scale-out và qua VIP sau scale-in đều khớp giá trị dưới đây. API verify trả `intact=true` ở cả ba lần kiểm tra.

```text
0341dcca4d64a4c75059dbe80bb3117435caf21884439d633a9c7676d898b5cd
```

Bộ dò readiness từ 15:30:23 đến 15:36:48 UTC ghi **56/60 HTTP 200**, **4 timeout ở 4 giây**, p95 **2,42 giây** tính trên phản hồi thành công. Bộ dò kết thúc trước khi Heat hoàn tất scale-in. Phép thử tải và verify sau scale-in xác nhận VIP vẫn phục vụ. Lượt này dùng tải CPU tổng hợp và chưa chạy Locust xuyên suốt chu kỳ.

Đã dọn stack, alarm, metric, relay và đường hầm thử. Đã xác minh hai backend gốc `ONLINE` sau khi dọn. Cấu hình telemetry của lượt thử dùng staging và relay tạm.
