# ABM Due-Date Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đo khả năng hoàn gốc cho người chưa lĩnh khi người đã lĩnh có động cơ bỏ góp tại kỳ kế tiếp vì ETH ký quỹ giảm, đồng thời báo gánh nặng vốn khóa và đối chiếu tỷ lệ 180% của demo.

**Architecture:** Bổ sung nhánh hành vi tùy chọn vào `AuctionRoscaModel` trước khi thu tiền ngày góp; dùng lại toàn bộ auction, bán ETH và quyết toán. Runner Phase B riêng tạo hồ sơ bid, các mức khả năng trả và các cửa sổ ETH lịch sử, lưu checkpoint có fingerprint và báo ngưỡng chỉ trên các case thật sự đã chạy. Phase A và các kết quả 2022 cũ không bị ghi đè.

**Tech Stack:** Python >=3.12, Mesa 3.5.1, pytest hiện có, CSV/JSON và thư viện chuẩn; không thêm dependency.

**Spec:** [ABM due-date default design](../specs/2026-11-08-abm-due-date-default-design.md).

**Target repo:** `C:/Users/Lenovo/Documents/Codex/abm_bitcoin`. Plan này đang lưu trong workspace Blockchain; trước khi triển khai, chép spec và plan vào `docs/superpowers/` trong checkout ABM. Kiểm tra trạng thái Git và quyền ghi khi bắt đầu; không tự push.

## Global Constraints

- Sáu người, sáu kỳ, 100 USDC mỗi 30 ngày; bid năm ở 0%, 5%, 10%, 15%, 20%; ETH chỉ khóa lúc lĩnh và giữ tới hoàn thành/dừng.
- Trigger chiến lược chỉ ở ngày góp sau khi đã lĩnh, trước khi thu tiền kỳ đó. Nếu không trigger, engine hiện hành tiếp tục bình thường. Không theo dõi wick giữa kỳ.
- Người tuân thủ khi quyết toán nộp 0%, 50% hoặc 100% nghĩa vụ còn lại trong 7 ngày; người bùng không nộp. Không coi thiếu USDC của người tuân thủ là bùng có chủ ý.
- Baseline giá ETH/USDT đóng cửa ngày, giả định USDT≈USDC, slippage=0; lưu nguồn, ngày cuối, SHA256 và nêu rõ giới hạn giá thực thi.
- PASS là `max(principal_loss của người chưa lĩnh) ≤ 1e-9` trên mọi case thuộc tập báo cáo; `no_eligible_bid`, case lỗi hoặc thiếu checkpoint không được âm thầm bỏ.
- Không thay contract, web, chính sách giải phóng ETH, công thức bid, waterfall, Phase A, hoặc tạo game theory đầy đủ.

## File Structure

| File trong target repo | Trách nhiệm |
|---|---|
| `src/rosca_sim/auction.py` | Cờ opt-in, trigger ngày góp, chẩn đoán người có động cơ, tỷ lệ USDC trả khi quyết toán; dùng luồng dừng dây hiện tại. |
| `src/rosca_sim/phase_b.py` (mới) | Hồ sơ bid, đường giá, case Phase B, runner checkpoint và tổng hợp có điều kiện. |
| `src/rosca_sim/cli.py` | Một lệnh `auction-phase-b` với dry-run, pilot, full, aggregate-only. |
| `tests/test_auction.py`, `tests/test_phase_b.py` (mới) | Kiểm tra hành vi, kế toán, input lỗi, độ bao phủ và tái lập. |
| `README.md` | Cách chạy và giới hạn kết luận. |

## Review Focus

1. ETH vừa chạm đúng nghĩa vụ: không trigger vì quy tắc là `E < O`; test Task 1.
2. Nhiều người có động cơ cùng ngày: dừng một lần, không thu kỳ hiện tại và không bán ETH hai lần; test Task 1.
3. Sự kiện bùng đặt trước trùng ngày/người với trigger chiến lược: hợp nhóm và bảo toàn dòng tiền; test Task 1.
4. 50% khả năng nộp USDC: tính trên **nghĩa vụ tại lúc dừng**, không trên nghĩa vụ ban đầu hay quỹ lĩnh; test Task 2.
5. Giá thiếu ngày cuối, checkpoint thiếu hoặc CSV đổi: từ chối công bố ngưỡng hoàn chỉnh; test Task 3 và Task 4.

---

### Task 1: Quyết định bùng tại ngày góp

**Files:** Modify `src/rosca_sim/auction.py`; Test `tests/test_auction.py`.

**Interfaces:**
- Thêm `AuctionScenario.strategic_default_on_due: bool = False` ở cuối dataclass; phải là bool thật.
- Trong model, `strategic_default_gaps: dict[int, float]` lưu `O − E` của người đã trigger; không thêm field vào `AuctionRunResult` cũ.
- `_due_strategic_defaults(day: int) -> tuple[int, ...]`: chỉ xét agent đã lĩnh, `remaining_obligation > 1e-9`; dùng `price_path.daily_prices[day]` hoặc override qua `_execution_price(day)` và `liquidation_slippage`. Điều kiện `E + 1e-9 < O`. Không xét người chưa lĩnh hoặc người đã trả xong.
- Gọi ngay đầu `step()` tại due date, trước `contribute()`; hợp với forced/missed events cùng ngày. Giữ xử lý sự kiện giữa kỳ cũ cho kịch bản legacy.

- [ ] **Step 1: Viết test đỏ** cho path 1.0 tới ngày 29, 0.5 ở ngày 30, bid 0, ratio 1.8: ID0 lĩnh ngày 0, bùng ngày 30, không ai đóng kỳ 30, `strategic_default_gaps[0]≈50`, người chưa lĩnh mỗi người mất 10 USDC khi không có lãi/nguồn khác. Test ratio 2.0 tại giá 0.5 không trigger; test cờ tắt giữ luồng cũ.
- [ ] **Step 2: Chạy** `python -m pytest tests/test_auction.py -q`; dự kiến test mới FAIL trước sửa.
- [ ] **Step 3: Cài nhánh quyết định tối thiểu** bằng helper trên, không viết engine quyết toán mới. Với nhiều trigger cùng ngày, union với sự kiện explicit, `default_ids` là set duy nhất và `stop_reason="default"`.
- [ ] **Step 4: Thêm test đỏ/rồi xanh** cho hai người đã lĩnh cùng trigger ngày 60, trigger tại đúng ranh giới `E=O` (không bùng), forced default trùng ID/ngày, người chưa lĩnh không tự trigger, và cùng giá giảm ngày 15 rồi phục hồi ngày 30 (không bùng).
- [ ] **Step 5: Chạy** `python -m pytest tests/test_auction.py -q`; tất cả PASS. Commit cục bộ phần engine/test nếu checkout có Git.

### Task 2: Khả năng nộp USDC theo phần trăm khi dây dừng

**Files:** Modify `src/rosca_sim/auction.py`; Test `tests/test_auction.py`.

**Interfaces:**
- Thêm `AuctionScenario.settlement_capacity_fraction: float | None = None` ở cuối dataclass; `None` giữ nguyên `AuctionAgentSeed.usdc_capacity` và mọi case cũ.
- Nếu có giá trị, kiểm tra finite, numeric nhưng không bool, nằm trong `[0,1]`. Trong `_settle()`, với người đã lĩnh nhưng không thuộc `default_ids`, dùng `fraction × remaining_obligation` làm trần USDC; với người bùng, giữ 0. `payment_day_offset=7`, `usdc_first` trong study.

- [ ] **Step 1: Viết test đỏ**: sau hai người đã lĩnh, ép ID0 bùng ngày 60; ID1 còn O=400. Với fraction 0/0.5/1, `usdc_settlement_paid` lần lượt 0/200/400; phần còn thiếu được xử lý bằng ETH ngày 67; ID0 không được nộp USDC.
- [ ] **Step 2: Chạy test riêng**, xác nhận FAIL; sau đó cài trần mới trong `_settle()` và validation.
- [ ] **Step 3: Kiểm tra** fraction âm, >1, `nan`, `bool` bị từ chối; `None` cho cùng kết quả như trước. Chạy `python -m pytest tests/test_auction.py -q`; PASS và bảo toàn tiền/ETH. Commit cục bộ nếu có Git.

### Task 3: Case và dữ liệu lịch sử Phase B

**Files:** Create `src/rosca_sim/phase_b.py`, `tests/test_phase_b.py`; reuse `src/rosca_sim/prices.py`.

**Interfaces:**
- `phase_b_paths(points: tuple[PricePoint, ...]) -> tuple[PricePath, ...]`: dùng `valid_historical_starts(points, 6, 30, 7)` và `sample_historical_path(..., normalize=False, extra_days=7)`; kiểm tra ngày trùng/thiếu và chỉ dùng cửa sổ liên tục 158 ngày.
- `phase_b_scenario(path: PricePath, ratio: float, profile: str, fraction: float, *, strategic: bool, paid_count: int | None = None, forced_ids: tuple[int, ...] = ()) -> AuctionScenario`.
- Ba profile cố định: `all_zero`, `all_twenty`, `mixed_rotating` với `rate = (member_id + period) % 5 × 0.05` cho các ID chưa lĩnh có thể chào; engine vẫn quyết định người thắng/tie theo quy tắc cũ. Dùng đủ ETH giả định để không bỏ qua bid trong nghiên cứu ngưỡng; báo rõ giả định.
- Stress forced default đặt ngày `paid_count × 30` (không dùng `(paid_count−1)×30+1` của Phase A); `paid_count=1..5`, mỗi tập con không rỗng của **payout order thực tế** trong lượt chạy đối chứng cùng path/profile/ratio. Không mặc định ID0..k−1 khi bid trộn. Kịch bản strategic không có forced default; đối chứng `strategic=False` dùng cùng path/profile/ratio/fraction.

- [ ] **Step 1: Viết test đỏ** cho 365 ngày 2022 tạo 208 cửa sổ, 158 ngày/cửa sổ, không normalize; CSV thiếu một ngày không được đệm và không tạo cửa sổ băng qua chỗ thiếu.
- [ ] **Step 2: Viết test đỏ** cho ba profile, bid trong `[0,.20]`, tie theo ID, mixed làm thay đổi thứ tự lĩnh; forced default sau k người ở ngày 30/60/90/120/150; không có bid sau khi đã lĩnh.
- [ ] **Step 3: Cài generator dùng price helpers hiện có**, chạy `python -m pytest tests/test_phase_b.py -q`; PASS. Commit cục bộ nếu có Git.

### Task 4: Runner pilot, full và checkpoint có đối chiếu

**Files:** Modify `src/rosca_sim/phase_b.py`, `src/rosca_sim/cli.py`; Test `tests/test_phase_b.py`.

**Interfaces:**
- CLI `auction-phase-b --prices PATH --output DIR --source-label TEXT --end YYYY-MM-DD --dry-run|--pilot|--full|--aggregate-only`. Bắt đầu 2022-01-01; `--end` phải là ngày cuối **đã có trong CSV**. Không tải mạng khi chạy; dùng `fetch-binance-prices` hiện có để chuẩn bị CSV đến cuối tháng hoàn chỉnh mới nhất.
- Pilot: path 2022-04-18 và một số cửa sổ do dữ liệu xác định có drawdown 30 ngày lớn nhất; ratios `[1.35,1.40,1.50,1.80,1.85,1.90]`; cả ba profile, ba fraction, strategic + all-pay + một số forced groups đại diện (một người đầu; hai người sau lượt ba; toàn bộ người đã lĩnh sau lượt năm). Pilot chỉ sàng lọc, không công bố ngưỡng chung.
- Full: từ pilot chọn **một ứng viên chung** cho tất cả profile/fraction, chạy ứng viên và điểm thấp hơn 0.05 trên mọi cửa sổ, 57 forced groups tại ngày góp và nhánh strategic. Nếu ứng viên FAIL, nâng 0.05; nếu điểm thấp hơn PASS, hạ 0.05 và lặp đến khi có ranh giới trong lưới 0.25–2.00. Báo “nhỏ nhất trong các mức đã thử đạt PASS”, không nhận là tối ưu liên tục hoặc chứng minh tính đơn điệu.
- Checkpoint một job cho `(profile, fraction, ratio, mode)` vào thư mục Phase B mới; ghi input fingerprint gồm SHA256 CSV, start/end, version study, nguồn, profiles, ratios, mã `auction.py`/`phase_b.py`/`prices.py`. Chỉ tái dùng job hoàn chỉnh khớp fingerprint; ghi file tạm rồi thay thế. Aggregate-only từ chối nếu thiếu/mismatch job và ghi `incomplete`, không xuất `complete` threshold.

- [ ] **Step 1: Viết test đỏ** cho `--dry-run`/pilot metadata, checkpoint tái dùng, CSV/hash thay đổi bị từ chối, một job thiếu không được báo PASS, và dữ liệu không đủ 7 ngày tail không được lặp giá cuối.
- [ ] **Step 2: Cài CLI và runner tối thiểu**, giữ Phase A và các tệp `results/phase-a-2022-annual/` nguyên trạng.
- [ ] **Step 3: Chạy** `python -m pytest tests/test_phase_b.py tests/test_phase_a.py -q`; PASS. Chạy pilot trên CSV 2022 gốc, kiểm số run/chỉ số và checkpoint. Commit cục bộ nếu có Git.

### Task 5: Bảng ngưỡng, gánh nặng ký quỹ và kiểm chứng cuối

**Files:** Modify `src/rosca_sim/phase_b.py`, `README.md`; Test `tests/test_phase_b.py`.

**Interfaces:**
- Xuất `phase_b_summary.csv` cho từng `(profile,fraction,ratio,mode)` gồm số cửa sổ/case yêu cầu và hoàn tất, số case mất gốc, mất gốc cá nhân lớn nhất, `no_eligible_bid`, số người có động cơ bùng, tổng `O−E` dương, lãi bị dùng, nợ chưa thu, ETH khóa và USDC thực nhận từng lượt.
- Xuất `phase_b_thresholds.csv` theo profile/fraction và giao toàn bộ; kèm tập ratios đã kiểm, điểm dưới còn FAIL, trạng thái `complete/incomplete/not_found`. `phase_b_metadata.json` giữ giả định và fingerprint. Báo riêng 180% là PASS/FAIL theo từng profile/fraction, không gọi ngưỡng 185% cũ là kết quả mới.
- Gánh nặng vốn: tỷ số `locked_eth × payout_day_price / net_payout` và, khi `net_payout>100`, tỷ số trên `net_payout−100`; không gán mức “hấp dẫn” hoặc tỷ lệ người sẵn lòng tham gia khi chưa có dữ liệu ví/ngân sách.

- [ ] **Step 1: Viết test đỏ** cho ngưỡng dựa trên **max loss từng người** (không dùng trung bình), tất cả profile/fraction, đủ checkpoint, và hai tỷ số vốn khóa; không tính tỷ số ròng khi mẫu số ≤0.
- [ ] **Step 2: Cài aggregate và README**: lệnh lấy CSV lịch sử, lệnh pilot/full/aggregate, giải thích bùng do giá, bùng đặt trước, thiếu USDC, giới hạn daily close/USDT≈USDC và cách đọc 180%.
- [ ] **Step 3: Chạy** `python -m pytest -q`; chạy full trên dữ liệu đã chốt khi CSV đầy đủ; chạy lại `--aggregate-only` để kiểm cùng fingerprint/ngưỡng. Kiểm tay ít nhất một case ranh giới theo trace và cân bằng tiền/ETH. Commit cục bộ nếu có Git.

## Điều kiện nghiệm thu

- Kịch bản ETH giảm giữa kỳ rồi hồi trước hạn không sinh strategic default; giảm còn kéo dài tới hạn có thể sinh default đúng ngày góp.
- Các case 0/50/100% của người tuân thủ, nhóm bùng đồng thời và bid trộn đều có dấu vết tái lập được; không đếm lãi hoặc ETH hai lần.
- Báo rõ **phạm vi đã chạy**, ngưỡng PASS có điều kiện, điểm ngay dưới FAIL, giá trị 180% của demo và chi phí ETH khóa. Không ghi “an toàn tuyệt đối” hay suy ra xác suất từ cửa sổ lịch sử chồng lấn.
- Không ghi đè Phase A, kết quả demo, hợp đồng Sepolia hoặc dashboard hiện có.

## Điều chỉnh khi triển khai

- `due_date_auction.py` chứa chính sách Phase B và gọi lại engine đấu giá hiện hành. Việc giữ nguyên byte của `auction.py` cho phép dashboard đọc và tái hiện checkpoint Phase A đã phát hành.
- Kiểm thử chính sách ngày góp nằm trong `tests/test_due_date_default.py`. Runner dùng cùng một bản CSV trong bộ nhớ để đọc giá và tính SHA256. Báo cáo chỉ công bố hoàn tất sau khi đối chiếu checkpoint và xuất các bảng.
