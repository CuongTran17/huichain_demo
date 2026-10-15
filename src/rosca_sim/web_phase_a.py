"""Streamlit views for validated phase-A checkpoints; no research writes."""

import altair as alt
import pandas as pd

from rosca_sim.phase_a import ANNUAL_RATES

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
