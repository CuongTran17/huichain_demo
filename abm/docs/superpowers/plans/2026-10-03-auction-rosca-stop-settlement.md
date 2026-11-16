# Auction ROSCA Stop-on-Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible auction-ROSCA ABM that locks ETH only at payout, stops on the first default, and reports each member's loss after a configurable settlement grace period.

**Architecture:** Add a separate Mesa auction model rather than changing the existing fixed-order model's meaning. Reuse its pure collateral and liquidation helpers, price loaders, and paired-policy experiment conventions; keep a separate auction cash ledger and output schema. Run both policies on the same bids, agents, events, and price path, while allowing their actual payout order to differ when collateral eligibility differs.

**Tech Stack:** Python >=3.12, Mesa 3.5.1, standard-library `dataclasses`/`csv`/`tomllib`, existing pytest suite; no new product dependency.

**Spec:** `docs/superpowers/specs/2026-10-02-auction-rosca-stop-settlement-design.md`

## Global Constraints

- Existing fixed-order model, command, and CSV semantics remain unchanged; auction output names must be distinct.
- `members == periods`, at least six members in auction mode, fixed contribution each period, no second payout or bid after payout.
- Bid discount is on the current gross pot: 600 USDC at 20% pays 480 and retains 120; later installments remain 100 USDC in the six-member case.
- ETH is locked only immediately before a payout, using remaining scheduled installments and the configured fixed or reputation-adjusted collateral ratio; `reserve_initial = 0` in this auction version.
- A default freezes auctions/contributions/payouts immediately; same-timestamp events settle as one order-independent batch; no continuing-circle behavior.
- Previously paid members' remaining installments accelerate at closure; honest members use `eth_first` or `usdc_first`; defaulting members' ETH is sold immediately; no fictitious USDC top-up.
- Initial `grace_days = 7`; compare 0, 1, 3, 7, and 14 on the same daily price path. Daily closes are not proof of intraday executable prices.
- Refund unpaid-saver principal before distributing any retained bid interest; allocate surplus interest by pre-payout USDC-days. Keep per-member losses and a cash-conservation identity.
- Bids, payment capacity, repayment mode, missed contributions, and forced defaults are exogenous scenario inputs; no game-theoretic bidder or automatic margin call.
- The source repository currently has no commits and Git metadata was unwritable in the planning environment. Never stage unrelated untracked files; if task commits are blocked, preserve files and report the skipped commit rather than changing Git permissions by other means.

## Bổ sung kế hoạch sửa được chốt ngày 2026-10-06

Phần này ghi nhận quyết định mới cho đợt sửa tiếp theo; các thay đổi bên dưới chưa được triển khai. Quy tắc dùng lãi chung để ưu tiên hoàn gốc đã có trong mô hình hiện tại. Đợt sửa cần làm rõ nguồn lãi và nghĩa vụ, không đổi khoản bid thành ký quỹ USD được hoàn lại cho người lĩnh.

Các quy tắc bổ sung dưới đây thay thế yêu cầu giải phóng ETH từng kỳ trong kế hoạch/spec ban đầu; các bước triển khai cũ được giữ để lưu lịch sử, không phải đặc tả cho đợt sửa mới.

### Quy tắc lãi chung và giữ ETH đến cuối

- Người thắng bid 20% trên quỹ 600 USDC lĩnh ròng 480; 120 bị khấu trừ là lãi đã trả, giữ trong quỹ đến khi dây hoàn thành hoặc quyết toán. Các kỳ sau vẫn góp 100 USDC, không thu lại 120 lần nữa.
- Sau khi thu USDC quyết toán và tiền bán ETH, ưu tiên hoàn gốc người chưa lĩnh. Phần thiếu được bù bằng lãi đã trả của nhóm bùng tại thời điểm đóng băng trước, rồi bằng lãi chung còn lại; chỉ chia lãi khi các khoản gốc được hoàn đủ. Nếu tài sản vẫn thiếu, ghi lỗ gốc từng người.
- Lãi của người bùng là một phần của quỹ lãi chung. Theo dõi nguồn lãi chỉ để phân bổ khoản lãi đã dùng; không cộng lại như một nguồn tiền mới. Không trừ lãi đã trả khỏi yêu cầu ETH lúc lĩnh.
- Lúc lĩnh: `ETH khóa = r × nghĩa vụ góp còn lại / giá ETH lúc lĩnh`. Nghĩa vụ là các kỳ góp tương lai, không phải toàn bộ quỹ lĩnh; khoản bid đã trả không được trừ khỏi yêu cầu ETH. Ví dụ còn 5 kỳ × 100, `r = 100%`, giá ETH 2.000 thì khóa 0,25 ETH.
- Dây đang hoạt động: đóng đủ mỗi kỳ thì giảm nghĩa vụ nhưng giữ nguyên toàn bộ lượng ETH đã khóa lúc lĩnh, không giải phóng từng kỳ và không tự tăng/giảm lượng khóa theo giá ETH. Khi dây hoàn thành bình thường, mọi người đã lĩnh và đóng đủ nghĩa vụ, trả toàn bộ ETH còn khóa. Giữ lâu hơn có thể tăng độ bao phủ khi nghĩa vụ giảm, nhưng không bảo đảm đủ nếu ETH sập; ABM cần báo cả rủi ro và thời gian khóa vốn.
- Dây đóng băng: người đã lĩnh muốn nhận lại toàn bộ ETH đang khóa phải trả đủ nghĩa vụ còn lại bằng USDC. Nếu dùng ETH trả nghĩa vụ, chỉ bán lượng cần thiết và trả phần ETH dư; bán hết mà vẫn thiếu thì không còn ETH để hoàn và khoản thiếu vẫn được ghi nhận.
- Quỹ lãi bù thiếu để bảo vệ người chưa lĩnh không được ghi thành khoản trả nợ của người bùng. `obligation_uncollected` vẫn phản ánh nghĩa vụ chưa thu sau USDC/ETH thực nhận, độc lập với `interest_used` và `principal_loss`.
- Mô hình hiện chốt ở hạn quyết toán. Nếu nghiên cứu thu hồi tiền sau hạn trong phiên bản sau, phải hoàn lại phần quỹ đã dùng bù trước khi chia thêm; không thu vượt nghĩa vụ hay bồi hoàn gốc hai lần. Bổ sung này không yêu cầu xây luồng thu hồi sau hạn ngay.

### Trượt giá tối giản khi bán ETH

- Dùng tham số `liquidation_slippage` hiện có, không xây mô hình sổ lệnh/thanh khoản: `giá bán mô phỏng = giá đóng cửa ETH ngày bán × (1 − liquidation_slippage)`. Trượt giá chỉ áp dụng lúc bán, không khấu trừ lần nữa vào tiền thu hồi hay quỹ lãi.
- Baseline dùng 0%; có thể so sánh 5% và 10% như giả định độ nhạy, không gọi đây là mức trượt giá thực tế đo được. Dùng đường giá ETH lịch sử và ghi rõ giá đóng cửa không mô tả các cú quét hay giá khớp lệnh trong ngày.
- Khi so sánh riêng tỷ lệ ký quỹ và trượt giá, để `stress_drop` không thiết lập để ngưỡng bảo vệ stress hiện có không tự nâng tỷ lệ ký quỹ và che mất tác động cần đo. Nếu chạy thêm ngưỡng stress, gắn nhãn thành kịch bản riêng.

### Các bước sửa và kiểm tra

Kế hoạch triển khai đợt sửa: `docs/superpowers/plans/2026-10-06-auction-risk-accounting-revision.md`. Đợt này chưa triển khai code; checklist dưới đây là tổng hợp quyết định, kế hoạch mới quy định thứ tự thực hiện.

**Files:** `src/rosca_sim/auction.py`, `src/rosca_sim/auction_experiment.py`, `src/rosca_sim/web_reporting.py`, `src/rosca_sim/web_app.py`, các test tương ứng và `README.md`. Đồng bộ spec trước khi sửa mã; chỉ thay đổi schema xuất kết quả nếu cần thêm trường nguồn lãi.

- [ ] Đồng bộ spec với chính sách giữ ETH đến cuối. Giữ test góp cố định, trả đủ USDC và lãi chung bù gốc; thay kỳ vọng giải phóng dần bằng test nghĩa vụ giảm 500 xuống 400 sau kỳ góp 100 nhưng lượng ETH khóa không đổi, ETH trả giữa dây bằng 0. Test hoàn thành bình thường trả toàn bộ lượng ETH ban đầu.
- [ ] Sửa riêng luồng góp của auction để không trả ETH từng kỳ; không thay đổi mô hình fixed-order. Kiểm thử quyết toán dừng sớm: trả đủ USDC nhận toàn bộ ETH, trả một phần USDC rồi bán đúng lượng ETH cần thiết, trả ETH dư và ghi khoản thiếu nếu bán hết vẫn không đủ. Giữ đến cuối không ngăn thanh lý khi quyết toán default.
- [ ] Kiểm thử công thức ký quỹ không trừ bid và trượt giá lúc bán. Fixture: nghĩa vụ 500, bid giữ 120, `r = 100%`, giá lúc lĩnh/ngày bán đều 2.000, khóa 0,25 ETH; bán với trượt giá 10% thu 450. Khi không có USDC nộp thêm, nghĩa vụ chưa thu 50, dùng 50 lãi bù gốc, lỗ gốc bằng 0; phần lãi 70 còn lại xử lý theo waterfall. Bảo đảm fixture có dòng tiền đầy đủ, không thu nợ vượt 500.
- [ ] Bổ sung kiểm thử phân bổ nguồn lãi: khi nhóm bùng đã trả 120, nhóm còn lại đã trả 40 và thiếu 150 để hoàn gốc, dùng 120 từ nhóm bùng và 30 từ nhóm còn lại; tổng dùng 150, còn 10. Dùng fixture có dòng tiền hợp lệ; thứ tự danh sách người bùng không thay đổi kết quả.
- [ ] Theo dõi lãi đã trả theo người từ gross pot × winning bid. Nếu cần xuất nguồn lãi, thêm `bid_interest_paid` vào kết quả từng người và `interest_used_from_defaulting`/`interest_used_from_other_members` vào kết quả từng lượt. Khi phân bổ trong mỗi nhóm, dùng tỷ lệ lãi đã trả của từng người; tổng hai nguồn phải bằng `interest_used` hiện có và không làm thay đổi tiền mặt trong quỹ.
- [ ] Bổ sung kiểm thử phân biệt nợ và lỗ gốc: nghĩa vụ 500, ETH thu hồi 350, lãi giữ lại 120 thì `obligation_uncollected = 150`, `interest_used = 120`, và tổng lỗ gốc người chưa lĩnh = 30. Khi thêm nguồn lãi chung hợp lệ đủ bù phần còn lại, lỗ gốc có thể bằng 0 nhưng nghĩa vụ chưa thu không tự giảm.
- [ ] Trên web/CSV và README, hiển thị riêng nghĩa vụ chưa thu, lãi dùng bảo vệ gốc, lỗ gốc và ETH bán/trả. Ghi rõ ETH giữ đến hoàn thành/quyết toán, lãi dự kiến có thể giảm khi quỹ bù thiếu, và khoản lãi đã trả không được hoàn về người thắng như ký quỹ. Cho phép chỉnh tham số trượt giá lúc bán và lưu cấu hình vào kết quả; cập nhật mô tả biểu đồ khóa vốn, không còn tuyên bố giải phóng ETH từng kỳ.
- [ ] Chạy các test auction, xuất kết quả và web liên quan, rồi bộ test toàn repo; xác nhận bảo toàn tiền/ETH, không tính lãi hai lần, không trả vượt gốc và không báo miễn nợ khi quỹ đã bù thiếu.

### Phạm vi bổ sung sau khi so sánh hai repo

- Giữ sự kiện bùng/bỏ góp do người nghiên cứu đặt trước, gồm nhiều người cùng thời điểm. Không xây ví tiền, thu nhập/chi tiêu hay xác suất bùng ngẫu nhiên. `usdc_capacity` chỉ là khả năng trả ngay khi quyết toán, không phải khả năng góp định kỳ.
- Giữ dừng cả dây ở sự kiện đầu tiên; không chạy tiếp dây con. Sau đóng băng không mô phỏng bùng góp ở kỳ tương lai; ghi riêng người không đủ khả năng trả nghĩa vụ bị tăng tốc khi quyết toán.
- Giữ xét bid theo mức lãi giảm dần, hòa thì ID ổn định; người đã lĩnh không được thắng tiếp, người thiếu ETH bị bỏ qua và ghi lý do. Không ai đủ điều kiện thì `no_eligible_bid`, không phải `default`; giữ quyết toán tiền đã góp như hiện tại, không chờ hay tự tạo người thắng.
- F11 chỉ theo dõi giá trị ETH đang khóa so với nghĩa vụ còn lại tại các kỳ được mô phỏng, không gọi nạp thêm hay thanh lý tự động. Nghĩa vụ bằng 0 thì tỷ lệ bao phủ không áp dụng, không chia cho 0. Chưa xây theo dõi giá/oracle liên tục.
- Giữ Streamlit. Báo riêng lý do kết thúc, số người gây đóng băng và số người khác còn thiếu nghĩa vụ sau quyết toán. Hiển thị dòng tiền từng người và nguồn lãi đã bù; không biến lãi chung thành khoản miễn nợ.
- Ngưỡng ký quỹ ứng viên phải không mất gốc và không có lượt `no_eligible_bid` trong mẫu. Báo số lượt lĩnh/tỷ lệ hoàn thành riêng; dây dừng do bùng không thể được yêu cầu hoàn thành như một điều kiện bắt buộc. Không diễn giải tần suất lỗ trong tập kịch bản đặt trước thành xác suất mất tiền ngoài thực tế.
- Chưa thêm F12 dùng ký quỹ để phá hòa, game theory, quỹ ngoài, mô hình thanh khoản/sổ lệnh, hay dữ liệu wick mặc định. Baseline lịch sử dùng giá ETH thật; tham số trượt giá là giả định độ nhạy được công bố.

## Review Focus của kế hoạch ban đầu

These five failure modes are pinned to the indicated task tests in addition to the core examples:

1. Non-finite/boolean/out-of-range bid or price input must fail before a payout or ETH sale (Tasks 1 and 3).
2. Duplicate, contradictory, or impossible same-day events must not depend on list order or charge a due-date contribution after freeze (Task 2).
3. Insufficient daily-history tail for a late freeze plus grace period must raise a clear error, not read past the path (Task 3).
4. A partial USDC payment plus partial ETH sale must never collect more than the accelerated obligation or release more ETH than was locked (Task 2).
5. When all waiting-time weights are zero, a positive surplus uses the documented contribution-weight fallback or remains explicitly undistributed (Task 2).

---

## File map

- Create `src/rosca_sim/auction.py`: auction scenario/result types, Mesa agents, period transitions, closure, and terminal cash waterfall. Reuse `fixed_collateral_ratio`, `reputation_collateral_ratio`, `strategic_default_utility`, and `settle_default` from `model.py`; do not fork their formulas.
- Create `src/rosca_sim/auction_experiment.py`: paired-policy runner, auction-specific CSV/metadata, and grace-period comparison.
- Modify `src/rosca_sim/prices.py`: optional post-horizon daily-price tail while preserving old default behavior.
- Modify `src/rosca_sim/cli.py`: `auction-run` and `auction-grace-sweep` subcommands with auction-only TOML validation; leave `run` and `sweep` paths unchanged.
- Create `tests/test_auction.py`, `tests/test_auction_experiment.py`; extend `tests/test_prices.py` and `tests/test_cli.py`.
- Create `configs/auction-six-member.toml`; update `README.md` with run commands, interpretation, and limitations.

### Task 1: Normal auction rounds, ETH lock, and retained interest

**Files:** Create `src/rosca_sim/auction.py`, `tests/test_auction.py`.

**Interfaces:** `AuctionAgentSeed(member_id: int, reputation: float, available_eth: float, settlement_mode: Literal['eth_first','usdc_first'], usdc_capacity: float, payment_day_offset: int | None = None)`; `AuctionBid(period: int, member_id: int, rate: float)`; `AuctionEvent(member_id: int, day: int)`; `AuctionPriceOverride(day: int, price: float)`; `AuctionScenario(rosca: RoscaConfig, collateral: CollateralConfig, behavior: BehaviorConfig, agents: tuple[AuctionAgentSeed, ...], bids: tuple[AuctionBid, ...], forced_defaults: tuple[AuctionEvent, ...] = (), missed_contributions: tuple[AuctionEvent, ...] = (), execution_price_overrides: tuple[AuctionPriceOverride, ...] = (), grace_days: int = 7)`; `AuctionRoscaModel(scenario: AuctionScenario, policy: Literal['fixed','reputation_adjusted'], price_path: PricePath, run_id: int = 0, seed: int = 0)` with `step() -> None` and `run() -> AuctionRunResult`. Expose `agents_by_id`, `interest_balance`, `payout_order`, `cash_balance`, and typed `AuctionRunResult`/`AuctionAgentResult` fields needed in Tasks 2–6.

- [ ] **Step 1: Write failing tests** `test_six_member_winning_discount_and_lock` and `test_paid_member_cannot_bid_again`: first step with bids 20% for ID 0 gives payout 480, interest 120, obligation 500, and no pre-payout lock for IDs 1–5; after the next step ID 0 has paid exactly 200 cumulatively and owes 400, while ID 1 wins even if ID 0 submits a higher later bid. Also test equal bids choose lowest member ID and the final recipient locks zero ETH.
- [ ] **Step 2: Run** `python -m pytest tests/test_auction.py -q` and confirm the new tests fail for missing auction behavior.
- [ ] **Step 3: Implement** the listed dataclasses and `AuctionRoscaModel.step` in `auction.py`: collect one fixed installment per member, select the highest eligible unreceived bidder, lock ETH before transfer, retain the discount once, release locked ETH after later paid installments. Reuse existing collateral helpers; a member with insufficient `available_eth` is skipped. Reject `bool`, NaN, infinity, negative, or >=1 bids and nonpositive/non-finite prices; reject duplicate bids and member IDs. If no candidate is eligible, set stop reason `no_eligible_bid` without inventing a payout.
- [ ] **Step 4: Run** `python -m pytest tests/test_auction.py -q`; verify all Task 1 tests pass, including invalid-bid and no-eligible-bid tests. Assert the period cash identity `opening_cash + contributions = payout + closing_cash`.
- [ ] **Step 5: Stage only Task 1 files and commit** `feat: add auction payout and collateral lock`; if Git metadata is still blocked, log that fact and keep the files intact.

### Task 2: Freeze, accelerated obligations, ETH/USDC settlement, and waterfall

**Files:** Modify `src/rosca_sim/auction.py`; extend `tests/test_auction.py`.

**Interfaces:** Consume Task 1's scenario/model/results; produce `AuctionRoscaModel.run() -> AuctionRunResult` with `stop_reason`, `freeze_day`, `settlement_day`, `default_count`, `payout_order`, `interest_retained`, `interest_used`, `interest_distributed`, `obligation_uncollected`, `principal_loss`, `worst_member_loss`, `total_collateral_locked`, `eth_sale_proceeds`, `ending_cash`, and `agent_results: tuple[AuctionAgentResult, ...]`. Each agent result includes `member_id`, `payout_day`, `winning_bid`, `net_payout`, `total_contributed`, `principal_claim`, `principal_repaid`, `principal_loss`, `interest_received`, `eth_locked`, `eth_released`, `eth_sold`, `eth_returned`, `usdc_settlement_paid`, `settlement_mode`, `payment_day`, and `obligation_uncollected`.

- [ ] **Step 1: Write failing settlement tests.** First payout 480, interest 120, day-1 default, obligation 500: when ETH sale yields 400, five 100-USDC claims are fully repaid, `interest_used == 100`, `interest_distributed == 20`, and `principal_loss == 0`; when sale yields 300, `interest_used == 120`, `principal_loss == 80`, and each of five claimants loses 16. In a normal six-period run with only the first bid at 20%, assert total interest paid is 120, first recipient earns zero wait-based interest, and later recipients' entitlements increase with their payout dates. Add tests for two reversed-order same-day defaults, freeze before due-date contributions, a missed pre-payout installment with no penalty, `eth_first` partial sale/ETH return, `usdc_first` full payment/ETH return, partial USDC plus ETH sale with no overcollection, and zero waiting-weight surplus fallback.
- [ ] **Step 2: Run** `python -m pytest tests/test_auction.py -q` and confirm the new settlement cases fail.
- [ ] **Step 3: Implement** freeze/terminal settlement in `AuctionRoscaModel.run`: batch timestamp events, stop new rounds, seize defaulting recipients' ETH at freeze-day executable price, accelerate every paid member's unpaid fixed installments, apply each non-defaulting recipient's configured repayment mode and `payment_day_offset`, cap USDC actually paid by `usdc_capacity`, sell only necessary ETH with slippage, and mark any remaining amount as uncollected. Refund never-paid members' actual contributions first, pro rata if assets are insufficient; allocate only the residual to non-defaulting members by pre-payout USDC-days. Attribute retained interest used for principal after non-interest cash, without adding interest twice. Keep a per-run and per-agent cash/ETH conservation assertion.
- [ ] **Step 4: Run** `python -m pytest tests/test_auction.py -q` and confirm Task 2 cases pass. Include input rejection tests for duplicate/conflicting events, impossible payout-timing forced defaults, negative USDC capacity, invalid payment offset, and zero-weight residual accounting.
- [ ] **Step 5: Stage only Task 2 files and commit** `feat: settle stopped auction circles`; record a skipped commit if Git remains inaccessible.

### Task 3: Price tails, deadline prices, and transient sale shocks

**Files:** Modify `src/rosca_sim/prices.py`, `src/rosca_sim/auction.py`; extend `tests/test_prices.py`, `tests/test_auction.py`.

**Interfaces:** Add `extra_days: int = 0` to `sample_historical_path(...) -> PricePath` and `make_stress_path(...) -> PricePath`; `PricePath.prices` remains exactly `periods` long and `daily_prices` becomes `(periods - 1) * period_days + 1 + extra_days` long. `AuctionPriceOverride(day, price)` changes only the executable sale price on that day, not the due-date lock price.

- [ ] **Step 1: Write failing tests:** six 30-day periods plus 14 grace days yield 165 daily prices and six due-date prices; a 164-day history is rejected; negative `extra_days` is rejected. With 400 ETH worth of collateral at a daily close of 1, a day-1 override of 0.6 yields 240 sale proceeds, while the same run without override yields 400. A `usdc_first` nonpayer sells at day `freeze_day + grace_days`, not at the freeze price.
- [ ] **Step 2: Run** `python -m pytest tests/test_prices.py tests/test_auction.py -q` and verify these cases fail.
- [ ] **Step 3: Extend** the two price constructors and auction price lookup; preserve legacy output for `extra_days=0`. Validate the complete tail at model construction or price sampling; never silently repeat the last historical close to fill missing days. Reject invalid override days/prices and duplicate overrides.
- [ ] **Step 4: Run** `python -m pytest tests/test_prices.py tests/test_auction.py tests/test_model.py -q`; confirm new cases pass and fixed-order price/model tests remain green.
- [ ] **Step 5: Stage only Task 3 files and commit** `feat: price auction grace and sale shocks`; record a skipped commit if needed.

### Task 4: Paired experiments and distinct auction outputs

**Files:** Create `src/rosca_sim/auction_experiment.py`, `tests/test_auction_experiment.py`.

**Interfaces:** `run_auction_pair(scenario: AuctionScenario, price_path: PricePath, run_id: int = 0, seed: int = 0) -> tuple[AuctionRunResult, AuctionRunResult]`; `run_auction_experiment(scenario: AuctionScenario, price_source: PricePath | Callable[[random.Random], PricePath], runs: int, seed: int, output_dir: Path) -> AuctionExperimentOutput`. Output `auction_run_results.csv`, `auction_agent_results.csv`, `auction_pair_results.csv`, `auction_metadata.json`; use `fixed` and `reputation_adjusted` policy labels and record realized payout order per policy.

- [ ] **Step 1: Write failing paired-output tests:** both policies see the same scenario inputs and price path; where one high bidder can lock under fixed ratio but not reputation ratio, first-recipient IDs differ and both orders are reported. Repeated runs with the same seed produce byte-identical CSV/metadata; the agent CSV contains actual payout, bid, ETH sale/return, principal claim/loss, and interest received. Auction filenames do not overwrite fixed-order outputs.
- [ ] **Step 2: Run** `python -m pytest tests/test_auction_experiment.py -q` and confirm failure before implementation.
- [ ] **Step 3: Implement** the pair runner and CSV writer using existing experiment conventions, but with auction-only schemas and metadata (`model_kind='auction_stop'`, seed, grace days, price source/window, assumptions). For each Monte Carlo run, sample one price path and pass that same object to both policies. Pair metrics include delta total principal loss, delta worst-person loss, delta collateral locked, delta interest distributed, and whether both policies produced the same payout order.
- [ ] **Step 4: Run** `python -m pytest tests/test_auction_experiment.py tests/test_experiment.py -q`; confirm new and legacy experiment tests pass.
- [ ] **Step 5: Stage only Task 4 files and commit** `feat: report paired auction experiments`; record a skipped commit if needed.

### Task 5: CLI configuration and reproducible six-member pilot

**Files:** Modify `src/rosca_sim/cli.py`, `tests/test_cli.py`, `README.md`; create `configs/auction-six-member.toml`.

**Interfaces:** `load_auction_config(path: Path) -> LoadedAuctionConfig` with `scenario: AuctionScenario`, `prices: dict[str, object]`, `runs: int`, `seed: int`; add `auction-run --config PATH --output DIR` to `build_parser()`/`main()`. TOML uses existing `[rosca]`, `[collateral]`, `[behavior]`, `[prices]`, `[experiment]`; new `[auction] grace_days`, `[[agents]]`, `[[bids]]`, and optional `[events] forced_defaults`, `missed_contributions`, `execution_price_overrides`. Agent rows use exactly the Task 1 seed field names.

- [ ] **Step 1: Write failing CLI tests:** running `auction-run` on the six-member TOML creates all four auction output files and copies the TOML; `run` on the existing baseline still creates only fixed-order outputs. Reject `reserve_initial > 0`, malformed bids/agent IDs, missing payment capacity or ETH inventory, a forced default before that member's realized payout, missing historical price tail, and an invalid grace value. The sample pilot's first bid is 20% and first payout is 480 USDC.
- [ ] **Step 2: Run** `python -m pytest tests/test_cli.py -q` and confirm the new cases fail.
- [ ] **Step 3: Implement** auction-only config loading and command dispatch. Reuse `_resolve_price_file`, historical/stress source construction, and metadata hashing; pass `extra_days=scenario.grace_days` to the price source. Keep old `load_config` and fixed-order command behavior unchanged. Document the sample run and explicitly distinguish research losses from a safety guarantee in `README.md`.
- [ ] **Step 4: Run** `python -m pytest tests/test_cli.py -q` and execute `python -m rosca_sim.cli auction-run --config configs/auction-six-member.toml --output work/auction-pilot`; inspect the generated summary and verify the 600/480/120 accounting.
- [ ] **Step 5: Stage only Task 5 files and commit** `feat: expose auction pilot in CLI`; record a skipped commit if needed.

### Task 6: Grace sensitivity and adversarial acceptance matrix

**Files:** Modify `src/rosca_sim/auction_experiment.py`, `src/rosca_sim/cli.py`, `README.md`; extend `tests/test_auction_experiment.py`, `tests/test_cli.py`.

**Interfaces:** `run_auction_grace_sweep(scenario: AuctionScenario, price_source: PricePath | Callable[[random.Random], PricePath], runs: int, seed: int, grace_days: tuple[int, ...], output_dir: Path) -> Path` writes `auction_grace_frontier.csv`; add `auction-grace-sweep --config PATH --output DIR --days 0 1 3 7 14`. Sample one daily path with the maximum requested tail for each run, then reuse it for every grace value and both collateral policies.

- [ ] **Step 1: Write failing stress tests:** after two zero-discount payouts, 50% fixed collateral, and a day-31 first default, a cash-poor `usdc_first` recipient sells ETH at day 31 with zero grace but at day 38 with seven-day grace; a 50% interim price drop makes seven-day principal loss strictly greater. In six members, four paid-member defaults on one day produce `default_count == 4`, one freeze date, no later payout, and unchanged results if event order is reversed. Exercise no USDC top-up, no eligible bidder, a missed contribution before payout, and a temporary 40% event-price wick. The frontier lists all requested days and worst individual principal loss.
- [ ] **Step 2: Run** `python -m pytest tests/test_auction_experiment.py tests/test_cli.py -q` and confirm the new cases fail.
- [ ] **Step 3: Implement** the sweep and CLI command; report mean and 95th-percentile total principal loss, worst individual loss, interest consumed, settlement delay, and forced ETH sales for each grace/policy pair. Compute percentiles from observed runs only, label the result a scenario comparison rather than a recommended safe grace period, and add the run command/limitations to `README.md`.
- [ ] **Step 4: Run** the full suite with `python -m pytest -q -o addopts= -p no:cacheprovider --basetemp work/pytest-auction-plan`; execute both sample auction commands and check auction-vs-fixed outputs, cash/ETH conservation, and no new legacy failures.
- [ ] **Step 5: Stage only Task 6 files and commit** `test: cover auction grace and correlated defaults`; record a skipped commit if needed.

## Handoff

No implementation is authorized by this plan alone. After review, execute Task 1 through Task 6 with TDD, keep the old mode intact, and stop if the actual repo state or contract rules differ from the approved spec. In particular, the no-penalty pre-payout refund and seven-day no-payment fallback are explicit assumptions to recheck before treating the simulator as a product design.
