# Tích hợp TV3 và lab TV2 - 28/10/2026

Nhánh local: `integration/tv3-tv2-handoff-20261028`, lấy nền `origin/feat/tv3-handoff` tại `fe4d7a6`, merge `origin/Truong` tại `6ed80f1`. Giữ nguyên nhánh gốc và main. Đây là bản mã nguồn ghép, không tự triển khai lên lab đang chạy.

## Có gì mới từ hai bạn

- TV3 handoff: UI chi tiết/copy hash, test frontend, Locust semantic/streaming/final summary, kit elasticity JSON (luồng chính), YAML cũ vẫn giữ riêng.
- Trường/TV2: runbook triển khai và rollback, bằng chứng Swift + PostgreSQL trên Cinder của lab riêng, script SSH tunnel và kiểm tra chỉ đọc. Theo tài liệu, lab hiện chỉ có một compute và một App VM; không phải cụm hai AZ/LB/autoscaling đã hoàn tất.
- Hai conflict README và `.dockerignore` được ghép có chủ đích: giữ hướng dẫn TV3 và TV2, loại cả cấu hình riêng lab và credential elasticity khỏi build context. Backend/API/schema không bị sửa.

## Việc đã làm tiếp

- Thêm runner Locust trên host `scripts/run_remote_loadtest.py` cho tunnel Windows/URL LB, bắt buộc fixture UUID, API key từ môi trường, báo cáo local có commit và final counters. Không upload lặp, không tự tạo tunnel/deploy hay thay hạ tầng.
- `check-lab.ps1` kiểm tra asset mới `api-client.js`, verify đúng kiểu boolean, ID/hash/size khớp metadata, không chỉ kiểm tra trường intact.
- Smoke workload ghi log sau khi subprocess kết thúc để tránh giữ file handle làm cleanup lỗi trên Windows.
- Smoke live mô tả kết quả theo backend được cấu hình, không tự gắn nhãn PostgreSQL khi chạy SQLite.
- CI nhận push nhánh `integration/**`; hướng dẫn chạy tải qua tunnel trong `loadtest/README.md`.

## Kiểm chứng của bản ghép trên máy này

- Windows/Python 3.13, Node trên host; SQLite và local storage tạm, không phải Docker/PostgreSQL hay lab thật.
- Pytest ứng dụng/JSON/Locust/runner/PowerShell 55/55 đạt (1 cảnh báo deprecation có sẵn); test giao diện Node 17/17 đạt; suite YAML 14/14 đạt; JSON lint và YAML validator đạt. Test PowerShell gọi script thật qua HTTP giả và từ chối intact sai kiểu/hash lệch/false.
- `tests/integration_local_smoke.py`: API tạm, smoke upload/list/download/verify, Locust thật trường hợp khỏe; ca không fixture/401/verify sai/download hỏng đều có failure và exit 1; runner host 6 giây đạt.
- Smoke workload xác nhận dữ liệu bị sửa, mất object, sai key, thiếu/sai UUID; subprocess/API tạm được dừng khi kết thúc.
- Không có Docker trong PATH; chưa chạy CI Linux hoặc build/deploy cloud cho commit tích hợp này. Không dùng bằng chứng cũ của bạn khác thay kết quả vừa chạy.

## Bước tiếp theo trên lab thật

1. Trường cung cấp endpoint hiện tại, SSH user/fingerprint, cấp public key của chính thành viên và API key riêng. Tạo `deploy/tv2/lab-access.json` từ mẫu; chưa có file cấu hình riêng trên máy này, không đoán endpoint từ evidence cũ.
2. Mở `scripts/connect-lab.ps1`, kiểm tra `scripts/check-lab.ps1 -CheckApi`, xác nhận readiness Swift. Chỉ mở tunnel thì chưa cần bật Ubuntu VMware local.
3. Thống nhất phiên đo tải và fixture trước khi chạy profile light qua tunnel. Kết quả chỉ chứng minh API của lab TV2; SSH/WAN ảnh hưởng số đo.
4. TV1 chốt provider/AZ/network/quota/metric; TV2 cung cấp golden image/shared data cho thêm app. Sau đó TV3 mới deploy LB/Heat/Aodh theo runbook, thử hai backend và metric-driven scale thật.

Tham khảo `AGENTS_TV2.md` cho truy cập/triển khai có quyền và `docs/TV3_HANDOFF.md` cho contract TV3. Không dùng credential quản trị của người khác; không tự cập nhật App VM chung khi chưa thống nhất phiên triển khai.
