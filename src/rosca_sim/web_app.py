"""Local Streamlit research dashboard for auction ROSCA simulations."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date, timedelta
from decimal import Decimal
import csv
from io import StringIO
import json
from pathlib import Path
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st

from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionEvent
from rosca_sim.prices import load_price_csv, valid_historical_starts
from rosca_sim.web_analysis import ratio_grid, run_named_cases, run_sweep, sample_common_starts
from rosca_sim.web_cases import dump_cases_json, example_case, load_cases_json
from rosca_sim.web_reporting import (
    candidate_ratio, comparison_rows, frontier_rows, member_loss_rows, sweep_run_rows,
    trace_rows, tradeoff_rows,
)


st.set_page_config(page_title="Phòng thí nghiệm hụi đấu giá", layout="wide")
st.markdown("""<style>
html, body, [class*="css"] {font-family: Manrope, sans-serif;}
h1, h2, h3 {text-wrap: balance;}
p {text-wrap: pretty;}
</style>""", unsafe_allow_html=True)
st.title("Phòng thí nghiệm hụi đấu giá")
st.caption("So sánh tổn thất và ETH phải khóa trên giá lịch sử. Đây là mô phỏng nghiên cứu, không phải cam kết bảo vệ vốn.")

if "cases" not in st.session_state:
    st.session_state.cases = (example_case(),)
if "manual_runs" not in st.session_state:
    st.session_state.manual_runs = ()
if "run_signature" not in st.session_state:
    st.session_state.run_signature = None
if "sweep_runs" in st.session_state and "sweep_cases_snapshot" not in st.session_state:
    st.session_state.sweep_runs = ()
if "selected_case_next" in st.session_state:
    st.session_state.selected_case = st.session_state.pop("selected_case_next")


def _signature():
    path = Path(st.session_state.get("csv_path", "")).expanduser()
    mtime = path.stat().st_mtime_ns if path.is_file() else None
    return (dump_cases_json(st.session_state.cases), str(path.resolve()), mtime,
            st.session_state.get("source_label", ""), st.session_state.get("quote_asset", "USD"))


@st.cache_data(show_spinner=False)
def _read_points(path: str, mtime_ns: int):
    return load_price_csv(Path(path), date.min, date.max)


def _points():
    path = Path(st.session_state.csv_path).expanduser()
    if not path.is_file():
        raise ValueError("Không tìm thấy tệp CSV giá ETH. Hãy nhập đường dẫn tệp date,close có thật.")
    return _read_points(str(path.resolve()), path.stat().st_mtime_ns)


def _csv_bytes(rows):
    if not rows:
        return b""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


view = st.radio("Chế độ nghiên cứu", ("So sánh kịch bản", "Quét tự động và tìm ngưỡng", "Kết quả nghiên cứu 2022"),
                horizontal=True, key="view")
if view == "Kết quả nghiên cứu 2022":
    from rosca_sim.web_phase_a import render_phase_a
    render_phase_a()
    st.stop()

with st.sidebar:
    st.subheader("Nguồn giá ETH")
    st.text_input("Đường dẫn CSV giá ETH", key="csv_path", placeholder="C:/data/eth_daily.csv")
    st.text_input("Tên nguồn giá", key="source_label", value="ETH daily close")
    st.selectbox("Đơn vị giá ETH", ("USD", "USDT"), key="quote_asset")
    st.caption("CSV có hai cột date,close theo ngày. Giả định quy đổi: 1 USD hoặc 1 USDT ≈ 1 USDC. Giá đóng cửa không bảo đảm bán ETH được ở mức đó.")

if view == "Quét tự động và tìm ngưỡng":
    st.subheader("Quét ký quỹ trên cùng cửa sổ ETH")
    st.caption("Mỗi tỷ lệ trong một dây dùng cùng ngày bắt đầu, cùng chào lãi và cùng giả định bùng. Dây dài hoặc ân hạn khác nhau có ngày kết thúc khác nhau.")
    selected_ids = st.multiselect("Các dây cần quét", [case.case_id for case in st.session_state.cases],
                                  default=[case.case_id for case in st.session_state.cases], key="sweep_cases")
    selected_cases = tuple(case for case in st.session_state.cases if case.case_id in selected_ids)
    a, b, c = st.columns(3)
    ratio_min = a.number_input("Tỷ lệ ký quỹ thấp nhất", min_value=0.0, max_value=10000.0,
                               value=0.5, step=0.1, key="ratio_min")
    ratio_max = b.number_input("Tỷ lệ ký quỹ cao nhất", min_value=0.0, max_value=10000.0,
                               value=2.0, step=0.1, key="ratio_max")
    ratio_step = c.number_input("Bước tỷ lệ ký quỹ", min_value=0.001, max_value=10000.0,
                                value=0.5, step=0.1, key="ratio_step")
    d, e = st.columns(2)
    window_count = d.number_input("Số cửa sổ giá lịch sử", min_value=1, max_value=10000,
                                  value=1, key="window_count")
    seed = e.number_input("Seed lấy mẫu", value=42, step=1, key="sweep_seed")
    sweep_signature = (_signature(), tuple(selected_ids), ratio_min, ratio_max,
                       ratio_step, window_count, seed)
    if ratio_max >= ratio_min:
        estimated = len(selected_cases) * (int((Decimal(str(ratio_max)) - Decimal(str(ratio_min)))
                                          // Decimal(str(ratio_step))) + 1) * int(window_count)
        st.caption(f"Dự kiến {estimated:,} lượt chạy engine; giới hạn 10.000 lượt.")
    else:
        estimated = 0
        st.error("Tỷ lệ cao nhất phải không nhỏ hơn tỷ lệ thấp nhất.")
    if st.button("Quét tỷ lệ", key="run_sweep"):
        try:
            if estimated > 10_000:
                raise ValueError("Vượt giới hạn 10.000 lượt chạy; hãy giảm số tỷ lệ hoặc cửa sổ.")
            if not selected_cases or ratio_max < ratio_min:
                raise ValueError("Chọn ít nhất một dây và dải tỷ lệ hợp lệ.")
            if not st.session_state.source_label.strip():
                raise ValueError("Cần ghi tên nguồn giá ETH")
            with st.spinner("Đang quét các cửa sổ giá lịch sử..."):
                points = _points()
                ratios = ratio_grid(Decimal(str(ratio_min)), Decimal(str(ratio_max)),
                                    Decimal(str(ratio_step)))
                starts = sample_common_starts(selected_cases, points, int(window_count), int(seed))
                st.session_state.sweep_runs = run_sweep(
                    selected_cases, points, ratios, starts, int(seed),
                    st.session_state.source_label, st.session_state.quote_asset)
                st.session_state.frontier = frontier_rows(st.session_state.sweep_runs)
                st.session_state.sweep_cases_snapshot = selected_cases
                st.session_state.sweep_signature = sweep_signature
        except (ValueError, OSError) as error:
            st.error(f"Không thể quét tỷ lệ: {error}")
    sweep_runs = st.session_state.get("sweep_runs", ())
    if sweep_runs:
        sweep_stale = st.session_state.sweep_signature != sweep_signature
        if sweep_stale:
            st.warning("Kết quả quét cũ: đầu vào đã đổi. Hãy bấm Quét tỷ lệ để cập nhật.")
        rows = st.session_state.frontier
        st.caption(f"{len(sweep_runs)} lượt · {len(set(run.start for run in sweep_runs))} cửa sổ · seed {sweep_runs[0].result.seed} · "
                   f"{sweep_runs[0].source_label} ({sweep_runs[0].quote_asset}/ETH). "
                   "Bùng và chào lãi là giả định; giá đóng cửa không bảo đảm giá khớp lệnh.")
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).transform_fold(
            ["worst_member_loss_usdc", "mean_loss_usdc"], as_=["Chỉ tiêu", "USDC"]
        ).mark_line(point=True).encode(
            x=alt.X("ratio:Q", title="Tỷ lệ ký quỹ / nghĩa vụ còn lại"),
            y=alt.Y("USDC:Q", title="Lỗ gốc (USDC)"),
            color="case_id:N", strokeDash="Chỉ tiêu:N",
            tooltip=["case_id", "ratio", "Chỉ tiêu:N", "USDC:Q", "runs", "start_date", "end_date"]), width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).mark_line(point=True).encode(
            x=alt.X("ratio:Q", title="Tỷ lệ ký quỹ / nghĩa vụ còn lại"),
            y=alt.Y("loss_run_share:Q", axis=alt.Axis(format="%"), title="Tỷ lệ lượt bị lỗ gốc"),
            color="case_id:N", tooltip=["case_id", "ratio", "loss_run_count", "runs", "loss_run_share"]),
            width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).mark_line(point=True).encode(
            x=alt.X("ratio:Q", title="Tỷ lệ ký quỹ / nghĩa vụ còn lại"),
            y=alt.Y("completion_share:Q", axis=alt.Axis(format="%"), title="Tỷ lệ dây hoàn thành"),
            color="case_id:N", tooltip=["case_id", "ratio", "completed_run_count", "runs",
                                        "completion_share", "mean_payout_count", "no_eligible_bid_count"]),
            width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).mark_circle(size=120).encode(
            x=alt.X("median_max_member_lock_usdc_proxy:Q", title="ETH khóa lớn nhất, trung vị (USDC giả định)"),
            y=alt.Y("worst_member_loss_usdc:Q", title="Lỗ gốc lớn nhất một người (USDC)"),
            color="case_id:N", tooltip=["case_id", "ratio", "median_max_member_lock_usdc_proxy",
                                        "worst_member_loss_usdc", "runs"]), width="stretch")
        raw = sweep_run_rows(sweep_runs, st.session_state.sweep_cases_snapshot)
        st.altair_chart(alt.Chart(pd.DataFrame(raw)).mark_bar().encode(
            x=alt.X("worst_member_loss_usdc:Q", bin=True, title="Lỗ gốc lớn nhất (USDC)"),
            y=alt.Y("count():Q", title="Số lượt"), color="case_id:N"), width="stretch")
        st.dataframe(list(rows), hide_index=True, width="stretch")
        st.download_button("Tải đường biên CSV", _csv_bytes(rows), "duong_bien.csv", "text/csv")
        st.download_button("Tải từng lượt CSV", _csv_bytes(raw), "tung_luot.csv", "text/csv")
        if sweep_stale:
            st.info("Ngưỡng ứng viên đang ẩn vì đầu vào đã đổi. Hãy quét lại để xem ngưỡng mới.")
        else:
            for case in st.session_state.sweep_cases_snapshot:
                candidate = candidate_ratio(rows, case.case_id)
                if candidate is None:
                    st.markdown(f"**{case.name} ({case.case_id}):** Không có ngưỡng thử nào vừa không lỗ gốc "
                                "vừa không dừng vì thiếu người đủ điều kiện lĩnh trong mẫu này.")
                else:
                    st.markdown(f"**{case.name} ({case.case_id}):** Ngưỡng ứng viên thấp nhất đã thử: {candidate:.2f} "
                                "(không lỗ gốc và không dừng vì thiếu người đủ điều kiện lĩnh trong mẫu, không bảo đảm tương lai).")
        if any(row["changed_order_count"] for row in rows):
            st.markdown("**Thứ tự lĩnh thay đổi:** người chào lãi cao có thể thiếu ETH ở tỷ lệ cao hơn; "
                        "so sánh lỗ không đồng nghĩa chỉ đổi mức bảo vệ.")
        if any(row["no_eligible_bid_count"] for row in rows):
            st.warning("Có lượt không có người chào lãi đủ điều kiện lĩnh: thiếu ETH hoặc không có bid hợp lệ. "
                       "Những lượt đó không được tính là ngưỡng ứng viên, dù lỗ gốc bằng 0.")
        if any(row["nonmonotonic"] for row in rows):
            st.warning("Có chỉ tiêu rủi ro tăng ở tỷ lệ ký quỹ cao hơn: " + ", ".join(sorted({
                metric for row in rows for metric in row["nonmonotonic_metrics"].split(", ") if metric
            })) + ". Không thể kết luận cứ tăng ký quỹ sẽ an toàn hơn.")
        st.caption("Ngưỡng chỉ là kết quả trong mẫu. Tần suất lỗ không phải xác suất mất tiền thực tế. "
                   "Trượt giá chỉ theo tham số giả định; chưa mô phỏng râu nến, thất bại thanh lý hay thông đồng. "
                   "Tỷ lệ hoàn thành và số lượt lĩnh là chỉ báo hoạt động, không phải điều kiện bắt buộc của kịch bản cố ý cho bùng.")
    else:
        st.info("Chọn dây, lưới ký quỹ và số cửa sổ, rồi bấm Quét tỷ lệ để xem phân bố lỗ và lượng ETH khóa lúc lĩnh.")
    st.stop()

st.subheader("So sánh kịch bản")
st.caption("Một người chỉ ký quỹ khi lĩnh hụi. Lãi chào thắng bị khấu trừ ngay, giữ trong quỹ; các kỳ sau người đó vẫn chỉ góp đúng khoản cố định.")
st.caption("Chào lãi tối đa 20%/năm: annual_rate=0.20 nghĩa là 20%/năm, không phải 20% quỹ lĩnh. "
           "Lãi đơn = nghĩa vụ góp còn lại × lãi suất năm × ngày còn lại / 365. "
           "Đây là quy ước nghiên cứu, chưa phải xác nhận tuân thủ pháp luật; JSON cũ schema 1 không được nhập lại như schema 2.")
st.caption("ETH giữ nguyên lượng đến khi hoàn thành hoặc quyết toán, không trả dần mỗi kỳ. "
           "Giả định góp đủ trừ sự kiện đặt trước; khả năng nộp USDC chỉ dùng lúc quyết toán. "
           "Web lịch sử không nhận stress_drop hay giá bán ghi đè qua JSON.")

cases = st.session_state.cases
if cases:
    ids = [case.case_id for case in cases]
    selected_id = st.session_state.get("selected_case")
    if selected_id not in ids:
        st.session_state.selected_case = ids[0]
    st.selectbox("Mã dây đang chỉnh", ids, key="selected_case")
    case = next(case for case in cases if case.case_id == st.session_state.selected_case)
    st.markdown(f"**Dây {case.scenario.rosca.members} người**, {case.scenario.rosca.contribution:,.0f} USDC mỗi kỳ")
    left, middle, right = st.columns(3)
    if left.button("Nhân bản dây", key="clone_case"):
        clone = replace(case, case_id=uuid4().hex, name=f"{case.name} (bản sao)")
        st.session_state.cases = (*cases, clone)
        st.session_state.selected_case_next = clone.case_id
        st.rerun()
    if middle.button("Xóa dây", key="remove_case"):
        st.session_state.cases = tuple(item for item in cases if item.case_id != case.case_id)
        st.session_state.selected_case_next = st.session_state.cases[0].case_id if st.session_state.cases else None
        st.rerun()
else:
    st.info("Chưa có dây hụi. Thêm dây mẫu hoặc nhập bộ kịch bản JSON để bắt đầu.")
    if st.button("Thêm dây mẫu", key="add_example"):
        st.session_state.cases = (replace(example_case(), case_id=uuid4().hex),)
        st.rerun()

with st.expander("Nhập hoặc xuất bộ kịch bản JSON"):
    st.text_area("Dán JSON kịch bản", key="import_json", height=100)
    if st.button("Nhập kịch bản", key="import_cases"):
        try:
            incoming = load_cases_json(st.session_state.import_json)
            st.session_state.cases = incoming
            st.session_state.selected_case_next = incoming[0].case_id if incoming else None
            st.success(f"Đã nhập {len(incoming)} kịch bản.")
            st.rerun()
        except (ValueError, TypeError) as error:
            st.error(f"JSON không hợp lệ: {error}")
    st.download_button("Tải bộ kịch bản JSON", dump_cases_json(st.session_state.cases),
                       file_name="rosca_cases.json", mime="application/json")

if cases:
    points = None
    if st.session_state.get("csv_path"):
        try:
            points = _points()
            st.caption(f"Nguồn: {st.session_state.source_label} · {points[0].day} đến {points[-1].day} · {len(points)} giá đóng cửa ngày")
        except (ValueError, OSError, IndexError) as error:
            st.error(f"Dữ liệu giá: {error}")
    with st.expander("Chỉnh điều kiện dây hụi", expanded=True):
        with st.form("case_editor"):
            name = st.text_input("Tên kịch bản", value=case.name)
            a, b, c = st.columns(3)
            members = a.number_input("Số người và số kỳ", 6, 100, case.scenario.rosca.members)
            contribution = b.number_input("Đóng mỗi kỳ (USDC)", min_value=0.01,
                                           value=float(case.scenario.rosca.contribution))
            period_days = c.number_input("Số ngày mỗi kỳ", 1, 365, case.scenario.rosca.period_days)
            d, e = st.columns(2)
            ratio = d.number_input("Tỷ lệ ký quỹ / nghĩa vụ còn lại", min_value=0.0,
                                   value=float(case.scenario.collateral.fixed_ratio), step=0.1)
            grace = e.number_input("Ân hạn quyết toán (ngày)", 0, 365, case.scenario.grace_days)
            slippage_percent = st.number_input("Trượt giá khi bán ETH (%)", min_value=0.0,
                value=100 * float(case.scenario.collateral.liquidation_slippage), step=1.0,
                format="%.5f")
            st.caption("Giá bán mô phỏng = giá đóng cửa ngày bán × (1 − trượt giá). "
                       "Mặc định 0%; thử 5% hoặc 10% là phân tích độ nhạy, không phải giá khớp lệnh đo được.")
            st.caption("Tỷ lệ 1,5 nghĩa là khóa ETH trị giá 150% phần góp cố định còn lại; không phải 150% khoản lĩnh ròng.")
            agent_rows = st.data_editor([asdict(agent) for agent in case.scenario.agents],
                                        key="agent_editor", num_rows="dynamic", hide_index=True)
            st.caption("Mỗi hàng người chơi: ETH sẵn có, khả năng nộp USDC, cách quyết toán và ngày thanh toán.")
            bid_rows = st.data_editor([asdict(bid) for bid in case.scenario.bids],
                                      key="bid_editor", num_rows="dynamic", hide_index=True,
                                      column_config={"annual_rate": st.column_config.NumberColumn(
                                          "Lãi suất năm (tỷ lệ)", min_value=0.0, max_value=0.20, step=0.01)})
            st.caption("Mỗi hàng chào lãi: kỳ, ID người chơi, annual_rate từ 0 đến 0.20. Người đã lĩnh không chào tiếp.")
            defaults = st.text_area("Người đã lĩnh bùng: JSON sự kiện", value=json.dumps(
                [asdict(item) for item in case.scenario.forced_defaults], ensure_ascii=False))
            missed = st.text_area("Người chưa lĩnh bỏ góp: JSON sự kiện", value=json.dumps(
                [asdict(item) for item in case.scenario.missed_contributions], ensure_ascii=False))
            st.caption("Sự kiện cùng ngày được xử lý trong một đợt. Dây dừng ở ngày bùng đầu tiên; sự kiện sau đó không chạy.")
            starts = valid_historical_starts(points, int(members), int(period_days), int(grace)) if points else ()
            options = (None, *starts)
            chosen_start = st.selectbox("Ngày bắt đầu cửa sổ ETH", options,
                index=options.index(case.window_start) if case.window_start in options else 0)
            st.caption(f"{len(starts)} cửa sổ lịch sử đầy đủ cho dây này, gồm cả phần đuôi ân hạn.")
            save = st.form_submit_button("Lưu điều kiện dây")
        if save:
            try:
                agents = tuple(AuctionAgentSeed(**row) for row in agent_rows)
                bids = tuple(AuctionBid(**row) for row in bid_rows)
                scenario = replace(case.scenario,
                    rosca=replace(case.scenario.rosca, members=int(members), periods=int(members),
                                  contribution=float(contribution), period_days=int(period_days)),
                    collateral=replace(case.scenario.collateral, fixed_ratio=float(ratio),
                                       liquidation_slippage=float(slippage_percent) / 100),
                    agents=agents, bids=bids,
                    forced_defaults=tuple(AuctionEvent(**item) for item in json.loads(defaults)),
                    missed_contributions=tuple(AuctionEvent(**item) for item in json.loads(missed)),
                    grace_days=int(grace))
                changed = replace(case, name=name, scenario=scenario, window_start=chosen_start)
                changed, = load_cases_json(dump_cases_json((changed,)))
                st.session_state.cases = tuple(changed if item.case_id == case.case_id else item for item in cases)
                st.success("Đã lưu. Hãy chạy lại để cập nhật kết quả.")
                st.rerun()
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
                st.error(f"Điều kiện dây chưa hợp lệ: {error}")

if st.button("Chạy các kịch bản", key="run_cases", disabled=not st.session_state.cases):
    try:
        if len(st.session_state.cases) > 10_000:
            raise ValueError("Vượt giới hạn 10.000 lượt chạy")
        if not st.session_state.source_label.strip():
            raise ValueError("Cần ghi tên nguồn giá ETH")
        with st.spinner("Đang chạy từng dây hụi..."):
            st.session_state.manual_runs = run_named_cases(
                st.session_state.cases, _points(), 42,
                st.session_state.source_label, st.session_state.quote_asset)
            st.session_state.run_signature = _signature()
    except (ValueError, OSError) as error:
        st.error(f"Không thể chạy kịch bản: {error}")

runs = st.session_state.manual_runs
if runs:
    if st.session_state.run_signature != _signature():
        st.warning("Kết quả cũ: điều kiện dây, dữ liệu CSV hoặc nhãn nguồn đã thay đổi. Hãy chạy lại.")
    st.subheader("Tổn thất giữa các kịch bản")
    comparison = comparison_rows(runs)
    losses = member_loss_rows(runs)
    tradeoffs = tradeoff_rows(runs)
    if len(runs) > 20:
        display_ids = st.multiselect("Lọc kịch bản trên biểu đồ", [run.case.case_id for run in runs],
            default=[run.case.case_id for run in sorted(runs,
                key=lambda item: item.result.worst_member_loss, reverse=True)[:20]],
            key="chart_cases")
    else:
        display_ids = [run.case.case_id for run in runs]
    shown_comparison = [row for row in comparison if row["case_id"] in display_ids]
    shown_losses = [row for row in losses if row["case_id"] in display_ids]
    shown_tradeoffs = [row for row in tradeoffs if row["case_id"] in display_ids]
    st.caption(f"{len(runs)} dây · {runs[0].source_label} · giá ETH bằng {runs[0].quote_asset}; bùng và chào lãi là giả định do người nghiên cứu đặt.")
    if all(row["principal_loss_usdc"] == 0 for row in comparison):
        st.success("Không có lỗ gốc trong các lượt lịch sử vừa thử; đây không phải bảo đảm an toàn tương lai.")
    bars = [{"case_id": row["case_id"], "case_name": row["case_name"], "Chỉ tiêu": kind, "USDC": row[key]}
            for row in shown_comparison for kind, key in (("Tổng lỗ gốc", "principal_loss_usdc"),
                                                     ("Lỗ lớn nhất một người", "worst_member_loss_usdc"))]
    if bars:
        st.altair_chart(alt.Chart(pd.DataFrame(bars)).mark_bar().encode(
            x=alt.X("case_id:N", title="Mã kịch bản"), y=alt.Y("USDC:Q", title="Lỗ gốc (USDC)"),
            color="Chỉ tiêu:N", xOffset="Chỉ tiêu:N", tooltip=list(bars[0])), width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(shown_losses)).mark_rect().encode(
            x=alt.X("member_id:O", title="Người chơi"), y=alt.Y("case_id:N", title="Mã kịch bản"),
            color=alt.Color("principal_loss_usdc:Q", title="Lỗ gốc (USDC)"),
            tooltip=["case_name", "member_id", "principal_loss_usdc", "contributed_usdc",
                     "net_payout_usdc", "interest_received_usdc", "eth_sold", "eth_returned"]), width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(shown_tradeoffs)).mark_circle(size=120).encode(
            x=alt.X("max_member_initial_lock_usdc_proxy:Q", title="ETH khóa lúc lĩnh, quy đổi USDC giả định"),
            y=alt.Y("worst_member_loss_usdc:Q", title="Lỗ gốc lớn nhất một người (USDC)"),
            color="case_id:N", tooltip=["case_id", "case_name", "ratio", "max_member_initial_lock_usdc_proxy",
                                          "worst_member_loss_usdc"]), width="stretch")
    else:
        st.info("Chọn ít nhất một kịch bản trong bộ lọc để xem biểu đồ.")
    st.caption("ETH khóa vẫn thuộc người lĩnh, không phải phí. Giá trị quy đổi dùng giá đóng cửa; 1 USD hoặc USDT ≈ 1 USDC chỉ là giả định.")
    st.dataframe(list(comparison), hide_index=True, width="stretch")
    st.download_button("Tải bảng so sánh CSV", _csv_bytes(comparison), "so_sanh.csv", "text/csv")
    run_labels = [f"{run.case.name} · {run.price_path.start_date} · {run.case.case_id}" for run in runs]
    selected = st.selectbox("Mở chi tiết dây", run_labels)
    run = runs[run_labels.index(selected)]
    result = run.result
    stop_label = {"completed": "Hoàn thành", "default": "Dừng do bùng hoặc bỏ góp",
                  "no_eligible_bid": "Không có người chào lãi đủ điều kiện lĩnh"}.get(
                      result.stop_reason, result.stop_reason)
    st.subheader(f"Diễn biến: {run.case.name}")
    if run.trace:
        st.markdown(f"Lĩnh kỳ đầu **{run.trace[0].net_payout:,.0f} USDC**, lãi giữ quỹ **{run.trace[0].bid_interest:,.0f} USDC**. "
                    f"Thứ tự lĩnh: {result.payout_order}. {stop_label} ({result.stop_reason}), ngày {result.freeze_day}; "
                    f"quyết toán ngày {result.settlement_day}.")
    else:
        st.markdown(f"**Chưa có kỳ góp hoặc lĩnh nào.** Dây dừng ngày {result.freeze_day} "
                    f"({stop_label}; {result.stop_reason}); quyết toán ngày {result.settlement_day}.")
    st.caption(f"Lãi đã giữ từ lúc lĩnh {result.interest_retained:,.2f} USDC · "
               f"trong đó dùng bù gốc {result.interest_used:,.2f} USDC · "
               f"tổng tiền chia lại {result.interest_distributed:,.2f} USDC · "
               f"tiền mặt còn trong quỹ sau quyết toán {result.ending_cash:,.2f} USDC")
    st.caption(f"Lãi nhóm gây dừng dùng bù gốc {result.interest_used_from_defaulting:,.2f} USDC · "
               f"lãi nhóm còn lại dùng bù {result.interest_used_from_other_members:,.2f} USDC · "
               f"nghĩa vụ chưa thu {result.obligation_uncollected:,.2f} USDC. Quỹ bù gốc không xóa nghĩa vụ này.")
    st.caption(f"{result.default_count} người gây đóng băng · {result.secondary_shortfall_count} người khác "
               "còn thiếu nghĩa vụ sau quyết toán. Hai nhóm không đồng nghĩa với nhau.")
    price_rows = [{"date": (run.case.window_start + timedelta(days=i)).isoformat(),
                   "close": price} for i, price in enumerate(run.price_path.daily_prices)]
    event_rows = [{"date": (run.case.window_start + timedelta(days=member.payout_day)).isoformat(),
                   "event": f"Lĩnh: người {member.member_id}"}
                  for member in result.agent_results if member.payout_day is not None]
    event_rows.extend((
        {"date": (run.case.window_start + timedelta(days=result.freeze_day)).isoformat(),
         "event": "Đóng băng"},
        {"date": (run.case.window_start + timedelta(days=result.settlement_day)).isoformat(),
         "event": "Hạn quyết toán"},
    ))
    event_rows.extend({"date": (run.case.window_start + timedelta(days=member.eth_sale_day)).isoformat(),
                       "event": f"Bán ETH: người {member.member_id}"}
                      for member in result.agent_results if member.eth_sale_day is not None)
    price_line = alt.Chart(pd.DataFrame(price_rows)).mark_line().encode(
        x=alt.X("date:T", title="Ngày lịch sử"),
        y=alt.Y("close:Q", title=f"Giá ETH ({run.quote_asset}/ETH)"),
        tooltip=["date", "close"])
    event_rules = alt.Chart(pd.DataFrame(event_rows)).mark_rule(opacity=0.45).encode(
        x="date:T", color=alt.Color("event:N", title="Sự kiện"), tooltip=["date", "event"])
    st.altair_chart(price_line + event_rules, width="stretch")
    st.caption("Giá đóng cửa quan sát được; điểm lĩnh, đóng băng và bán ETH không chứng minh lệnh bán khớp ở giá này.")
    trace = trace_rows(run)
    if trace:
        pool = [row for row in trace if row["member_id"] == 0]
        st.altair_chart(alt.Chart(pd.DataFrame(pool)).transform_fold(
            ["pool_cash_usdc", "retained_interest_usdc"], as_=["Chỉ tiêu", "USDC"]
        ).mark_line(point=True).encode(x=alt.X("day:Q", title="Ngày trong dây"),
                                       y=alt.Y("USDC:Q", title="Quỹ (USDC)"),
                                       color="Chỉ tiêu:N"), width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(trace)).transform_fold(
            ["cumulative_contribution_usdc", "cumulative_payout_usdc"],
            as_=["Chỉ tiêu", "USDC"]
        ).mark_line(point=True).encode(x=alt.X("day:Q", title="Ngày trong dây"),
                                       y=alt.Y("USDC:Q", title="Lũy kế (USDC)"),
                                       color=alt.Color("member_id:N", title="Người chơi"),
                                       strokeDash=alt.StrokeDash("Chỉ tiêu:N")), width="stretch")
        st.dataframe(list(trace), hide_index=True, width="stretch")
        st.altair_chart(alt.Chart(pd.DataFrame(trace)).mark_point().encode(
            x=alt.X("day:Q", title="Ngày trong dây"),
            y=alt.Y("coverage_ratio:Q", title="Giá trị ETH đang khóa / nghĩa vụ còn lại"),
            color=alt.Color("member_id:N", title="Người chơi"),
            tooltip=["member_id", "day", "retained_eth", "remaining_obligation_usdc",
                     "coverage_ratio", "collateral_shortfall_usdc", "skipped_for_insufficient_eth"]),
            width="stretch")
        st.caption("Chỉ báo ký quỹ tại các kỳ đã chạy, sau góp và lĩnh nhưng trước quyết toán; "
                   "không gọi nạp thêm hay tự thanh lý. Nghĩa vụ bằng 0 thì tỷ lệ không áp dụng. "
                   "ETH khóa mới mỗi kỳ khác với ETH còn giữ; không nội suy trạng thái giữa các kỳ.")
    else:
        st.info("Chưa có kỳ nào để vẽ dòng tiền trong dây.")
    member_rows = tuple(row for row in losses if row["case_id"] == run.case.case_id)
    st.dataframe(list(member_rows), hide_index=True, width="stretch")
    st.download_button("Tải quyết toán từng người CSV", _csv_bytes(member_rows),
                       "quyet_toan.csv", "text/csv")
else:
    st.info("Nhập CSV giá ETH, chọn ngày bắt đầu và chạy các kịch bản để xem biểu đồ kết quả.")
