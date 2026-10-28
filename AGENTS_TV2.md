# AGENTS_TV2 Triển khai và sử dụng phần TV2

Đây là tài liệu bàn giao cho agent của các thành viên khác triển khai và kiểm tra phần TV2: FastAPI upload/list/download/verify SHA-256, nội dung tệp trong Swift, metadata trong PostgreSQL trên Cinder. Đọc mục 8 để chọn luồng công việc; **mục 9 hướng dẫn triển khai code từ repo lên App VM**, còn mục 2–3 hướng dẫn dùng ứng dụng đã triển khai qua tunnel. Agent chỉ cần được người dùng chỉ tới file này; không có file AGENTS riêng để đọc tiếp.

Phạm vi triển khai là ứng dụng TV2 trên hạ tầng OpenStack đã có. VM, mạng, Swift/Keystone, PostgreSQL trên volume Cinder và quyền truy cập phải được lab hiện tại hoặc TV1 cung cấp. Repo chưa có bộ tự dựng lại toàn bộ OpenStack từ một EC2 trống. Trên App VM cần Docker Engine và Docker Compose; trên máy thành viên chỉ dùng tunnel thì không cần Docker/Python/PostgreSQL.

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

Với yêu cầu **triển khai TV2**, thực hiện mục 9 để đưa đúng phiên bản code lên App VM và kiểm chứng; mở được tunnel tới bản cũ chưa hoàn thành tác vụ triển khai. Với yêu cầu chỉ mở lab/kiểm tra kết nối, thực hiện mục 2–3 và quy trình bên dưới. Nếu cần chạy code mới trên máy thành viên, dùng local ở mục 7. Các bước vận hành EC2/guest của người quản lý nằm ở mục 4–5. Xác định phạm vi từ yêu cầu người dùng trước khi chạy lệnh.

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

## 9 Triển khai code TV2 bằng agent

### 9.1 Đầu vào và điều kiện triển khai

Agent cần xác định các giá trị sau trước khi thay đổi deployment:

| Đầu vào | Lab TV2 đang có | Khi triển khai trên cụm khác |
|---|---|---|
| Phiên bản nguồn | Commit đã merge mà thành viên yêu cầu triển khai | Chốt commit cụ thể; không dùng một nhánh thay đổi không rõ phiên bản |
| Đường tới App VM | SSH tới EC2, rồi dùng key quản trị guest trên EC2 | SSH trực tiếp hoặc bastion của cụm đích |
| Quyền triển khai | Tài khoản EC2 có `sudo` và được phép dùng key guest; App VM có `sudo`/Docker | Quyền tương ứng do quản lý cụm cấp |
| Backend dữ liệu | Swift và PostgreSQL/Cinder đang hoạt động trong lab | Container Swift, Keystone credential đúng project, DB đã tạo và mount Cinder bền vững |
| Cấu hình bí mật | Tái sử dụng `app.env` từ deployment hiện tại trên App VM | Tạo `deploy/app.env` từ mẫu, nhận secret qua kênh riêng |
| Phối hợp | Thống nhất phiên cập nhật lab vì container app sẽ được tạo lại | Thống nhất với người đang dùng cùng deployment |

Quyền SSH chỉ để dùng tunnel chưa đủ để triển khai. Nếu thành viên thiếu quyền quản trị, yêu cầu người quản lý cấp quyền phù hợp hoặc thực hiện bước triển khai; không mượn private key của người khác. Không cần yêu cầu cấp lại secret nếu đã có `app.env` hợp lệ trên VM.

Giữ nguyên API contract và schema trong lần bàn giao này. Mọi App VM dùng cùng DB/container Swift. VM mới trên cụm khác phải được cho phép kết nối tới PostgreSQL (security group và `pg_hba.conf`), Keystone và Swift; không đổi sang storage local để làm readiness xanh. Nếu chưa có các dịch vụ này, báo rõ phần hạ tầng còn thiếu thay vì khẳng định triển khai cloud đã xong.

### 9.2 Đóng gói đúng commit trên máy thành viên

Chạy PowerShell tại gốc repo, sau khi code đã được merge/cập nhật và working tree sạch. Agent kiểm tra mã thoát sau mỗi lệnh; nếu có thay đổi chưa commit thì lưu/chốt phiên bản trước, vì `git archive HEAD` không mang thay đổi chưa commit.

```powershell
git status --short
$Release = (git rev-parse --short=12 HEAD).Trim()
$Bundle = Join-Path $env:TEMP "tv2-$Release.tar.gz"
git archive --format=tar.gz --output=$Bundle HEAD
$Release
```

Ghi lại `$Release` để dùng cùng giá trị ở các shell tiếp theo. Archive chỉ chứa file được Git theo dõi, không chứa `.env`, `app.env`, key và cấu hình cá nhân đã bị ignore. Trước khi chuyển, xác nhận các file bí mật chưa từng bị theo dõi trong Git.

Với lab hiện tại, thay hai giá trị dưới bằng endpoint và key của **tài khoản được cấp quyền triển khai**:

```powershell
$Ec2Target = 'ubuntu@IP_HOAC_DNS_HIEN_TAI'
$Ec2Key = 'DUONG_DAN_TUYET_DOI_KEY_CUA_NGUOI_TRIEN_KHAI'
scp -i $Ec2Key $Bundle "${Ec2Target}:/tmp/tv2-$Release.tar.gz"
ssh -i $Ec2Key $Ec2Target
```

### 9.3 Chuyển archive từ EC2 tới App VM

Chạy Bash trên EC2. Thay `COMMIT_12_KY_TU` bằng release vừa ghi. Đường dẫn key/known_hosts dưới đây là tài nguyên quản trị đã có **trên EC2 của lab**, không phải file phải lấy từ laptop Trường. Không chạy lại `deploy_guests.py` hoặc format volume để cập nhật code ứng dụng.

```bash
set -euo pipefail
RELEASE=COMMIT_12_KY_TU
[[ "$RELEASE" =~ ^[0-9a-f]{12}$ ]]
APP_IP=$(sudo -n python3 -c 'import json; print(json.load(open("/srv/btl-tv2/state.json"))["app_ip"])')
sudo -n scp -i /srv/btl-tv2/id_ed25519 \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/srv/btl-tv2/known_hosts \
  "/tmp/tv2-$RELEASE.tar.gz" "ubuntu@$APP_IP:/tmp/tv2-$RELEASE.tar.gz"
btl-tv2 app
```

Trên cụm khác, chuyển cùng archive qua đường SSH được cấp tới App VM của cụm đó, rồi thực hiện bước 9.4. Không sử dụng state/key/địa chỉ private của lab Trường cho cụm khác.

### 9.4 Chuẩn bị thư mục release và cấu hình trên App VM

Chạy Bash trên **App VM**, không phải EC2 controller. Dùng một thư mục release mới để giữ lại mã nguồn bản trước; không giải nén đè lên bản đang chạy. Kiểm tra có Docker/Compose và dung lượng build trước:

```bash
set -euo pipefail
RELEASE=COMMIT_12_KY_TU
[[ "$RELEASE" =~ ^[0-9a-f]{12}$ ]]
sudo -n docker info >/dev/null
sudo -n docker compose version
df -h /srv
NEW_ROOT="/srv/file-integrity-releases/$RELEASE"
sudo -n test ! -e "$NEW_ROOT"
sudo -n install -d -m 755 "$NEW_ROOT"
sudo -n tar -xzf "/tmp/tv2-$RELEASE.tar.gz" -C "$NEW_ROOT"
```

Nếu thư mục release đã tồn tại, xác minh nó thuộc lần triển khai nào rồi tiếp tục có chủ đích hoặc chọn thư mục release mới; không xóa đệ quy hoặc ghi đè để né lỗi.

**Nâng cấp lab đang chạy:** tìm deployment đang chạy và giữ image cũ để có thể rollback. Lệnh inspect chỉ lấy đường dẫn/image, không in biến môi trường chứa secret. Lab hiện dùng Compose project `file-integrity-cloud-app`:

```bash
CID=$(sudo -n docker ps -q \
  --filter label=com.docker.compose.project=file-integrity-cloud-app \
  --filter label=com.docker.compose.service=app)
test -n "$CID"
PREVIOUS_DEPLOY=$(sudo -n docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$CID")
PREVIOUS_IMAGE=$(sudo -n docker inspect --format '{{.Image}}' "$CID")
PREVIOUS_IMAGE_REF=$(sudo -n docker inspect --format '{{.Config.Image}}' "$CID")
sudo -n test -f "$PREVIOUS_DEPLOY/app.env"
sudo -n docker image tag "$PREVIOUS_IMAGE" "file-integrity-tv2:rollback-$RELEASE"
sudo -n install -m 600 "$PREVIOUS_DEPLOY/app.env" "$NEW_ROOT/deploy/app.env"
printf 'Previous deployment: %s\nNew deployment: %s\nPrevious image ref: %s\n' \
  "$PREVIOUS_DEPLOY" "$NEW_ROOT/deploy" "$PREVIOUS_IMAGE_REF"
```

Ghi lại ba giá trị đường dẫn/image và release để rollback. Nếu không tìm được đúng một container app của project đích, xác định deployment thực tế trước khi tiếp tục; không chọn ngẫu nhiên container hoặc nhầm project của thành viên khác.

**Triển khai lần đầu trên App VM mới:** bỏ nhóm lệnh tìm bản trước ở trên, thay bằng:

```bash
sudo -n install -m 600 "$NEW_ROOT/deploy/app.env.example" "$NEW_ROOT/deploy/app.env"
sudo -n nano "$NEW_ROOT/deploy/app.env"
```

Điền các biến đúng theo [file mẫu](deploy/app.env.example): `DATABASE_URL` của PostgreSQL thật, `APP_API_KEY`, `OS_AUTH_URL`, `OS_APPLICATION_CREDENTIAL_ID`, `OS_APPLICATION_CREDENTIAL_SECRET`, `OS_REGION_NAME`, `OS_INTERFACE`, `SWIFT_CONTAINER` và `MAX_FILE_BYTES`. URL-encode ký tự đặc biệt trong tài khoản/mật khẩu của `DATABASE_URL`. File Compose luôn chọn `STORAGE_BACKEND=swift`. `CHANGE_ME` và các IP mẫu phải được thay bằng cấu hình thật; secret được nhập trên VM hoặc từ nguồn bí mật được cấp, không đưa vào chat/log/Git.

App VM mới chưa có Docker/Compose cần được người quản lý hạ tầng chuẩn bị trước. Database mới phải có user/database chuyên dụng, thư mục dữ liệu PostgreSQL thực sự trên Cinder và rule cho phép App VM truy cập. Bước chạy app không tự tạo những tài nguyên đó.

### 9.5 Build và chạy bản mới

Tiếp tục trên App VM tại đúng release đã chuẩn bị:

```bash
cd "$NEW_ROOT/deploy"
sudo -n docker compose --project-name file-integrity-cloud-app \
  --env-file app.env -f compose.openstack.yaml config --quiet
sudo -n docker compose --project-name file-integrity-cloud-app \
  --env-file app.env -f compose.openstack.yaml up -d --build --wait --wait-timeout 180
sudo -n docker compose --project-name file-integrity-cloud-app \
  --env-file app.env -f compose.openstack.yaml ps
```

Giữ cùng project name khi cập nhật cùng deployment, tránh tạo project khác tranh cổng 8000. Trên VM mới độc lập có thể dùng project name này nếu chưa có deployment chiếm cổng. `config --quiet` chỉ kiểm tra cấu hình; không dùng `config` không có `--quiet`, `env`, hoặc inspect toàn bộ container để in secret ra log. Nếu cấu hình, build hoặc health check lỗi, dừng luồng và chẩn đoán trước bước tiếp theo.

### 9.6 Kiểm chứng trước khi báo triển khai xong

Trên App VM, tại thư mục deploy của release mới:

```bash
sudo -n docker compose --project-name file-integrity-cloud-app \
  --env-file app.env -f compose.openstack.yaml exec -T app \
  python -m pytest tests -q -p no:cacheprovider
sudo -n docker compose --project-name file-integrity-cloud-app \
  --env-file app.env -f compose.openstack.yaml exec -T app python tests/smoke_live.py
curl -fsS http://127.0.0.1:8000/health/ready
```

Pytest phải đạt toàn bộ ca kiểm thử của commit đang triển khai (bản TV2 hiện có 17 ca). Smoke live tạo một tệp có tiền tố `smoke-`, kiểm tra UI assets, upload/list/download/verify qua API với DB và Swift thật; đây là bước kiểm thử có tạo dữ liệu demo. Readiness cần `status=ready`, `storage=swift`. Khi nâng cấp lab, verify thêm một tệp đã có từ trước để xác nhận bản mới vẫn đọc dữ liệu dùng chung.

Sau đó mở tunnel từ máy thành viên và chạy `check-lab.ps1 -CheckApi` theo mục 3. Agent báo commit/release, App VM đích, thư mục release, kết quả từng kiểm tra, URL truy cập và cách rollback. Bằng chứng lịch sử trong `deploy/tv2/evidence/` chỉ tham khảo, không thay kết quả vừa triển khai. Với cụm khác, đối chiếu thêm data directory/mount PostgreSQL và attachment Cinder; readiness Swift không tự chứng minh DB nằm trên Cinder.

Các lệnh rollout ở mục 9 là quy trình bàn giao; phiên biên soạn tài liệu chưa chạy một rollout mới trên lab hoặc cấp quyền cho thành viên. Agent nhận việc phải chạy và thu kết quả thực tế trên môi trường được giao.

### 9.7 Rollback khi nâng cấp thất bại

Nếu có bản trước và schema không đổi, dùng lại các giá trị đã ghi tại bước 9.4, trên App VM. Giữ nguyên database, Swift và Cinder:

```bash
# Gán lại RELEASE, PREVIOUS_DEPLOY và PREVIOUS_IMAGE_REF nếu đổi shell.
sudo -n docker image tag "file-integrity-tv2:rollback-$RELEASE" "$PREVIOUS_IMAGE_REF"
cd "$PREVIOUS_DEPLOY"
sudo -n docker compose --project-name file-integrity-cloud-app \
  --env-file app.env -f compose.openstack.yaml up -d --no-build --force-recreate --wait --wait-timeout 180
curl -fsS http://127.0.0.1:8000/health/ready
```

Chạy lại kiểm tra API/verify sau rollback và báo rõ release chưa đạt. Không dùng `down -v`, xóa database/container Swift, format Cinder hoặc chạy lại cài đặt PostgreSQL để sửa deployment app. Nếu commit mới có migration schema thì cần quy trình migration/rollback tương ứng; không áp dụng rollback chỉ bằng image một cách máy móc.
