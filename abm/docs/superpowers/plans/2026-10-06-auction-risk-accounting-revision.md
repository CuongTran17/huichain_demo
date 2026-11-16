# Auction Risk Accounting Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Giữ ETH đến cuối dây, làm rõ nguồn lãi bảo vệ gốc và nguyên nhân thiếu hụt, rồi cập nhật web để đánh giá cả tổn thất và khả năng thực hiện lượt lĩnh.

**Architecture:** Sửa trực tiếp auction model và các bộ xuất kết quả hiện có, không đổi fixed-order model. Kết quả engine là nguồn dữ liệu chính cho CSV/Streamlit; không tính lại waterfall trong dashboard. Giữ schema cũ và bổ sung trường có tên rõ ràng, cập nhật mọi chỗ khởi tạo dataclass.

**Tech Stack:** Python >=3.12, Mesa 3.5.1, Streamlit hiện có, standard library, pytest; không thêm dependency.

**Hoàn thành ngày 2026-10-15:** Bốn task triển khai trong các commit `888a10c`, `41ef955`, `c90405e`, `851a1cf` trên main; không push. Toàn repo **180 test PASS**, compileall và diff check đạt. Reviewer độc lập không có finding cần sửa (thêm kiểm tra in-memory/accounting; không chạy lại toàn bộ suite web).

**Demo đã kiểm chứng:** `results/auction-risk-revision-demo/` có 8 case, CSV so sánh/từng người/trace và metadata SHA-256 giá Binance ETHUSDT 2022. Chung ngày bắt đầu 2022-04-01, seed42; AppTest nạp cả 8 case và đối chiếu bảng UI với engine. Không thêm giá giả vào demo; trượt giá vẫn là giả định độ nhạy. Dữ liệu và kết quả là artifact ignored, cần giữ riêng nếu sao chép repo.

**Spec:** `docs/superpowers/specs/2026-10-02-auction-rosca-stop-settlement-design.md`, gồm revision decisions ngày 2026-10-06.

**Rà soát lại ngày 2026-10-15:** Giữ một kế hoạch duy nhất ở file này, không tạo bản sao. Đối chiếu với commit `e226764`: code vẫn giải phóng ETH từng kỳ và chưa có các trường nguồn lãi/shortfall/coverage bên dưới. Cơ chế skip người thiếu ETH, `no_eligible_bid`, trả ETH terminal và lọc candidate không khả thi đã có; tận dụng và kiểm thử lại, không viết lại engine.

**Lịch sử kiểm chứng:** Lượt chuẩn bị trước triển khai từng dừng vì test web chậm. Trong triển khai đã truy ra socket nội bộ Streamlit bị sandbox chặn; cấp quyền loopback và dùng TEMP/TMP trong repo thì web baseline15 test PASS, full suite sau Task3 đạt167 và suite cuối đạt180. Không sửa ứng dụng để né hạn chế môi trường.

## Global Constraints

- Làm trên main, chỉ commit trên máy, không push; không sửa/thêm `work/` vào commit.
- Auction giữ `members == periods >= 6`, góp cố định; đã lĩnh không thắng bid lần nữa.
- Bid 20% × gross pot 600: lĩnh 480, lãi trả 120 nằm trong pool, không hoàn như ký quỹ và không thu thêm lãi ở kỳ sau.
- ETH khóa lúc lĩnh theo tỷ lệ × nghĩa vụ tương lai / giá; không trừ bid. Giữ nguyên lượng khóa đến hoàn thành/quyết toán.
- Bùng đầu tiên dừng cả dây; cùng thời điểm xử lý một batch; không tiếp tục kỳ góp sau đóng băng.
- Dùng USDC/ETH thực thu và lãi giữ lại hoàn gốc trước; bù gốc không xóa nghĩa vụ chưa thu.
- Giữ hai chế độ `eth_first`/`usdc_first`, grace mặc định 7 ngày; không margin call cưỡng chế, cash wallet, game theory hay dây con.
- Giá đóng cửa lịch sử không phải giá khớp lệnh; slippage 0/5/10% là giả định. Không tự đặt execution override hay stress floor cho baseline.
- Giữ rõ hai tầng kiểm chứng: giá hằng số/shock nhân tạo chỉ dùng làm unit test dễ đối chiếu số học; thí nghiệm/demo lịch sử dùng dữ liệu ETH thật, không gọi fixture là kết quả thị trường.

## Review Focus

1. Nghĩa vụ giảm nhưng ETH không trả giữa dây; cuối dây trả đúng lượng còn lại, không trả hai lần (Task 1).
2. Nhiều người bùng cùng lúc: đảo thứ tự sự kiện không đổi nguồn lãi sử dụng hay dòng tiền (Task 2).
3. Người không gây đóng băng vẫn thiếu nghĩa vụ sau quyết toán: không nhập vào `default_count` hay nhóm lãi của người gây bùng (Task 2).
4. Không có bid/không đủ ETH khác default; góp đã thu vẫn được hạch toán, zero-loss không trở thành ngưỡng an toàn (Tasks 3–4).
5. Nghĩa vụ bằng 0, ETH giá thấp, cấu hình slippage sai và chỉnh scenario sau chạy: không chia 0, không thanh lý do chỉ báo và không hiển thị kết quả cũ như mới (Tasks 3–4).

## File map và lệnh kiểm tra

- `src/rosca_sim/auction.py`: góp/khóa ETH, trạng thái quyết toán, nguồn lãi và period trace.
- `src/rosca_sim/auction_experiment.py`: xuất dataclass/metadata; không fork phép tính.
- `src/rosca_sim/web_reporting.py`: bảng kết quả, coverage chỉ báo và frontier.
- `src/rosca_sim/web_app.py`: tham số trượt giá, nhãn/bảng/biểu đồ và giới hạn diễn giải.
- `tests/test_auction.py`, `tests/test_auction_experiment.py`, `tests/test_web_reporting.py`, `tests/test_web_app.py`, `tests/test_web_cases.py`: regression theo từng task.
- `README.md`: cập nhật giả định và cách đọc kết quả; giữ lệnh chạy Windows hiện có.

**Không sửa:** `src/rosca_sim/model.py` và các quy tắc fixed-order, loader giá, chiến lược bid/default, framework web. `web_analysis.py` chỉ đọc để xác nhận dùng chung case/window/seed; không cần thay nếu các interface giữ nguyên.

Chạy từ repo bằng `.\.venv\Scripts\python.exe -m pytest <test-files> -q -o addopts= -p no:cacheprovider --basetemp .superpowers/sdd/2026-10-06-risk-revision/<task>`. Mỗi task: viết/chỉnh test → thấy fail đúng hành vi mới → sửa tối thiểu → chạy pass → commit đúng file task. Test đã đúng hành vi cũ được giữ làm regression, không cố tạo failure giả.

### Task 1: Giữ ETH đến hoàn thành hoặc quyết toán

**Files:** `src/rosca_sim/auction.py`, `tests/test_auction.py`.

**Interfaces:** Giữ `AuctionAgent.contribute(day: int) -> float`, `AuctionRoscaModel._required_eth(agent, period, price) -> float`, `_sell(agent, obligation, day) -> float`, `_settle() -> AuctionRunResult`. `eth_released` giữ tương thích, bằng 0 cho trả giữa kỳ; `eth_returned` ghi ETH trả khi kết thúc/quyết toán.

- [x] Thay `test_trace_releases_after_fixed_contribution` bằng `test_trace_keeps_eth_after_fixed_contribution`: O=500, r=1, P=2.000, khóa 0,25 ETH; sau góp 100, O=400, khóa vẫn 0,25 và released=0. Không đổi góp/khả năng bid sau lĩnh.
- [x] Với ví dụ P=2.000, tạo `PricePath((2000.0,) * 6, ..., (2000.0,) * 158)` thay vì dùng nguyên helper `constant_prices()` hiện có giá1. Với test coverage giảm giá ở Task3, giá kỳ và daily cùng ngày phải khớp nhau. Dùng `pytest.approx` cho các phép chia tiền/ETH.
- [x] Chạy test trên và xác nhận fail vì engine đang giải phóng từng kỳ.
- [x] Bỏ riêng nhánh release trong `AuctionAgent.contribute`; giữ giảm nghĩa vụ. Hoàn thành thường phải trả mọi ETH còn khóa tại `_settle`; quyết toán vẫn bán tối đa nghĩa vụ và trả dư.
- [x] Thêm `test_completion_returns_full_initial_eth`; kiểm tra toàn bộ member `eth_locked == eth_sold + eth_returned`, released=0. Chạy lại test USDC đủ, USDC một phần, ETH dư, default ngày góp, final recipient khóa 0.
- [x] Thêm `test_sale_slippage_does_not_reduce_initial_bid_collateral`: O500, bid120, ETH0,25, P2.000, slippage10%, default sau lượt lĩnh trước kỳ kế; proceeds450, uncollected50, interest_used50, principal_loss0, surplus70. Không nạp USDC, fixture đủ dòng tiền.
- [x] Chạy `tests/test_auction.py`; PASS và cash/ETH identities giữ đúng. Commit `feat: retain auction ETH until terminal settlement`.

### Task 2: Nguồn lãi và thiếu hụt quyết toán

**Files:** `src/rosca_sim/auction.py`, `src/rosca_sim/auction_experiment.py`, `tests/test_auction.py`, `tests/test_auction_experiment.py`.

**Interfaces:** Bổ sung `AuctionAgentResult.bid_interest_paid: float`, `is_trigger_default: bool`, `settlement_shortfall: bool`; `AuctionRunResult.interest_used_from_defaulting: float`, `interest_used_from_other_members: float`, `secondary_shortfall_count: int`. Không đổi nghĩa `default_count = len(default_ids)`.

- [x] Thêm `test_interest_sources_follow_freeze_group_not_event_order`: sáu người góp100, giá lúc lĩnh1, r1; kỳ0 ID0 bid20% giữ120 và khóa500ETH, kỳ1 ID1 bid `40/600` giữ40 và khóa400ETH. Ngày60 trước góp kỳ2: forced default ID0 và missed contribution ID2; giá bán0,5, ID0 còn nợ400 và thu250, ID1 trả đủ400USDC. Bốn người chưa lĩnh có claim800, pool thực thu810 → interest_used150, from_defaulting120, from_other30, lãi còn10. Đảo sự kiện cùng ngày không đổi kết quả; ID2 chưa lĩnh có bid_interest_paid0. Thêm trường hợp dùng ít hơn120 và nhóm default không có lãi đã trả.
- [x] Thêm test người gây bùng thu ETH đủ nhưng người khác hết capacity và ETH thiếu: người khác có `settlement_shortfall=True`, `is_trigger_default=False`; default_count không tăng, secondary_shortfall_count tăng. Người chưa lĩnh không có nghĩa vụ tăng tốc, flag=False.
- [x] Chạy các test mới và xác nhận fail vì thiếu trường/phân loại.
- [x] Ghi `bid_interest_paid` từ gross × winning rate đúng một lần. Từ `interest_used` hiện có, phân bổ nguồn với `D = sum(bid_interest_paid của default_ids)`, `from_defaulting = min(interest_used, D)`, `from_other = interest_used − from_defaulting`; không thay cash waterfall. Chỉ cần tổng nhóm, không thêm ledger phân bổ cá nhân chưa dùng.
- [x] Đặt flag shortfall khi người đã lĩnh còn `obligation_uncollected > 1e-9`; secondary count chỉ đếm người không thuộc default_ids. Kiểm tra uncollected không giảm khi lãi bù hết gốc. Giữ quy tắc chia lãi hiện có; không thêm chế tài người thiếu tiền quyết toán.
- [x] Trong `run_auction_experiment`, metadata hiện chưa lưu scenario đầy đủ: thêm `scenario = asdict(scenario)` và `collateral_release_policy = "terminal"`; giữ các khóa cũ. CSV run/agent đã dùng `asdict`, chỉ đổi khi test phát hiện cột bị thiếu; không viết serializer mới.
- [x] Kiểm thử CSV chứa trường mới, metadata scenario/slippage giữ nguyên, tổng hai nguồn bằng interest_used và không vượt lãi của từng nhóm; normal completion sources/count bằng0. Chạy hai test files, PASS; commit `feat: report auction interest sources and settlement shortfalls`.

### Task 3: Chỉ báo F11 và khả năng lĩnh

**Files:** `src/rosca_sim/auction.py`, `src/rosca_sim/web_reporting.py`, `tests/test_auction.py`, `tests/test_web_reporting.py`.

**Interfaces:** Thêm vào `AuctionPeriodTrace`: `remaining_obligation_by_member: tuple[float, ...]`, `retained_eth_by_member: tuple[float, ...]`, `insufficient_eth_bidder_ids: tuple[int, ...]`. Snapshot sau xử lý kỳ; ghi skip thực sự trước khi tìm được winner. `trace_rows(run: CaseRun)` thêm `remaining_obligation_usdc`, `retained_eth`, `coverage_ratio`, `collateral_shortfall_usdc`, `skipped_for_insufficient_eth`.

- [x] Thêm test snapshot người đầu sau hai kỳ: O400, ETH0,25, P kỳ2=1.000 → value250, coverage0,625, thiếu150. O0 → coverage=None, shortfall0. Đây là giá trị ETH cá nhân, không cộng pool lãi và không tự dùng slippage bán vào market coverage.
- [x] Thêm test highest bidder thiếu ETH được ghi skip, next eligible thắng; không ai đủ ETH và không có bid đều giữ stop_reason=`no_eligible_bid`, không default. Kiểm tra người đã lĩnh không được ghi thành skip do ETH, tiền kỳ đã góp không biến mất.
- [x] Chạy test mới xác nhận fail ở trace fields.
- [x] Cập nhật `_record_period` và selection loop để ghi snapshot/skip; `trace_rows` dùng giá tại ngày trace. Không tạo sự kiện top-up, không thay settlement vì coverage thấp. Snapshot không tồn tại ở ngày giữa kỳ thì không nội suy/giả tạo trạng thái.
- [x] Ghim thời điểm snapshot: sau góp/lĩnh nhưng trước terminal settlement. Kỳ cuối O0 vẫn có thể thấy ETH còn giữ trong trace, sau `run()` ETH được trả trong result. `eth_locked_by_member` cũ là lượng khóa mới trong kỳ; không đổi nghĩa thành tổng còn khóa, dùng `retained_eth_by_member` cho tổng. Coverage=None cho người chưa lĩnh/O0, không nối đường biểu đồ qua đoạn không áp dụng.
- [x] Giữ `candidate_ratio` loại mọi nhóm có `no_eligible_bid_count > 0`. Bổ sung `frontier_rows` các cột `completed_run_count`, `completion_share`, `mean_payout_count`; dùng tất cả cửa sổ chung, không lược bỏ run không hoạt động khỏi mẫu tính lỗ. Completion share là thông tin, không phải điều kiện candidate cho scenario có default.
- [x] Kiểm thử no-loss nhưng no-eligible vẫn candidate=None; default được thu đủ có thể là candidate và completion_share=0; so sánh payout order vẫn báo nonmonotonic như cũ. Chạy test files, PASS; commit `feat: expose observational coverage and auction feasibility`.

### Task 4: Dashboard, xuất kết quả và nghiệm thu

**Files:** `src/rosca_sim/web_app.py`, `src/rosca_sim/web_reporting.py`, `tests/test_web_app.py`, `tests/test_web_reporting.py`, `tests/test_web_cases.py`, `README.md`.

**Interfaces:** Giữ `comparison_rows`, `member_loss_rows`, `frontier_rows`, `candidate_ratio`; thêm các trường kết quả Task2 vào bảng tương ứng. Editor ghi slippage vào `scenario.collateral.liquidation_slippage`, JSON/CSV snapshot giữ đúng giá trị.

- [x] Thêm test Streamlit editor lưu 0%/5%/10%, roundtrip JSON giữ cấu hình; chỉnh slippage làm kết quả stale. Chỉ có input số 0 ≤ s < 1, không làm scenario mặc định trượt5/10%. Giữ validation engine/JSON cho bool/NaN/infinity/out-of-range.
- [x] Thêm test bảng người và lượt chạy có lãi đã trả, hai nguồn lãi bù, flags/count shortfall, nghĩa vụ chưa thu; stop label phân biệt completed/default/no_eligible_bid. Bảng trace có coverage và lý do skip, không xuất hiện nút margin call.
- [x] Chạy test mới xác nhận fail ở UI/report fields.
- [x] Bổ sung input/slippage caption, các cột mới và biểu đồ/bảng coverage theo kỳ; tái dùng chart hiện có, không dựng dashboard mới. Editor dùng nhãn `Trượt giá khi bán ETH (%)`, mặc định `100 × scenario.collateral.liquidation_slippage`, lưu chia100 và kiểm tra `0 ≤ giá trị < 100` khi lưu; không nhầm5% thành5. Không đặt trần99,99 làm lỗi case import hợp lệ có trượt giá99,999%. JSON giữ số dạng tỷ lệ0,05.
- [x] Frontier báo loss-run share, completion share, số lượt lĩnh và initial collateral proxy với đơn vị đúng. Không gọi initial-lock proxy là chi phí vốn hay số ngày khóa thực tế. Candidate chỉ gọi là ngưỡng không mất gốc trong mẫu có thể thực hiện, không gọi bảo vệ hoàn toàn.
- [x] Thêm `_meta` vào CSV web `collateral_release_policy = "terminal"`; scenario snapshot đã có thì tái dùng. Giữ chặn import `stress_drop` và execution overrides như `web_cases` hiện có, hiển thị lỗi inline và không ghi đè case đã lưu; không mở hỗ trợ mới chỉ để thêm cảnh báo. Các cấu hình này vẫn dùng qua CLI, không phải baseline web.
- [x] Sửa README: giữ ETH đến terminal, tiền góp giả định đủ trừ event đặt trước, capacity chỉ terminal, F11 observational, source interest attribution, không đảm bảo lợi suất/xác suất thực tế; giữ hướng dẫn cài extra web và lệnh chạy hiện có. Phần README hiện mô tả giải phóng ETH cho fixed-order phải giữ đúng cơ chế đó, thêm phân biệt auction thay vì thay mọi câu release trong tài liệu.
- [x] Chạy test auction/experiment/web cases/reporting/app, rồi toàn repo với basetemp riêng; `python -m compileall -q src`, `git diff --check`. Phải PASS, không chỉ kiểm tra import. Chạy demo normal completion, một default có lãi bù đủ, simultaneous defaults, no eligible, người compliant thiếu tiền terminal, slippage sensitivity trên cùng lịch sử ETH.
- [x] Đối chiếu CSV với UI và ledger engine, giữ cố định case/window/seed giữa các tỷ lệ. Review diff chỉ trong scope; commit `feat: explain auction risk and feasibility in local dashboard`, không push. Báo số test thực chạy và giới hạn mô hình.

## Handoff

Đã triển khai trực tiếp theo phê duyệt, có RED→GREEN và review độc lập. Không thêm cơ chế ngoài phạm vi; fixed-order không đổi. Không có minor bị hoãn.

Quyết định khi triển khai: (1) thay script Bash bị chặn bằng ledger/PowerShell, không đổi logic app; (2) sửa số học fixture người lĩnh thứ hai còn nợ400 thay vì300, không đổi chính sách; (3) giữ từ chối stress_drop/price overrides trong web thay vì mở hỗ trợ chỉ để cảnh báo. Chi phí tương ứng: theo dõi thủ công thay tự động; ví dụ số học phải dùng số đã sửa; kịch bản stress vẫn ở CLI.

Reviewer không đánh giá ví tiền/hành vi nội sinh/margin call/dây con và triển khai production vì ngoài phạm vi; vẫn loại các phần này như đã duyệt, không tuyên bố an toàn triển khai. Reviewer không kiểm tra artifact ignored; dataset/demo đã được main executor kiểm chứng riêng, không coi review số học là thẩm định nguồn giá.
