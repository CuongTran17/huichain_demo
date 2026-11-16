# Đặc tả web khám phá kết quả đợt A

**Trạng thái:** Đã triển khai và nghiệm thu ngày 2026-10-16 theo implementation plan `docs/superpowers/plans/2026-10-16-phase-a-results-explorer.md`. Toàn suite 242 tests đạt, có review độc lập và kiểm tra trình duyệt desktop/hẹp. Báo cáo: `docs/superpowers/reports/2026-10-16-phase-a-results-explorer-verification.md`. Chỉ commit cục bộ trên main, không push.

## 1. Mục tiêu và phạm vi đã chốt

Người nghiên cứu dùng web nội bộ trên máy để hiểu đánh đổi giữa ký quỹ ETH, mất gốc và quỹ lãi của nghiên cứu ETH 2022. Có thể đổi bộ lọc, xem đồ thị rõ ràng và chạy lại một tình huống để giải thích diễn biến. Không biến dashboard thành sản phẩm tài chính hay một nghiên cứu mới.

- Thêm chế độ **Kết quả nghiên cứu 2022** vào Streamlit hiện có, giữ hai chế độ cũ và lệnh khởi động hiện tại.
- Dùng bộ kết quả ở `results/phase-a-2022-annual`, mặc định giá ở `data/eth_usdt_binance_2022.csv`; cho chọn đường dẫn thư mục kết quả và CSV cục bộ. Không truy cập mạng.
- Bộ thật hiện có: 180 jobs, 36 tỷ lệ 25–200% bước 5 điểm phần trăm, 5 mức lãi năm, 57 nhóm/mốc, 208 cửa sổ; 2.134.080 engine runs. Ngưỡng theo lãi 0/5/10/15/20% lần lượt 185/175/160/150/140%; chung 185%. Đây là dữ liệu nghiệm thu, không hard-code để tạo kết quả.
- Chỉ đổi cách xem hoặc chạy lại một case thuộc phạm vi nghiên cứu; không sửa số người, tiền góp, cách tính lãi, slippage, nhóm/ngày bùng tùy ý hoặc mở full sweep từ chế độ mới.
- Không thêm dependency, frontend riêng, backend/API, cơ sở dữ liệu, đăng nhập hay triển khai công khai. Dùng Streamlit và Altair đang có.

**Thành công:** Người dùng nhìn ra mức ký quỹ nào còn mất gốc, mở được một phản ví dụ và giải thích tiền thiếu đi đâu; số liệu khớp checkpoint và các chế độ cũ không hồi quy.

## 2. Quy ước hiển thị bắt buộc

- Ký quỹ biểu diễn bằng phần trăm nghĩa vụ còn lại tại lúc lĩnh: `ratio=1.40` hiện **140%**. Lãi `annual_rate=0.20` hiện **20%/năm**; không coi là khấu trừ 20% quỹ lĩnh.
- USDC là đơn vị dòng tiền; giá ETH hiển thị USDT/ETH với giả định 1 USDT ≈ 1 USDC. Tiền hiển thị hai số lẻ, tooltip cho phép xem giá trị chưa làm tròn. Xét PASS vẫn dùng tolerance 1e-9 như runner.
- `k` là **số người đã lĩnh tại lúc bùng**, không phải số người bùng. Nhóm bùng là tập con của người đã lĩnh. UI dùng Người 1–6; dữ liệu và mã vẫn ID0–5, chuyển đổi nhất quán ở nhãn.
- Ghi rõ giá đóng cửa 2022, trượt giá0, giả định đủ ETH và người tuân thủ trả đủ USDC ngày7, ETH giữ nguyên lượng đến quyết toán, lãi chung có thể dùng bù gốc.
- Không dùng nhãn “an toàn tuyệt đối”, “xác suất mất tiền” hoặc “lãi chắc chắn”. Dùng “Không mất gốc trong bộ điều kiện đã thử”.
- Giữ đúng quy ước annual_simple_act365 hiện tại. Phân biệt đây là lãi tính trên nghĩa vụ ban đầu cho thời gian còn lại, không phải dư nợ giảm dần; chưa xác nhận tuân thủ pháp luật. Không âm thầm sửa quy ước khi làm UI.

## 3. Bố cục và tương tác

Một chế độ nghiên cứu, ba vùng theo chiều dọc. Ngưỡng toàn nghiên cứu nằm riêng với vùng lọc và chi tiết. Không bắt người dùng xem một bảng hàng nghìn dòng trước khi thấy đồ thị.

### 3.1. Tổng quan toàn nghiên cứu

- Tiêu đề **Kết quả nghiên cứu ETH 2022**, cảnh báo diễn giải ngắn luôn thấy được, đường dẫn và fingerprint rút gọn; phần mở rộng chứa provenance và giả định đầy đủ.
- Hiển thị jobs có/expected, tổng runs hoàn tất/expected, số cửa sổ và trạng thái dữ liệu. Đếm từ checkpoint hợp lệ, không tin riêng `aggregate_status` cũ hoặc suy số runs từ số tệp.
- Đồ thị cột lãi năm → ngưỡng nhỏ nhất đã thử, luôn dùng toàn bộ nhóm/cửa sổ/tỷ lệ planned của nghiên cứu. Đủ dữ liệu thật phải ra 185/175/160/150/140%.
- Chỉ báo ngưỡng chung lấy giao các tập PASS toàn nghiên cứu, dự kiến185%. Bộ lọc bên dưới và việc ẩn đường biểu đồ không thay đổi chỉ báo này. Ghi rõ phạm vi toàn nghiên cứu ngay cạnh số.
- Thiếu kiểm tra thì ngưỡng liên quan hiện **Chưa đủ dữ liệu**, không hiển thị số0 hoặc dùng số complete cũ. `not_found` là **Chưa tìm thấy trong lưới đã thử**, khác với `incomplete`. Không tạo thêm ngưỡng “theo bộ lọc” trong bản đầu.

### 3.2. Khám phá rủi ro

**Bộ lọc:** multiselect lãi năm, khoảng ký quỹ trên các điểm đã thử, multiselect `k`1–5, multiselect nhóm `(k, default_ids)`. Mặc định toàn bộ. Danh sách nhóm cập nhật theo các `k` đã chọn; không tự giữ lựa chọn không còn hợp lệ. Đổi bộ lọc chỉ xử lý dữ liệu đã nạp, tuyệt đối không gọi engine.

**Đồ thị đường:** trục X ký quỹ, trục Y chọn một trong hai chỉ số:

1. **Mất gốc cá nhân lớn nhất (USDC):** maximum của `max_individual_loss` trên các nhóm còn trong bộ lọc tại mỗi `(annual_rate, ratio)`.
2. **Số tình huống mất gốc:** sum `loss_window_count` trên cùng tập nhóm. Tooltip ghi số mất gốc, số runs đã có và expected. Không đổi tên thành số ngày hoặc số người mất tiền; một cửa sổ có thể xuất hiện ở nhiều nhóm.

Mỗi mức lãi một màu cố định, có nhãn/chú giải và tooltip; điểm dữ liệu không chỉ có đường nội suy. Trục tiền mặc định tuyến tính bắt đầu0. Có zoom/pan trục X, nút hoặc thao tác đặt lại khung nhìn được hướng dẫn rõ. Tooltip cho biết `k`/nhóm/cửa sổ gây maximum khi chỉ số có worst-case tương ứng; không gán một worst-case duy nhất cho chỉ số tổng đếm.

**Bản đồ nhiệt:** chọn đúng một mức lãi trong bộ lọc; trục X ký quỹ, trục Y số người đã lĩnh, ô là maximum `max_individual_loss` trên các nhóm được chọn tại ô đó. Tooltip gồm tỷ lệ, lãi, `k`, nhóm gây worst, raw loss, ngày bắt đầu và coverage. Thiếu job hoặc nhóm do bộ lọc: ô không có dữ liệu, không tô như mất gốc0.

Mỗi đồ thị có tiêu đề, đơn vị và dòng phạm vi: bao nhiêu nhóm, bao nhiêu cửa sổ, bao nhiêu runs. Nếu thiếu job, không cộng thiếu thành0, không nối đường xuyên điểm thiếu như một kết quả đã kiểm tra; đánh dấu các điểm tổng hợp thiếu coverage. Mất gốc lớn nhất quan sát được trên phần đã có phải ghi là chưa đầy đủ, không gọi là maximum của bộ đầy đủ.

Không lọc ngày bắt đầu cho các đồ thị tổng hợp ở bản đầu: checkpoint chỉ có thống kê trên208 cửa sổ và các cửa sổ worst, không có kết quả riêng mọi cửa sổ. Không dựng histogram mất gốc từng run hoặc đồ thị lãi dùng tối đa toàn lịch sử từ dữ liệu không lưu.

### 3.3. Chi tiết một dây

- Chọn một `(annual_rate, ratio, k, default_ids)` hợp lệ từ các nhóm điều kiện còn trong bộ lọc. Tỷ lệ và lãi chỉ nằm trong tập đã thử của nghiên cứu.
- **Mở trường hợp tệ nhất** chọn summary có `max_individual_loss` lớn nhất trong bộ lọc; tie theo ngày worst sớm nhất rồi khóa `(annual_rate, ratio, k, default_ids)` tăng dần để ổn định. Thao tác này chỉ đổi lựa chọn, chưa gọi engine.
- Nút chọn **Cửa sổ mất gốc cá nhân tệ nhất** lấy `worst_individual_start`. Cho chuyển sang **Cửa sổ mất gốc toàn dây tệ nhất** lấy `worst_total_start`, hoặc chọn một trong các starts đã có trong manifest.
- Bấm **Xem diễn biến** mới chạy đúng một engine run cùng scenario đợt A và seed42. Không gọi paired policy hoặc sweep. Kết quả chỉ ở session/cache, không ghi vào thư mục nghiên cứu.
- Nhãn rõ **Chạy lại một tình huống**, kèm cấu hình, ngày cửa sổ và fingerprint. Đối với cửa sổ worst đã lưu, đối chiếu result với summary/member rows tương ứng; sai lệch vượt tolerance thì cảnh báo không khớp, không xác nhận tái lập. Worst member rows chỉ đại diện cửa sổ worst-individual, không dùng để đối chiếu nhầm worst-total hoặc cửa sổ tùy chọn.
- Đối chiếu worst-individual dùng worst_member_loss, interest_used, obligation_uncollected và sáu member rows đã lưu; đối chiếu worst-total dùng principal_loss với max_total_loss. Chỉ kết hợp hai nhóm kiểm tra nếu cùng ngày cửa sổ. Không yêu cầu các chỉ tiêu khác đạt maximum ở một cửa sổ không được lưu cho chỉ tiêu đó.
- Khi chọn một cửa sổ khác, kết quả là kiểm tra riêng trong bộ starts, không tự gán lại ngưỡng hoặc sửa summary gốc.
- Biểu đồ giá ETH theo ngày, đánh dấu lĩnh, đóng băng, bán ETH và hạn quyết toán; không coi giá đóng cửa là chứng cứ khớp lệnh thực.
- Biểu đồ góp/lĩnh lũy kế theo người, tiền quỹ và lãi giữ lại tại các mốc engine có trace. Cho chọn mốc đầu/kỳ đã chạy/đóng băng/quyết toán bằng điều khiển từng bước; các mốc đóng băng và quyết toán dùng thông tin sự kiện/result có thật, không bịa snapshot tiền/ETH chưa được engine ghi. Không nội suy số dư mỗi ngày từ các trace kỳ.
- Biểu đồ cột quyết toán theo người tách hoàn gốc, mất gốc, lãi nhận; tách khoản lãi đã dùng bù gốc và nợ chưa thu thành các chỉ tiêu có nhãn, không cộng chúng hai lần vào cùng tiền thu hồi. Nêu rõ principal_claim hiện chỉ dành cho người chưa lĩnh, không phải thước đo toàn bộ lãi/lỗ kinh tế của người giữ ETH.
- Đổi lựa chọn case/cửa sổ/nguồn sau khi đã xem phải ẩn kết quả cũ hoặc gắn nhãn **Chưa chạy lại theo lựa chọn mới**, không đổi nhãn của run cũ. Đổi mốc/chú giải/zoom của một run không gọi engine lần nữa.

## 4. Nguồn dữ liệu và tính toàn vẹn

Nguồn chuẩn để dựng số liệu là manifest và các job JSON đã xác thực. CSV tổng hợp là export tham khảo, không phải nguồn duy nhất để công bố PASS: CSV có thể là bản cũ khi nghiên cứu đang mở rộng lưới hoặc bị ngắt.

- Reader không gọi `aggregate_phase_a`, `prepare_phase_a`, `plan_phase_a_refinement` hoặc runner có ghi tệp. Không sửa bất kỳ checkpoint, CSV, metadata hoặc report cũ khi mở web/lọc/replay/download.
- Tái dùng kiểm tra `_manifest`, `_read_job` và thuật toán `_threshold_rows` hiện có qua adapter mới; không fork công thức ngưỡng hoặc waterfall. Đây là phụ thuộc nội bộ có kiểm thử, không tái cấu trúc core ở đợt làm UI.
- Duyệt đúng các jobs kỳ vọng từ annual_rates × planned_ratios. Job thiếu làm coverage incomplete; job tồn tại nhưng hỏng JSON/hash/fingerprint/counts/semantics làm lỗi nguồn, không âm thầm bỏ để dựng đồ thị đẹp. File `.tmp` không phải job hoàn tất.
- Hỗ trợ study_version1, result_schema_version2, annual_simple_act365, cấu hình cố định đợt A. Legacy gross-discount hoặc code hash không khớp phải giải thích rõ không tương thích; không tự sửa metadata để nạp.
- Dữ liệu CSV giá chỉ cần cho replay. Thiếu hoặc SHA256 không khớp manifest: vẫn có thể xem các tổng hợp checkpoint hợp lệ, nhưng không vẽ giá hay chạy replay với nguồn khác.
- Dữ liệu nguồn thay đổi trong lúc đọc phải báo tải lại; không ghép các phiên khác nhau thành complete. Giả định một writer, không xây khóa phân tán hoặc cơ chế phục hồi giao dịch nhiều tệp.
- Đọc các jobs lần lượt, giữ summaries/thresholds và metadata; chỉ giữ member rows của job được mở khi cần. Không nạp2.13 triệu result/agent objects để làm web.
- Cache theo chữ ký metadata, tập file job kỳ vọng/có thật (tên, kích thước, mtime_ns) và code hashes hiện tại. Chữ ký CSV giá gồm đường dẫn, kích thước, mtime_ns; kiểm SHA256 khi nạp giá. Đọc ổn định trước/sau xác thực; có nút **Tải lại dữ liệu** để bỏ cache khi cần. Không chống sửa file có chủ ý nhưng giữ nguyên mọi thuộc tính cache.

## 5. Tổ chức mã và giao diện

- Sửa `src/rosca_sim/web_app.py` ở điểm chọn chế độ và dispatch, không viết toàn bộ tính năng mới trong tệp hiện đã dài. Giữ state/đường dẫn riêng cho nghiên cứu và các chế độ cũ; nguồn giá/sidebar cũ không vô tình chi phối replay của nghiên cứu mới.
- Thêm `src/rosca_sim/phase_a_results.py`: adapter đọc/xác thực chỉ đọc, phép gộp cho bộ lọc, lựa chọn worst và tái chạy một case. Phần xử lý này không phụ thuộc Streamlit.
- Thêm `src/rosca_sim/web_phase_a.py`: renderer Streamlit và các chart Altair, cache/UI state. Tái dùng `run_named_cases`, `CaseRun`, `trace_rows` và giá/scenario generators hiện có khi phù hợp; không viết engine thứ hai.
- Giữ nguyên `phase_a.py`, `auction.py`, `model.py`, `prices.py`: các tệp này nằm trong fingerprint nghiên cứu đã chạy. Không đổi core chỉ để xuất helper cho UI, vì sẽ làm corpus hiện tại không còn khớp code hash.
- Tests tập trung ở `tests/test_phase_a_results.py`, `tests/test_web_phase_a.py`, regression `tests/test_web_app.py`; cập nhật README cách mở chế độ mới. Implementation plan sau duyệt sẽ chốt interfaces/signatures và chia task TDD.

Thiết kế hiển thị áp dụng landing-page-design cho độ rõ, typography Manrope hiện có, nền phẳng, không dựa vào màu sắc đơn độc, focus bàn phím và trạng thái loading/empty/error cụ thể. Vì người dùng yêu cầu dashboard nội bộ đơn giản, không thêm hero marketing, testimonial, SEO, cookie/tracking, animation cuộn hoặc landing-page reveal. Không tải font/icon mới qua mạng; không dùng số giả để lấp dữ liệu.

Mỗi biểu đồ có bảng số liệu tương ứng trong phần mở rộng và tải CSV tạo trong bộ nhớ. Không ép người dùng rê chuột mới đọc được thông tin thiết yếu; xuất bảng nghiên cứu và chi tiết theo phạm vi đang hiển thị, có cấu hình/provenance đi kèm. Nhãn tiếng Việt ngắn, không trộn thiếu USDC/ETH hoặc phần trăm/thập phân.

## 6. Trạng thái và nghiệm thu

1. Với bộ thật hiện tại, đọc ra180 jobs,10260 summaries,208 starts,36 ratios, tổng2134080 runs; ngưỡng toàn nghiên cứu185% và theo lãi185/175/160/150/140%. Không hard-code con số vào reader/render.
2. Kiểm thử bằng fixture nhỏ có đủ các nhóm/ratios cần thiết, không bắt suite chạy lại nghiên cứu thật. Thiếu job, corrupt job, legacy/schema/basis/code mismatch và CSV giá khác phải ra trạng thái đúng; metadata/CSV cũ ghi complete không được qua mặt reader.
3. Phép gộp lấy max cá nhân và sum số lượt đúng; denominator có/expected rõ, không lấy max của các minimum thay giao tập PASS. Tooltip worst-individual không mượn ngày worst-total. Raw loss1e-10 khác0.01 khi xét PASS.
4. Chuyển bộ lọc, khoảng tỷ lệ, chọn nhóm, reset và zoom thay dữ liệu đúng; bộ lọc rỗng có hướng dẫn, không crash hoặc dùng lại nhóm cũ. Ngưỡng toàn nghiên cứu không đổi theo bộ lọc.
5. Spy engine xác nhận nạp trang/lọc/chọn case không gọi model; nút replay gọi đúng một run, thay mốc không gọi lại. Nguồn không khớp hoặc state cũ không được giả là run mới.
6. Replay fixture và một case thực có phản ví dụ phải khớp các giá trị đã lưu tại cửa sổ tương ứng trong tolerance. Kiểm tra ít nhất hai cửa sổ worst-total/worst-individual khác nhau, một cửa sổ tùy chọn, và case mọi loss0 có tie ngày sớm nhất.
7. Read-only tests chụp bytes/mtimes của corpus và nguồn giá trước/sau nạp/lọc/replay/export để xác nhận không ghi nghiên cứu. Trạng thái dữ liệu đổi trong lúc đọc/cache được xử lý, không thành false complete.
8. Streamlit AppTest cho mode mới và hai mode cũ; kiểm schema chart gồm unit, tooltip, domain rate/ratio đúng. Kiểm tra trực quan bằng trình duyệt khi triển khai: chữ Việt, khả năng đọc trục/chú giải, zoom/reset, bảng thay thế, trạng thái thiếu dữ liệu, màn hình desktop và hẹp. Tối ưu đủ cho10260 summaries; không đặt SLA tốc độ chưa đo.

## 7. Ngoài phạm vi và bước tiếp theo

Không Aave simulation/live rates, game theory, sửa lãi dư nợ giảm dần, margin call, slippage model, dữ liệu sau2022, server công khai, quét triệu lượt trên web hoặc thay đổi giới hạn10000 của chế độ quét cũ. Những thảo luận về tính lãi và khả thi vốn giữ như cảnh báo, không âm thầm đổi nghiên cứu để đẹp số.

Sau khi người dùng duyệt tài liệu này: viết implementation plan theo các phần dữ liệu chỉ đọc, đồ thị/lọc, replay và tích hợp/kiểm thử. Giữ làm trên main, commit cục bộ, không push, không đụng `work/` theo lựa chọn trước của người dùng. Chỉ triển khai sản phẩm sau khi người dùng duyệt implementation plan.
