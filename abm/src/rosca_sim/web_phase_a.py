"""Streamlit views for validated phase-A checkpoints; no research writes."""

import altair as alt
import pandas as pd
import streamlit as st
from dataclasses import asdict
from pathlib import Path
from datetime import date, timedelta
import json

from rosca_sim.phase_a import ANNUAL_RATES, phase_a_cases
from rosca_sim.phase_a_results import (StudyFilters, case_key, csv_bytes, filter_summaries,
    heatmap_rows, load_study, member_label, replay_case, replay_frames, risk_rows,
    select_worst, study_signature)
from rosca_sim.web_reporting import trace_rows

RATE_COLOR = alt.Color("annual_rate:N", title="Lãi năm", scale=alt.Scale(
    domain=list(ANNUAL_RATES), range=["#315b7c", "#bc6644", "#4b8063", "#927343", "#806194"]),
    legend=alt.Legend(labelExpr="format(datum.value, '.0%')"))
ZOOM_NOTE = "Kéo để dịch trục ký quỹ, cuộn để phóng to; nhấp đúp để đặt lại. Trục tiền bắt đầu từ 0."


def threshold_chart(thresholds) -> alt.LayerChart:
    rows = [dict(r, label={"incomplete": "Chưa đủ dữ liệu", "not_found": "Chưa tìm thấy"}.get(
        r["status"], f'{r["candidate_ratio"]:.0%}' if r["candidate_ratio"] is not None else ""))
        for r in thresholds if r["scope"] == "rate"]
    base = alt.Chart(pd.DataFrame(rows)).encode(
        x=alt.X("annual_rate:N", title="Lãi chào (%/năm)", axis=alt.Axis(labelExpr="format(datum.value, '.0%')")),
        tooltip=[alt.Tooltip("annual_rate:Q", title="Lãi năm", format=".0%"),
                 alt.Tooltip("candidate_ratio:Q", title="Ký quỹ / nghĩa vụ", format=".0%"), "status:N"])
    bars = base.mark_bar(size=40).encode(y=alt.Y("candidate_ratio:Q", title="Ngưỡng ký quỹ", axis=alt.Axis(format=".0%")))
    labels = base.mark_text(dy=-8, color="#888888").encode(y="candidate_ratio:Q", text="label:N")
    # Missing candidates have no bar; status remains visible above the baseline.
    missing = base.transform_filter("datum.candidate_ratio == null").mark_text(dy=-8, color="#888888").encode(y=alt.value(240), text="label:N")
    return (bars + labels + missing).properties(height=260)


def risk_chart(rows, metric="max_individual_loss") -> alt.LayerChart:
    if metric not in ("max_individual_loss", "loss_count"):
        raise ValueError("unsupported risk metric")
    plotted, segments = [], {}
    for row in sorted(rows, key=lambda r: (r["annual_rate"], r["ratio"])):
        rate = row["annual_rate"]
        segment = segments.get(rate, 0)
        if not row["coverage_complete"]:
            segment += 1
        plotted.append({**row, "worst_key": _case_label(row["worst_key"]) if row["worst_key"] else None, "segment": f"{rate}:{segment}"})
        segments[rate] = segment + (not row["coverage_complete"])
    title = "Mất gốc cá nhân lớn nhất (USDC)" if metric == "max_individual_loss" else "Số tình huống mất gốc"
    tips = [alt.Tooltip("ratio:Q", title="Ký quỹ", format=".0%"),
            alt.Tooltip("annual_rate:Q", title="Lãi năm", format=".0%"),
            alt.Tooltip(f"{metric}:Q", title=title), "completed_runs:Q", "expected_runs:Q", "coverage_complete:N"]
    if metric == "max_individual_loss":
        tips += ["worst_key:N", "worst_start:N"]
    base = alt.Chart(pd.DataFrame(plotted)).encode(
        x=alt.X("ratio:Q", title="Ký quỹ / nghĩa vụ", axis=alt.Axis(format=".0%")),
        y=alt.Y(f"{metric}:Q", title=title, scale=alt.Scale(zero=True, type="linear")),
        color=RATE_COLOR, tooltip=tips)
    zoom = alt.selection_interval(bind="scales", encodings=["x"])
    return (base.mark_line().encode(detail="segment:N") + base.mark_point(filled=True).encode(
        shape=alt.Shape("coverage_complete:N", title="Đủ dữ liệu"))).add_params(zoom).properties(height=320)


def heatmap_chart(rows) -> alt.LayerChart:
    data = [dict(r, worst_key=_case_label(r["worst_key"]) if r["worst_key"] else None,
                 status="Đủ dữ liệu" if r["coverage_complete"] else "Thiếu dữ liệu") for r in rows]
    base = alt.Chart(pd.DataFrame(data)).encode(
        x=alt.X("ratio:O", title="Ký quỹ / nghĩa vụ", axis=alt.Axis(labelExpr="format(datum.value, '.0%')")),
        y=alt.Y("k:O", title="Số người đã lĩnh (k)"), tooltip=["annual_rate:Q", "ratio:Q", "k:O",
            alt.Tooltip("max_individual_loss:Q", title="Mất gốc cá nhân (USDC)"), "worst_key:N",
            "worst_start:N", "completed_runs:Q", "expected_runs:Q", "status:N"])
    tiles = base.mark_rect().encode(color=alt.condition("datum.max_individual_loss == null",
        alt.value("#cccccc"), alt.Color("max_individual_loss:Q", title="USDC", scale=alt.Scale(scheme="oranges", zero=True))))
    # Dense grids use the legend, raw tooltip and table instead of overlapping amounts.
    labels = base.transform_filter("true" if len({r["ratio"] for r in rows}) <= 12 else "false").mark_text(fontSize=12).encode(
        text=alt.Text("max_individual_loss:Q", format=".2f"))
    return (tiles + labels).properties(height=240)


def _price_event_rows(replay):
    events = {}
    for frame in replay_frames(replay):
        if frame["kind"] != "initial":
            events.setdefault(frame["day"], []).append(frame["label"])
    for member in replay.run.result.agent_results:
        if member.eth_sale_day is not None:
            events.setdefault(member.eth_sale_day, []).append(f"Bán ETH {member_label(member.member_id)}")
    start = date.fromisoformat(replay.run.price_path.start_date)
    return tuple(dict(day=i, date=(start + timedelta(days=i)).isoformat(), price=price,
                      events="; ".join(events.get(i, ())))
                 for i, price in enumerate(replay.run.price_path.daily_prices))


def render_replay(replay) -> None:
    run = replay.run
    frames = replay_frames(replay)
    if st.session_state.get("pa_frame") not in range(len(frames)):
        st.session_state.pa_frame = 0
    selected = st.select_slider("Mốc diễn biến", options=list(range(len(frames))), key="pa_frame",
        format_func=lambda i: f'{frames[i]["label"]} · ngày {frames[i]["day"]}')
    frame = frames[selected]
    st.caption(f"Cửa sổ {run.price_path.start_date} · seed {run.result.seed} · {run.source_label}")
    if replay.mismatches:
        st.warning("Không khớp checkpoint: " + ", ".join(replay.mismatches))
    elif replay.checks:
        st.success(f"Khớp {len(replay.checks)} phép đối chiếu với checkpoint đã lưu.")
    else:
        st.info("Cửa sổ tùy chọn: không có benchmark riêng đã lưu để xác nhận tái lập.")
    price_rows = _price_event_rows(replay)
    events = [r for r in price_rows if r["events"]]
    price = alt.Chart(pd.DataFrame(price_rows)).mark_line().encode(
        x=alt.X("day:Q", title="Ngày từ lúc bắt đầu"), y=alt.Y("price:Q", title=f"{run.quote_asset}/ETH", scale=alt.Scale(zero=False)),
        tooltip=["day:Q", "date:N", "price:Q", "events:N"])
    rules = alt.Chart(pd.DataFrame(events)).mark_rule(strokeDash=[4, 4], color="#927343").encode(x="day:Q", tooltip=["day:Q", "date:N", "events:N"])
    cursor = alt.Chart(pd.DataFrame([frame])).mark_rule(color="#315b7c").encode(x="day:Q")
    st.altair_chart((price + rules + cursor).properties(height=240), width="stretch")
    st.caption("Giá đóng cửa, không phải giá khớp lệnh. Đường sự kiện cho biết lĩnh, đóng băng, bán ETH và quyết toán.")
    if frame["kind"] == "initial":
        st.info("Ban đầu: quỹ 0 USDC, lãi giữ lại 0 USDC, chưa góp hoặc lĩnh.")
    elif frame["kind"] == "freeze":
        st.info("Đây là sự kiện đóng băng; engine không lưu snapshot tiền/ETH tại mốc này. Không nội suy số dư sau bán từ kỳ trước.")
    else:
        trace = [dict(r, member=member_label(r["member_id"])) for r in trace_rows(run)
                 if r["day"] <= frame["day"]]
        if trace:
            data = pd.DataFrame(trace).melt(id_vars=["day", "member"],
                value_vars=["cumulative_contribution_usdc", "cumulative_payout_usdc"], var_name="flow", value_name="USDC")
            st.altair_chart(alt.Chart(data).mark_line(point=True).encode(
                x=alt.X("day:Q", title="Ngày có trace kỳ"), y=alt.Y("USDC:Q", scale=alt.Scale(zero=True)),
                color=alt.Color("member:N", title="Người chơi"), strokeDash=alt.StrokeDash("flow:N", title="Góp/lĩnh lũy kế"),
                tooltip=["member:N", "day:Q", "flow:N", "USDC:Q"]), width="stretch")
            pool = [dict(day=t.day, pool=t.pool_cash, interest=t.retained_interest)
                    for t in run.trace if t.day <= frame["day"]]
            pool = pd.DataFrame(pool).melt("day", var_name="fund", value_name="USDC")
            st.altair_chart(alt.Chart(pool).mark_line(point=True).encode(x="day:Q", y="USDC:Q", color="fund:N",
                tooltip=["day:Q", "fund:N", "USDC:Q"]), width="stretch")
            st.caption("Chỉ số tại các kỳ có trace, không phải số dư mỗi ngày. pool là tiền quỹ, interest là lãi đang giữ (USDC).")
    if frame["kind"] == "settlement":
        a, b = st.columns(2)
        a.metric("Lãi đã dùng bù gốc (USDC)", f"{run.result.interest_used:,.2f}")
        b.metric("Nghĩa vụ chưa thu (USDC)", f"{run.result.obligation_uncollected:,.2f}")
        members = [dict(asdict(a), member=member_label(a.member_id)) for a in run.result.agent_results]
        data = pd.DataFrame(members).melt(id_vars="member", value_vars=["principal_repaid", "principal_loss", "interest_received"],
                                          var_name="component", value_name="USDC")
        st.altair_chart(alt.Chart(data).mark_bar().encode(x=alt.X("member:N", title="Người chơi"), y="USDC:Q",
            color=alt.Color("component:N", title="Hoàn gốc / mất gốc / lãi nhận"), tooltip=["member:N", "component:N", "USDC:Q"]), width="stretch")
        st.caption("principal_claim chỉ là gốc cần hoàn cho người chưa lĩnh, không phải toàn bộ lãi/lỗ kinh tế khi giữ ETH. Lãi dùng bù gốc và nghĩa vụ chưa thu không cộng thêm vào tiền hoàn.")
        with st.expander("Bảng quyết toán từng người"):
            st.dataframe(pd.DataFrame(members), hide_index=True)


@st.cache_data(show_spinner=False, max_entries=4)
def _cached_study(directory: str, signature: tuple):
    study = load_study(Path(directory))
    if study.signature != signature:
        raise ValueError("source changed; reload study")
    return study


def _table_download(title, rows, provenance, key):
    st.caption(f'{len(rows):,} điểm/bản ghi · {provenance["window_count"]} cửa sổ · phạm vi {provenance["scope"]}')
    with st.expander(title):
        safe = [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (tuple, list, dict)) else v
                 for k, v in row.items()} for row in rows]
        st.dataframe(pd.DataFrame(safe), hide_index=True)
        st.download_button("Tải bảng CSV", csv_bytes(rows, provenance), f"{key}.csv", "text/csv", key=key)


def _reconcile(key, options, default=None):
    if st.session_state.get(key) not in options:
        st.session_state[key] = default if default in options else (options[0] if options else None)


def _multi(key, options):
    if key not in st.session_state:
        st.session_state[key] = list(options)
    else:
        st.session_state[key] = [x for x in st.session_state[key] if x in options]


def _group_label(group):
    return f'k={group[0]} · bùng: {", ".join(member_label(i) for i in group[1])}'


def _case_label(key):
    return f'{key[0]:.0%}/năm · ký quỹ {key[1]:.0%} · {_group_label((key[2], key[3]))}'


def render_phase_a() -> None:
    st.markdown('<style>[data-testid="stSliderThumbValue"] {width:max-content; white-space:nowrap;} '
                '[data-testid="stSliderThumbValue"] p {white-space:nowrap;}</style>', unsafe_allow_html=True)
    root = Path(__file__).resolve().parents[2]
    with st.sidebar:
        st.subheader("Nguồn nghiên cứu 2022")
        directory = st.text_input("Thư mục kết quả", value=str(root / "results/phase-a-2022-annual"), key="pa_results_dir")
        csv_path = st.text_input("CSV giá để xem diễn biến", value=str(root / "data/eth_usdt_binance_2022.csv"), key="pa_prices_csv")
        if st.button("Tải lại dữ liệu", key="pa_reload"):
            _cached_study.clear()
            st.session_state.pop("pa_replay_result", None)
            st.session_state.pop("pa_replay_signature", None)
    st.header("Kết quả nghiên cứu ETH 2022")
    st.caption("Không mất gốc trong bộ điều kiện đã thử không có nghĩa là an toàn tuyệt đối. Các cửa sổ chồng lấn không phải các mẫu độc lập.")
    loading = st.empty()
    loading.markdown('<div style="height:48px;background:#ededed;border-radius:8px" aria-label="Đang đọc checkpoint"></div>', unsafe_allow_html=True)
    try:
        signature = study_signature(Path(directory))
        study = _cached_study(directory, signature)
        # Cache hits skip the decorated body: verify stability outside the cache too.
        if study_signature(Path(directory)) != signature:
            raise ValueError("source changed; reload study")
    except (ValueError, OSError) as error:
        loading.empty()
        st.error(f"Không thể đọc nghiên cứu: {error}")
        return
    loading.empty()
    manifest = study.manifest
    identity = manifest["identity"]
    provenance = dict(identity["provenance"], fingerprint=manifest["fingerprint"],
                      window_count=manifest["windows"], scope="toàn nghiên cứu", bid_rate_basis=identity["bid_rate_basis"])
    st.caption(f'{study.directory} · fingerprint {manifest["fingerprint"][:12]}')
    with st.expander("Nguồn và giả định nghiên cứu"):
        st.json(identity)
        st.write("6 người, 100 USDC mỗi 30 ngày. Giá đóng cửa 2022, trượt giá 0; đủ ETH để lĩnh và người tuân thủ trả đủ USDC ngày 7. ETH giữ đến quyết toán, lãi chung có thể bù gốc. 1 USDT ≈ 1 USDC.")
        st.write("annual_simple_act365: lãi trên nghĩa vụ ban đầu theo thời gian còn lại, không phải dư nợ giảm dần; chưa xác nhận tuân thủ pháp luật.")
    a, b, c = st.columns(3)
    a.metric("Jobs hợp lệ", f"{study.completed_jobs}/{study.expected_jobs}")
    b.metric("Lượt mô phỏng hoàn tất", f"{study.completed_runs:,}")
    b.caption(f"Trên {study.expected_runs:,} lượt dự kiến")
    global_row = study.thresholds[-1]
    status = {"incomplete": "Chưa đủ dữ liệu", "not_found": "Chưa tìm thấy trong lưới"}
    c.metric("Ngưỡng chung toàn nghiên cứu", f'{global_row["candidate_ratio"]:.0%}' if global_row["candidate_ratio"] is not None else status[global_row["status"]])
    st.subheader("Ngưỡng ký quỹ theo lãi năm")
    st.altair_chart(threshold_chart(study.thresholds), width="stretch")
    st.caption("Giao các tập PASS trên mọi nhóm, cửa sổ và tỷ lệ đã lên kế hoạch. Bộ lọc bên dưới không đổi ngưỡng này.")
    _table_download("Bảng ngưỡng toàn nghiên cứu", tuple(r for r in study.thresholds if r["scope"] == "rate"), provenance, "pa_threshold_csv")
    st.subheader("Khám phá rủi ro")
    rates = st.multiselect("Lãi chào (%/năm)", list(ANNUAL_RATES), default=list(ANNUAL_RATES), format_func=lambda r: f"{r:.0%}/năm", key="pa_rates")
    ratios = sorted(manifest["planned_ratios"])
    previous = st.session_state.get("pa_ratio_range", (ratios[0], ratios[-1]))
    if not isinstance(previous, (tuple, list)) or any(v not in ratios for v in previous):
        st.session_state.pa_ratio_range = (ratios[0], ratios[-1])
    ratio_range = st.select_slider("Khoảng ký quỹ / nghĩa vụ", options=ratios,
        value=(ratios[0], ratios[-1]), key="pa_ratio_range", format_func=lambda r: f"{r:.0%}")
    paid = st.multiselect("Số người đã lĩnh khi bùng (k)", list(range(1, 6)), default=list(range(1, 6)), key="pa_paid_counts")
    all_groups = sorted({(c.paid_count, c.default_ids) for c in phase_a_cases() if c.paid_count in paid})
    group_map = {_group_label(g): g for g in all_groups}
    _multi("pa_groups", list(group_map))
    with st.expander(f"Lọc nhóm bùng ({len(st.session_state.pa_groups)} nhóm đang chọn)"):
        groups = st.multiselect("Nhóm bùng trong số người đã lĩnh", list(group_map), key="pa_groups")
    filters = StudyFilters(tuple(rates), *ratio_range, tuple(paid), tuple(group_map[g] for g in groups))
    filtered = filter_summaries(study, filters)
    risks = risk_rows(study, filters)
    if not risks:
        st.info("Bộ lọc đang rỗng. Chọn ít nhất một mức lãi, số người đã lĩnh và nhóm bùng để xem kết quả.")
        st.button("Xem diễn biến", disabled=True, key="pa_replay")
        return
    metric = st.radio("Chỉ số rủi ro", ("max_individual_loss", "loss_count"), key="pa_metric",
        format_func=lambda m: "Mất gốc cá nhân lớn nhất (USDC)" if m == "max_individual_loss" else "Số tình huống mất gốc")
    st.altair_chart(risk_chart(risks, metric), width="stretch")
    st.caption(ZOOM_NOTE)
    st.caption(f'{len(filters.groups)} nhóm · {manifest["windows"]} cửa sổ · {sum(r["completed_runs"] for r in risks):,}/{sum(r["expected_runs"] for r in risks):,} runs trong bộ lọc. Số tình huống không phải xác suất, số ngày hay số người.')
    if any(not r["coverage_complete"] for r in risks):
        st.warning("Có điểm thiếu coverage: số mất gốc chỉ là lớn nhất quan sát được trên phần đã có, chưa phải bộ đầy đủ.")
    filtered_provenance = dict(provenance, scope="bộ lọc", filters=asdict(filters))
    _table_download("Bảng rủi ro đang hiển thị", risks, filtered_provenance, "pa_risk_csv")
    _reconcile("pa_heat_rate", sorted(rates), .2)
    heat_rate = st.selectbox("Lãi năm cho bản đồ nhiệt", sorted(rates), key="pa_heat_rate", format_func=lambda r: f"{r:.0%}/năm")
    heat = heatmap_rows(study, filters, heat_rate)
    st.altair_chart(heatmap_chart(heat), width="stretch")
    st.caption("Mỗi ô là mất gốc cá nhân lớn nhất (USDC). Ô xám là thiếu dữ liệu, không phải mất gốc 0. k là số người đã lĩnh, không phải số người bùng.")
    st.caption("Lưới nhiều tỷ lệ ẩn chữ trong ô để tránh chồng lấn; xem giá trị chính xác qua tooltip hoặc bảng bên dưới.")
    _table_download("Bảng bản đồ nhiệt", heat, dict(filtered_provenance, heat_rate=heat_rate), "pa_heat_csv")
    st.subheader("Chạy lại một tình huống")
    choices = {_case_label(case_key(r)): case_key(r) for r in sorted(filtered, key=case_key)}
    if not choices:
        st.info("Không có job hợp lệ cho bộ lọc này; chưa thể chạy lại.")
        return
    if st.button("Mở trường hợp tệ nhất", key="pa_worst"):
        st.session_state.pa_case = _case_label(select_worst(filtered))
    _reconcile("pa_case", list(choices))
    label = st.selectbox("Tình huống", list(choices), key="pa_case")
    key = choices[label]
    summary = next(r for r in filtered if case_key(r) == key)
    kind = st.radio("Cửa sổ chạy lại", ("worst_individual", "worst_total", "custom"), key="pa_window_kind",
        format_func=lambda k: {"worst_individual": "Mất gốc cá nhân tệ nhất", "worst_total": "Mất gốc toàn dây tệ nhất", "custom": "Chọn ngày khác"}[k])
    if kind == "custom":
        _reconcile("pa_window_start", identity["window_starts"])
        start = st.selectbox("Ngày bắt đầu cửa sổ", identity["window_starts"], key="pa_window_start")
    else:
        start = summary[f"{kind}_start"]
        st.caption(f"Ngày bắt đầu: {start}")
    price_path = Path(csv_path).expanduser().resolve()
    try:
        stat = price_path.stat()
        price_signature = (str(price_path), stat.st_size, stat.st_mtime_ns)
    except OSError:
        price_signature = (str(price_path), None, None)
    replay_signature = (study.signature, key, start, price_signature)
    if st.button("Xem diễn biến", key="pa_replay"):
        try:
            replay = replay_case(study, key, start, price_path)
            st.session_state.pa_replay_result = replay
            st.session_state.pa_replay_signature = replay_signature
            st.session_state.pa_frame = 0
        except (OSError, ValueError) as error:
            st.session_state.pop("pa_replay_result", None)
            st.error(f"Không thể chạy lại: {error}")
    replay = st.session_state.get("pa_replay_result")
    if replay is not None:
        if st.session_state.get("pa_replay_signature") != replay_signature:
            st.info("Chưa chạy lại theo lựa chọn mới. Kết quả cũ đã được ẩn.")
        else:
            render_replay(replay)
            replay_meta = dict(provenance, scope="replay", case_key=key, window_start=start, seed=42,
                               checks=replay.checks, mismatches=replay.mismatches)
            _table_download("Bảng giá ETH theo ngày và sự kiện", _price_event_rows(replay),
                            replay_meta, "pa_price_events_csv")
            _table_download("Bảng kết quả chạy lại", (asdict(replay.run.result),), replay_meta, "pa_replay_csv")
            _table_download("Bảng trace kỳ chạy lại", trace_rows(replay.run), replay_meta, "pa_trace_csv")
