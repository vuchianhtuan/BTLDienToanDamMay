# Minh chứng dữ liệu TV2 cho bài nộp cuối kỳ

Rà soát ngày 19/11/2026 theo phần Trường TV2 trong `FINAL_SUBMISSION_CHECKLIST.md` do nhóm cung cấp. Tài liệu này tập hợp bằng chứng dữ liệu hiện có và các phép kiểm tra còn cần phiên lab. Chưa đủ bằng chứng để xác nhận hoàn tất toàn bộ phần TV2.

## Phiên bản mã giao nộp

Đã fetch GitHub ngày 19/11. `origin/main` đang ở `3f1a25723d4aac55776a3dac1ede3582526bf03a`, đúng mốc trong checklist, đã chứa nhánh bàn giao TV3 và tích hợp hạ tầng TV1. Nhánh làm việc TV2 `tv2/final-data-evidence-20261119` được tạo từ mốc này.

GitHub API xác nhận lượt CI `44558990932` có `status=completed`, `conclusion=success`, chạy tại `9083184d391a5d542e1fab017ec12d5c2bc2be14`. Cây mã của commit đó và `main` có cùng tree SHA `7dcecf81ba0cad01fa4942f84b0b84186a5fd95d`. [Docker CI](https://github.com/vuchianhtuan/BTLDienToanDamMay/actions/runs/44558990932)

Hai commit local trước đây `9e36544` và `bbb610b` chưa nằm trong lịch sử `main`. Các sửa riêng về HTTP 503 khi truy vấn database thất bại và ngưỡng CPU mặc định tại `bbb610b` chưa có trong bản giao nộp. Nhánh TV2 này giữ nền `main` theo checklist để thu minh chứng. Lượt nghiệm thu cloud 13/11 dùng container `file-integrity:4650bd0`.

## Tệp mẫu và chuỗi bằng chứng đã có

Chọn fixture TV2 từ lượt kiểm tra lúc **09:58:30 UTC ngày 28/10/2026**. [Báo cáo gốc](../deploy/tv2/evidence/verification-20261028.json)

| Trường | Giá trị |
| --- | --- |
| UUID tệp | `aa49cb61-fe7e-4eba-bf4e-46874d13ac0e` |
| SHA-256 | `f019ae93c4afda3fd63c701abec8a9c3421f58371ec398b124cb6b4eae98226a` |
| Nội dung | `TV2 real Swift and PostgreSQL integration` và một ký tự xuống dòng LF |
| Kích thước | 42 byte |
| DB VM tại lượt kiểm tra | `48819692-232a-448b-824c-7b5f2c1a3b24` |
| Cinder volume tại lượt kiểm tra | `82f4a4cf-3dca-437a-a521-758be483a67e` |

[Tệp mẫu](evidence/tv2-final/sample.txt) được tái tạo từ payload cố định trong [script kiểm tra TV2](../deploy/tv2/verify_tv2.py). Đã tính SHA-256 trên máy và đối chiếu khớp báo cáo lịch sử. Tệp được ghi dạng byte với LF để giữ đúng hash. Đây là bản tái tạo phục vụ đối chiếu, chưa tải lại từ cloud trong phiên 19/11. [Manifest tổng hợp](evidence/tv2-final/manifest.json)

| Yêu cầu dữ liệu | Minh chứng hiện có | Kết luận |
| --- | --- | --- |
| Upload/list/download/verify cùng UUID/hash | Báo cáo 28/10 ghi tất cả phép kiểm tra đạt trên App A | Đã có bằng chứng lịch sử qua App A |
| Swift object cùng tệp | Script đọc object theo UUID fixture, đối chiếu byte với payload; báo cáo ghi đạt | Đã có bằng chứng lịch sử |
| PostgreSQL UUID/hash | Script SELECT metadata theo cùng UUID, đối chiếu hash/size; báo cáo ghi đạt | Đã có bằng chứng lịch sử, cần row gốc hoặc thu lại để minh họa báo cáo |
| PostgreSQL trên Cinder | Script kiểm tra `SHOW data_directory` và mount `/dev/vdb`; báo cáo có DB VM/volume ID | Đã có bằng chứng lịch sử, cần attachment hiện tại để chốt |
| Cùng tệp qua VIP | Log gốc do người dùng cung cấp có VIP, readiness Swift, hash `0341dcca4d64a4c75059dbe80bb3117435caf21884439d633a9c7676d898b5cd` và `VERIFY intact=true` | Đã nhận log gốc, chưa có UUID để nối Swift/PostgreSQL |

Các phép thử sửa/xóa object trong script lịch sử chỉ mô tả lần kiểm tra 28/10. Phiên rà soát này chưa thực hiện lại các thao tác đó. [Biên bản VIP 13/11](evidence/autoscaling-acceptance-20261113.md)

[Log VIP sau scale-in](evidence/tv2-final/vip-scale-in-20261113.txt) đã nhận từ Downloads ngày 19/11, gồm bốn dòng. Log không ghi UUID, tên tệp, kích thước hoặc timestamp bên trong. Ngày 13/11 được xác định từ tên tệp và biên bản liên quan. Bước tiếp theo là tìm row PostgreSQL theo hash rồi xác minh đúng Swift object của UUID thu được, hoặc lấy log chi tiết bổ sung. Chưa thể ghép hai hash khác nhau thành một chuỗi minh chứng cùng tệp.

## Thu minh chứng còn thiếu trong phiên lab

Sau khi đăng nhập lại và xác minh endpoint, dùng một trong hai fixture theo thứ tự ưu tiên sau.

1. Lấy UUID tương ứng hash của lượt VIP ngày 13/11 từ log gốc, đối chiếu Swift object và row PostgreSQL của đúng UUID đó. Kiểm tra các log `tv1-auto-vip-scale-in-20261113.txt` và `tv1-auto-members-out-20261113.txt` đang do nhóm quản lý. Tận dụng bản ghi cũ khi có đủ liên kết tới cùng tệp.
2. Nếu thiếu log gốc, thử đọc lại fixture 28/10 qua VIP. Thu list/download/verify, tính lại hash và lấy bằng chứng Swift/PostgreSQL/Cinder. Bằng chứng upload cũ cần ghi rõ endpoint App A.
3. Nếu cần một bộ hoàn toàn cùng phiên qua VIP, upload một bản sao tệp mẫu duy nhất qua VIP, ghi UUID mới rồi dùng UUID đó xuyên suốt list/download/verify, Swift object và row PostgreSQL. Giữ lại tệp giả có nhãn phục vụ demo.

Chỉ trích xuất các trường cần đưa vào báo cáo. API key, application secret, token và mật khẩu giữ tại máy quản trị. Không dùng shell tracing hoặc ghi toàn bộ file môi trường vào log.

Các đầu ra cần lưu cùng timestamp gồm metadata API, kết quả verify, hash/size download, hash/size object Swift, row PostgreSQL với `id, filename, size, sha256`, `SHOW data_directory`, mount của thư mục PostgreSQL và Cinder attachment tới đúng DB VM. Khi chạy live, xác nhận PostgreSQL, Swift và VPN sẵn sàng trước khi thử luồng tệp.

## Credential pilot

Biên bản 13/11 ghi đã dọn stack, alarm, metric, relay và đường hầm thử. Biên bản chưa nêu ID hoặc bằng chứng thu hồi/hết hạn credential DB/Swift pilot. Chưa xác nhận mục credential pilot đã hoàn tất.

Trong phiên lab, cần danh sách credential pilot do người triển khai lưu, rồi kiểm tra từng application credential bằng danh tính có quyền, ghi ID, thời điểm hết hạn hoặc kết quả không còn tồn tại. Với role PostgreSQL riêng cho pilot, kiểm tra `rolcanlogin`, `rolvaliduntil` và tình trạng còn được workload sử dụng. Credential ứng dụng đang phục vụ hai backend cần được xác định rõ trước khi xử lý credential pilot. Phiên rà soát này chưa thu hồi hay thay đổi credential.

## Trạng thái tiếp tục công việc

Cả profile AWS `tv2-lab` và `fresh-canvas-tv3` đều báo phiên hết hạn trong lần kiểm tra 19/11. Cần đăng nhập lại và đường truy cập hiện hành để hoàn tất phần VIP, Cinder attachment, credential pilot và readiness. Đã nhận log VIP sau scale-in từ người dùng, đang thiếu UUID và dữ liệu đối chiếu từ Swift/PostgreSQL.

Bộ dữ liệu này phục vụ phần TV2. Nội dung kiến trúc/quyền TV1, failover/autoscaling/chi phí TV3 và video toàn nhóm được đối chiếu qua tài liệu nhóm khi ghép báo cáo.
