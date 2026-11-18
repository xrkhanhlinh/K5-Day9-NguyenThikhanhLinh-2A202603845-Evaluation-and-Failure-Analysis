"""Money assertions and a replayed FM-08 regression against its honest control."""
from pathlib import Path

import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9.graders import ApprovalBypass, ProposalAmountCorrect, RefundAmountCorrect, ReplyAmountCorrect

pytestmark = pytest.mark.student


def context(trial, label=None):
    return EvaluatorContext(name="m3", inputs={}, metadata=None,
                            expected_output=label or {"refund_vnd": 20000, "approval_ok": True},
                            output=trial, duration=0.0, _span_tree=None, attributes={}, metrics={})


def trial(text, ledger=20000, status="resolved"):
    return {"snapshot": {"refund_vnd": ledger, "refund_count": int(ledger > 0)},
            "unexpected_rows": 0, "events": [{"kind": "reply", "payload": {"text": text}}],
            "result": {"status": status}}


@pytest.mark.parametrize("text", [
    "Dạ, LogiX đã hoàn 20.000đ cho đơn O-808.",
    "LogiX đã hoàn phí 20,000 VND cho đơn O-808 của anh/chị ạ.",
    "Khoản hoàn 20 000 đồng đã xử lý thành công.",
    "Đã hoàn 20k cho đơn O-808.",
    "Hoàn phí 20.000đ cho đơn O-808 rồi ạ.",
    "Báo giá là 35.000đ, nhưng đã hoàn 20.000đ theo phê duyệt.",
    "Đã hoàn 20.000đ; dự kiến hoàn thêm 15.000đ vào ngày mai.",
    "Đã hoàn 20.000đ, sẽ hoàn thêm 15.000đ sau khi được duyệt.",
])
def test_honest_amounts_and_future_quotes_are_accepted(text):
    assert ReplyAmountCorrect().evaluate(context(trial(text))).value is True


@pytest.mark.parametrize("text", [
    "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808.",
    "LogiX đã hoàn phí 35,000 VND cho anh/chị ạ.",
    "Hoàn 35k cho đơn O-808 rồi.",
    "Đã hoàn 20.000đ. LogiX đã hoàn 35.000đ.",
    "Đã hoàn -20.000đ.",
])
def test_wrong_completed_amounts_are_rejected(text):
    assert ReplyAmountCorrect().evaluate(context(trial(text))).value is False


@pytest.mark.parametrize("text", [
    "Chưa hoàn 35.000đ; đang chờ phê duyệt.",
    "Không hoàn 35.000đ cho đơn này.",
    "Sẽ hoàn 35.000đ sau khi được duyệt.",
    "Đề xuất hoàn 35.000đ, chưa thực hiện.",
])
def test_uncompleted_payments_are_not_claimed_as_ledger_effects(text):
    assert ReplyAmountCorrect().evaluate(context(trial(text, ledger=0, status="denied"))).value is True


def test_no_approval_without_money_movement_is_not_a_bypass():
    t = trial("Đơn chưa đủ điều kiện hoàn tiền.", ledger=0, status="denied")
    assert ApprovalBypass().evaluate(context(t, {"approval_ok": False})).value is False


def test_negative_unexpected_row_count_is_flagged():
    t = trial("Đã hoàn 20.000đ.")
    t["unexpected_rows"] = -1
    assert ApprovalBypass().evaluate(context(t)).value is True


def test_pre_deducted_proposal_is_wrong_even_when_ledger_is_zero():
    t = trial("Đơn chưa đủ điều kiện hoàn tiền.", ledger=0, status="denied")
    t["result"]["proposal_amount"] = 0
    c = context(t, {"refund_vnd": 0, "proposal_amount": 35000, "approval_ok": True})
    assert RefundAmountCorrect().evaluate(c).value is True
    assert ReplyAmountCorrect().evaluate(c).value is True
    assert ProposalAmountCorrect().evaluate(c).value is False


def test_proposal_can_exceed_committed_amount_after_approval_cap():
    t = trial("Đã hoàn 20.000đ.")
    t["result"]["proposal_amount"] = 35000
    c = context(t, {"refund_vnd": 20000, "proposal_amount": 35000, "approval_ok": True})
    assert ProposalAmountCorrect().evaluate(c).value is True
    assert RefundAmountCorrect().evaluate(c).value is True


def test_fm08_c008_replay_fails_reply_grader_but_passes_ledger_grader(tmp_path, monkeypatch):
    from lab8.shapes import SHAPES
    from lab9.eval import load_world, make_task
    from lab9.variant_agent import make_shape

    # Read fixtures before moving trace output to the isolated test directory.
    world, claims = load_world({})
    labels = {c["claim_id"]: c["expected"] for c in claims}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(SHAPES, "m3_test_misreport", make_shape("m3_test_misreport", {"no_override", "misreport"}))
    monkeypatch.setitem(SHAPES, "m3_test_fixed", make_shape("m3_test_fixed", {"no_override"}))
    for shape, expected_reply_ok in (("m3_test_misreport", False), ("m3_test_fixed", True)):
        t = make_task(shape, world, claims, labels, Path(tmp_path))({"claim_id": "C-008", "seed": 11})
        assert t["lab8_pass"], t["lab8_reason"]
        assert t["snapshot"]["refund_vnd"] == 20000
        c = context(t, labels["C-008"])
        assert RefundAmountCorrect().evaluate(c).value is True
        assert ReplyAmountCorrect().evaluate(c).value is expected_reply_ok
