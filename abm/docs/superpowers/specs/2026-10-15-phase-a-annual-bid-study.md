# Đợt A: lãi năm và ngưỡng bảo vệ gốc trên ETH 2022

**Trạng thái:** Đã triển khai, rà soát độc lập và sửa phát hiện quan trọng; 220 tests đạt. Chưa chạy pilot/quét lịch sử đầy đủ, chưa có ngưỡng mới. Phạm vi được chốt qua trao đổi ngày 2026-10-15. Kế hoạch: `docs/superpowers/plans/2026-10-15-phase-a-annual-bid-study.md`.

## Câu hỏi và phạm vi

Tìm tỷ lệ ký quỹ nhỏ nhất đã thử để mọi người chưa lĩnh được hoàn đủ gốc thực góp, trên mọi cửa sổ hợp lệ năm 2022 và mọi nhóm con người đã lĩnh tại các mốc đã chốt. Đây là ngưỡng có điều kiện của mô hình, không phải bảo đảm ngoài thực tế hay xác suất mất tiền.

- Sáu người ID0–5, sáu lượt lĩnh; mỗi người góp100 USDC mỗi30 ngày. Đây là kỳ30 ngày, không phải tháng lịch.
- Bid là lãi suất năm: 0%, 5%, 10%, 15%, 20%. Trong một case mọi người chào cùng mức, tie-break ID tăng dần nên thứ tự lĩnh0–5. Không mô phỏng hành vi đấu giá tối ưu, Sybil hay hình thành liên minh; chỉ đặt trước các nhóm cùng bùng.
- Ký quỹ cố định từ25% đến200%, bước25 điểm phần trăm; tinh chỉnh bước5 điểm phần trăm. Không uy tín, stress floor, top-up tự động, quỹ ngoài, margin call hay game theory.
- Bước A giả định có đủ ETH để không ai bị bỏ qua vì thiếu ký quỹ; không tuyên bố mức này khả thi về vốn. Bước B xét giới hạn vốn được hoãn.
- Sau khi đã có k người lĩnh, k=1..5, xét mọi tập con không rỗng của ID0..k−1. Bùng ở ngày `(k−1)×30+1`: 1,31,61,91,121. Mỗi run có đúng một batch bùng và dừng ngay; không mô phỏng sự kiện sau đóng băng. Có57 cặp `(k, nhóm)` vì1+3+7+15+31=57.
- Người bùng không nộp USDC; bán ETH ngay ở giá đóng cửa ngày bùng. Người đã lĩnh không thuộc nhóm bùng trả đủ nghĩa vụ còn lại bằng USDC ngày7 sau đóng băng, không bán ETH của họ. Grace7 ngày, `usdc_first`, trượt giá0, không execution-price override.
- Giữ ETH nguyên lượng từ lúc lĩnh tới hoàn thành/quyết toán, ưu tiên hoàn gốc, nguồn lãi nhóm bùng trước rồi nhóm khác, nợ chưa thu tách biệt mất gốc như engine hiện tại. Người chưa lĩnh có claim đúng số thực góp.

## Lãi năm: quy ước nghiên cứu, không chứng nhận pháp lý

Tham chiếu Điều21 Nghị định19/2019/NĐ-CP về giới hạn20%/năm: [Cổng Chính phủ](https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=196233), [giải thích của Báo Chính phủ](https://baochinhphu.vn/quy-dinh-ve-ho-hui-bieu-phuong-102252244.htm). Không đồng nhất20%/năm với20% quỹ lĩnh. Việc áp dụng cho cơ chế khấu trừ trước bằng USDC/ETH chưa được xác nhận tuân thủ pháp luật.

Quy ước lãi đơn ACT/365 cố định, không lãi kép, không APR/IRR hiệu dụng:

`O = contribution × (periods − payout_period − 1)`; `D = (periods − payout_period − 1) × period_days` (period zero-based).

`bid_interest_paid = O × annual_rate × D / 365`; `net_payout = members × contribution − bid_interest_paid`.

Annual rate finite numeric, không bool, `0 ≤ annual_rate ≤ 0.20`. Giá trị lớn hơn0.20 bị từ chối, không tự cắt về trần. Nếu một cấu hình ngoài đợt A làm lãi >=gross pot, từ chối trước dòng tiền của lượt đó, không tạo payout âm. Kỳ cuối O=D=0 nên lãi0 và không khóa ETH. Sau lĩnh vẫn góp100, không thu lãi lần nữa; khoản đã khấu trừ không được tính lại khi quyết toán sớm.

Golden examples (gross600): người đầu O500,D150,r20% trả41.0958904109589, lĩnh558.9041095890411; người thứ hai O400,D120 trả26.3013698630137; kỳ cuối trả0. Nếu mọi lượt cùng20%/năm, hoàn thành thường tích lũy90.4109589041096 tiền lãi. Không hoàn lãi pro-rata khi dừng sớm trong phiên bản này.

## Chuyển đổi đơn vị và dữ liệu cũ

- Đổi `AuctionBid.rate` thành `annual_rate`; kết quả `winning_bid` thành `winning_annual_rate`. Không giữ hai engine hoặc thêm tùy chọn chạy cả hai cơ chế lãi.
- TOML mới dùng `[[bids]].annual_rate`; input cũ có `rate` bị từ chối kèm giải thích. JSON case chuyển schema2, schema1 bị từ chối rõ ràng, không đổi nhãn phiên bản để tái diễn giải số cũ.
- Metadata mới ghi `bid_rate_basis="annual_simple_act365"`, `annual_rate_cap=0.20`, `day_count_basis=365`, `result_schema_version=2`, `collateral_release_policy="terminal"`. Áp dụng cho engine exports/web metadata mới.
- Dữ liệu/demo gross-discount đã chạy giữ nguyên; không ghi đè, không dùng làm bằng chứng cho lãi năm. Cập nhật tests và tài liệu auction đồng bộ; fixed-order không đổi.

## Dữ liệu, lưới và tính đầy đủ

- CSV ETH/USDT đóng cửa ngày, lọc2022-01-01..2022-12-31, không normalize và không tự truy cập mạng khi chạy nghiên cứu. Ghi nguồn, đơn vị và SHA256 nội dung CSV; 1USDT≈1USDC là giả định.
- Mỗi cửa sổ vẫn cần158 ngày theo loader hiện có:150 ngày tới kỳ cuối +1 ngày đầu +7 ngày tail. Không tối ưu cắt ngắn theo ngày bùng, không lặp giá cuối. CSV đủ365 ngày sẽ có208 cửa sổ hợp lệ; thiếu ngày thì loại cửa sổ ảnh hưởng và báo số thực tế, không đệm giá.
- Lưới thô `[0.25,0.50,0.75,1.00,1.25,1.50,1.75,2.00]`. Với208 cửa sổ,57 nhóm,5 mức lãi có474240 run coarse. Đây là số lượng tính trước, không phải benchmark thời gian.
- Một mức tỷ lệ chỉ PASS nếu đủ mọi cửa sổ yêu cầu, không có run lỗi/no-eligible, và mọi member principal_loss≤1e−9 USDC (sai số số học, không phải mức cho phép mất tiền). Giữ số lỗ chưa làm tròn khi xét PASS.
- Ngưỡng riêng cho mỗi `(annual_rate,k,default_ids)` là nhỏ nhất trong lưới đã hoàn tất có PASS trên mọi cửa sổ. Ngưỡng theo mức lãi là giao các tập tỷ lệ PASS của57 nhóm; ngưỡng chung là giao của cả5 mức lãi. Không lấy trung bình ngưỡng; không thay phép giao bằng lấy max khi chưa xác nhận tính đơn điệu.
- Tinh chỉnh: với mỗi ngưỡng coarse riêng/theo lãi/chung có tồn tại, thử các điểm5% bên trong khoảng25% từ coarse ngay trước tới ngưỡng đó, không xuống dưới25%/vượt200%. Lấy hợp các điểm mới và chạy chúng trên toàn bộ bộ điều kiện, không chỉ case gợi ý ngưỡng. Không dùng binary search; giữ và gắn cờ nếu có PASS rồi FAIL ở tỷ lệ cao hơn. Không tìm thấy coarse thì báo not_found trong lưới đã thử, không tuyên bố đã vét mọi mức liên tục.
- Đợt A là mô tả sự bao phủ các đường giá quá khứ; cửa sổ chồng lấn không phải quan sát độc lập, không biến tần suất case lỗ thành xác suất mất tiền.

## Runner và đầu ra tối thiểu

Runner CLI riêng, tuần tự, gọi đúng `AuctionRoscaModel(..., policy="fixed")`, tái dùng loader giá, không viết lại công thức recovery/waterfall. Chuẩn bị208 PricePath một lần; generate case theo nhu cầu, không giữ toàn bộ kết quả agents/trace của hàng trăm nghìn run.

- Chia job theo một `(annual_rate, collateral_ratio)` và stage coarse/refinement. Không database, scheduler, worker pool hay sửa giới hạn10.000 lượt của web. Có lệnh dry-run và chạy một job để đo thời gian trước full sweep; chỉ báo ETA sau có thời gian đo.
- Mỗi job ghi tệp tạm rồi publish sau hoàn tất tất cả windows×57 cases. Chỉ reuse job đã hoàn tất có fingerprint khớp: study version, SHA256 source ảnh hưởng (phase_a/auction/model/prices), CSV hash, danh sách windows và tham số; mã Git nếu khả dụng là thông tin thêm, không thay code hash khi cây dirty. Không reuse partial, không ghi đè job hoàn tất không khớp. Đây là checkpoint file đơn giản, không hệ thống resume tổng quát.
- `phase_a_summary.csv`: mỗi `(annual_rate,ratio,k,default_ids)` có expected/completed windows, loss-window count, max total loss, max individual loss và ngày bắt đầu tương ứng của mỗi maximum. Interest used và uncollected debt gắn với worst-individual-loss window, không gọi đó là maximum riêng của hai chỉ số này; initial collateral value báo maximum riêng. Tie chọn ngày sớm nhất. Raw agent rows chỉ xuất cho worst-individual-loss window theo từng summary key; không đổ toàn bộ hàng triệu agent rows.
- `phase_a_thresholds.csv`: các dòng scope case/rate/global, ratio ứng viên hoặc null, tập tỷ lệ đã thử, số kiểm tra hoàn tất và status `complete`/`incomplete`/`not_found`. Một job thiếu/lỗi khiến aggregate chưa được công bố là ngưỡng chung đạt; không âm thầm bỏ run xấu.
- `phase_a_worst_members.csv` và `phase_a_metadata.json`: đủ đầu vào để tái lập case tệ nhất, có annual-rate semantics và giới hạn diễn giải. Không cần biểu đồ/UI mới ở đợt này; CSV mở bằng công cụ sẵn có.

## Ngoài phạm vi

Không quét ngày bùng, slippage, payment capacity/day, settlement mode, số người hay thị trường khác. Chưa làm smart contract/demo ví, KYC/duyệt người, nghiên cứu game theory, hay cơ chế chống Sybil. Kết quả không đánh giá người chơi thật có đủ ETH hay có sẵn USDC trả đúng ngày7. Mở rộng dữ liệu2022..hiện tại là đợt kế tiếp sau khi chốt kết quả năm2022, không tự thêm dữ liệu đó ở lần chạy này.
