# TV3 elasticity kit — kiểm chứng ngày 28/10/2026

## Phạm vi kết luận

Đây là kiểm chứng công cụ/template **offline và Docker local**. Chưa có kết quả Heat API validation, VM boot, Octavia, Gnocchi hoặc Aodh trên OpenStack thật. Các dữ liệu cloud vẫn là `NOT AVAILABLE`. Không dùng HTTP server giả trong unit test làm kết quả triển khai cloud.

Nhánh độc lập `feat/tv3-elasticity-kit` dựa trên `main` tại `9fea54d`; không chứa UI PR #1 hoặc Locust PR #2. Không merge hoặc push lên main trong lần chuẩn bị này.

## Đã chạy

| Phép thử | Kết quả |
|---|---|
| `python -m unittest discover -s tests/elasticity -v` trên Windows Python 3.13.9 | 22 đạt; gồm cấu hình sai, budget/CPU conversion, environment có secret thử nghiệm, filter snapshot và HTTP 503/redirect/JSON/storage mismatch |
| `docker compose up --build -d --wait --wait-timeout 180` | Build thành công; App và PostgreSQL healthy |
| `docker compose exec -T app python -m pytest tests -q -p no:cacheprovider` | 39 đạt trên Python 3.12; 1 cảnh báo deprecation từ thư viện Starlette/AnyIO |
| `docker compose exec -T app python deploy/elasticity/kit.py lint` | Tham chiếu và nested parameter contract đạt; đây không phải schema validator của Heat |
| `docker compose exec -T app python tests/smoke_live.py` | Readiness, frontend, upload, PostgreSQL metadata, list, download, SHA-256 verify đạt |
| `plan` với `config.example.json` còn placeholder | Từ chối, exit 2; không ghi file kết quả |
| `git check-ignore` với local config/env/generated environment/test-results | Các đường dẫn nhạy cảm/kết quả thô đều bị bỏ qua |

Các HTTP test cần được phép kết nối loopback. Lần chạy Windows bị giới hạn truy cập mạng ban đầu thất bại; chạy lại khi được phép kết nối và trong Docker đều đạt. Không chỉnh test để bỏ qua các thất bại HTTP.

## Mẫu readiness thật trên app local

```powershell
python deploy/elasticity/probe_http.py --url http://127.0.0.1:8000 --expected-storage local --samples 10 --interval 1 --out test-results/elasticity/local-ready-final-20261028.json
```

Kết quả đã lược/chọn để chia sẻ tại [local-readiness.json](local-readiness.json): 10 mẫu, 0 mẫu lỗi, sampled availability 100%, chuỗi lỗi liên tiếp dài nhất 0, p95 latency của probe 520,35 ms. Latency này gồm overhead HTTP client Windows và kiểm tra readiness; không so trực tiếp với p95 nghiệp vụ của Locust và không coi là uptime liên tục/SLO. Không đo failover hoặc autoscale trong lần chạy này.

Docker engine 29.7.2, Linux containers; PostgreSQL 16; base image Python 3.12-slim digest `6b25cbe6577518889d553cdd5a5da97d259348d8f6e45b527dd731caaba27a07`. Không đổi dependency/lock hoặc cấu trúc API/DB.

## Còn cần trên cụm thật

1. Điền endpoint/UUID/AZ/flavor/route/SG thực và xác nhận đủ quota/RAM tính cả App cũ, DB và amphora.
2. Validate template bằng Heat API, boot từ private image đã chuẩn bị, kiểm tra cloud-init và shared storage.
3. Xác nhận metric `cpu`, `rate:mean`, archive policy/granularity, dimension từng AZ và native Heat signal có trust hoạt động.
4. Sau khi bật alarm có kiểm soát, thu timeline scale-out/scale-in cùng HTTP/Locust; chỉ khi đó mới kết luận autoscaling hoạt động.
