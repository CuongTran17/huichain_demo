"""Streamlit views for validated phase-A checkpoints; no research writes."""

import altair as alt
import pandas as pd
import streamlit as st
from dataclasses import asdict

from rosca_sim.phase_a import ANNUAL_RATES
from rosca_sim.phase_a_results import member_label, replay_frames
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
    labels = base.mark_text(dy=-8).encode(y="candidate_ratio:Q", text="label:N")
    # Missing candidates have no bar; status remains visible above the baseline.
    missing = base.transform_filter("datum.candidate_ratio == null").mark_text(dy=-8).encode(y=alt.value(240), text="label:N")
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
        plotted.append({**row, "segment": f"{rate}:{segment}"})
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
    data = [dict(r, status="Đủ dữ liệu" if r["coverage_complete"] else "Thiếu dữ liệu") for r in rows]
    base = alt.Chart(pd.DataFrame(data)).encode(
        x=alt.X("ratio:O", title="Ký quỹ / nghĩa vụ", axis=alt.Axis(labelExpr="format(datum.value, '.0%')")),
        y=alt.Y("k:O", title="Số người đã lĩnh (k)"), tooltip=["annual_rate:Q", "ratio:Q", "k:O",
            alt.Tooltip("max_individual_loss:Q", title="Mất gốc cá nhân (USDC)"), "worst_key:N",
            "worst_start:N", "completed_runs:Q", "expected_runs:Q", "status:N"])
    tiles = base.mark_rect().encode(color=alt.condition("datum.max_individual_loss == null",
        alt.value("#cccccc"), alt.Color("max_individual_loss:Q", title="USDC", scale=alt.Scale(scheme="oranges", zero=True))))
    labels = base.mark_text(fontSize=12).encode(text=alt.Text("max_individual_loss:Q", format=".1f"))
    return (tiles + labels).properties(height=240)


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
    events = [dict(day=f["day"], event=f["label"]) for f in frames if f["kind"] != "initial"]
    events.extend(dict(day=a.eth_sale_day, event=f"Bán ETH {member_label(a.member_id)}")
                  for a in run.result.agent_results if a.eth_sale_day is not None)
    price = alt.Chart(pd.DataFrame(dict(day=i, price=p) for i, p in enumerate(run.price_path.daily_prices))).mark_line().encode(
        x=alt.X("day:Q", title="Ngày từ lúc bắt đầu"), y=alt.Y("price:Q", title=f"{run.quote_asset}/ETH", scale=alt.Scale(zero=False)),
        tooltip=["day:Q", "price:Q"])
    rules = alt.Chart(pd.DataFrame(events)).mark_rule(strokeDash=[4, 4], color="#927343").encode(x="day:Q", tooltip=["day:Q", "event:N"])
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
