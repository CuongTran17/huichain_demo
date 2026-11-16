# Phase A Annual Bid Study Implementation Plan

**Tiến độ 2026-10-15:** Ba task triển khai xong trên main, commit cục bộ; rà soát độc lập và sửa lỗi trạng thái hoàn tất cũ khi mở rộng lưới. Toàn bộ 220 tests đạt lại trong31.64s; compileall/diff check đạt. Dry-run CSV thực: 208 cửa sổ, 474240 coarse runs; chưa chạy pilot/full sweep/refinement bằng dữ liệu thực.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Chuyển auction sang lãi năm tối đa 20% và chạy đợt A thu gọn để tìm ngưỡng không mất gốc có điều kiện trên ETH năm 2022.

**Architecture:** Đổi đơn vị bid một lần, đồng bộ engine/CLI/JSON/web/tests; không giữ hai chế độ lãi. Thêm một module `phase_a.py` cho scenario generation, runner tuần tự và aggregation; engine Mesa hiện tại vẫn là nguồn quyết định dòng tiền. CLI chạy nghiên cứu, dashboard chỉ cập nhật đơn vị lãi, không xây màn hình sweep mới.

**Tech Stack:** Python≥3.12, Mesa3.5.1, Streamlit hiện có, stdlib itertools/dataclasses/csv/json/hashlib/Decimal, pytest; không thêm dependency.

**Spec:** `docs/superpowers/specs/2026-10-15-phase-a-annual-bid-study.md`. Spec mới thay riêng gross-discount semantics của spec auction cũ, không thay cơ chế giữ ETH/quyết toán/hoàn gốc đã triển khai.

## Global Constraints

- Main, commit cục bộ, không push; không chạm `work/`, không sửa/ghi đè kết quả demo cũ.
- 6 người, 100 USDC/kỳ 30 ngày, giá ETH 2022 trên mọi cửa sổ 158 ngày hợp lệ; đủ 365 ngày thì có 208 windows.
- Annual rates 0/5/10/15/20%; đơn vị input là tỷ lệ 0..0.20, lãi đơn ACT/365; không khẳng định tuân thủ pháp luật.
- 57 nhóm/mốc: mọi nonempty subset của prefix k=1..5, default day 1/31/61/91/121. Bùng bán ETH ngay, người khác trả đủ USDC ngày 7. Không trượt giá/stress floor/reserve.
- Sẵn đủ ETH cho tỷ lệ lớn nhất 200%; chỉ fixed collateral. Ký quỹ 25..200%, bước 25 điểm phần trăm, tinh chỉnh 5 điểm; không nghiên cứu khả thi vốn ở bước A.
- 0% mất gốc từng người với tolerance 1e−9; incomplete không được thành PASS. Dữ liệu cũ không được tự diễn giải theo đơn vị mới.
- Không game theory, cash wallet, margin call, nhiều năm, đổi framework hoặc nâng giới hạn web sweep.

## Review Focus

1. Nhầm20% quỹ thành20%/năm, tính cả kỳ đã góp hoặc lãi âm ở kỳ cuối; dữ liệu schema1 bị tái diễn giải âm thầm (Task1).
2. Prefix/subset không đúng người đã lĩnh, k5 thiếu nhóm5 người, giá ký quỹ sai ngày, ETH giả định đủ nhưng có no-eligible (Task2).
3. Ngày thiếu/tail thiếu, normalization hoặc dữ liệu ngoài2022 lọt vào; số windows không đúng mẫu thực có (Tasks2–3).
4. Checkpoint khác CSV/config/code, job dở dang hoặc lỗi bị bỏ qua làm báo ngưỡng chung sai (Task3).
5. Ngưỡng riêng khác ngưỡng chung, làm tròn giấu mất gốc, PASS không đơn điệu hoặc refinement dùng một vài windows mà báo toàn bộ (Task3).

## File map

- Modify `src/rosca_sim/auction.py`: annual bid validation/calculation và result field, không thay fixed-order `model.py`.
- Modify `src/rosca_sim/cli.py`, `auction_experiment.py`, `web_cases.py`, `web_app.py`, `web_reporting.py`: đồng bộ config/export/UI units.
- Modify `configs/auction-six-member.toml`, các config auction khác nếu có bằng cách tìm `[[bids]]`; không sửa config fixed-order.
- Create `src/rosca_sim/phase_a.py`, `tests/test_phase_a.py`; không tạo thêm runner/report framework.
- Modify tests auction/auction_experiment/cli/web_cases/web_analysis/web_reporting/web_app khi phụ thuộc bid cũ; `README.md` hướng dẫn dữ liệu mới và cách chạy.

## Preflight và lệnh test

Chỉ triển khai sau người dùng duyệt plan. Kiểm tra git status, giữ thay đổi người dùng; đọc AGENTS nếu có. Tạo thư mục scratch riêng trước khi pytest dùng basetemp. Các helper Bash trước đây bị sandbox chặn; nếu vẫn vậy dùng PowerShell và ledger, không thay quyền Git toàn máy.

Lệnh nền: `.\.venv\Scripts\python.exe -m pytest -q -o addopts= -p no:cacheprovider --basetemp .superpowers/sdd/2026-10-15-phase-a-annual-bid-study/<run-id>`. Khi chạy Streamlit tests, dùng TEMP/TMP trong scratch; nếu socketpair bị chặn xin quyền loopback, không bỏ test hay sửa app để né. Mỗi task RED→GREEN, commit scoped; full suite trước handoff. Chưa chạy lại suite ở lượt viết tài liệu này.

### Task 1: Chuyển đơn vị bid xuyên suốt, có ranh giới dữ liệu cũ

**Files:** `auction.py`, `cli.py`, `auction_experiment.py`, `web_cases.py`, `web_reporting.py`, `web_app.py`, config auction, các tests liên quan và README.

**Interfaces:** `AuctionBid(period: int, member_id: int, annual_rate: float)`; `annual_bid_interest(obligation: float, annual_rate: float, remaining_days: int) -> float` trong auction.py. Result field `winning_annual_rate: float | None` thay `winning_bid`; JSON schema2, TOML field `annual_rate`. Monetary field `bid_interest_paid` và trace `bid_interest` giữ nghĩa USDC. Không còn consumer nào suy ra interest bằng gross×annual_rate.

- [x] Viết `test_annual_bid_interest_uses_remaining_days`: O500,r0.20,D150→41.0958904109589; O400,D120→26.3013698630137; O0,D0→0; r0→0. Kiểm thử bool, NaN/inf, âm, >0.20; không clamp. Kiểm tra rate0.20 được chấp nhận.
- [x] Viết engine test first payout558.9041095890411, lock theo O500 độc lập bid; sau góp100 O400 và ETH không giảm. Completion mọi bid20%/năm giữ/chia90.4109589041096, không thu lãi hai lần. Test cấu hình dài có computed interest>=gross bị từ chối trước góp/transfer của lượt lỗi. Chạy test mới, Expected FAIL do chưa có annual semantics.
- [x] Implement helper và validation tại input boundary; gọi đúng helper khi xác định tiền lĩnh, xếp bid theo annual_rate. Tính/validate khoản chi trước mutation góp của lượt để lỗi không để ledger nửa chừng. Không đổi recovery, interest-source attribution hoặc collateral policy.
- [x] Cập nhật tất cả caller/result construction với tên field mới. CLI cũ `rate`/JSONschema1 bị từ chối giải thích rõ gross-discount khác annual; schema2 có `annual_rate` hợp lệ roundtrip. Không cung cấp nút tự chuyển0.20 cũ thành0.20 mới. UI editor cột annual_rate có caption0.20=20%/năm, giới hạn20% inclusive. Result tables/metadata lưu basis/cap/day-count/schema2.
- [x] Chuyển fixtures tests/config auction sang annual semantics, tính lại kỳ vọng độc lập bằng số học; không giảm coverage giữ ETH, đồng thời bùng, USDC/ETH settlement, nguồn lãi, cash conservation. Những ví dụ lãi120 cũ không còn hợp lệ với dây6 người: thay fixture/kỳ vọng hợp lệ, không cho rate vượt cap để giữ số cũ. Cập nhật README phân biệt nghiên cứu với pháp lý và file cũ.
- [x] Run toàn suite, Expected PASS; kiểm tra CLI+web mới cùng case ra cùng tiền lĩnh và lãi. Commit `feat: use capped annual simple interest in auction bids`.

### Task 2: Sinh đúng bộ tình huống đợt A và cửa sổ2022

**Files:** Create `src/rosca_sim/phase_a.py`, `tests/test_phase_a.py`.

**Interfaces:** `PhaseACase(annual_rate: float, paid_count: int, default_ids: tuple[int, ...])` frozen dataclass, property `default_day: int`; `phase_a_cases() -> tuple[PhaseACase, ...]` (285 cases); `phase_a_paths(points: tuple[PricePoint, ...]) -> tuple[PricePath, ...]`; `phase_a_scenario(case: PhaseACase, ratio: float, path: PricePath) -> AuctionScenario`.

- [x] Viết `test_phase_a_has_all_nonempty_prefix_subsets`:5 rates×57=285 unique cases, nhóm chứa cả5 người ở k5, không có người chưa lĩnh, dates đúng1/31/61/91/121. Chạy test, Expected FAIL thiếu interfaces.
- [x] Dùng `itertools.combinations`/prefix theo thứ tự ổn định. Sinh bid annual bằng nhau cho mọi người chưa lĩnh tại mỗi kỳ, tie-ID đảm bảo0..5; không dùng mức lãi khác nhau để ép thứ tự.
- [x] Viết `test_phase_a_uses_all_2022_windows`: fixture365 ngày2022 cho208 paths bắt đầuJan1..Jul27, mỗi path158 ngày, giá không normalize; có thêm2021/2023 vẫn không dùng; một ngày thiếu loại đúng các windows ảnh hưởng, không fill; không cówindow thì ValueError. Giá fake chỉ là unit fixtures. Dùng `valid_historical_starts` và `sample_historical_path(..., normalize=False, window_start=..., extra_days=7)` hiện có, không fork loader.
- [x] Cấp mỗi agent lượng ETH hữu hạn đủ bảo đảm mọi ratio≤2 theo giá due-date thấp nhất path, ví dụ `2×500/min(path.prices)+1`; không dùng infinity, không động tới cap xác thực engine. All agents modeusdc_first, capacity500, payment_day_offset7; default batch xử lý như engine nên không thu USDC của người bùng. Không có missed event/override/stress/slippage/reserve.
- [x] Viết test k=1, k=3 với subset không liên tiếp (0,2), và k=5 với tất cả người đã lĩnh: payout_order bằng prefix k, run default đúng ngày; compliant USDC bằng nghĩa vụ còn lại và payment_day=freeze+7, ETH trả đủ; trigger USDC bằng 0 và ETH bán đúng ngày, không có no-eligible. Rerun test permutation default_ids; hoàn gốc/nguồn lãi và ETH identities giữ đúng.
- [x] Run `tests/test_phase_a.py` và auction regression, Expected PASS. Commit `feat: generate bounded phase A historical default cases`.

### Task 3: Runner CLI nhỏ, tổng hợp ngưỡng và tinh chỉnh

**Files:** Modify `phase_a.py`, `cli.py`, `tests/test_phase_a.py`, `tests/test_cli.py`, `README.md`.

**Interfaces:** `run_phase_a_job(paths: tuple[PricePath,...], annual_rate: float, ratio: float, output_dir: Path, fingerprint: str) -> Path`; `aggregate_phase_a(output_dir: Path) -> tuple[dict[str, object], ...]`; `refinement_ratios(rows: tuple[dict[str, object], ...]) -> tuple[float, ...]`. Dùng `phase_a_paths` từ Task 2 một lần rồi truyền các paths cho mọi job. Job tables/metadata đúng spec; CLI lệnh `auction-phase-a` đọc một CSV và không gọi paired reputation runner.

- [x] Test một synthetic path (158 ngày) tạo 57 engine runs/job, 5 rates × 8 ratios là 40 coarse jobs; dữ liệu đầy đủ 2022 cho 474240 expected runs. Test dry-run chỉ in counts/fingerprint, không tạo kết quả/instantiate model; fake dates không được gắn nhãn data thật.
- [x] Implement CLI flags `--prices PATH --output DIR --source-label TEXT --quote-asset USDT`, modes `--dry-run`, `--aggregate-only`, `--refine`, hoặc cặp selector `--annual-rate VALUE --ratio VALUE`. Các modes/selector loại trừ nhau; thiếu một selector thì lỗi trước chạy. Annual rate thuộc 5 mức đã chốt; ratio thuộc lưới coarse hoặc lưới 5 điểm phần trăm trong 25..200%. Không flag tùy biến số người, slippage, event day, capacity hay server. Không có mode/selector thì chạy 40 coarse jobs; refinement đòi coarse đầy đủ, chạy các điểm mới trên cả 5 rates và toàn bộ windows × 57; aggregate ghi cuối.
- [x] Run model tuần tự, aggregate online theo `(rate,ratio,k,default_ids)`. Lưu 57 summaries/job và 6 member rows cho worst-individual-loss window của từng key; ghi expected/completed counts tuyệt đối. Tie chọn ngày sớm nhất; ghi ngày max-total-loss riêng nếu khác ngày max-individual-loss. Không giữ toàn bộ runs trong bộ nhớ.
- [x] Test checkpoint: cùng input/code hash/window list/version reuse completed job không gọi lại model; đổi CSV/rate/ratio/semantics không reuse. Code fingerprint phải gồm SHA256 các source ảnh hưởng (phase_a/auction/model/prices), kể cả cây Git dirty hoặc Git không khả dụng; commit ID chỉ là thông tin bổ sung. Publish bằng tempfile+replace sau tất cả runs đạt; không reuse phần dở dang, mọi exception làm job failed/incomplete, không ghi complete giả. Reject job xung đột ở output dir, không tự xóa/ghi đè; lưu run manifest trước để kiểm tra phạm vi.
- [x] Test aggregation bằng rows literal có hai nhóm PASS sets khác nhau: ngưỡng riêng có thể tồn tại nhưng giao rỗng thì ngưỡng chung not_found. Thiếu window/job hoặc no-eligible thì incomplete, không PASS; loss 1e−10 khác loss 0.01, không làm tròn trước xét. Mỗi output ghi raw worst loss và member values; ngưỡng là nhỏ nhất đã thử, không phải minimum liên tục.
- [x] Test refinement: coarse PASS tại 1.25 có trước 1.00 thì thêm 1.05/1.10/1.15/1.20; boundary 0.25 không xuống dưới. Hợp điểm từ case/rate/global dedup bằng Decimal, không binary search. Nếu ratio cao hơn FAIL sau PASS vẫn giữ/báo cảnh báo, lấy giao thực tế; không thấy coarse PASS thì not_found với tested grid, không tự vượt 2.00.
- [x] Run targeted tests rồi toàn repo, compileall và diff check, Expected PASS. Independent read-only review trước kết luận. README nêu CLI Windows, outputs, không sửa limit web 10k; dùng thời gian đo được thay vì đoán ETA, không claim yield/safety.
- [x] Commit `feat: run phase A collateral thresholds from local ETH history` (742f21c).

**Bước nghiên cứu riêng, chưa chạy:** Sau khi người dùng duyệt chạy thí nghiệm, pilot một job 20%/ratio 1.00, ghi wall time/coverage/identities rồi chạy coarse và refine. Không coi tiny fixture/pilot là full study, không overwrite results cũ; study chưa đủ job chỉ báo incomplete.

## Handoff và giới hạn

Rà soát độc lập: không phát hiện Critical; một Important đã sửa RED→GREEN: mở rộng lưới phải công bố `incomplete` và xóa ngưỡng ứng viên cũ trước chạy job mới, kể cả khi tiến trình bị ngắt. Một góp ý hình thức hoãn: dòng trống dư cuối `tests/test_phase_a.py` trong commit range.

Các quyết định giữ nguyên: main/PowerShell theo yêu cầu người dùng, không có cách ly nhánh; tách runner tests sang tệp riêng để từng task có commit xanh. Runner chỉ hỗ trợ một tiến trình trên mã cố định (không xử lý cạnh tranh ghi hay sửa source giữa job). Checksum phát hiện hỏng file, không xác thực chống sửa dữ liệu có chủ ý. Không bảo đảm giao dịch nguyên tử trên toàn bộ CSV/metadata khi filesystem lỗi: sau sửa lỗi I/O cần chạy aggregate lại. Chưa có kết luận ngưỡng/runtime nghiên cứu thực, pháp lý hay khả thi vốn; vi phạm các giả định này có thể làm kết quả không đáng tin hoặc không triển khai được.

Đã triển khai theo ba task, giữ phạm vi spec; không xây scheduler/resume tổng quát. Chưa có benchmark/kết quả ngưỡng lịch sử mới. Nếu pilot chứng minh Mesa chạy quá lâu, báo thời gian đo và đề xuất lựa chọn trước khi viết một engine nhanh khác hay giảm số case. Chạy nghiên cứu đầy đủ là bước riêng sau kiểm thử triển khai, không tự chạy gần nửa triệu lượt trong lúc sửa UI.
