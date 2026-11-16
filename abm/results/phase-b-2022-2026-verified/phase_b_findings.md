# Phase B · Bùng ở kỳ góp

## Kết quả quét toàn bộ cửa sổ

Đã đối chiếu đủ 90 checkpoint, gồm 4.196.880 lượt trên 1.608 cửa sổ tại năm mức ký quỹ từ 180% đến 200%. Mỗi mức có 839.376 lượt. Giá là ETH/USDT đóng cửa ngày của Binance Spot từ 01/01/2022 đến 31/10/2026. Mỗi cửa sổ gồm ngày bắt đầu, 150 ngày đến kỳ góp cuối và thêm 7 ngày quyết toán. Tổng hợp lại từ checkpoint cho ra cùng ba tệp CSV theo SHA256.

Mức mất gốc lớn nhất của một người chưa lĩnh, tính bằng USDC:

| Ký quỹ | Cùng bid 0%/năm | Cùng bid 20%/năm | Bid trộn |
|---|---:|---:|---:|
| 180% | 39,12 | 22,27 | 22,27 |
| 185% | 34,65 | 17,80 | 17,80 |
| 190% | 30,18 | 13,33 | 13,33 |
| 195% | 25,71 | 8,86 | 8,86 |
| 200% | 21,24 | 4,39 | 4,39 |

Mỗi hồ sơ được chạy với ba mức khả năng trả USDC khi quyết toán (0%, 50% và 100%), với nhánh người đã lĩnh bỏ góp theo giá và 57 nhóm bỏ góp đặt trước tại ngày đến hạn. Cả chín tổ hợp hồ sơ chào lãi và khả năng trả đều có ít nhất một tình huống mất gốc ở mỗi mức ký quỹ trong bảng. [Bảng tổng hợp](phase_b_summary.csv) · [Bảng ngưỡng](phase_b_thresholds.csv) · [Bảng gánh nặng vốn](phase_b_payouts.csv).

## Phản ví dụ trên toàn bộ lưới 25–200%

Cửa sổ bắt đầu 19/04/2022, bid 0% và người tuân thủ có khả năng trả 100% nghĩa vụ trong 7 ngày. Một lượt chạy riêng cho mỗi tỷ lệ từ 25% đến 200% theo bước 5 điểm phần trăm đều có người mất gốc. Kết quả đủ bác bỏ một ngưỡng chung trên lưới này theo tiêu chí hoàn đủ gốc cho mọi tình huống. [Dữ liệu 36 lượt](../phase-b-pilot-reviewed/phase_b_2022_counterexample_grid.csv).

Tại 180%, hai người đầu lĩnh rồi bỏ góp vào ngày 60 (18/06/2022). Họ còn nghĩa vụ 400 USDC/người. Giá ETH đóng cửa dùng trong mô hình là 995,13 USDT. Bán ETH của hai người thu 643,52 USDC, trong khi bốn người chưa lĩnh đã góp tổng cộng 800 USDC. Bid 0% tạo ra quỹ lãi bằng 0. Mỗi người chưa lĩnh nhận lại 160,88 USDC trên 200 USDC đã góp, thiếu 39,12 USDC.

Tại 200% trên cùng cửa sổ, mức mất gốc là 21,24 USDC/người chưa lĩnh. Trên lưới đã thử, tăng tỷ lệ giúp thu thêm USDC trong phản ví dụ này.

Khi đặt trước việc hai người đầu bỏ góp ở ngày 60, cùng cửa sổ trên cũng gây mất gốc ở cả 324 tổ hợp (36 tỷ lệ × 3 hồ sơ bid × 3 mức khả năng nộp USDC). Ở 200%, bid 20% và bid trộn giảm mức lỗ còn 4,39 USDC/người. Hai người đã lĩnh đều thuộc nhóm bùng, vì vậy thay đổi khả năng trả của người tuân thủ không bù được phần thiếu trong tình huống này. [Dữ liệu 324 lượt](../phase-b-pilot-reviewed/phase_b_2022_forced_counterexample_grid.csv).

## Điều kiện diễn giải

Với người lĩnh đầu và bid 20%/năm, ở 180% họ khóa lượng ETH trị giá 900 USDC để nhận 558,90 USDC. Khoản tăng tiền mặt sau khi tính 100 USDC tự góp trong kỳ là 458,90 USDC. Hai cách đo gánh nặng vốn lần lượt là 1,61 lần tiền nhận và 1,96 lần tiền tăng thêm.

Mô hình giả định đủ ETH để lĩnh, dùng giá đóng cửa ngày làm giá đại diện khi ra quyết định và bán ETH, trượt giá bằng 0 và quy đổi USDT≈USDC. Tần suất mất gốc tính trên cửa sổ chồng lấn và các nhóm bùng đặt trước. Hai tỷ số vốn khóa trên USDC nhận được nằm trong bảng payout của runner.
