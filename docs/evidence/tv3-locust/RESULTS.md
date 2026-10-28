# Kết quả kiểm chứng Locust TV3

Ngày chạy: 28/10/2026. Docker Linux engine 29.7.2, app FastAPI và PostgreSQL local; Locust 2.37.5 chạy cùng container với app. Mỗi user nghỉ 1–3 giây giữa các tác vụ; trọng số list/verify/download là 3/1/1. Mỗi lượt gồm cả thời gian tăng users và các request kiểm tra fixture ban đầu, không tách warm-up.

## Fixture giả

- Tên: `tv3-fixture-1MiB.bin`; kích thước 1,048,576 byte.
- UUID: `f42e5078-d2d7-4ba7-af46-efb8b7fdb136`.
- SHA-256: `c22f04a310cf7d86fb2f5c03e025abc543b260d4b9511a9518541db550493027`.
- Chuẩn bị một lần, dùng cùng fixture trong cả ba lượt; workload không upload liên tục.

## Kết quả đo

| Users | Tăng users/s | Thời gian | Requests | Failures | Avg ms | p95 ms | Req/s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 20 s | 63 | 0 | 6.32 | 10 | 3.25 |
| 10 | 2 | 20 s | 123 | 0 | 7.62 | 12 | 6.28 |
| 20 | 2 | 20 s | 224 | 0 | 8.07 | 14 | 11.47 |

Các JSON summary đi kèm là snapshot bộ đếm cuối. CSV, lịch sử và HTML đầy đủ nằm trên máy chạy tại `test-results/locust/`, được loại khỏi Git. Script tái hiện: `scripts/run-loadtest.ps1`; tham số `-DurationSeconds 20` được dùng cho ba lượt này.

## Kiểm thử tính đúng

- 29 pytest đạt, trong đó 12 test validation mới; API/PostgreSQL smoke đạt.
- Locust CLI thật với app khỏe: exit 0, 14 requests, 0 failures trong lượt smoke 6 giây.
- HTTP fixture không có tệp: exit 1, 2 requests, 2 failures.
- HTTP fixture trả 401: exit 1, 2 requests, 2 failures.
- HTTP fixture verify trả false dù HTTP 200: exit 1, 4 requests, 2 failures.
- HTTP fixture download sai SHA-256 nhưng cùng kích thước và HTTP 200: exit 1, 6 requests, 2 failures.

Các ca lỗi là HTTP server có kiểm soát trong `tests/smoke_locust.py`, không sửa dữ liệu ứng dụng thật. Kiểm tra yêu cầu có request/failure và lý do lỗi tương ứng; lỗi import hoặc CSV rỗng không được tính là test đạt. Báo cáo cuối riêng giúp tránh CSV định kỳ còn số 0 khi run dừng quá nhanh.

## Giới hạn

Đây là kiểm thử local ngắn, máy tạo tải và ứng dụng dùng chung tài nguyên. Các con số không phải sức tải tối đa, benchmark WAN hoặc chứng minh autoscaling. Chưa triển khai Octavia/Heat/Aodh; cần chạy lại qua LB với máy tạo tải riêng và thu metric thật khi có OpenStack.
