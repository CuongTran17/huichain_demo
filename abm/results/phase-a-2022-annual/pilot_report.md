## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-15
- Verification Status: UNVERIFIED — đã chạy thành công và đối chiếu đầu ra; chưa tái chạy độc lập để chứng nhận tái lập.
- Version Label: phase_a_pilot_result_v1

## Kết luận của lô thử

Ký quỹ 100% nghĩa vụ còn lại, cùng lãi 20%/năm, chưa bảo vệ đủ gốc trên bộ điều kiện đã chạy. Có 271/11.856 tình huống mất gốc; 16/57 nhóm/mốc có ít nhất một cửa sổ mất gốc. Đây là đếm tình huống được đặt trước, không phải xác suất người chơi thật mất tiền.

## Cấu hình và thực thi

- Sáu người, góp 100 USDC mỗi 30 ngày. Giữ nguyên lượng ETH đã khóa đến quyết toán.
- Lãi đơn ACT/365, mọi người chào cùng 20%/năm; người chưa lĩnh được chọn theo ID tăng dần khi hòa bid.
- Ký quỹ cố định 100% nghĩa vụ còn lại tại ngày lĩnh, không phải 100% quỹ 600 USDC. Người đầu khóa ETH trị giá 500 USDC, người thứ hai 400, người thứ ba 300 tại từng ngày lĩnh.
- Giá đóng cửa ngày ETH/USDT năm 2022 trong CSV cục bộ; không normalize, không tải dữ liệu mới. Giả định USDT tương đương USDC.
- 208 cửa sổ liên tục dài 158 ngày, bắt đầu 2022-01-01 đến 2022-07-27. Mọi cửa sổ đều nằm trong năm 2022.
- 57 nhóm/mốc bùng: mọi tập con không rỗng của người đã lĩnh sau lượt 1–5. Bùng ngày kế sau lượt lĩnh, đóng băng dây và bán ETH người bùng ngay. Người đã lĩnh không bùng trả đủ nghĩa vụ USDC ngày thứ 7; không phát sinh thiếu hụt thứ cấp trong lô hợp lệ này.
- Trượt giá 0, không quỹ dự phòng ngoài, không margin call, giả định luôn đủ ETH để lĩnh.
- Hoàn thành 11.856/11.856 engine runs, exit code 0; không thấy lỗi hoặc timeout. Engine kiểm tra bảo toàn dòng tiền/ETH trong mỗi lượt chạy.
- Thời gian job: 3.4850402000010945 giây; toàn workflow CLI: 3.7096019000018714 giây, không tính khởi động Python từ shell. Đây không phải benchmark full sweep.
- Commit thông tin: `a2b6f54e92dd55af4f10de7bb5ad75d88677ebba`.
- CSV SHA256: `bad25f9a10e5a9c462c19dec910f3cbe5b66b17269b8ccc2517f185215f974b3`.
- Fingerprint: `04969ffca20bf0b3acd44fe7761d7791e7d97a24bc0b6d3a4d0418ee29ace4d5`.

Lệnh đã chạy, từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m rosca_sim.cli auction-phase-a --prices data/eth_usdt_binance_2022.csv --output results/phase-a-2022-annual --source-label "Binance ETHUSDT daily close 2022" --quote-asset USDT --annual-rate 0.20 --ratio 1.00
```

## Kết quả theo mốc bùng

Số người đã lĩnh không đồng nghĩa số người bùng: tại mỗi mốc xét toàn bộ tập con không rỗng. Hai cột mất gốc lớn nhất là maximum riêng trên tất cả nhóm và cửa sổ tại mốc đó. Làm tròn chỉ để trình bày; xét đạt bằng số chưa làm tròn, tolerance 1e-9 USDC.

| Đã có bao nhiêu người lĩnh | Số nhóm bùng | Số lượt chạy | Lượt mất gốc | Mất gốc toàn dây lớn nhất (USDC) | Mất gốc một người lớn nhất (USDC) |
|---|---:|---:|---:|---:|---:|
| 1 | 1 | 208 | 8 | 37.32 | 7.46 |
| 2 | 3 | 624 | 91 | 123.23 | 30.81 |
| 3 | 7 | 1,456 | 128 | 172.95 | 57.65 |
| 4 | 15 | 3,120 | 44 | 73.35 | 36.68 |
| 5 | 31 | 6,448 | 0 | 0.00 | 0.00 |
| Tổng | 57 | 11,856 | 271 | 172.95 | 57.65 |

Không mất gốc tại mốc 5 trong lô này không phải bảo đảm mọi nhóm 5 người bùng đều an toàn trong tương lai: nợ còn lại giảm trong khi lượng ETH khóa vẫn giữ nguyên.

## Trường hợp tệ nhất

- Dây bắt đầu 2022-04-16. Ba người đầu lĩnh tại ngày 0, 30, 60 rồi cùng bùng ngày 61, tức 2022-06-16.
- Giá ETH các ngày lĩnh: 3,059.30; 2,023.66; 1,237.52 USDT. Giá bán ngày bùng: 1,068.50 USDT.
- Mỗi người bùng còn nghĩa vụ 300 USDC; tổng 900 USDC. Không có người đã lĩnh tuân thủ nào khác trong trường hợp này để nộp USDC quyết toán.
- Bán ETH thu 644.8590548045944 USDC. Nợ chưa thu sau bán: 255.14094519540564 USDC.
- Toàn bộ lãi đã giữ 82.1917808219178 USDC được dùng bù gốc, không đủ lấp thiếu hụt.
- Ba người chưa lĩnh mỗi người đã góp 300 USDC; mỗi người nhận lại 242.35027854217074 USDC, mất 57.64972145782926 USDC, khoảng 19.22% vốn đã góp. Không nhận lãi.
- Tổng mất gốc: 172.94916437348778 USDC. Nợ chưa thu không đồng nhất với mất gốc: lãi giữ lại đã hấp thụ một phần thiếu hụt.

Đối chiếu dòng tiền hoàn gốc:

`644.8590548045944 + 82.19178082191775 = 727.0508356265123 USDC`.

`900 - 727.0508356265123 = 172.94916437348778 USDC`.

Đối chiếu thêm 342 dòng thành viên ở các cửa sổ tệ nhất: không có sai lệch vượt 1e-6 ở đẳng thức ETH khóa = ETH giải phóng + ETH bán + ETH trả lại, hoặc claim = hoàn gốc + mất gốc.

## Độ đầy đủ và giới hạn

Đã hoàn tất một trong 40 coarse jobs. Trạng thái nghiên cứu chung vẫn `incomplete`, ngưỡng ứng viên chung là null: mới thử một mức lãi và một mức ký quỹ. Chưa chạy coarse đầy đủ hoặc refinement, chưa xác định ký quỹ bao nhiêu là đủ.

271/11.856 = khoảng 2.29% tình huống duyệt có mất gốc; không dùng tỷ lệ này như xác suất rủi ro. Các cửa sổ chồng lấn và nhóm bùng được đặt trước, không độc lập hoặc lấy mẫu hành vi ngoài đời. Giá đóng cửa ngày không kiểm thử cú quét trong ngày, trượt giá, thanh khoản thực, phí giao dịch hoặc depeg. Không đánh giá khả thi vốn/pháp lý/chống Sybil.

Bước nghiên cứu tiếp theo có thể so sánh ký quỹ 125%, 150% và mức lãi 0% đối chứng, hoặc chạy đủ 40 coarse jobs rồi tinh chỉnh theo kế hoạch. Không suy ra ngưỡng từ riêng lô thử này.

## Đầu ra đi kèm

- `jobs/rate-20-ratio-100.json`: checkpoint hoàn tất, 57 summaries và 342 dòng thành viên tệ nhất.
- `phase_a_summary.csv`: 57 dòng tổng hợp.
- `phase_a_worst_members.csv`: 342 dòng thành viên.
- `phase_a_thresholds.csv`: 291 dòng case/rate/global, nghiên cứu chung chưa đầy đủ.
- `phase_a_metadata.json`: nguồn, hash, phạm vi và trạng thái.

Không sửa mã nguồn hoặc kết quả demo cũ trong lượt chạy thử này.
