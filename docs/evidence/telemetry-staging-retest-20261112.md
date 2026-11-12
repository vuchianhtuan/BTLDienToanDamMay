# Minh chứng telemetry staging ngày 12/11/2026

Canary chạy CPU thật với 1 vCPU mỗi VM, hai mẫu 300 giây và cooldown Heat 600 giây. Ngưỡng tăng là 210.000.000.000 ns, ngưỡng giảm là 60.000.000.000 ns. Hai mẫu khi có tải là 269.920.000.000 và 295.580.000.000 ns.

| Giờ Việt Nam | Kết quả |
|---|---|
| 22:31:02 | Bắt đầu tải CPU. |
| 22:41:28 | Nova xác nhận hai VM `ACTIVE`. |
| 22:41:30 | Dừng tải CPU. |
| 22:52:32 | Nova xác nhận tự giảm còn một VM `ACTIVE`. |
| 22:52:42 | Bài thử kết thúc với mã 0. Cả hai alarm đã tắt. |

Aodh lặp action scale-in sau khi Heat từ chối trong cooldown. VM được tạo trong lượt scale-out là VM còn lại.

Sau khi áp dụng [bản vá Aodh](../../deploy/elasticity/aodh-negative-cpu.patch) trên staging, thử với metric kiểm soát trong Gnocchi và Aodh thật:

| Dữ liệu thử | Trạng thái |
|---|---|
| Hai mẫu âm | `insufficient data` |
| Một mẫu âm và một mẫu dương thấp | `insufficient data` |
| Thiếu metric | `insufficient data` |
| Hai mẫu dương thấp hợp lệ | `alarm` |

Các alarm thử không có action Heat. Nova giữ nguyên một VM và tài nguyên thử đã được dọn. Chu kỳ autoscaling của ứng dụng qua Octavia còn chờ nghiệm thu.
