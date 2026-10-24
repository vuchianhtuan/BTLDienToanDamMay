# Mau ban giao TV3 - chua co ket qua cloud

Nguoi phu trach: Dinh Kieu Cong Tuan, 23020875. Dien bang so lieu that; o chua do giu CHUA DO, khong thay bang ket qua local.

## Moi truong / ban giao

| Muc | Gia tri |
|---|---|
| Commit ung dung / template | CHUA DIEN |
| OpenStack / DevStack / Octavia provider | CHUA DIEN |
| AZ-1 / AZ-2, compute thuc te | CHUA XAC MINH |
| Image/flavor/vCPU/RAM, max app, quota amphora | CHUA DIEN |
| Duong di client -> VIP -> app | CHUA KIEM TRA |
| PostgreSQL/Cinder va Swift shared | CHUA KIEM TRA |
| Fixture UUID / bytes / SHA-256 | CHUA DIEN |
| Metric, units, aggregation, sample period, granularity | CHUA DO |
| Nguong cao/thap, periods, cooldown | CHUA CHOT |

## Timeline UTC va bang chung

| Su kien | UTC | Tep log/anh da che secret | Ket qua |
|---|---|---|---|
| 2 backend ONLINE, co request tren ca 2 | CHUA DO | | |
| Dung app A, B van phuc vu; restart A | CHUA DO | | |
| Tai tang / metric vuot nguong | CHUA DO | | |
| Aodh ALARM / Heat create / Nova ACTIVE | CHUA DO | | |
| App thu 3 boot xong / member ONLINE / nhan request | CHUA DO | | |
| Tai giam / alarm low / Heat scale-in | CHUA DO | | |
| Con 2 app tren 2 AZ, fixture cu verify/download dat | CHUA DO | | |

Locust: users/spawn/duration; request/failure; RPS; p50/p95/p99; CPU/RAM/network cua client/app. Failover: so request loi, thoi gian phat hien/phuc hoi; khong cam ket zero downtime neu khong do duoc. Chup Nova/Heat resource IDs, Octavia member va alarm history cung moc.

## Chi phi hang thang - muc 8

| Hang muc | Cach tinh / nguon gia / ngay lay gia | Chi phi |
|---|---|---|
| Ban quyen phan mem | Open-source; xac minh thanh phan thuc te | CHUA CHOT |
| Thue VPS/cloud | 0 neu hoan toan dung laptop san co; ghi dich vu neu phat sinh | CHUA CHOT |
| VPN/ten mien/dich vu bo sung | Ghi goi thuc su su dung, khong gia dinh mien phi | CHUA CHOT |
| Tong/thang | Cong cac hang muc trong pham vi | CHUA CHOT |

Theo proposal, dien/Internet/hao mon laptop khong nam trong pham vi tinh. 0 VND thue/ban quyen khong co nghia van hanh khong ton tai nguyen. Neu thue theo gio: don gia x so gio, ghi ro VAT/ti gia/region neu co. Khong uoc luong gia dich vu chua xac minh.

## Demo phan TV3 (nam trong demo 10 phut cua nhom)

1. Mo pool, chi 2 member ONLINE va app private; upload/verify 1 fixture.
2. Cho thay traffic hai backend, failover da do (live neu nhom thong nhat hoac bang chung truoc do).
3. Chay Locust da calibrate; mo metric + Aodh history + Heat events, doi VM/member thu 3 nhan request.
4. Giam tai, cho scale-in; verify/download tep cu. Neu khong kip thoi gian lay mau/boot, dung bang chung da thu va ghi ro, khong tu signal gia.
5. Hien bang chi phi, ket qua va gioi han. Khong quay key/token/user-data/signal URL.
