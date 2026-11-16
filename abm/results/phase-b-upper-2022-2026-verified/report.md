# Phase B trên 200% · Mức thấp nhất đạt là 250%

**250% là điểm thấp nhất đạt tiêu chí hoàn đủ gốc trên lưới mở rộng 205–300%, bước 5 điểm phần trăm.** Ở mức này, 839.376 lượt hoàn tất trên 1.608 cửa sổ, với 0 lượt mất gốc theo ngưỡng sai số 1e-9 USDC và 0 lượt thiếu người đủ điều kiện lĩnh theo giả định vốn của mô hình. Dữ liệu là giá đóng cửa ETH/USDT Binance Spot từ 01/01/2022 đến 31/10/2026.

## Phạm vi đã chạy

| Ký quỹ | Kiểm tra | Kết quả |
|---|---|---|
| 205–245%, bước 5 | Sàng lọc trên các cửa sổ giá bất lợi | Mỗi điểm có một ca mất gốc. Cả chín ca nằm trong cửa sổ bắt đầu ngày 19/04/2022. |
| 250% | Quét đầy đủ | 1.608 cửa sổ × 3 hồ sơ bid × 3 mức khả năng nộp USDC × 58 kịch bản = 839.376 lượt. |
| 255–300%, bước 5 | Sàng lọc | Đã chạy trên tập 15 cửa sổ. Quét đầy đủ dừng tại 250%. |

Sàng lọc có 9.579 lượt. Cấu hình dùng bid đồng nhất 0% và khả năng trả 0% của người đã lĩnh còn tuân thủ. Quét đủ dùng ba hồ sơ bid gồm đồng nhất 0%, đồng nhất 20% và bid trộn. Khả năng nộp USDC được xét ở 0%, 50% và 100%. Mỗi tổ hợp gồm một nhánh bùng theo giá và 57 nhóm bùng đặt trước. Giá đóng cửa ngày là đại diện cho giá bán ETH, với trượt giá 0 và quy đổi USDT≈USDC.

## Phát lại ca sát ranh giới

Cửa sổ bắt đầu 19/04/2022, bid 0%. Hai người đã lĩnh cùng bỏ góp tại kỳ ngày 18/06/2022 trong phép đối chiếu nhóm đặt trước. Bốn người chưa lĩnh cần được hoàn tổng cộng 800 USDC.

| Ký quỹ | Tiền bán ETH thu được | Gốc thiếu tổng cộng | Mất mỗi người chưa lĩnh |
|---|---:|---:|---:|
| 200% | 715,03 USDC | 84,97 USDC | 21,24 USDC |
| 245% | 793,01 USDC | 6,99 USDC | 1,75 USDC |
| 250% | 800,00 USDC | 0,00 USDC | 0,00 USDC |

Nhánh theo giá cho một người bỏ góp ở 245% và ca đó cũng mất khoảng 1,75 USDC mỗi người chưa lĩnh. Tại 250% trên cùng đường giá, nhánh theo giá đi hết dây, còn phép đặt trước hai người cùng bùng vẫn hoàn đủ gốc.

## Vốn phải khóa khi lĩnh đầu ở 250%

Nghĩa vụ sau khi lĩnh đầu là 500 USDC. ETH phải khóa tại lúc lĩnh trị giá **1.250 USDC**. Ở giá 3.101,77 USDT/ETH của ngày 19/04/2022, số lượng tương ứng là khoảng **0,403 ETH** theo cách quy đổi của ABM.

| Bid năm | USDC nhận sau khấu trừ lãi | Tiền tăng thêm sau khoản góp 100 USDC | Giá trị ETH khóa / tiền nhận | Giá trị ETH khóa / tiền tăng thêm |
|---|---:|---:|---:|---:|
| 0% | 600,00 | 500,00 | 2,08 lần | 2,50 lần |
| 20% | 558,90 | 458,90 | 2,24 lần | 2,72 lần |

## Kiểm chứng và tệp dữ liệu

- 18 checkpoint đầy đủ tại 250%. Chạy lại tổng hợp cho cùng SHA256 ở ba bảng CSV và tệp ngưỡng.
- Sàng lọc và mô phỏng mất khoảng 102 giây trên máy chạy, theo `last_run_timing.json`.
- Phạm vi kết luận là lưới bước 5 và tập giá cùng quy tắc Phase B đã kiểm tra. Điều kiện đủ ETH để lĩnh là giả định mô hình. Giá thực thi, phí và trượt giá có thể làm thay đổi số thu hồi.
- [Ngưỡng](threshold.json) · [Kết quả từng tỷ lệ](phase_b_upper_ratios.csv) · [Tổng hợp theo kịch bản](phase_b_upper_jobs.csv) · [Checkpoint sàng lọc](screening.json) · [Manifest](manifest.json).

