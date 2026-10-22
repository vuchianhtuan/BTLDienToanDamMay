# API contract phiên bản 1

Backend, frontend và load test dùng tài liệu này làm điểm thống nhất. Thay đổi contract cần được review cùng các nơi gọi API. Bản chạy có OpenAPI tại `/openapi.json` và Swagger tại `/docs`.

## Quy ước

- Base URL local: `http://localhost:8000`.
- Khi `APP_API_KEY` được cấu hình, gửi `X-API-Key` trên mọi `/api/*`. Sai/thiếu key trả 401. `/`, `/assets/*`, `/health/*`, `/docs` và `/openapi.json` không yêu cầu key.
- Đây là kho tệp dùng chung, chưa có tài khoản/ownership từng người.
- Metadata là JSON; thời gian theo ISO 8601, frontend tự chuyển múi giờ để hiển thị.
- Lỗi HTTP có dạng `{"detail":"mô tả"}`. Lỗi validation 422 có `detail` là mảng.
- ID là UUID do server sinh, không phải filename. Không sử dụng đường dẫn local của server.

## Upload

`POST /api/files?filename=example.txt`

Body là **raw file bytes**. Header khuyến nghị `Content-Type: application/octet-stream`. Không dùng multipart/FormData vì server sẽ coi toàn bộ body là nội dung tệp. Giới hạn mặc định 25 MiB; đọc giá trị thực tại `/health/ready`.

Trả 201 với các trường:

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "filename": "example.txt",
  "size": 12,
  "sha256": "64 ký tự hex",
  "created_at": "2026-10-22T10:00:00+00:00"
}
```

Ví dụ minh họa schema, không phải kết quả chạy thật. `size` tính theo byte; tệp rỗng được chấp nhận. Tên trùng tạo ID mới. Tên có path bị rút về basename; tên rỗng/ký tự điều khiển bị từ chối. Lỗi 400 cho tên/header không hợp lệ, 413 cho quá giới hạn, 503 cho storage/database lỗi.

## Danh sách

`GET /api/files?offset=0&limit=50`

Trả 200 và mảng metadata như upload. Mới nhất trước, sau đó ID để sắp xếp ổn định. `offset >= 0`, `1 <= limit <= 200`. Không có trường total trong contract v1. Danh sách rỗng là `[]`.

## Download

`GET /api/files/{id}/download`

Trả 200 với body nhị phân, `Content-Type: application/octet-stream` và `Content-Disposition: attachment; filename*=UTF-8''...`. Frontend cần dùng response Blob nếu gửi API key; không mở nội dung HTML của tệp trong trang.

404 nếu không có metadata; 422 nếu ID không phải UUID; 503 nếu không đọc được object từ đầu. Nếu storage mất kết nối giữa một response đã bắt đầu, client có thể nhận stream bị ngắt; chỉ báo thành công khi download hoàn tất.

## Verify

`POST /api/files/{id}/verify`, không có request body.

Trả 200 với `id`, `filename`, `intact` (boolean), `expected_sha256`, `actual_sha256`, `expected_size`, `actual_size`, `verified_at`.

`intact=true` khi cả SHA-256 và size đọc lại từ storage khớp metadata. Nội dung khác trả **200 và `intact=false`**, không phải 500. Storage không đọc được trả 503; không thể kết luận toàn vẹn. Hash nằm trong cùng database, chưa có cơ chế chống sửa cả metadata và object.

## Health

- `GET /health/live`: 200 `{"status":"ok"}` khi tiến trình phản hồi.
- `GET /health/ready`: 200 gồm `status=ready`, `storage=local|swift`, `max_file_bytes`; 503 nếu kiểm tra database/storage thất bại.

## Storage contract cho người phát triển adapter

`app/storage/base.py` mô tả `ObjectStorage`. `put(key, source, size)` đọc source từ đầu và ghi object; `chunks(key)` yield byte chunks, là generator có thể đóng; `delete(key)` dùng để bù khi ghi metadata thất bại; `check()` kiểm tra khả dụng hoặc raise exception.

Test adapter không cần OpenStack bằng fake transport/injected storage. Trước khi báo hoàn thành Swift, vẫn phải thử upload/download/verify với Keystone/Swift thật.
