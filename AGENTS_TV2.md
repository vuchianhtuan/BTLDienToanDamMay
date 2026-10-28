# AGENTS_TV2 Hướng dẫn chạy phần TV2 cho thành viên và agent

Tài liệu này dành cho thành viên nhóm và coding agent hỗ trợ họ chạy phần TV2 trên lab OpenStack: upload, download và verify SHA-256, lưu tệp trong Swift và metadata trong PostgreSQL trên Cinder. Thành viên mở SSH tunnel từ máy mình tới ứng dụng đã triển khai; không cần Docker, Python, PostgreSQL hoặc DevStack trên máy cá nhân để dùng bản lab. Agent bắt đầu từ mục 8 để chọn đúng vai trò và quy trình.

**Điều kiện:** người quản lý lab đã bật EC2, hai VM App/DB hoạt động, cấp quyền SSH và API key cho thành viên. Merge code chỉ mang về script và tài liệu, không tự cấp quyền hoặc bật lab.

## 1 Ai cần làm gì

| Người | Chuẩn bị một lần | Mỗi lần sử dụng |
|---|---|---|
| Thành viên | Có code/script, SSH key riêng, cấu hình kết nối và API key | Chạy tunnel, mở web, nhập API key |
| Trường hoặc người quản lý lab | Thêm public key của thành viên, cho phép kết nối SSH, cấp endpoint/API key/fingerprint | Bật EC2 và hai guest; kiểm tra readiness; báo endpoint mới nếu IP đổi |

Người quản lý không cần mở tunnel trên laptop của mình cho người khác. Sau khi lab sẵn sàng, có thể đóng phiên SSH và tắt laptop cá nhân; EC2 và hai guest vẫn phải chạy trong suốt thời gian thành viên sử dụng.

## 2 Thành viên chuẩn bị một lần

### 2.1 Lấy code và kiểm tra SSH

Sau khi phần TV2 đã được merge vào nhánh chung, cập nhật repo theo quy trình Git của nhóm. Giữ hoặc commit công việc đang sửa trước khi cập nhật; mở PowerShell tại thư mục có `compose.yaml` và `scripts/`.

Kiểm tra:

```powershell
ssh -V
Test-Path ./scripts/connect-lab.ps1
```

Lệnh thứ hai cần trả `True`. Nếu chưa có script, nhánh hiện tại chưa chứa phần bàn giao TV2. Nếu chưa có `ssh`, cài OpenSSH Client trong Optional Features của Windows.

### 2.2 Tạo key SSH riêng và xin quyền

Nếu chưa có key dành cho lab:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\btl_lab_ed25519"
Get-Content "$env:USERPROFILE\.ssh\btl_lab_ed25519.pub"
```

Nếu key đã tồn tại thì giữ nguyên, không ghi đè. Chỉ gửi nội dung file **`.pub`** cho người quản lý lab để thêm quyền. File không có đuôi `.pub` là private key, giữ trên máy mình; không gửi cho nhóm hoặc commit vào Git.

Nhận lại từ người quản lý: endpoint EC2 đang dùng, tên tài khoản SSH, fingerprint SSH và API key. API key được gửi qua kênh riêng, không ghi vào repository. Không cần nhận credential Keystone hoặc mật khẩu PostgreSQL.

### 2.3 Tạo cấu hình riêng

Chạy ở thư mục gốc repo; nếu file đích đã có thì sửa file hiện tại thay vì chép đè:

```powershell
Copy-Item ./deploy/tv2/lab-access.example.json ./deploy/tv2/lab-access.json
notepad ./deploy/tv2/lab-access.json
```

Điền cấu hình:

```json
{
  "ec2_host": "IP_HOAC_DNS_DO_NGUOI_QUAN_LY_CUNG_CAP",
  "ssh_user": "ubuntu",
  "ssh_key_path": "~/.ssh/btl_lab_ed25519",
  "known_hosts_path": "",
  "app_host": "10.42.0.21",
  "app_port": 8000,
  "local_port": 18000
}
```

Thay giá trị `ec2_host` bằng endpoint thật, không kèm `http://` hoặc cổng. `ssh_user` phải đúng tài khoản được cấp. `~` trỏ tới home của chính người chạy; nếu dùng key khác thì sửa `ssh_key_path`. Để trống `known_hosts_path` để SSH dùng file mặc định của mình. Cấu hình `app_host:app_port` hiện tại là đích private từ EC2, không phải địa chỉ truy cập trực tiếp từ Windows.

`lab-access.json` được loại khỏi Git và Docker build context. Không thêm API key vào file mẫu hoặc commit cấu hình riêng của mình.

## 3 Thành viên chạy mỗi lần

### 3.1 Mở tunnel

Sau khi người quản lý báo lab sẵn sàng, mở PowerShell tại thư mục gốc repo:

```powershell
./scripts/connect-lab.ps1
```

Lần đầu SSH có thể hỏi xác nhận host fingerprint: so sánh với fingerprint người quản lý cung cấp rồi xác nhận. Nếu key có passphrase, nhập passphrase của key mình. **Giữ terminal này mở**; việc terminal chờ sau khi kết nối là bình thường.

### 3.2 Mở ứng dụng và thử chức năng

Mở trình duyệt:

- Giao diện: http://127.0.0.1:18000
- API docs: http://127.0.0.1:18000/docs
- Trạng thái: http://127.0.0.1:18000/health/ready

Nhập API key được cấp vào ô API key trên giao diện, tải lại danh sách. Chọn một tệp demo nhỏ, upload, bấm Verify rồi Download. Kết quả mong đợi: trạng thái `Sẵn sàng · swift`, verify báo `TOÀN VẸN`, tệp tải xuống giống tệp ban đầu. Các thành viên đang dùng chung database và Swift nên sẽ thấy dữ liệu lab dùng chung.

### 3.3 Kiểm tra tự động

Mở PowerShell thứ hai tại thư mục gốc repo, giữ tunnel ở terminal thứ nhất:

```powershell
./scripts/check-lab.ps1 -CheckApi
```

Nhập API key khi script hỏi; ký tự sẽ được ẩn. Kết quả mong đợi:

```text
PASS: readiness (Swift), frontend and static assets.
PASS: authenticated API and SHA-256 verification of one existing file.
```

Nếu chưa có tệp, script chỉ xác nhận API có quyền truy cập và thông báo chưa có tệp để verify. Có thể chạy `./scripts/check-lab.ps1` không kèm `-CheckApi` để chỉ kiểm tra readiness và assets. Script kiểm tra không upload, sửa/xóa object, dừng dịch vụ hoặc reboot VM.

### 3.4 Kết thúc

Nhấn `Ctrl+C` trong terminal chạy tunnel. Chỉ tunnel trên máy thành viên được đóng; các thành viên khác và dịch vụ AWS vẫn chạy. Không chạy lệnh dừng lab khi người khác đang sử dụng.

## 4 Trường cần chuẩn bị một lần trước khi nhóm sử dụng

1. Nhận public key `.pub` của từng thành viên. Đăng nhập EC2 bằng key quản trị của mình; với tài khoản lab `ubuntu`, mở `~/.ssh/authorized_keys` và thêm mỗi public key thành một dòng riêng. Giữ nguyên các dòng đang có, không thêm private key. Nếu dùng tài khoản SSH khác, cấu hình key và quyền forward cho tài khoản đó rồi thông báo đúng `ssh_user`.
2. Bảo đảm security group của EC2 cho phép SSH TCP 22 từ đường kết nối/IP của thành viên. Nếu họ đổi mạng và public IP thay đổi, có thể cần cập nhật nguồn được phép. Không cần public cổng PostgreSQL, Swift hoặc gắn floating IP cho App VM để dùng tunnel này.
3. Cung cấp endpoint EC2 và `app_host:app_port` hiện tại (`10.42.0.21:8000`). Trên EC2, lấy fingerprint để thành viên đối chiếu:

   ```bash
   ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
   ```

4. Cấp API key qua kênh riêng. Người quản lý hiện có key trong file riêng `D:\aws\btl-tv2-20261026\access.json`; chỉ lấy giá trị `api_key` để cấp cho nhóm. Đây là file trên máy người quản lý, không phải file thành viên phải có. Không gửi SSH private key EC2, token hoặc credential Keystone/DB.
5. Cho một thành viên thử kết nối bằng **key riêng của họ**, mở UI và chạy `check-lab.ps1 -CheckApi` một lần để xác nhận quyền. Các kiểm tra trước đó dùng key của người vận hành; quyền của từng thành viên cần được cấp riêng.

Các bước này là hướng dẫn cấu hình; việc tạo tài liệu/merge code chưa tự thêm key của thành viên hoặc thay security group.

## 5 Trường cần làm mỗi lần nhóm muốn chạy

1. Trong AWS Console, bật đúng EC2 chứa lab; đợi trạng thái `Running`, các status check đạt và SSH kết nối được. Lấy public IP/DNS hiện tại.
2. Từ PowerShell của mình, đăng nhập bằng key quản trị. Thay các giá trị trong dấu nháy bằng key/endpoint thật:

   ```powershell
   ssh -i 'DUONG_DAN_KEY_QUAN_TRI.pem' ubuntu@IP_HOAC_DNS_HIEN_TAI
   ```

3. **Tại shell EC2**, chạy:

   ```bash
   btl-tv2 start
   btl-tv2 status
   ```

   Đợi hai VM App/DB khởi động. Kết quả status cần có readiness:

   ```json
   {"status":"ready","storage":"swift","max_file_bytes":26214400}
   ```

   Nếu chưa ready, đợi rồi chạy lại `btl-tv2 status`; xem `btl-tv2 logs` nếu vẫn lỗi. Chỉ báo lab sẵn sàng khi readiness đạt. Không chạy lại DevStack chỉ để bật ứng dụng.

4. Gửi cho nhóm thông báo lab sẵn sàng và endpoint hiện tại. Nếu IP đã đổi, thành viên sửa `ec2_host` trong JSON; không cần sửa code hoặc tạo commit mới.
5. Giữ EC2 và hai guest chạy trong suốt phiên. Có thể đóng SSH hoặc tắt laptop của mình sau khi lab đã sẵn sàng. Khi nhóm dùng xong mới thống nhất dừng lab/EC2.

Người quản lý không cần chạy tunnel cho từng người, không cần đọc/gửi lại API key mỗi lần nếu key chưa đổi, và không cần build lại app chỉ để họ mở bản đã triển khai.

## 6 Khi có lỗi

| Hiện tượng | Thành viên làm gì | Người quản lý cần kiểm tra |
|---|---|---|
| Không tìm thấy script | Kiểm tra đang ở gốc repo và đã có phần TV2 sau merge | Branch đã bàn giao đầy đủ chưa |
| PowerShell chặn script | Nếu máy cho phép, đặt policy cho riêng terminal: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, rồi chạy lại | Nếu máy do trường/công ty quản lý, theo policy của máy |
| `Permission denied (publickey)` | Đối chiếu `ssh_user`, `ssh_key_path`, dùng đúng key | Public key đã thêm đúng tài khoản chưa |
| SSH timeout | Kiểm tra endpoint và kết nối mạng | EC2 đang chạy, IP mới, security group cho phép nguồn SSH |
| Host key thay đổi | Dừng và đối chiếu fingerprint mới trước khi cập nhật `known_hosts` | Xác nhận có đổi server/key hay không |
| Cổng 18000 bị chiếm | Dùng `./scripts/connect-lab.ps1 -LocalPort 18001`; mở web tại cổng 18001 | Không cần đổi cổng App VM |
| Web chưa ready hoặc connection refused | Giữ tunnel, kiểm tra đúng URL/cổng; báo người quản lý | `btl-tv2 status`, hai guest, PostgreSQL, Swift và container app |
| API trả 401 | Nhập lại đúng API key vào UI/script | Key đang cấp có đúng với bản triển khai không |

Nếu dùng cổng khác, kiểm tra theo đúng cổng đó:

```powershell
./scripts/check-lab.ps1 -BaseUrl http://127.0.0.1:18001 -CheckApi
```

## 7 Phạm vi chạy và code sau merge

Tunnel mở **bản đã triển khai trên AWS**, không chạy code mới từ máy thành viên. Nếu nhóm sửa UI/backend rồi merge, cần triển khai phiên bản đó lên App VM trong phiên tích hợp theo [hướng dẫn triển khai](deploy/README.md). Không tự chạy đồng thời nhiều lần triển khai trên lab đang có người demo.

Muốn tự phát triển và chạy code mới khi EC2 của Trường tắt: dùng [hướng dẫn local](CONTRIBUTING.md), hoặc `./scripts/start.ps1` khi Docker Desktop đã chạy. Bản local mặc định dùng storage local và PostgreSQL riêng, không phải bằng chứng Swift/Cinder trên OpenStack.

Chi tiết mô hình, kiểm thử quản trị và bằng chứng thật nằm tại [tài liệu lab TV2](deploy/tv2/README.md). Không cần chạy các lệnh `test-all`, `reboot-test` hoặc dừng DB để chỉ sử dụng giao diện/API.

## 8 Quy trình dành cho agent của thành viên khác

### 8.1 Xác định phạm vi và đầu vào

Mặc định tác vụ "chạy phần TV2", "mở lab" hoặc "kiểm tra kết nối" của thành viên là mở tunnel tới bản đang triển khai trên AWS và kiểm tra API. Nếu yêu cầu là sửa/chạy code mới trên máy thành viên, dùng quy trình local ở mục 7; nếu yêu cầu là triển khai hoặc vận hành lab với quyền quản trị, áp dụng checklist người quản lý ở mục 4–5 theo phạm vi đã được người dùng giao.

| Đầu vào | Nguồn lấy | Xử lý khi thiếu |
|---|---|---|
| Gốc repository | Thư mục chứa tài liệu này, `scripts/` và `compose.yaml` | Xác định đường dẫn trước khi chạy lệnh |
| Endpoint, SSH user, App private host/port | `deploy/tv2/lab-access.json` của thành viên | Tạo từ file mẫu, hỏi endpoint hiện tại; không đoán IP từ log/bằng chứng cũ |
| SSH private key | `ssh_key_path` do chính thành viên cấu hình | Yêu cầu người dùng tạo key và gửi `.pub` cho người quản lý theo mục 2.2 |
| Quyền SSH | Người quản lý thêm public key vào lab | Báo cần cấp quyền một lần; merge code không tự cấp quyền |
| API key | Biến môi trường `APP_API_KEY` nếu đã được cấp, hoặc người dùng nhập trực tiếp trong terminal/UI | Hướng dẫn người dùng nhập riêng; không yêu cầu dán key vào chat hoặc tài liệu |

Không cần file trên ổ `D:` của Trường để chạy từ máy thành viên. Đường dẫn ở mục 4 chỉ giúp chính người quản lý tìm key trên máy của họ. Không tìm hoặc sao chép private key EC2/credential của người khác để bỏ qua bước cấp quyền.

### 8.2 Thực hiện theo thứ tự

1. Đọc `scripts/connect-lab.ps1`, `scripts/check-lab.ps1` và cấu hình mẫu nếu cần xác minh tham số. Chạy các lệnh từ gốc repository. Giữ cấu hình riêng đã có; chỉ tạo `lab-access.json` từ mẫu khi file chưa tồn tại, rồi điền giá trị do thành viên cung cấp. Không ghi secret vào mã nguồn.
2. Kiểm tra cú pháp/cấu hình trước, chưa mở kết nối:

   ```powershell
   ./scripts/connect-lab.ps1 -DryRun
   ```

   Lệnh cần trả executable SSH, danh sách argument và URL local đúng cấu hình. Đây mới là kiểm tra tham số, chưa chứng minh SSH hay ứng dụng hoạt động.
3. Chạy `./scripts/connect-lab.ps1` trong terminal/session có thể giữ hoạt động. Lệnh cố ý chạy foreground và chờ; **không đợi lệnh tunnel hoàn tất mới chạy bước kiểm tra**. Nếu công cụ hỗ trợ session, giữ ID/handle của session; dùng terminal/session thứ hai để kiểm tra. Nếu phải tạo tiến trình nền trên Windows, dùng `Start-Process -WindowStyle Hidden`, lưu PID/log trong thư mục tạm ngoài Git và giữ thông tin để dọn đúng tiến trình mình tạo. Không mở nhiều tunnel cùng cổng.
4. Lần đầu gặp fingerprint hoặc key có passphrase, cần người dùng xử lý tương tác SSH. Đối chiếu fingerprint với người quản lý; giữ cơ chế kiểm tra host key của script. Nếu công cụ không hỗ trợ nhập tương tác, hướng dẫn người dùng chạy tunnel trong terminal của họ, rồi tiếp tục kiểm tra qua URL local.
5. Tại terminal/session thứ hai, chạy `./scripts/check-lab.ps1`. Khi API key đã có trong môi trường của chính thành viên hoặc người dùng có thể nhập trực tiếp vào terminal, chạy thêm `./scripts/check-lab.ps1 -CheckApi`. Không đặt API key trong argument dòng lệnh hoặc in ra log. Nếu chưa kiểm tra được API do thiếu key, báo rõ readiness/assets đã đạt nhưng xác thực API chưa được kiểm chứng.
6. Nếu cổng bị chiếm, không dừng tiến trình lạ hoặc tunnel của người khác. Chọn cổng rảnh bằng `-LocalPort`, rồi dùng cùng cổng trong `check-lab.ps1 -BaseUrl` và URL gửi cho người dùng. Nếu readiness cho thấy storage khác Swift, kiểm tra có đang kết nối nhầm bản local hay không.
7. Với yêu cầu mở ứng dụng để người dùng sử dụng, giữ tunnel hoạt động và báo URL/cách đóng. Với yêu cầu chỉ kiểm tra, đóng đúng session/PID tunnel agent vừa tạo sau khi kiểm tra xong. Không đóng tunnel có sẵn hoặc dừng dịch vụ AWS để kết thúc kiểm tra.

### 8.3 Tiêu chí báo kết quả

- Thành công kết nối: tunnel hoạt động, readiness trả `status=ready`, `storage=swift`, frontend/assets tải được.
- Thành công xác thực: `-CheckApi` đọc được danh sách; nếu có tệp thì verify một tệp trả `intact=true`. Nếu không có tệp, báo API đạt và chưa có dữ liệu để verify; không tự tạo dữ liệu chỉ để làm đẹp kết quả.
- Báo URL local thực tế, trạng thái tunnel còn mở hay đã đóng và phần nào chưa kiểm chứng. Không chép nội dung key, token, credential hoặc danh sách dữ liệu cá nhân vào báo cáo.
- Nếu EC2/guest tắt hoặc quyền chưa được cấp, nêu điều kiện còn thiếu và chỉ người quản lý tới mục 4–5. Không khẳng định code lỗi hoặc đã hoạt động chỉ dựa trên các báo cáo lịch sử trong `evidence/`.
- Với yêu cầu truy cập/kiểm tra của thành viên, không chạy `btl-tv2 test-all`, `reboot-test`, dừng DB/EC2 hoặc triển khai code. Các thao tác quản trị chỉ nằm trong phạm vi công việc khi người dùng đã giao tác vụ đó; xem các điều kiện phối hợp nhóm ở [hướng dẫn đóng góp](CONTRIBUTING.md).
