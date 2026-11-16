# ROSCA collateral simulation

Mô phỏng ABM của Hụi Chain chạy local bằng Python và Streamlit. Bản demo blockchain sáu người nằm ở [thư mục demo](../demo/); web Sepolia được build từ thư mục đó.

Đầu ra dùng trong báo cáo BTL nằm trong [quét chính](results/phase-b-2022-2026-verified/phase_b_findings.md), [quét trên 200%](results/phase-b-upper-2022-2026-verified/report.md) và [kiểm thử giá đáy](results/phase-b-crash-15-20/report.md). Các bảng này xem trực tiếp được. Dashboard hiện tại có mục riêng cho kết quả nghiên cứu 2022.

Mô hình Mesa này có hai chế độ nghiên cứu tách biệt: ROSCA thứ tự cố định ban đầu và ROSCA đấu giá lãi, dừng dây ngay khi có người bùng. Cả hai so sánh chính sách ký quỹ cố định với chính sách điều chỉnh theo uy tín trên cùng đầu vào.

## Thử dây hụi đấu giá 6 người

### Xem bộ kết quả nghiên cứu ETH 2022

Chạy Streamlit theo hướng dẫn bên dưới, chọn **Kết quả nghiên cứu 2022** ở đầu trang. Chế độ này đọc checkpoint đã có tại `results/phase-a-2022-annual`; CSV giá chỉ cần khi xem diễn biến. Nếu máy khác chưa có bộ kết quả nghiên cứu, hãy sao chép đúng thư mục nghiên cứu và CSV gốc, không đổi metadata để bỏ qua kiểm tra fingerprint.

Trang gồm ngưỡng toàn nghiên cứu, đồ thị rủi ro và bản đồ nhiệt. Lọc lãi năm, khoảng ký quỹ, số người đã lĩnh và nhóm bùng; chọn mất gốc cá nhân lớn nhất hoặc tổng số tình huống mất gốc. Các bộ lọc **không đổi ngưỡng chung**. Kéo/cuộn đồ thị đường để dịch/phóng trục ký quỹ, nhấp đúp để đặt lại. Bảng mở rộng và CSV giữ số liệu gốc, phạm vi và nguồn dữ liệu.

**Mở trường hợp tệ nhất** chỉ đổi lựa chọn; **Xem diễn biến** mới chạy một tình huống với seed 42. Có thể chọn cửa sổ worst cá nhân, worst toàn dây hoặc ngày khác trong nghiên cứu. Đổi mốc diễn biến không chạy lại engine. Đổi nguồn/case/ngày sẽ ẩn kết quả cũ; bấm lại để cập nhật. **Tải lại dữ liệu** bỏ cache của chế độ mới, không xóa các dây ở chế độ cũ.

Ô xám hoặc ngưỡng **Chưa đủ dữ liệu** không phải mất gốc 0. Job thiếu không được thay bằng số complete từ CSV cũ; job hỏng hoặc fingerprint không tương thích sẽ báo lỗi. Số tình huống là tổng theo nhóm và cửa sổ chồng lấn, **không phải xác suất mất tiền**. Giá đóng cửa, trượt giá 0, đủ ETH và người tuân thủ trả USDC ngày 7 đều là giả định; không chứng minh thanh lý ngoài thực tế. Lãi ACT/365 tính trên nghĩa vụ ban đầu, không phải dư nợ giảm dần hay xác nhận pháp lý.

Nghiệm thu ngày 2026-10-16: 242 kiểm thử đạt; corpus180 jobs/2.134.080 lượt và replay khớp checkpoint, không sửa dữ liệu gốc. Xem [báo cáo nghiệm thu](docs/superpowers/reports/2026-10-16-phase-a-results-explorer-verification.md) để biết phạm vi kiểm tra và giới hạn. Khi lưới heatmap dày, chữ trong ô được ẩn để tránh chồng lấn; xem số chính xác trong tooltip hoặc bảng.

### Chạy giao diện nghiên cứu trên Windows

Mở PowerShell **tại thư mục dự án có `pyproject.toml`**. Cần Python 3.12 trở lên. Lần đầu, tạo môi trường và cài nhóm phụ thuộc cho web:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,web]"
```

Web cần CSV giá ETH hằng ngày. Nếu chưa có, tải giá đóng cửa ETH/USDT năm 2022 từ kho Binance (bước này cần Internet):

```powershell
.\.venv\Scripts\rosca-sim.exe fetch-binance-prices --start 2022-01-01 --end 2022-12-31 --output data/eth_usdt_binance_2022.csv
```

Sau đó mở giao diện, chỉ cho truy cập từ chính máy này:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src/rosca_sim/web_app.py --server.address 127.0.0.1
```

Mở `http://127.0.0.1:8501` nếu trình duyệt chưa tự mở. Ở thanh bên, nhập **đường dẫn tuyệt đối** của CSV; dùng `(Resolve-Path .\data\eth_usdt_binance_2022.csv).Path` trong PowerShell để lấy đường dẫn. Ghi tên nguồn, chọn `USDT`, rồi trong **So sánh kịch bản** chọn một ngày bắt đầu hợp lệ ở mục **Chỉnh điều kiện dây hụi**, bấm **Lưu điều kiện dây** và **Chạy các kịch bản**. Muốn tìm ngưỡng, chuyển sang **Quét tự động và tìm ngưỡng**, chọn dải tỷ lệ và số cửa sổ, rồi bấm **Quét tỷ lệ**. Năm 2022 chỉ là ví dụ; dữ liệu phải đủ số ngày cho cả dây và thời gian ân hạn.

Lần sau chỉ cần chạy lại lệnh `streamlit run` ở trên, không cần tạo `.venv` hay tải lại CSV. Nhấn `Ctrl+C` trong PowerShell để dừng web. Giao diện **không** kết nối ví hay đặt lệnh giao dịch. CSV tự chuẩn bị cũng dùng được nếu có đúng hai cột `date,close`, mỗi ngày một giá dương và không trùng ngày.

Ở **So sánh kịch bản**, chỉnh dây mẫu, chào lãi, ETH sẵn có, khả năng nộp USDC, ngày bùng, trượt giá khi bán ETH và cách quyết toán; bấm **Lưu điều kiện dây**, rồi **Chạy các kịch bản**. Có thể nhân bản dây để đổi một giả định, nhập/xuất JSON, lọc biểu đồ và tải các bảng CSV. Biểu đồ chi tiết thể hiện giá đóng cửa, thời điểm lĩnh/dừng/bán ETH, tiền trong quỹ và lỗ của từng người. Người đã lĩnh vẫn chỉ đóng mức góp cố định về sau; lãi thắng đã khấu trừ ngay lúc lĩnh và ở lại quỹ.

Trong **chế độ đấu giá**, ETH chỉ khóa lúc lĩnh theo `tỷ lệ × nghĩa vụ góp tương lai / giá ETH lúc lĩnh`, không trừ khoản bid đã trả. Mỗi lần góp tiếp làm giảm nghĩa vụ nhưng **không giải phóng ETH từng kỳ**. Dây hoàn thành thì trả toàn bộ ETH; dừng sớm thì quyết toán bằng USDC/ETH, chỉ bán lượng ETH cần cho nghĩa vụ và trả ETH dư. Chế độ thứ tự cố định cũ vẫn có quy tắc giải phóng từng kỳ riêng, không thay đổi.

Chỉ báo ký quỹ (F11) là giá trị ETH còn khóa chia nghĩa vụ còn lại, quan sát ở các kỳ đã chạy, không phải theo dõi liên tục hay margin call. Nghĩa vụ bằng 0 thì tỷ lệ không áp dụng. ETH giảm làm chỉ báo thiếu hụt tăng nhưng không tự kích hoạt nạp thêm/thanh lý. Bảng trace phân biệt ETH khóa mới trong kỳ với ETH còn giữ; kỳ cuối ghi snapshot trước khi trả ETH terminal.

Tiền góp định kỳ được giả định đủ trừ sự kiện bùng/bỏ góp do người nghiên cứu đặt trước. `usdc_capacity` chỉ là khả năng trả USDC khi toàn bộ nghĩa vụ bị yêu cầu quyết toán, không phải số dư ví hay thu nhập hằng tháng. Kết quả phân biệt người gây đóng băng (`is_trigger_default`, tổng `default_count`) với người khác còn thiếu nghĩa vụ sau quyết toán (`settlement_shortfall`, tổng `secondary_shortfall_count`); thiếu tiền trả ngay không đồng nghĩa đã bỏ góp định kỳ.

Ở **Quét tự động và tìm ngưỡng**, chọn các dây, khoảng tỷ lệ ký quỹ, bước lưới, số cửa sổ lịch sử và seed; bấm **Quét tỷ lệ**. Mỗi tỷ lệ của một dây dùng cùng ngày bắt đầu và cùng giả định hành vi. Giới hạn là 10.000 lượt mô phỏng; giao diện báo trước số lượt. “Ngưỡng ứng viên” chỉ là tỷ lệ thấp nhất *đã thử* không lỗ gốc trong các cửa sổ được chọn, không phải mức ký quỹ bảo vệ chắc chắn. Lượt không ai đủ ETH để lĩnh không được tính là ngưỡng. Tỷ lệ cao hơn có thể đổi người lĩnh và làm kết quả không đơn điệu. Dữ liệu CSV xuất ra không chứa đường dẫn tệp riêng trên máy.

Biểu đồ sweep cho thấy lỗ trung bình, lỗ lớn nhất của một người, tỷ lệ cửa sổ bị lỗ, tỷ lệ dây hoàn thành và đánh đổi với lượng ETH khóa quy đổi. Bảng có số lượt lĩnh trung bình và số lượt không có người đủ điều kiện lĩnh; không có bid cũng có thể gây `no_eligible_bid`, không chỉ thiếu ETH. Kịch bản cố ý có bùng có thể không hoàn thành dù thu đủ gốc. Lượng khóa lúc lĩnh là proxy quy mô vốn, không phải chi phí vốn hay số ngày bị khóa. File `tung_luot.csv` giữ seed, cửa sổ ngày và `scenario_json` đúng theo tỷ lệ đã chạy để đối chiếu giả định; muốn tái lập còn phải giữ bản CSV giá ETH gốc tương ứng với nhãn nguồn.

Giá ETH dùng trong web là **giá đóng cửa từng ngày**, không phải giá thực thi lúc bán. `Giá bán mô phỏng = giá đóng cửa × (1 − liquidation_slippage)`: baseline 0%; 5% và 10% chỉ là giả định phân tích độ nhạy, không phải dữ liệu trượt giá đo được. UI nhập theo phần trăm, JSON lưu tỷ lệ (5% thành `0.05`); giá trị phải từ 0 đến dưới 100%. Web lịch sử từ chối `stress_drop` và `execution_price_overrides` khi nhập JSON, giữ lưới tỷ lệ không bị sàn stress tự nâng. CLI vẫn hỗ trợ các kịch bản stress riêng.

Quy đổi ETH theo giá USD/USDT sang nghĩa vụ USDC dùng giả định 1 USD hoặc 1 USDT xấp xỉ 1 USDC; chưa mô phỏng mất neo stablecoin, râu nến, sổ lệnh, thất bại thanh lý hay thông đồng. Các vụ bùng và mức chào lãi là đầu vào giả định. Tỷ lệ lượt lỗ trong mẫu **không phải xác suất mất tiền ngoài thực tế**; test giá hằng số/cú sốc nhân tạo chỉ kiểm tra số học, không phải kết quả thị trường.

```powershell
.\.venv\Scripts\rosca-sim.exe auction-run --config configs/auction-six-member.toml --output results/auction-pilot
```

Bid auction hiện dùng `annual_rate` từ 0 đến 0.20 (tối đa 20%/năm), lãi đơn ACT/365: `lãi giữ lại = nghĩa vụ góp còn lại × annual_rate × ngày còn lại / 365`. Ví dụ kỳ đầu sáu người góp 100 USDC/người, kỳ 30 ngày: nghĩa vụ còn 500 trong 150 ngày. Chào 20%/năm giữ khoảng **41,10 USDC**, lĩnh khoảng **558,90 USDC**. Đây là quy ước mô phỏng, không phải APR/IRR hiệu dụng hay xác nhận tuân thủ pháp luật cho USDC/ETH.

Người lĩnh chỉ khóa ETH lúc lĩnh, năm kỳ sau vẫn góp 100 USDC/kỳ và không chào tiếp. Lãi đã khấu trừ không thu lại hoặc tính lại khi quyết toán sớm; kỳ cuối nghĩa vụ bằng 0 nên lãi khấu trừ bằng 0. Nếu có người bùng, dây dừng trước khi thu kỳ mới; người đã lĩnh quyết toán nghĩa vụ còn lại bằng ETH/USDC theo cấu hình, ân hạn mặc định 7 ngày. Quỹ hoàn gốc người chưa lĩnh trước, chỉ chia phần dư theo thời gian chờ. **Lãi không được bảo đảm** vì có thể dùng bù gốc.

**Không tái diễn giải dữ liệu cũ:** TOML auction dùng `annual_rate` thay `rate`; JSON case dùng `schema_version=2`, từ chối schema 1. Result field `winning_annual_rate` và metadata `bid_rate_basis=annual_simple_act365`, `day_count_basis=365`, `result_schema_version=2` ghi rõ đơn vị. Demo cũ 20% quỹ lĩnh → 480/120 vẫn giữ nguyên như kết quả gross-discount, không phải kết quả cơ chế năm mới. Không chỉ sửa version của JSON cũ để nhập lại; cần tạo case mới với lãi suất năm có chủ đích. Fixed-order không thay đổi.

Kết quả đấu giá nằm trong `auction_run_results.csv`, `auction_agent_results.csv`, `auction_pair_results.csv` và `auction_metadata.json`; không ghi đè kết quả chế độ cũ. Các tệp báo lỗ gốc từng người, nghĩa vụ chưa thu, ETH bán/trả lại và lãi thực nhận. Giá lịch sử dùng giá đóng cửa từng ngày, không chứng minh giá khớp lệnh trong cú râu nến. Đây là mô hình nghiên cứu có đầu vào đấu giá và sự kiện bùng được ấn định, **không phải cam kết an toàn hoặc thiết kế hợp đồng triển khai thực tế**.

Nguồn lãi bù gốc được hạch toán từ lãi đã trả của nhóm gây đóng băng trước (`interest_used_from_defaulting`), rồi phần lãi chung còn lại (`interest_used_from_other_members`). Tổng hai khoản bằng `interest_used`, không phải hai nguồn tiền nạp mới. `bid_interest_paid` là lãi đã trả của từng người, không được hoàn lại như ký quỹ USD. Quỹ bù gốc không xóa `obligation_uncollected`: nghĩa vụ chưa thu, lãi đã dùng và lỗ gốc là ba chỉ số riêng. Metadata CLI lưu scenario và `collateral_release_policy="terminal"`; bảng CSV web cũng ghi chính sách giữ ETH để phân biệt kết quả cũ.

Để so sánh thời hạn quyết toán trên **cùng đường giá** và cùng nhóm người chơi:

```powershell
.\.venv\Scripts\rosca-sim.exe auction-grace-sweep --config configs/auction-six-member.toml --output results/auction-grace --days 0 1 3 7 14
```

`auction_grace_frontier.csv` báo lỗ gốc trung bình, bách phân vị 95 từ đúng các lượt đã chạy, lỗ gốc tệ nhất của một người, lãi bị dùng bù gốc, thời gian chờ và số vụ bán ETH. Cấu hình mẫu không có sự kiện bùng nên các số lỗ có thể đều bằng 0; hãy thêm `forced_defaults`, khả năng nộp USDC và cú sốc giá để kiểm thử rủi ro. Bảng này là so sánh kịch bản, không xác định “7 ngày là an toàn”. Nếu dùng giá lịch sử, dữ liệu phải đủ cả phần đuôi sau kỳ cuối cho thời hạn dài nhất; mô hình không tự lặp lại giá ngày cuối.

## Cài đặt và kiểm thử

Yêu cầu Python 3.12 trở lên. Trong PowerShell, chạy từ thư mục dự án:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q -o 'addopts=' -p no:cacheprovider --basetemp work/pytest-run
```

## Chạy pilot với cú sốc giá

```powershell
.\.venv\Scripts\rosca-sim.exe run --config configs/stress.toml --output results/stress-pilot
```

`configs/stress.toml` mặc định chạy 100 cặp mô phỏng với kịch bản ETH giảm 40%. Có thể sửa các giả định trong TOML, gồm quy mô ROSCA, khoản góp, tỷ lệ thế chấp, phân phối uy tín, chi phí hành vi, số lượt chạy và seed.

## Ký quỹ theo nghĩa vụ còn lại và sức chịu cú sốc

Người nhận hụi ở kỳ `k` khóa ETH theo số tiền còn phải đóng sau khi nhận:
`contribution × (periods - k - 1) × tỷ lệ`. Mỗi kỳ đóng tiếp thành công sẽ
giải phóng phần ETH tương ứng. Nếu cấu hình `stress_drop` và
`liquidation_slippage`, tỷ lệ tối thiểu được nâng thành
`1 / ((1 - stress_drop) × (1 - liquidation_slippage))` cho cả hai chính sách.
Giá trị vượt 100% là có chủ đích; đây là kịch bản thử sức chịu đựng, không phải
bảo đảm trước mọi cú sập. Trượt giá cũng được trừ khi thanh lý thực tế trong
mô phỏng. Không cấu hình `stress_drop` thì tỷ lệ ký quỹ cũ được giữ nguyên.

Hai cấu hình sau dùng cùng 6 người, seed và cú giảm 40% vào ngày 30; người nhận
đầu tiên bùng đúng ngày đó. Cấu hình thứ nhất giữ ký quỹ cố định 50%, cấu hình
thứ hai đặt mức đủ chịu cú giảm 40% và trượt giá 10%:

```powershell
.\.venv\Scripts\rosca-sim.exe run --config configs/six-member-drop40-baseline.toml --output results/six-member-baseline
.\.venv\Scripts\rosca-sim.exe run --config configs/six-member-drop40-covered.toml --output results/six-member-covered
```

Xem dòng `policy=fixed` trong `run_results.csv` và từng lượt trong
`recipient_results.csv` để đối chiếu. Với người nhận đầu tiên, mức ký quỹ
stress là khoảng 925,93 USDC cho nghĩa vụ 500 USDC. Mức này lớn hơn lợi ích
nhận sớm ròng, nên kết quả an toàn phải được đánh giá cùng tính hấp dẫn của
dây hụi. Mô hình vẫn bán theo giá đóng cửa hằng ngày, không mô phỏng râu nến
trong ngày hay thời gian chờ thanh lý.

Để xem đánh đổi ở các mức ký quỹ khả thi hơn, giữ nguyên người chơi, seed, giá,
trượt giá và sự kiện bùng rồi chỉ thay tỷ lệ cố định:

```powershell
.\.venv\Scripts\rosca-sim.exe sweep --config configs/six-member-drop40-baseline.toml --output results/six-member-frontier --ratios 0.2 0.35 0.5 0.7
```

`frontier.csv` báo ký quỹ và thanh khoản ròng trung bình của người lĩnh đầu,
phần chi trả thiếu trung bình, tỷ lệ lượt chạy có thiếu và mức dự phòng tối đa
cần có sau khi chạy. Mỗi thư mục `ratio-*` giữ kết quả chi tiết của mức đó;
`base-config.toml` là cấu hình gốc, còn tỷ lệ thực chạy nằm trong `frontier.csv`.
Không đặt `stress_drop` cho lệnh `sweep`, vì sàn ký quỹ chịu stress sẽ che mất
sự khác nhau giữa các tỷ lệ thử. Đây là đường đánh đổi trong giả định mô hình,
không phải tỷ lệ an toàn hay mức ký quỹ khuyến nghị cho sản phẩm.

## Dùng giá ETH lịch sử

Để phát lại cả giai đoạn Terra/Luna và FTX năm 2022, tải giá đóng cửa hằng ngày
của cặp giao ngay ETH/USDT từ kho dữ liệu công khai của Binance:

```powershell
.\.venv\Scripts\rosca-sim.exe fetch-binance-prices --start 2021-01-01 --end 2026-08-31 --output data/eth_usdt_binance_2021_2026.csv
.\.venv\Scripts\rosca-sim.exe run --config configs/baseline.toml --output results/historical-full
```

File CSV này không được đưa vào Git. `baseline.toml` dùng toàn bộ khoảng 2021–2026;
mỗi lượt chọn một cửa sổ lịch sử hoàn chỉnh và hai chính sách dùng cùng cửa sổ đó.
Nguồn là ETH/USDT, nên kết quả giữ giả định USDT tương đương một đơn vị stablecoin;
mô hình không kiểm tra rủi ro USDT mất neo giá.

Để phát lại một cửa sổ cố định gồm tháng 5 và 11/2022, có hai cấu hình với cùng
giá ETH, agent và hai sự kiện bùng sau payout. Cấu hình thứ hai cấp sẵn 800
stablecoin cho quỹ dự phòng:

```powershell
.\.venv\Scripts\rosca-sim.exe run --config configs/2022-crises.toml --output results/2022-crises-unfunded
.\.venv\Scripts\rosca-sim.exe run --config configs/2022-crises-protected.toml --output results/2022-crises-protected
```

Các sự kiện bùng trong hai cấu hình này là stress test được ấn định trước, tách
khỏi quyết định strategic default của agent. Số ngày trong `[events]` tính từ
ngày đầu tiên của cửa sổ (`day = 0`). Quỹ dự phòng là vốn thật được cấp từ ngoài
vòng hụi; số tiền rút và số dư cuối được ghi riêng, không được tự tạo thêm.

Giá đóng cửa được theo dõi từng ngày; đóng góp và quyết định strategic default
vẫn diễn ra vào các ngày đến hạn cách nhau `period_days`. Nếu có sự kiện bùng
giữa kỳ, ETH được định giá bằng giá đóng cửa của ngày đó. Ngày ký quỹ giảm dưới
mức yêu cầu được đếm, nhưng chưa tự động kích hoạt nạp thêm hoặc thanh lý.

Lệnh `fetch-prices` dùng CoinGecko cũ vẫn có thể tạo CSV cùng định dạng nếu API
của tài khoản cho phép khoảng ngày cần tải. Khóa API được đọc từ biến môi
trường `COINGECKO_API_KEY` hoặc file `.env`; muốn dùng dữ liệu ấy, chỉnh
`[prices].file`, `start_date` và `end_date` trong TOML. Lệnh mô phỏng chỉ đọc
CSV cục bộ và không tự truy cập mạng.

File giá phải có hai cột `date,close`, mỗi ngày xuất hiện đúng một lần và giá phải dương. Một cửa sổ lịch sử cần đầy đủ **mọi ngày** trong vòng hụi; nếu thiếu ngày, cửa sổ đó không được chọn.

Phát lại giá lịch sử là phân tích có điều kiện: nó cho biết mô hình sẽ ứng xử thế nào dưới các đường giá đã quan sát, không phải dự báo giá ETH. Khi chạy kết quả dùng cho luận văn, cần khóa TOML, seed, khoảng ngày và file dữ liệu tại cùng một mốc chốt.

## Kết quả

Mỗi thư mục kết quả gồm:

- `run_results.csv`: hai dòng chính sách cho mỗi `run_id`.
- `paired_results.csv`: chênh lệch của chính sách điều chỉnh uy tín so với chính sách cố định trên cùng đầu vào.
- `recipient_results.csv`: payout thực nhận, phần thiếu, giá trị ETH ký quỹ lúc nhận tính bằng stablecoin và thanh khoản ròng của từng người.
- `summary.json`: tỷ lệ lượt/người nhận thiếu và nhu cầu dự phòng trung bình, bách phân vị 95, cao nhất trong mẫu chạy.
- `metadata.json`: phiên bản chương trình/Mesa, seed, số lượt chạy và nguồn giá; với dữ liệu lịch sử còn có SHA-256 của CSV.
- `config.toml`: bản sao nguyên văn cấu hình đã chạy.

Chỉ số chính gồm số lần bùng, tổn thất sau thanh lý, payout thiếu của người nhận,
quỹ dự phòng đã dùng, vốn thế chấp khóa và tỷ lệ kỳ được chi trả đủ.
`reserve_required_for_full_payouts` là mức dự phòng tối thiểu **tính sau khi chạy**
cho chính đường giá và hành vi đã xảy ra; đó không phải bảo đảm cho tương lai.
`risk_equivalent=true` so sánh tổn thất sau thanh lý; `participant_risk_equivalent=true`
so sánh phần payout thiếu. Tổng `capital_locked` là tổng mức ký quỹ lúc từng người
nhận payout, không phải lượng vốn bị khóa đồng thời ở một ngày bất kỳ.
`net_liquidity` là payout trừ giá trị ký quỹ lúc nhận, theo góc nhìn người nhận;
chi phí cấp vốn cho quỹ dự phòng được báo riêng qua `reserve_initial` và
`reserve_drawn`.

Mô hình bán ETH theo giá đóng cửa tại ngày bán sau trượt giá cấu hình, chưa mô phỏng phí
thanh lý, cú giảm trong ngày, mất neo stablecoin hay khả năng chi trả của bên
cấp vốn dự phòng. Các giới hạn này cần được xét trước khi diễn giải kết quả như
một cam kết an toàn trong triển khai thực tế.

## Đợt A — lãi năm và ngưỡng ký quỹ trên giá ETH 2022

Auction dùng lãi đơn ACT/365, tối đa `annual_rate = 0.20` (20%/năm),
không phải khấu trừ 20% quỹ lĩnh. Đây là quy ước nghiên cứu, không chứng nhận
tuân thủ pháp luật. Schema JSON cũ và TOML `rate` bị từ chối; không đổi nhãn
kết quả gross-discount cũ để dùng làm kết quả mới.

Chạy từ thư mục dự án bằng Python trong `.venv`. Không tải mạng khi chạy nghiên cứu.
Kiểm tra quy mô trước (không tạo thư mục kết quả, không chạy mô hình):

```powershell
.\.venv\Scripts\python.exe -m rosca_sim.cli auction-phase-a --prices data/eth_usdt_binance_2022.csv --output results/phase-a-2022-annual --source-label "Binance ETHUSDT daily close 2022" --quote-asset USDT --dry-run
```

CSV đủ 365 ngày năm 2022 cho 208 cửa sổ 158 ngày, 57 nhóm/mốc bùng,
5 mức lãi năm 0/5/10/15/20% và 8 mức ký quỹ 25–200%: **474.240 lượt coarse**.
Thiếu ngày thì chỉ dùng cửa sổ liên tục hợp lệ và báo số thực tế, không đệm giá.
Trượt giá cố định 0; người bùng bán ETH ngay ngày kế sau lĩnh; người khác trả
đủ nghĩa vụ USDC vào ngày thứ 7. Giả định đủ ETH để lĩnh, không phải kiểm tra khả thi vốn.

Sau khi quyết định chạy thí nghiệm, đo một job trước; chưa đủ để kết luận ngưỡng chung:

```powershell
.\.venv\Scripts\python.exe -m rosca_sim.cli auction-phase-a --prices data/eth_usdt_binance_2022.csv --output results/phase-a-2022-annual --source-label "Binance ETHUSDT daily close 2022" --quote-asset USDT --annual-rate 0.20 --ratio 1.00
```

Cùng lệnh nhưng bỏ hai selector sẽ chạy 40 coarse jobs tuần tự. Thêm `--refine`
sau khi coarse đầy đủ để thử bước 5 điểm phần trăm trong các khoảng gợi ý;
mọi điểm mới đều chạy cả 5 mức lãi và toàn bộ cửa sổ/nhóm bùng. `--aggregate-only`
chỉ tổng hợp job đã có. Các mode không dùng cùng nhau hoặc cùng selector;
selector phải có cả rate và ratio (lưới 5 điểm, 25–200%).

Mỗi job hoàn tất được lưu riêng trong `jobs/`, tái dùng khi fingerprint CSV,
source code, cửa sổ và quy ước khớp. Job lỗi/dở dang không thành PASS; job hoàn tất
bị sửa/hỏng hoặc khác fingerprint sẽ bị từ chối. Đổi dữ liệu/code dùng thư mục
kết quả mới. Chỉ chạy một tiến trình trên cùng thư mục kết quả; không hỗ trợ worker pool.
Thời gian mỗi job được lưu trong checkpoint; chưa có benchmark nghiên cứu đầy đủ.

Đầu ra:

- `phase_a_summary.csv`: mất gốc lớn nhất toàn dây/từng người cùng cửa sổ tương ứng;
  lãi đã dùng/nợ chưa thu gắn với cửa sổ mất gốc cá nhân tệ nhất, không phải max riêng.
- `phase_a_worst_members.csv`: 6 người ở cửa sổ tệ nhất của từng nhóm điều kiện.
- `phase_a_thresholds.csv`: 285 ngưỡng riêng, 5 ngưỡng theo lãi, 1 ngưỡng chung;
  `incomplete` nếu thiếu bất kỳ kiểm tra cần thiết, `not_found` nếu không có giao
  mức đạt trong lưới đã thử. Có cờ PASS rồi FAIL ở mức cao hơn (`nonmonotonic`).
- `phase_a_metadata.json`: phạm vi, nguồn/đơn vị/hash, annual semantics và độ đầy đủ.

Ngưỡng là mức nhỏ nhất **đã thử** mà mọi người mất gốc không quá sai số `1e-9` USDC;
không làm tròn trước xét. Cửa sổ chồng lấn không độc lập, tỷ lệ cửa sổ lỗ không
phải xác suất mất tiền. ETH/USDT được xem tương đương ETH/USDC trong mô hình.
Không bảo đảm an toàn tương lai, không mô phỏng hành vi chống Sybil/game theory.
## Phase B: bùng tại kỳ góp

Phase B dùng dây sáu người, 100 USDC mỗi 30 ngày. Trước khi thu tiền ở kỳ mới, mô hình kiểm tra người đã lĩnh và còn nghĩa vụ. Trong nhánh bùng do giá, họ bỏ góp nếu giá trị ETH có thể thu hồi thấp hơn nghĩa vụ còn lại. Mô hình dừng dây trước khi thu tiền của kỳ đó. Cú giảm giữa kỳ không kích hoạt quy tắc này. Nhánh bùng đặt trước xét các nhóm từ thứ tự lĩnh thực tế, gồm đủ 57 nhóm và thời điểm trên mỗi cửa sổ trong lượt chạy đầy đủ.

Khi dây dừng, người đã lĩnh và vẫn trả thử nộp 0%, 50% hoặc 100% nghĩa vụ còn lại sau 7 ngày. ETH bù phần chưa trả theo quy tắc quyết toán hiện có. Mô hình so sánh bid đồng loạt 0%, đồng loạt 20% và bid trộn. Giá Binance ETH/USDT đóng cửa theo ngày là giá đại diện tại hạn góp và lúc bán, với giả định USDT≈USDC, trượt giá 0 và đủ ETH để lĩnh.

Chạy từ thư mục dự án sau khi cài `pip install -e ".[dev]"`. Chọn một mốc cuối tháng đã hoàn chỉnh và dùng cùng mốc cho tải dữ liệu và chạy mô phỏng. Các lệnh dưới đây dùng dữ liệu đến 31/10/2026.

```powershell
python -m rosca_sim.cli fetch-binance-prices --start 2022-01-01 --end 2026-10-31 --output data/eth_usdt_binance_phase_b.csv
python -m rosca_sim.cli auction-phase-b --prices data/eth_usdt_binance_2022.csv --end 2022-12-31 --source-label "Binance spot ETHUSDT" --output results/phase-b-pilot-2022 --pilot
python -m rosca_sim.cli auction-phase-b --prices data/eth_usdt_binance_phase_b.csv --end 2026-10-31 --source-label "Binance spot ETHUSDT" --output results/phase-b-2022-2026 --dry-run
python -m rosca_sim.cli auction-phase-b --prices data/eth_usdt_binance_phase_b.csv --end 2026-10-31 --source-label "Binance spot ETHUSDT" --output results/phase-b-2022-2026 --full
python -m rosca_sim.cli auction-phase-b --prices data/eth_usdt_binance_phase_b.csv --end 2026-10-31 --source-label "Binance spot ETHUSDT" --output results/phase-b-2022-2026 --aggregate-only
```

Chạy một tiến trình CLI cho mỗi thư mục đầu ra. Chạy lại cùng lệnh để dùng các checkpoint đã hoàn tất. Khi đổi CSV, phạm vi hoặc phiên bản mã, tạo thư mục kết quả mới. Kết quả Phase A cũ gắn với fingerprint của phiên bản mã lúc chạy và dùng lịch bùng khác.

- `phase_b_summary.csv` có độ bao phủ, mất gốc cá nhân lớn nhất, lãi bù gốc, nghĩa vụ chưa thu và số lần phát sinh động cơ bùng. Các tổng cộng dồn qua nhiều tình huống.
- `phase_b_thresholds.csv` cho thấy trạng thái tại 180% và mức nhỏ nhất trong **các mức đã thử** có hoàn đủ gốc. Lượt đầy đủ luôn kiểm tra 180%. Runner dùng mức thấp nhất đạt ở pilot làm điểm dò, hoặc 180% nếu pilot chưa tìm thấy mức đạt. Runner dò theo bước 5 điểm phần trăm đến ranh giới cục bộ hoặc hết khoảng 25–200%. `not_found` nghĩa là chưa có mức đạt trong tập đã thử.
- `phase_b_payouts.csv` có ETH khóa, USDC thực nhận và tỷ số vốn khóa theo thứ tự lĩnh. Một tỷ số dùng tiền thực nhận, một tỷ số trừ tiếp 100 USDC đã góp ở kỳ lĩnh.
- `phase_b_metadata.json` ghi ngày chốt, SHA256 của dữ liệu và độ đầy đủ. Checkpoint từng nhóm cấu hình giữ một tình huống xấu nhất để đối chiếu.

Chỉ diễn giải các kết quả trong tập điều kiện đã chạy. Các cửa sổ lịch sử chồng lấn và các nhóm bùng đặt trước không cho biết xác suất mất tiền. Tỷ số vốn khóa là thước đo gánh nặng vốn, còn khả năng và ý muốn tham gia cần dữ liệu về người chơi.

### Phase B trên 200%

Lệnh dưới đây dùng bản CSV Phase B đến 31/10/2026, có SHA256 được kiểm tra tự động. Sàng lọc 205–300% bằng các cửa sổ bất lợi, sau đó quét đầy đủ từ mức thấp nhất còn lại đến điểm đầu tiên đạt.

```powershell
python -m rosca_sim.cli auction-phase-b-upper --prices data/eth_usdt_binance_phase_b.csv --end 2026-10-31 --output results/phase-b-upper-2022-2026 --dry-run
python -m rosca_sim.cli auction-phase-b-upper --prices data/eth_usdt_binance_phase_b.csv --end 2026-10-31 --output results/phase-b-upper-2022-2026 --run
python -m rosca_sim.cli auction-phase-b-upper --prices data/eth_usdt_binance_phase_b.csv --end 2026-10-31 --output results/phase-b-upper-2022-2026 --aggregate-only
```

Đọc trạng thái ở `threshold.json`. Trong bảng `phase_b_upper_ratios.csv`, `fail_witness` nghĩa là đã có ca mất gốc, `full_pass` là đạt qua toàn bộ lượt bắt buộc, `not_scanned` là chưa quét đủ để kết luận. Dùng lại cùng lệnh `--run` để tiếp tục một thư mục có fingerprint khớp. Mỗi thư mục đầu ra dành cho một tiến trình chạy.

