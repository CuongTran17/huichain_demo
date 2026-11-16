# Kiểm thử Phase B ở 250% khi ETH giảm 15–20%

Phát lại tám ngày giảm giá lịch sử với hai giá thực thi mô phỏng, gồm giá đóng cửa và đáy trong ngày. Có 12.282 lượt có bán ETH vào đúng ngày đang xét. Chạy thêm 24 lượt có đối chứng để xem ảnh hưởng của cú giảm 15% và 20% tại kỳ góp.

## Tám ngày giảm trên Binance Spot

Mức giảm đóng cửa và mức giảm tới đáy đều tính so với giá đóng cửa ngày liền trước theo UTC. Cột cuối là mức mất gốc lớn nhất của một người chưa lĩnh trong nhánh dùng đáy làm giá bán.

| Ngày | Giá đóng cửa | Đáy trong ngày | Mất gốc tối đa khi bán ở đáy |
|---|---:|---:|---:|
| 09/05/2022 | −11,56% | −11,70% | 0,00 USDC |
| 13/06/2022 | −15,68% | −18,77% | 0,00 USDC |
| 18/06/2022 | −8,45% | −18,90% | **11,18 USDC** |
| 09/11/2022 | −17,38% | −19,57% | 0,00 USDC |
| 05/08/2024 | −10,02% | −21,49% | 0,00 USDC |
| 06/04/2025 | −12,47% | −14,87% | 0,00 USDC |
| 10/10/2025 | −12,33% | −21,36% | 0,00 USDC |
| 05/02/2026 | −14,96% | −15,36% | 0,00 USDC |

Tất cả lượt dùng giá đóng cửa hoàn đủ gốc. Trong 825 lượt dùng giá đáy ngày 18/06/2022, có 22 lượt mất gốc. Ca tệ nhất bắt đầu ngày 19/04/2022, dùng bid 0% và giả định người đã lĩnh còn tuân thủ nộp được 0% USDC. Bốn người chưa lĩnh cần được hoàn 800 USDC. Sau khi định giá giao dịch bán của người bùng ở đáy 881,56 USDT/ETH và quyết toán phần còn lại theo quy tắc Phase B, thu được 755,26 USDC. Tổng gốc thiếu 44,74 USDC, mỗi người thiếu khoảng 11,18 USDC. Giá đóng cửa cùng ngày là 995,13 USDT/ETH.

Kịch bản đặt trước thử các nhóm bùng tại kỳ góp sao cho ngày bán của người bùng hoặc ngày bán sau 7 ngày của người tuân thủ trùng ngày sự kiện. Tám ngày dùng ba hồ sơ bid và ba mức nộp USDC của Phase B. Chỉ lượt thực sự có bán ETH vào ngày sự kiện được đếm trong bảng. Đáy là mức giá đã xuất hiện trên Binance Spot và được dùng làm giá thực thi giả định, với trượt giá 0.

## Cú giảm đúng 15% và 20% tại kỳ góp

Thay giá bán tại kỳ góp bằng 85% hoặc 80% giá đóng cửa hôm trước. Giữ các giá ở ngày khác và quy tắc quyết toán Phase B. Bảng dưới đây ghi mất gốc lớn nhất trong ca đặt trước nhóm bùng.

| Bối cảnh | Bid | Giảm 15% | Giảm 20% |
|---|---:|---:|---:|
| Giá đi ngang từ ngày lĩnh đến trước cú giảm | 0% | 0,00 USDC | 0,00 USDC |
| Giá đi ngang từ ngày lĩnh đến trước cú giảm | 20% | 0,00 USDC | 0,00 USDC |
| Cửa sổ 19/04/2022, đã giảm sâu trước kỳ ngày 60 | 0% | 6,92 USDC | 12,39 USDC |
| Cửa sổ 19/04/2022, đã giảm sâu trước kỳ ngày 60 | 20% | 0,00 USDC | 0,00 USDC |

Ở cửa sổ 19/04, người lĩnh đầu khóa ETH khi giá 3.101,77 USDT. Trước kỳ góp ngày 60, giá đã xuống 1.086,94 USDT. Cú giảm tới đáy sau đó bào mòn phần ký quỹ còn lại. Trong ca đặt trước hai người cùng bùng với bid 20%, quỹ lãi khoảng 67,40 USDC đủ bù phần thiếu của hai cú giảm giả định.

## Dữ liệu và nguồn

- [Nến lịch sử Binance Spot ETH/USDT](https://data.binance.vision/?prefix=data/spot/monthly/klines/ETHUSDT/1d/) · [Nến và URL đã dùng](historical_ohlc.json).
- [Chicago Fed về các đợt rút tiền và sụp đổ crypto năm 2022](https://www.chicagofed.org/publications/chicago-fed-letter/2023/479) · [Fed về đợt TerraUSD tháng 5/2022](https://www.federalreserve.gov/publications/2022-november-financial-stability-report-funding-risks.htm).
- [Coinbase về đợt biến động đầu tháng 8/2024](https://www.coinbase.com/institutional/research-insights/research/weekly-market-commentary/weekly-2024-08-09) · [Binance về đợt biến động ngày 10/10/2025](https://www.binance.com/en/support/announcement/detail/d9cb0d52d7c142a5be4f49732bd8760c).
- [Phát lại lịch sử](historical_event_replays.csv) · [Cú giảm đặt trước](synthetic_crashes.csv) · [Mã chạy lại](replay.py).
