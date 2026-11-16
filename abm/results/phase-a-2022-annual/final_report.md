## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-15
- Verification Status: UNVERIFIED — đã hoàn thành, kiểm tra checkpoint và đối chiếu tổng hợp; chưa có tái chạy mô phỏng độc lập để chứng nhận tái lập.
- Version Label: phase_a_2022_final_result_v1

## Kết luận chính

Đã hoàn tất 180/180 jobs, tương ứng 2.134.080/2.134.080 lượt mô phỏng. Mức ký quỹ nhỏ nhất đã thử bảo toàn gốc trên toàn bộ bộ điều kiện là **185% nghĩa vụ còn lại tại lúc lĩnh**. Riêng khi tất cả bid cùng 20%/năm, ngưỡng nhỏ nhất đã thử là **140%**.

Đây là kết quả có điều kiện trên giá ETH đóng cửa ngày năm 2022, không phải mức ký quỹ bảo đảm an toàn ngoài thực tế hoặc khuyến nghị đưa thẳng vào smart contract. Mức thấp nhất chính xác giữa các điểm lưới chưa được xác định.

## Phạm vi và cấu hình

- Sáu người, sáu lượt, góp 100 USDC mỗi 30 ngày; kỳ 30 ngày không phải tháng lịch.
- Mức lãi năm 0%, 5%, 10%, 15%, 20%; trong một case mọi người chào cùng mức, tie-break ID tăng dần. Không mô phỏng chiến lược đấu giá.
- Lãi đơn ACT/365: nghĩa vụ còn lại × lãi năm × số ngày còn lại / 365, khấu trừ ngay lúc lĩnh. Đây là quy ước nghiên cứu, chưa đánh giá tuân thủ pháp luật.
- Khóa ETH tại lúc lĩnh theo nghĩa vụ còn lại, không tính theo quỹ 600 USDC. Giữ nguyên lượng ETH qua các kỳ góp tới quyết toán.
- 208 cửa sổ liên tục dài 158 ngày, bắt đầu 2022-01-01 đến 2022-07-27, dùng dữ liệu ETH/USDT đóng cửa ngày trong năm 2022; không normalize, không tự tải hoặc điền dữ liệu. Giả định USDT tương đương USDC.
- 57 nhóm/mốc: mọi tập con không rỗng của người đã lĩnh sau lượt 1–5; bùng ngày kế sau lượt lĩnh. Bao gồm một người bùng muộn và nhiều người cùng bùng, không chỉ tất cả người đã lĩnh cùng bùng.
- Người bùng không nộp USDC, bán ETH ngay ngày đóng băng. Người đã lĩnh không bùng trả đủ nghĩa vụ bằng USDC ngày thứ 7 và được nhận lại ETH. Giả định luôn đủ ETH để lĩnh và đủ khả năng trả USDC của người tuân thủ.
- Trượt giá 0, không phí, không execution override, không margin call hoặc quỹ dự phòng ngoài. Quỹ lãi chung được dùng bù gốc khi thiếu, ưu tiên nguồn lãi người bùng trước.
- PASS khi mọi cá nhân không mất gốc vượt tolerance số học 1e-9 USDC; xét số chưa làm tròn. Không dùng ngưỡng mất gốc trung bình.

## Mức ký quỹ theo lãi

Lưới coarse có 8 mức 25–200%, bước 25 điểm phần trăm. Refinement từ các ngưỡng riêng/theo lãi/chung sinh thêm 28 mức; hợp hai giai đoạn phủ đủ 36 mức 25–200%, bước 5 điểm phần trăm. Mỗi mức đều chạy đủ 5 mức lãi × 57 nhóm × 208 cửa sổ.

| Lãi năm | Ngưỡng coarse | Ngưỡng sau tinh chỉnh | Mức ngay dưới còn thất bại | Số lượt mất gốc ở mức ngay dưới / 11.856 | Mất gốc cá nhân lớn nhất ở mức ngay dưới (USDC) |
|---|---:|---:|---:|---:|---:|
| 0% | 200% | **185%** | 180% | 4 | 2.296469386953561 |
| 5% | 175% | **175%** | 170% | 4 | 0.8751282414074808 |
| 10% | 175% | **160%** | 155% | 4 | 2.1677740573348956 |
| 15% | 150% | **150%** | 145% | 4 | 0.7464329117887019 |
| 20% | 150% | **140%** | 135% | 4 | 5.79344084279694 |

Mỗi ngưỡng trong cột tinh chỉnh có 0 lượt mất gốc trên 11.856 điều kiện của mức lãi đó. Giao tập PASS của cả năm mức lãi là 185%, 190%, 195%, 200%; ngưỡng chung nhỏ nhất đã thử là 185%, không lấy trung bình các ngưỡng.

Không thấy cờ PASS rồi FAIL ở tỷ lệ cao hơn trong 291 dòng ngưỡng case/rate/global trên lưới đã thử. Điều này không chứng minh tính đơn điệu ở mọi cấu hình hoặc mọi tỷ lệ liên tục.

## Hai trường hợp sát ranh giới

### 180%, lãi 0%: một người bùng cũng gây mất gốc

Cửa sổ bắt đầu 2022-04-18. Sau ba lượt lĩnh, chỉ người đầu (ID0) bùng ngày61, tức 2022-06-18; giá ETH bán là 995.13 USDT. Người này đã đóng ba kỳ, còn nợ 300 USDC.

ETH khóa lúc lĩnh trị giá 900 USDC (180% × 500), khi bán chỉ thu khoảng 293.11059183913915 USDC. Hai người đã lĩnh còn lại trả đủ 300 USDC/người; không có quỹ lãi đối chứng 0% để bù.

Ba người chưa lĩnh có tổng claim 900 USDC, thiếu 6.8894081608606825 USDC; mỗi người mất 2.296469386953561 USDC. Đây là một phản ví dụ cho việc chỉ thử nhóm tất cả người đã lĩnh cùng bùng. Mức 185% đã vượt qua toàn bộ bộ điều kiện đã chạy, không chỉ riêng phản ví dụ này.

### 135%, lãi 20%: dùng cả lãi người tuân thủ vẫn còn thiếu

Cùng cửa sổ bắt đầu 2022-04-18, sau ba lượt lĩnh, ID0 và ID1 cùng bùng ngày61. ID2 tuân thủ, trả đủ 300 USDC ngày thứ7. ETH người bùng bán ở giá 995.13 USDT.

Sau bán ETH, nghĩa vụ chưa thu của hai người bùng là 99.57210335030871 USDC. Toàn bộ lãi ba người đã lĩnh giữ lại là 82.1917808219178 USDC được dùng bù: khoảng 67.3972602739726 của hai người bùng và 14.794520547945206 của người tuân thủ.

Vẫn thiếu 17.38032252839082 USDC; ba người chưa lĩnh mất 5.79344084279694 USDC/người. Vì vậy, quỹ lãi chung có ích nhưng không bảo đảm đủ bù tại mọi mức ký quỹ. Mức 140% đã vượt qua toàn bộ bộ điều kiện của nhóm lãi20% được chạy.

## Ý nghĩa với thiết kế sản phẩm

1. **Không nên coi 140% là ngưỡng chung.** Nó đạt khi mọi bid là20%/năm theo đúng bộ điều kiện này. Với lãi thấp hơn, quỹ đệm nhỏ hơn; đối chứng0% cần185% trên lưới đã thử.
2. **Bảo toàn gốc không đồng nghĩa có lãi.** Pool có thể phải dùng tiền lãi của cả người tuân thủ để bù thiệt hại. Đầu ra lãi dùng/nợ chưa thu gắn với cửa sổ mất gốc cá nhân tệ nhất; không tự coi đó là maximum của hai chỉ số trên mọi cửa sổ, đặc biệt khi mọi cửa sổ đều không mất gốc.
3. **Chi phí vốn vẫn cao.** Người lĩnh đầu còn nghĩa vụ500 USDC: tỷ lệ185% đòi ETH trị giá925 USDC để lĩnh600 USDC ở lãi0%; tỷ lệ140% đòi ETH trị giá700 USDC để lĩnh khoảng558.90 USDC ở lãi20%/năm. Các khoản này tính tại lúc lĩnh, chưa trừ kỳ góp100 USDC của chính họ khỏi dòng tiền nhận. Bước A giả định có đủ ETH, chưa chứng minh người dùng sẽ muốn hoặc có khả năng tham gia.
4. **Ngưỡng chỉ có điều kiện, không bảo đảm tương lai.** Chưa kiểm thử giá ngoài2022, low trong ngày, thanh khoản/slippage/phí thực, oracle, depeg, người tuân thủ không xoay đủ USDC, hay chiến lược Sybil/game theory. Không biến tần suất tổ hợp lỗ thành xác suất vì cửa sổ chồng lấn và nhóm bùng được đặt trước.

## Kiểm chứng thực thi và thời gian

- Coarse: 40 jobs, 474240 runs; workflow 194.0922969000021 giây, tái dùng pilot đã có.
- Refinement: thêm140 jobs, 1659840 runs; workflow 654.9947710000051 giây.
- Hai workflow: khoảng14 phút9 giây, chưa tính khởi động Python, các lệnh phân tích và lệnh aggregate đối chiếu sau đó. Tổng thời gian các checkpoint gồm pilot là840.6570320999963 giây.
- 180/180 jobs, mỗi job57 nhóm ×208 cửa sổ, tổng2134080 runs. 10260/10260 kiểm tra nhóm×ratio hoàn tất; metadata/threshold global là `complete`, candidate1.85.
- Đã chạy lại `--aggregate-only`, xác thực checkpoint/fingerprint/payload và nhận cùng ngưỡng1.85, không chạy lại engine; workflow đối chiếu2.2885920999979135 giây.
- Engine kiểm tra bảo toàn dòng tiền/ETH ở từng run. Đối chiếu thêm61560 dòng thành viên lưu ở các cửa sổ tệ nhất: 0 lỗi ETH identity và0 lỗi principal identity vượt1e-6. Đây không phải độc lập tái lập toàn bộ mô phỏng.
- Không có lỗi mô phỏng, timeout hoặc checkpoint thiếu được báo. Truy vấn hệ điều hành để đọc tài nguyên tiến trình bị hạn chế quyền; tiến độ và trạng thái process được theo dõi qua phiên thực thi, tệp job và exit code, không có số đo RAM đáng tin để báo.
- Không sửa mã nguồn, không commit/push, không ghi đè kết quả demo cũ. pilot_report.md và coarse_report.md được giữ như snapshot của các giai đoạn trước.

## Tái lập và tệp đầu ra

- Git commit thông tin: `a2b6f54e92dd55af4f10de7bb5ad75d88677ebba`.
- CSV: `data/eth_usdt_binance_2022.csv`.
- CSV SHA256: `bad25f9a10e5a9c462c19dec910f3cbe5b66b17269b8ccc2517f185215f974b3`.
- Fingerprint: `04969ffca20bf0b3acd44fe7761d7791e7d97a24bc0b6d3a4d0418ee29ace4d5`.
- `phase_a_summary.csv`: 10260 dòng.
- `phase_a_worst_members.csv`: 61560 dòng; không phải tất cả agent rows của2.13 triệu runs.
- `phase_a_thresholds.csv`: 291 dòng (285 case,5 rate,1 global).
- `phase_a_metadata.json`: nguồn, hash, quy ước và phạm vi.
- `jobs/`: 180 checkpoint, có thời gian và độ đầy đủ từng job.

Các lệnh coarse, refinement và đối chiếu từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m rosca_sim.cli auction-phase-a --prices data/eth_usdt_binance_2022.csv --output results/phase-a-2022-annual --source-label "Binance ETHUSDT daily close 2022" --quote-asset USDT
.\.venv\Scripts\python.exe -m rosca_sim.cli auction-phase-a --prices data/eth_usdt_binance_2022.csv --output results/phase-a-2022-annual --source-label "Binance ETHUSDT daily close 2022" --quote-asset USDT --refine
.\.venv\Scripts\python.exe -m rosca_sim.cli auction-phase-a --prices data/eth_usdt_binance_2022.csv --output results/phase-a-2022-annual --source-label "Binance ETHUSDT daily close 2022" --quote-asset USDT --aggregate-only
```

Chạy lại cùng thư mục sẽ tái dùng checkpoint khớp, không phải independent rerun. Muốn kiểm chứng tái lập engine phải dùng thư mục kết quả mới với cùng mã/dữ liệu/cấu hình.
