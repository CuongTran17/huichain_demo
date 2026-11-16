# Phase A Results Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended for this plan) or superpowers:subagent-driven-development, following the user's selected execution method, to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm web khám phá kết quả ETH 2022, lọc/zoom đồ thị và chạy lại đúng một tình huống để giải thích diễn biến.

**Architecture:** Giữ Streamlit hiện có và thêm một chế độ nghiên cứu. Adapter mới đọc/check các job chuẩn, dựng dữ liệu biểu đồ trong bộ nhớ; renderer mới quản lý bộ lọc và replay. Không sửa engine hoặc tệp nằm trong fingerprint nghiên cứu.

**Tech Stack:** Python≥3.12, Streamlit/Altair/pandas đang có trong extra web; stdlib dataclasses/pathlib/hashlib/csv/json, pytest và Streamlit AppTest. Không thêm dependency.

**Spec:** `docs/superpowers/specs/2026-10-16-phase-a-results-explorer-design.md`, người dùng duyệt ngày2026-10-16.

**Trạng thái thực hiện:** Hoàn tất bốn task và một lượt sửa sau review ngày2026-10-16. Suite cuối242/242, kiểm tra corpus/replay và trình duyệt đạt. Chi tiết bằng chứng, các quyết định và giới hạn: `docs/superpowers/reports/2026-10-16-phase-a-results-explorer-verification.md`.

## Global Constraints

- Main, commit cục bộ, không push; giữ nguyên `work/`, corpus và demo cũ.
- Thêm **Kết quả nghiên cứu 2022** vào app; giữ hai chế độ cũ và giới hạn10000 của sweep cũ.
- Nguồn chuẩn là manifest và job JSON đã xác thực, không tin riêng CSV/metadata aggregate_status. UI và replay không ghi nghiên cứu.
- Giữ nguyên `src/rosca_sim/phase_a.py`, `auction.py`, `model.py`, `prices.py`; không đổi semantics lãi, ký quỹ, default hoặc waterfall.
- Chỉ nghiên cứu đã chạy:6 người,100 USDC/30 ngày,5 mức lãi năm,57 nhóm/mốc, dữ liệu2022. Bộ thật có180 jobs,36 ratios,208 windows,2134080 runs.
- Ngưỡng toàn nghiên cứu dùng giao PASS, tolerance1e-9; số hiển thị làm tròn không tham gia xét PASS. Bộ lọc không đổi ngưỡng toàn nghiên cứu.
- Ký quỹ hiển thị25–200% nghĩa vụ còn lại; lãi0–20%/năm. UI Người1–6 ánh xạ ID0–5.
- Giữ nhãn annual_simple_act365: lãi trên nghĩa vụ ban đầu, không phải dư nợ giảm dần; chưa chứng nhận pháp lý. Luôn ghi giá đóng cửa, trượt giá0, đủ ETH và USDC ngày7 là giả định.
- Không mạng, backend, frontend mới, Aave simulation, game theory, thay tham số tùy ý hoặc full sweep trong mode mới.
- Dùng Manrope/nền phẳng hiện có, nhãn/đơn vị/tooltip và bảng thay thế rõ; không thêm marketing, tracking, font/icon tải mạng hoặc animation cuộn.

## Review Focus

1. Metadata/CSV cũ complete nhưng planned grid có job thiếu; phải hạ coverage và ẩn ngưỡng liên quan, không im lặng tái dùng PASS cũ (Task1).
2. Bộ lọc có nhóm không tồn tại, rỗng hoặc thiếu điểm tỷ lệ; không giữ số liệu cũ, tô ô thiếu thành0 hay nối đường qua khoảng chưa chạy (Tasks2,4).
3. Cache giữ snapshot sau khi nguồn đổi hoặc đang đọc nửa phiên; phải vô hiệu hóa, không ghép các phiên thành complete (Tasks1,4).
4. Worst-total khác ngày worst-individual và tie loss0; không đối chiếu nhầm member rows/interest ở ngày khác hoặc tự gọi engine khi đổi filter (Tasks2–4).
5. Chế độ cũ chi phối nguồn replay, UI ghi lại corpus hoặc sửa file hash core; phải tách state và chứng minh read-only, bảo toàn fingerprint (Tasks3,4).

## File map và kiểm thử nền

- Create `src/rosca_sim/phase_a_results.py`: đọc/xác thực, lọc/gộp dữ liệu, adapter replay; không import Streamlit.
- Create `src/rosca_sim/web_phase_a.py`: chart builders, cache và renderer.
- Modify `src/rosca_sim/web_app.py`: chọn mode và dispatch trước sidebar nguồn cũ, không refactor toàn bộ app.
- Create `tests/conftest.py`: fixture nghiên cứu nhỏ dùng chung; hiện repo chưa có tệp này. Không đổi fixtures của tests cũ.
- Create `tests/test_phase_a_results.py`, `tests/test_web_phase_a.py`; modify `tests/test_web_app.py`, `README.md`.

Khi triển khai, đọc spec và kiểm tra git/AGENTS trước. Dùng scratch riêng `.superpowers/sdd/2026-10-16-phase-a-results-explorer/`, tạo thư mục bằng file tools/PowerShell. Giữ lựa chọn main của người dùng; không tạo worktree làm mất corpus local. Không xóa scratch của plan khác hoặc tìm cách vượt qua lệnh dọn dẹp bị policy chặn.

Lệnh test: `.\.venv\Scripts\python.exe -m pytest <test-paths> -q -o addopts= -p no:cacheprovider --basetemp .superpowers/sdd/2026-10-16-phase-a-results-explorer/<unique-run>`.
Đặt TEMP/TMP vào scratch cho AppTest nếu môi trường cần; lỗi socketpair xin quyền loopback bằng cơ chế permission, không bỏ test. Mỗi task phải có RED→GREEN rồi commit. Không chạy lại2.13 triệu engine runs để kiểm thử UI.

### Task 1: Đọc snapshot nghiên cứu chỉ đọc và xác thực độ đầy đủ

**Files:** Create `phase_a_results.py`, `tests/conftest.py`, `tests/test_phase_a_results.py`.

**Interfaces** (tất cả hàm sản phẩm trong `rosca_sim.phase_a_results`):

- `CaseKey = tuple[float, float, int, tuple[int, ...]]`: annual_rate, ratio, k, default_ids; `GroupKey = tuple[int, tuple[int, ...]]`.
- Frozen `StudySnapshot(directory: Path, manifest: dict[str, object], summaries: tuple[dict[str, object], ...], thresholds: tuple[dict[str, object], ...], signature: tuple, completed_jobs: int, expected_jobs: int, completed_runs: int, expected_runs: int)`.
- `study_signature(directory: Path) -> tuple`; `load_study(directory: Path) -> StudySnapshot`.
- `member_rows(study: StudySnapshot, key: CaseKey) -> tuple[dict[str, object], ...]`: sáu dòng worst-individual ở job tương ứng, kiểm snapshot trước/sau đọc.

- [x] **Viết fixture và test RED.** Session fixture `phase_a_fixture` trong conftest tạo158 ngày2022, close2000 hằng số, CSV hash thật; gọi prepare/runner hiện có cho5rates×8coarse ratios trên một window (2280 runs). Function fixture `phase_a_copy` copy fixture vào tmp_path, trả `(study_dir, price_csv)` độc lập từng test. Ghi source_label synthetic, không dùng corpus thật làm fixture. Assertions reader:

```python
snapshot = load_study(study_dir)
assert (snapshot.completed_jobs, snapshot.expected_jobs) == (40, 40)
assert snapshot.completed_runs == snapshot.expected_runs == 2280
assert len(snapshot.summaries) == 2280
assert len(snapshot.thresholds) == 291
assert snapshot.thresholds[-1]["candidate_ratio"] == 1.0
```

Thêm test xóa một job fixture trong khi metadata/CSV vẫn complete: global.status=incomplete,candidate=None,completed_jobs39,completed_runs2223,expected_runs2280. Bắt mọi hàm runner/aggregate/prepare bằng spy raise sau khi fixture đã tạo; load_study vẫn hoạt động. Spy `_threshold_rows` xác nhận nhận đủ summaries và toàn planned_ratios, không chỉ các job/ratios có PASS. Chụp bytes+mtime_ns của toàn fixture trước/sau đọc. Chạy `tests/test_phase_a_results.py`; Expected FAIL thiếu module/interfaces, không phải lỗi fixture.

- [x] **Implement reader nhỏ.** Reuse `_manifest`, `_read_job`, `_job_path`, `_threshold_rows`, `_code_hashes` trong phase_a qua adapter, không sửa core. Xác minh study/schema/basis và fixed semantics trước đọc jobs: version1/schema2/ACT365, members6, contribution100,period30,grace7,slippage0,terminal,cap0.20,day_count365,tolerance1e-9 và annual_rates đúng ANNUAL_RATES. Lỗi schema/key/type/OSError chuyển ValueError có tên tệp/nguyên nhân hữu ích. Duyệt annual_rates×planned_ratios, thiếu file ghi coverage thiếu, `.tmp` bỏ qua; file có nhưng hỏng phải từ chối toàn nguồn. Sum completed_runs của job đã xác thực, expected_runs=jobs_expected×57×windows. Giữ summaries, không giữ members của mọi job; threshold tính lại trong bộ nhớ, không đọc CSV để suy PASS.

- [x] **Test rồi implement chữ ký và ổn định đọc.** Signature chứa resolved dir, metadata(name,size,mtime_ns), từng expected job (kể cả marker missing), code hashes; trước/sau đọc phải giống nhau. Test monkeypatch `_read_job` làm đổi metadata/job giữa lần đọc, Expected ValueError yêu cầu tải lại. Test job mới/thay thế làm signature đổi; corrupt payload/incomplete count/duplicate keys, legacy/schema/basis/code mismatch bị chặn; member_rows đúng key/6IDs/window và read-only. File ngoài planned grid không được tính thêm thành coverage. Chữ ký stat không chống tampering cố ý giữ nguyên stat, không thêm hệ thống lock/auth.

- [x] **GREEN và commit.** Run `tests/test_phase_a_results.py tests/test_phase_a.py tests/test_phase_a_runner.py`; Expected PASS, core hashes và corpus thật không đổi. Commit `feat: read validated phase A study snapshots without writes`.

### Task 2: Dữ liệu lọc và ba đồ thị tổng hợp

**Files:** Modify `phase_a_results.py`, `tests/test_phase_a_results.py`; create `web_phase_a.py`, `tests/test_web_phase_a.py`.

**Interfaces:**

- Frozen `StudyFilters(annual_rates: tuple[float, ...], min_ratio: float, max_ratio: float, paid_counts: tuple[int, ...], groups: tuple[GroupKey, ...])`. Tuple rỗng nghĩa là chọn rỗng, không tự hiểu thành tất cả.
- `filter_summaries(study: StudySnapshot, filters: StudyFilters) -> tuple[dict[str, object], ...]`.
- `risk_rows(study: StudySnapshot, filters: StudyFilters) -> tuple[dict[str, object], ...]`; `heatmap_rows(study: StudySnapshot, filters: StudyFilters, annual_rate: float) -> tuple[dict[str, object], ...]`.
- `select_worst(rows: tuple[dict[str, object], ...]) -> CaseKey | None`; `member_label(member_id: int) -> str`.
- `threshold_chart(thresholds: tuple[dict[str, object], ...]) -> alt.LayerChart`; `risk_chart(rows: tuple[dict[str, object], ...], metric: Literal["max_individual_loss", "loss_count"]) -> alt.LayerChart`; `heatmap_chart(rows: tuple[dict[str, object], ...]) -> alt.LayerChart`, trong web_phase_a.

- [x] **Viết literal tests và RED.** Trong synthetic snapshot windows3, cùng rate.20/ratio1, chọn3 nhóm `(k1,0),(k2,0),(k2,1)` có max_individual_loss lần lượt5/7/1 và loss_window_count2/1/0; mỗi nhóm completed/expected_windows3. Assert risk một điểm max7,loss_count3,completed_runs=expected_runs9; heatmap k1max5,k2max7; không chia count thành xác suất hoặc số ngày. Đổi filters không mutate thresholds/snapshot. Empty rates/groups trả rỗng; group ngoài k được chọn bị loại, group malformed hoặc ratio nonfinite/range đảo bị ValueError. Chạy targeted tests; Expected FAIL thiếu interfaces.

- [x] **Implement phép gộp.** Gộp theo `(annual_rate,ratio)` cho risk và `(annual_rate,ratio,k)` cho heatmap; counts là tổng raw window counts, loss là max raw cá nhân, expected groups dựng từ phase_a_cases đã lọc chứ không từ các rows có mặt. Rows có rate,ratio,max_individual_loss,loss_count,completed_runs,expected_runs,coverage_complete,group_count,worst_key,worst_start; heatmap thêm k. Không có observation thì monetary/count=null và coverage_complete=False, không0. Tie worst theo ngày sớm nhất rồi CaseKey tăng dần. member_label(0)='Người 1',member_label(5)='Người 6'.

- [x] **Test RED chart contracts rồi build chart.** Assert `.to_dict()` có X ratio:Q format%,Y tiềnUSDC hoặc count, threshold Y candidate_ratio format%, nominal5 annual rates theo domain cố định0/.05/.10/.15/.20; legend và tooltip đơn vị/raw loss/date/coverage. Ngưỡng incomplete/not_found không thành cột0: biểu diễn trạng thái bằng nhãn/bảng, global lấy study.thresholds[-1], không lấy từ filters. Risk có điểm+đường; chia series thành các segment theo thứ tự planned ratios khi gặp gap, không nối qua ratio thiếu. Heatmap có ô xám/nhãn thiếu dữ liệu cho null, loss0 khác ô thiếu; cell k không còn do bộ lọc không dựng giá trị0. Zoom/pan chỉ trụcX; reset bằng double-click, có chú thích tiếng Việt; khóa Y tiền bắt đầu0, tuyến tính. Tooltip worst thuộc max-individual, không gắn worst cho count. Test một series có ratio.5/1.0 nhưng.75missing không nối chung segment. Test loss1e-10 và0.01 không bị làm tròn trước khi tính threshold.

- [x] **GREEN và commit.** Run `tests/test_phase_a_results.py tests/test_web_phase_a.py`; Expected PASS, chart builders không gọi Streamlit render hay engine. Commit `feat: chart phase A collateral risk with scoped filters`.

### Task 3: Replay một case và diễn biến có mốc thật

**Files:** Modify `phase_a_results.py`, `web_phase_a.py` và hai tệp tests tương ứng.

**Interfaces:**

- Frozen `ReplayResult(run: CaseRun, checks: tuple[str, ...], mismatches: tuple[str, ...])` trong phase_a_results.
- `replay_case(study: StudySnapshot, key: CaseKey, window_start: str, csv_path: Path) -> ReplayResult`.
- `replay_frames(replay: ReplayResult) -> tuple[dict[str, object], ...]`: index,kind,label,day,trace_index(int|None), kinds initial/period/freeze/settlement.
- `render_replay(replay: ReplayResult) -> None` trong web_phase_a; Task4 gọi renderer này, không thực hiện engine bên trong render_replay.

- [x] **Viết test RED đúng một engine call.** Dùng phase_a_copy, case(.2,1.0,1,(0,)),window2022-01-01. Wrap AuctionRoscaModel đúng chỗ được gọi để đếm, replay_case gọi1 lần policyfixed/seed42. Assert:

```python
assert replay.run.result.freeze_day == 1
assert replay.run.result.settlement_day == 8
assert replay.run.result.agent_results[0].net_payout == pytest.approx(558.9041095890411)
assert replay.run.result.worst_member_loss == 0.0
assert not replay.mismatches
assert [(f["kind"], f["day"]) for f in replay_frames(replay)] == [
    ("initial", 0), ("period", 0), ("freeze", 1), ("settlement", 8)]
```

Chụp bytes+mtime_ns corpus và CSV trước/sau. Nguồn không khớp SHA, không đủ paths, start ngoài manifest, key không có summary hoặc study đã đổi phải bị chặn trước engine. Run test; Expected FAIL thiếu replay.

- [x] **Implement adapter replay.** Kiểm chữ ký study hiện tại; đọc CSV2022 ổn định trước/sau, verify SHA256, gọi phase_a_paths rồi kiểm `_paths_hash`/starts khớp manifest, chọn đúng start. Dùng PhaseACase và phase_a_scenario để giữ đúng lượng ETH giả định/capacity; NamedCase+run_named_cases với tuple một case, seed42/source/quote lấy manifest để nhận CaseRun+trace. Không tái tạo formulas, không gọi runner nghiên cứu có write. CSV chỉ nạp khi bấm replay, không cache engine xuyên những lần bấm rõ ràng; session giữ run khi thay mốc. Sau đọc/run chữ ký giá và study phải còn khớp.

- [x] **Test và implement đối chiếu đúng cửa sổ.** Nếu start=worst_individual_start, kiểm worst_member_loss,interest_used,obligation_uncollected và sáu member fields (các field AuctionAgentResult; bỏ study columns), float abs≤1e-9, int/bool/string/None exact. Nếu start=worst_total_start, kiểm principal_loss; cả hai bộ kiểm tra chỉ khi cùng ngày. Đối với start tùy chọn không là worst: checks rỗng, nhãn không có benchmark lưu, không gọi đó là reproduced. Fake stored summaries với hai ngày khác nhau và các maximum độc lập để assert không báo mismatch sai; tie loss0 chọn ngày đã lưu sớm nhất. Stored member khác kết quả tạo mismatches cụ thể, không sửa file hoặc che cảnh báo. Fixture sai logic nhưng checksum hợp lệ chỉ dùng trong test đối chiếu, không giả là data thật.

- [x] **Viết test chart/frame và renderer rồi implement.** Khởi tạo known initial pool/contribution/retained_interest0 theo scenario reserve0; từng period dùng trace có thật. Freeze chỉ là event nếu không có snapshot, không gán số dư sau bán ETH từ trace trước bán. Settlement dùng AuctionRunResult/agent_results. Cho chọn frame theo index để không gộp initial/period cùng ngày0. Render giá dailyUSDT/ETH + rules sự kiện, góp/lĩnh lũy kế và pool/interest tại trace kỳ, cột cuối principal_repaid/principal_loss/interest_received theo Người1–6; claim chỉ người chưa lĩnh. Hai KPI interest_used/obligation_uncollected tách riêng, không cộng kép. Frame không phải settlement không giả cột cuối là trạng thái thời điểm đó. Test AppTest harness render_replay: đổi frame không gọi model, phần không có trace hiện giải thích thay vì đường nội suy.

- [x] **GREEN và commit.** Run hai tests mới + `tests/test_web_analysis.py tests/test_web_reporting.py`; Expected PASS. Commit `feat: replay a phase A case with validated historical traces`.

### Task 4: Tích hợp mode, cache và nghiệm thu đầu cuối

**Files:** Modify `web_app.py`, `web_phase_a.py`, `tests/test_web_phase_a.py`, `tests/test_web_app.py`, `README.md`.

**Interfaces:** `render_phase_a() -> None` trong web_phase_a, gọi từ entrypoint. Cache wrapper `_cached_study(directory: str, signature: tuple) -> StudySnapshot` gọi load_study và xác nhận signature đúng. `csv_bytes(rows: tuple[dict[str, object], ...], provenance: dict[str, object]) -> bytes` trong phase_a_results: export in-memory UTF-8-SIG, metadata nghiên cứu/scope được thêm vào mỗi row; empty trả bytes header không mang số liệu cũ.

- [x] **Viết AppTest RED.** Mode radio `view` thêm 'Kết quả nghiên cứu 2022' sau hai lựa chọn cũ, giữ default cũ để tests/người dùng cũ không đổi luồng. Chọn mode mới và fixture: hiện2280runs/40jobs/global100%, có3 overview/explorer charts trước replay. Assert sửa source cũ không ảnh hưởng study, và study input không sửa old cases. Monkeypatch model raise sau fixture: mở/lọc/zoom reset/chọn case/worst vẫn không gọi engine; chỉ nút replay gọi1, đổi frame không gọi thêm. Run targeted AppTests; Expected FAIL chưa có mode.

- [x] **Implement dispatch và renderer.** Đặt mode radio trước sidebar nguồn cũ; nhánh mode mới lazy-import/render_phase_a rồi st.stop để không rơi vào mã chế độ cũ. Không đổi thứ tự text_input/widget của chế độ cũ. Dùng default đường dẫn tính từ root project, không từ cwd tùy ý. Key mới: `pa_results_dir`, `pa_prices_csv`, `pa_reload`, `pa_rates`, `pa_ratio_range`, `pa_paid_counts`, `pa_groups`, `pa_metric`, `pa_heat_rate`, `pa_case`, `pa_window_kind`, `pa_window_start`, `pa_worst`, `pa_replay`, `pa_frame`; old state không được dùng làm nguồn cho chúng. Mặc định filters all; metricmax_individual_loss; heat rate20% nếu đang chọn, nếu không lấy mức thấp nhất còn chọn.

- [x] **Cache/state tests RED→GREEN.** Trước mỗi cached load lấy study_signature; load_study bảo vệ before/after; nút Tải lại dữ liệu xóa cache của mode mới và replay state, không clear old cases. Replay signature gồm study signature,key,start,resolved CSV path,size,mtime_ns (hash được kiểm khi bấm); thay lựa chọn/nguồn làm ẩn output cũ, giữ nguyên metadata của run cũ. Chọn k mới làm groups/selectedcase/window/frame được reconcile trước tạo widget; empty không fallback sang all. Case không còn trong filters thì không hiển thị như đang chọn. Heat rate ngoài selectedrates tự điều chỉnh; không có rates thì empty state và disable replay. Mỗi thay đổi chỉ xử lý tập summaries. Thiếu CSV vẫn xem tổng hợp, replay báo lỗi cụ thể. File mới xuất hiện/xóa/thay thế sau cache làm coverage/candidate được đọc lại. Test metadata cũ complete + missingjob ở UI: không còn số global100%; không xuất số cũ qua download.

- [x] **Export, copy và docs.** Mỗi chart có bảng mở rộng và download cùng phạm vi; csv_bytes serialize list/tuple/dict thành JSON trong ô, thêm fingerprint,source_label,quote_asset,scope,window_count; result/replay riêng kèmkey/start/seed/các checks. Dùng tiếng Việt và % qua formatters, không sửa raw values. Full overview không thay khi filters thay. Inline error/empty, skeleton khi đọc nguồn, nhãn focus/keyboard rõ, không download external fonts. README thêm cách chạy lệnh Streamlit hiện tại, chọn mode, ý nghĩa controls/zoom reset và cảnh báo không phải xác suất/thanh lý thực.

- [x] **Chạy kiểm chứng tự động và corpus read-only.** Full pytest, `python -m compileall -q src`, `git diff --check`; Expected PASS, hai mode cũ không hồi quy. Đọc corpus thật bằng load_study, assert180/180jobs,10260 summaries,208starts,36ratios,2134080runs,291thresholds; rate candidates [1.85,1.75,1.60,1.50,1.40],global1.85. Replay duy nhất case(.20,1.00,3,(0,1,2)),start2022-04-16: principal_loss172.94916437348778,worst_member_loss57.64972145782926,interest_used82.19178082191775,uncollected255.14094519540564,checks khớp. Chụp corpus bytes/hash+mtime và4core hashes trước/sau đọc/replay/browser; không file nào đổi. Đo thời gian load/filter/replay thực rồi báo, không tự đặt claim hiệu năng.

- [x] **Nghiệm thu trình duyệt và review.** Chạy web loopback127.0.0.1, giữ phiên và mở tab local bằng công cụ browser được cấp. Kiểm desktop và hẹp: chữ Việt/trục/chú giải, đầy đủdata/empty/missingjob ở fixture, filter đổi charts, zoom/pan/doubleclick reset, openworst, replay, đổiframe, stale, exports và quay lại hai mode cũ. Ghi screenshot minh chứng trong scratch hoặc artifact được hỗ trợ, không dựng mockup thay kiểm thử thật. Nếu không có browser/loopback, báo rõ giới hạn, không nói đã visually verified. Một review độc lập read-only toàn diff trước handoff; sửa Important/Critical bằng test RED→GREEN rồi chạy lại suite.

- [x] **Commit và bàn giao.** Commit `feat: integrate the local phase A results explorer`. Chỉ localmain, không push. README/spec/plan ghi trạng thái và kết quả kiểm chứng thật. Không xóa corpus để làm sạch git; giữ `work/`. Theo quy trình finishing, giữ checkout/main như người dùng đã chọn, không hỏi lại merge/push.

## Tự rà soát kế hoạch và handoff

Spec1–2: GlobalConstraints/Tasks1,4; spec3.1:Tasks1,2,4; spec3.2:Task2 và widget testsTask4; spec3.3:Tasks3,4; spec4:Tasks1,3,4; spec5:Filemap/Task4; spec6:tests và nghiệm thu thậtTask4. Năm ReviewFocus đều có test ở task sở hữu. Không có product implementation trong lượt viết plan.

Đã thực hiện inline theo bốn task, với một review độc lập cuối và regression tests cho các sửa lỗi. Giữ corpus local/fingerprint ổn định; không có engine hoặc dependency mới.
