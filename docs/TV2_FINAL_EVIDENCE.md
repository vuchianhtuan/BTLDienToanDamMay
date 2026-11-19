# Minh chứng dữ liệu TV2 cho bài nộp cuối kỳ

Rà soát ngày 19/11/2026 theo phần Trường TV2 trong FINAL_SUBMISSION_CHECKLIST.md do nhóm cung cấp. Đã kiểm tra trực tiếp dữ liệu trên lab TV2, ghép với log VIP ngày 13/11 và xác nhận credential Heat của TV2 hết hạn. Phép thử VIP hiện tại cùng log upload/list qua VIP còn cần Controller hoặc dữ liệu bổ sung từ TV1.

## Phiên bản mã giao nộp

Đã fetch GitHub ngày 19/11. origin/main đang ở commit 3f1a25723d4aac55776a3dac1ede3582526bf03a, đúng mốc trong checklist, đã chứa nhánh bàn giao TV3 và tích hợp hạ tầng TV1. Nhánh TV2 tv2/final-data-evidence-20261119 được tạo từ mốc này.

GitHub API xác nhận lượt CI 44558990932 có status completed và conclusion success, chạy tại 9083184d391a5d542e1fab017ec12d5c2bc2be14. Commit đó và main có cùng tree SHA 7dcecf81ba0cad01fa4942f84b0b84186a5fd95d. [Docker CI](https://github.com/vuchianhtuan/BTLDienToanDamMay/actions/runs/44558990932)

Hai commit local trước đây 9e36544 và bbb610b chưa nằm trong lịch sử main. Các sửa riêng về HTTP 503 khi truy vấn database thất bại và ngưỡng CPU mặc định tại bbb610b chưa có trong bản giao nộp. Nhánh TV2 này giữ nền main theo checklist và bổ sung bộ minh chứng. Lượt nghiệm thu OpenStack 13/11 dùng container file-integrity:4650bd0. Phiên 19/11 thu dữ liệu từ deployment hiện hữu.

## Tệp mẫu chung với log VIP

Đã tìm PostgreSQL theo hash trong log người dùng cung cấp. Có một row khớp. Sau đó đọc Swift object và download/verify qua App A theo UUID của row đó, đối chiếu byte count và SHA-256.

| Trường | Giá trị đã xác minh |
| --- | --- |
| UUID | 42f42fae-4293-4b14-91f9-aace63c74456 |
| Tên tệp | octavia-retest-ba7aed4f0946.txt |
| Kích thước | 94 byte |
| SHA-256 | 0341dcca4d64a4c75059dbe80bb3117435caf21884439d633a9c7676d898b5cd |
| Thời điểm tạo metadata UTC | 2026-11-12T16:17:30.847703+00:00 |
| Swift container | file-integrity |
| Swift object name | 42f42fae-4293-4b14-91f9-aace63c74456 |

[Tệp mẫu tải từ App A](evidence/tv2-final/vip-sample.bin) có đúng 94 byte và hash trên. [Manifest tổng hợp](evidence/tv2-final/manifest.json)

## Chuỗi bằng chứng và kết luận

| Hạng mục TV2 | Bằng chứng | Kết luận |
| --- | --- | --- |
| Readiness qua VIP | Log có URL http://10.0.0.26 và status ready, storage swift | Có bằng chứng lịch sử sau scale-in |
| Download/verify qua VIP | Log ghi SHA-256 như bảng trên và VERIFY intact=true | Hash khớp row và object được kiểm tra lại ngày 19/11 |
| List cùng tệp | API App A ngày 19/11 có UUID này trong trang 200 tệp đầu | Đạt qua App A, còn thiếu log list qua VIP |
| Upload qua VIP | Row metadata cho biết thời điểm tạo; log bốn dòng không ghi HTTP 201 hoặc endpoint upload | Cần log upload gốc hoặc một lượt thu mới qua VIP |
| Swift object | Ngày 19/11 đọc object theo cùng UUID, 94 byte, hash khớp | Đạt |
| PostgreSQL metadata | Row có UUID, filename, size, SHA-256 và created_at | Đạt |
| Download/verify qua App A | Ngày 19/11 download khớp Swift; verify trả đúng UUID, hai hash khớp và intact=true | Đạt |
| PostgreSQL trên Cinder | Data directory /srv/postgresql/data, mount /dev/vdb tại /srv/postgresql | Đạt |
| Cinder attachment | Volume 82f4a4cf-3dca-437a-a521-758be483a67e, 10 GiB, in-use, gắn DB VM 48819692-232a-448b-824c-7b5f2c1a3b24 qua /dev/vdb | Đạt |
| VPN và dữ liệu cho diễn tập | tailscaled active, App A ready với Swift; SELECT PostgreSQL, đọc Swift và verify thành công | Đạt trong phiên kiểm tra 19/11 |

[Báo cáo kiểm tra trực tiếp](evidence/tv2-final/live-data-20261119.json) bắt đầu lúc 16:21:05 UTC ngày 19/11, tương ứng 23:21:05 UTC+7. Báo cáo đã chọn các trường cần thiết và không chứa API key, token, application secret hoặc mật khẩu.

[Log VIP sau scale-in](evidence/tv2-final/vip-scale-in-20261113.txt) được người dùng cung cấp ngày 19/11. Log chỉ có bốn dòng, không ghi UUID, tên tệp, kích thước hoặc timestamp bên trong. Ngày 13/11 được xác định từ tên tệp và [biên bản nghiệm thu](evidence/autoscaling-acceptance-20261113.md). UUID được bổ sung từ truy vấn PostgreSQL theo hash trong phiên 19/11. Hai mốc thu thập được ghi riêng để đối chiếu khi viết báo cáo.

## Credential pilot của TV2

| Thành phần | Kết quả đọc trực tiếp ngày 19/11 |
| --- | --- |
| Keystone application credential | tv2-tv1-heat-eeb3f15c, ID c6d4f179eaa04b1c977fa5628906b87f |
| Keystone expires_at UTC | 2026-11-13T19:06:03.000000 |
| Role PostgreSQL tương ứng | tv2_tv1_heat_eeb3f15c |
| Role rolvaliduntil UTC | 2026-11-13T19:06:03+00:00 |
| Role rolcanlogin | true; thời hạn đã qua |
| Thời gian UTC trên host khi đối chiếu | 2026-11-19T16:21:45Z |

Credential Heat của TV2 và role DB có cùng hậu tố eeb3f15c, cùng hạn hết hiệu lực, trước thời điểm kiểm tra. Kết luận mục này là đã hết hạn. Phiên rà soát chỉ đọc trạng thái và không xoay hoặc thu hồi credential backend đang phục vụ ứng dụng. Không thực hiện phép đăng nhập âm bằng secret pilot trong phiên này. Nếu nhóm đã cấp thêm credential pilot dưới danh tính khác, người cấp cần đối chiếu danh sách đó riêng.

## Dữ liệu TV2 lịch sử kèm theo

Bộ kiểm tra 28/10 có fixture aa49cb61-fe7e-4eba-bf4e-46874d13ac0e, 42 byte, SHA-256 f019ae93c4afda3fd63c701abec8a9c3421f58371ec398b124cb6b4eae98226a. [Báo cáo gốc](../deploy/tv2/evidence/verification-20261028.json)

[Tệp 42 byte tái tạo](evidence/tv2-final/sample.txt) được ghi từ payload cố định trong [script TV2](../deploy/tv2/verify_tv2.py), đã kiểm tra hash khớp. Đây là fixture lịch sử khác với tệp 94 byte ở chuỗi VIP. Các phép thử sửa/xóa object trong script mô tả phiên lịch sử, chưa chạy lại trong phiên thu minh chứng này.

## Phần còn cần phối hợp

Người dùng hiện chỉ có tài khoản TV2. Phiên AWS Sydney chưa được xác thực. Đường SSH Controller 100.127.44.18 qua gateway TV2 bằng key và host key đã bàn giao bị timeout trong bước banner exchange. Vì vậy chưa kiểm tra lại readiness VIP trong phiên 19/11.

Để chốt đủ upload/list/download/verify qua VIP cho cùng tệp, TV1 cung cấp log upload/list gốc của UUID 42f42fae-4293-4b14-91f9-aace63c74456 hoặc thu một bộ API qua VIP trong phiên Controller sẵn sàng. Khi thu mới, dùng một tệp giả duy nhất, ghi UUID/hash rồi đối chiếu Swift, PostgreSQL và Cinder theo quy trình trong báo cáo này.

## Kết thúc phiên lab

EC2 TV2 i-0179850f722838bcf ban đầu stopped. Đã bật máy và hai VM App/DB theo sự đồng ý của người dùng để thu minh chứng. Sau kiểm tra, btl-tv2 stop báo btl-app SHUTOFF và btl-db SHUTOFF. Đã dùng AWS API xác nhận EC2 trở về trạng thái stopped. Thời điểm xác nhận được ghi trong manifest.

Lab cần được bật lại và xác nhận readiness trước buổi diễn tập. Bộ bằng chứng này phục vụ phần TV2 trong checklist nhóm.
