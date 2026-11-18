"""Streamlit view for the experiment results cited in the BTL report."""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from rosca_sim.btl_results import CLOSE, FOCUS_DAY, LOW, load_report, replay_focus_case


def _date(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def _number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _render_replay(replays) -> None:
    labels = {CLOSE: "Giá đóng cửa", LOW: "Giá đáy"}
    cols = st.columns(2)
    for column, basis in zip(cols, labels):
        result = replays[basis].result
        column.metric(f"{labels[basis]} · Tổng thiếu gốc", f"{_number(result.principal_loss)} USDC")
        column.write(f"ETH bán thu {_number(result.eth_sale_proceeds)} USDC. "
                     f"Mất gốc lớn nhất {_number(result.worst_member_loss)} USDC mỗi người.")

    for tab, basis in zip(st.tabs(tuple(labels.values())), labels):
        replay = replays[basis]
        result = replay.result
        with tab:
            st.write(f"Dây dừng ở ngày {result.freeze_day}. Quyết toán ở ngày {result.settlement_day}.")
            st.dataframe([{
                "Ngày": row.day, "Kỳ": row.period + 1, "ID lĩnh": row.winner_id,
                "Góp trong kỳ (USDC)": round(sum(row.contributions_by_member), 2),
                "Lĩnh ròng (USDC)": round(row.net_payout, 2),
                "Nghĩa vụ còn lại (USDC)": round(sum(row.remaining_obligation_by_member), 2),
                "ETH khóa trong kỳ": round(sum(row.eth_locked_by_member), 6),
            } for row in replay.trace], hide_index=True)
            st.dataframe([{
                "ID": member.member_id, "Bỏ góp": member.is_trigger_default,
                "Đã góp (USDC)": round(member.total_contributed, 2),
                "Cần hoàn (USDC)": round(member.principal_claim, 2),
                "Được hoàn (USDC)": round(member.principal_repaid, 2),
                "Thiếu gốc (USDC)": round(member.principal_loss, 2),
                "ETH đã khóa": round(member.eth_locked, 6),
                "ETH đã bán": round(member.eth_sold, 6),
                "Giá bán (USDT/ETH)": member.eth_sale_price,
                "USDC thu hồi": round(member.eth_sold * (member.eth_sale_price or 0) + member.usdc_settlement_paid, 2),
            } for member in result.agent_results], hide_index=True)


def render_btl() -> None:
    st.header("Kết quả báo cáo BTL")
    st.caption("Kết quả đã lưu từ các lần chạy dùng trong báo cáo, đọc trực tiếp từ thư mục results/.")
    try:
        report = load_report()
    except ValueError as error:
        st.error(f"Không thể mở bảng kết quả. Kiểm tra {error}")
        return

    threshold, runs, loss = st.columns(3)
    threshold.metric("Ngưỡng đạt theo giá đóng cửa", f"{report.threshold}%")
    runs.metric("Số lượt tại mức ngưỡng", _number(report.full_runs, 0))
    loss.metric("Ca mất gốc tại mức ngưỡng", "0")
    st.write("Dây có **6 người**, góp **100 USDC mỗi kỳ**, cách nhau **30 ngày**. "
             "Dữ liệu giá ETH/USDT từ **01/01/2022 đến 31/10/2026**.")
    st.write("**1.608 cửa sổ × 3 hồ sơ chào lãi × 3 mức nộp USDC × 58 kịch bản = 839.376 lượt** "
             "cho mỗi mức quét đủ.")
    with st.expander("Cấu hình và cách đọc số liệu"):
        st.write("Hồ sơ chào lãi gồm cả dây chào 0%, cả dây chào 20%/năm và chào luân phiên giữa "
                 "0%, 5%, 10%, 15%, 20%/năm. Khả năng nộp USDC khi quyết toán là 0%, 50% hoặc 100%. "
                 "58 kịch bản gồm 57 tổ hợp nhóm bỏ góp tại các kỳ và một nhánh bỏ góp theo giá.")
        st.write("Một cửa sổ có 158 quan sát ngày. Giá đóng cửa đại diện cho giá thực thi, "
                 "trượt giá bằng 0 và 1 USDT được quy đổi xấp xỉ 1 USDC.")

    st.subheader("Mất gốc theo tỷ lệ ký quỹ")
    points = pd.DataFrame([{"Ký quỹ (%)": point.ratio, "Phạm vi": point.category,
                            "Mất gốc (USDC)": point.loss, "Số lượt": point.runs}
                           for point in report.risks])
    chart = alt.Chart(points.dropna(subset=["Mất gốc (USDC)"])).mark_point(filled=True, size=95).encode(
        x=alt.X("Ký quỹ (%):Q", scale=alt.Scale(zero=False)),
        y=alt.Y("Mất gốc (USDC):Q", title="USDC thiếu mỗi người chưa lĩnh"),
        color=alt.Color("Phạm vi:N", scale=alt.Scale(
            domain=["Quét đầy đủ", "Phản ví dụ qua sàng lọc"], range=["#176493", "#B4512A"])),
        shape="Phạm vi:N",
        tooltip=["Ký quỹ (%):Q", "Phạm vi:N", alt.Tooltip("Mất gốc (USDC):Q", format=".2f"), "Số lượt:Q"],
    )
    st.altair_chart(chart)
    st.caption("Điểm quét đầy đủ là mức thiếu lớn nhất trong toàn bộ lượt của tỷ lệ đó. Điểm sàng lọc là mức thiếu "
               "trong ca phản ví dụ ghi nhận được. Mức 180% là cấu hình demo Sepolia.")
    with st.expander("Bảng chi tiết các mức ký quỹ"):
        st.dataframe(points, hide_index=True)

    st.subheader("So sánh giá đóng cửa và giá đáy")
    dates = sorted(report.events)
    day = st.selectbox("Ngày giảm trong dữ liệu", dates, index=dates.index(FOCUS_DAY), format_func=_date, key="btl_day")
    for column, basis, label in zip(st.columns(2), (CLOSE, LOW), ("Giá đóng cửa", "Giá đáy")):
        event = report.events[day][basis]
        column.metric(label, f"{event.losses}/{event.runs} lượt mất gốc")
        column.write(f"Giá bán {_number(event.price)} USDT/ETH. Biến động {_number(event.change)}%.")
        column.write(f"Thiếu gốc lớn nhất {_number(event.worst_loss)} USDC mỗi người.")
    st.caption("Tám ngày có 6.141 lượt dùng giá đóng cửa và 6.141 lượt dùng giá đáy. "
               "Các lượt được tính khi có bán ETH đúng ngày sự kiện.")

    st.subheader("Phát lại ca ngày 18/06/2022")
    st.write("Đây là ngày duy nhất trong tám ngày đã thử mà dùng giá đáy ghi nhận mất gốc ở mức ký quỹ 250%. "
             "Kết quả đổi từ **0/825** lượt theo giá đóng cửa sang **22/825** theo giá đáy. "
             "Phát lại ca thiếu gốc lớn nhất để thấy riêng việc đổi giá bán ETH làm thay đổi phần gốc được hoàn ra sao.")
    st.caption("Phần này chạy hai lượt của cùng một ca. Dây bắt đầu 19/04/2022, bid 0%, "
               "ID 0 bỏ góp sau hai lượt lĩnh. Người đã lĩnh còn lại nộp 0% nghĩa vụ bằng USDC.")
    if st.button("Phát lại ca 18/06/2022", key="btl_replay"):
        st.session_state.pop("btl_replay_result", None)
        try:
            st.session_state.btl_replay_result = replay_focus_case(report.events[FOCUS_DAY][LOW])
        except ValueError as error:
            st.error(f"Không thể phát lại ca. Kiểm tra {error}")
    if "btl_replay_result" in st.session_state:
        _render_replay(st.session_state.btl_replay_result)
