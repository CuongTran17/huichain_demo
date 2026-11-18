from pathlib import Path
import shutil

import pytest
from streamlit.testing.v1 import AppTest

from rosca_sim.btl_results import CLOSE, EVENTS, FOCUS_DAY, LOW, REPORT_MODE, ROOT, SUMMARY, UPPER, load_report


def test_report_archive_rejects_missing_and_inconsistent_event_data(tmp_path):
    for relative in (SUMMARY, f"{UPPER}/threshold.json", f"{UPPER}/phase_b_upper_ratios.csv"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    with pytest.raises(ValueError, match="historical_event_replays.csv"):
        load_report(tmp_path)
    events = tmp_path / EVENTS
    events.parent.mkdir(parents=True)
    text = (ROOT / EVENTS).read_text(encoding="utf-8-sig")
    events.write_text(text.replace(",825,22,", ",825,21,"), encoding="utf-8-sig")
    with pytest.raises(ValueError, match="historical_event_replays.csv"):
        load_report(tmp_path)


def test_default_report_filters_and_replays_paired_case():
    app = Path(ROOT / "src/rosca_sim/web_app.py")
    view = AppTest.from_file(str(app), default_timeout=20).run()
    assert not view.exception
    assert not view.error
    assert view.radio(key="view").value == REPORT_MODE
    assert view.selectbox(key="btl_day").value == FOCUS_DAY
    assert "btl_replay_result" not in view.session_state
    assert [metric.value for metric in view.metric][:5] == [
        "250%", "839.376", "0", "0/825 lượt mất gốc", "22/825 lượt mất gốc",
    ]
    report = load_report()
    assert all(point.loss is None for point in report.risks if point.ratio >= 255)
    view.selectbox(key="btl_day").set_value("2022-05-09").run()
    assert view.selectbox(key="btl_day").value == "2022-05-09"
    assert "btl_replay_result" not in view.session_state
    view.button(key="btl_replay").click().run()
    assert not view.exception
    assert not view.error
    replays = view.session_state.btl_replay_result
    close, low = replays[CLOSE].result, replays[LOW].result
    assert close.payout_order == low.payout_order == (0, 1)
    assert close.freeze_day == low.freeze_day == 60
    assert [m.member_id for m in low.agent_results if m.is_trigger_default] == [0]
    assert close.principal_loss == pytest.approx(0)
    assert round(low.principal_loss, 2) == 44.74
    assert round(low.worst_member_loss, 2) == 11.18
    view.radio(key="view").set_value("So sánh kịch bản").run()
    assert not view.exception
    view.radio(key="view").set_value(REPORT_MODE).run()
    assert not view.exception
    assert "btl_replay_result" in view.session_state
