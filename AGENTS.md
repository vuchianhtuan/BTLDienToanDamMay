# Hướng dẫn cho coding agent

Khi được yêu cầu chạy, mở hoặc kiểm tra phần TV2, đọc [AGENTS_TV2.md](AGENTS_TV2.md), đặc biệt mục 8 dành cho agent, trước khi thực hiện.

- Hướng dẫn này phân biệt truy cập lab đã triển khai, chạy code local và vận hành lab với quyền quản trị.
- Script truy cập: `scripts/connect-lab.ps1`; script kiểm tra chỉ đọc: `scripts/check-lab.ps1`.
- Cấu hình riêng: `deploy/tv2/lab-access.json`, tạo từ file mẫu khi chưa tồn tại; cấu hình riêng và credential giữ ngoài Git.
- Quy trình phát triển và kiểm thử ứng dụng chung nằm trong [CONTRIBUTING.md](CONTRIBUTING.md).
