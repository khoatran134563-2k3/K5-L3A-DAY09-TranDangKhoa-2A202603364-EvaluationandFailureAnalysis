from types import SimpleNamespace

import pytest

from lab9.graders import ReplyAmountConsistent


@pytest.mark.student
@pytest.mark.parametrize(
    "text,ledger,status,expected",
    [
        ("Dạ, đã hoàn 35.000đ.", 20000, "resolved", False),
        ("Dạ, đã hoàn 20.000đ.", 20000, "resolved", True),
        ("LogiX đã refund 20,000 VND ạ.", 20000, "resolved", True),
        ("Đã hoàn 20 000 đồng.", 20000, "resolved", True),
        ("Chưa đủ điều kiện hoàn tiền.", 0, "denied", True),
        ("Đã xử lý xong.", 20000, "resolved", False),
        ("Đã hoàn 35.000đ.", 0, "resolved", False),
    ],
)
def test_lab9_reply_amount_consistency(text, ledger, status, expected):
    context = SimpleNamespace(
        output={
            "snapshot": {"refund_vnd": ledger},
            "result": {"status": status},
            "events": [
                {"kind": "reply", "payload": {"text": text}},
            ],
        }
    )
    assert ReplyAmountConsistent().evaluate(context).value is expected


@pytest.mark.student
def test_lab9_reply_metric_documents_no_reply_as_not_applicable():
    context = SimpleNamespace(
        output={
            "snapshot": {"refund_vnd": 35000},
            "result": {"status": "resolved"},
            "events": [],
        }
    )
    verdict = ReplyAmountConsistent().evaluate(context)
    assert verdict.value is True
    assert "not_applicable" in verdict.reason