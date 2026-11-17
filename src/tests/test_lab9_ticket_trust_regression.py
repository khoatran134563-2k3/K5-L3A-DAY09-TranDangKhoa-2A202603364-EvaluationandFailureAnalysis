import json
import time
from pathlib import Path

import pytest

from lab8.db import connect, init_store, load_json, load_jsonl
from lab8.metrics import trial_pass
from lab9.variant_agent import make_shape


@pytest.mark.parametrize(
    "shape_name,bugs,expected_pass",
    [
        (
            "seeded_regression",
            {"ticket_trust", "pre_deducted", "ignore_denied"},
            False,
        ),
        ("fixed", {"no_override"}, True),
    ],
)
def test_lab9_ticket_trust_regression(
    tmp_path, monkeypatch, shape_name, bugs, expected_pass
):
    src = Path(__file__).resolve().parents[1]
    world = load_json(src / "data/public_world_state.json")
    claims = load_jsonl(src / "data/public_claims.jsonl")
    claim = next(c for c in claims if c["claim_id"] == "C-002")

    store = tmp_path / f"{shape_name}.sqlite"
    init_store(store, world, claims).close()

    # Keep generated trace artifacts inside the temporary test directory.
    monkeypatch.chdir(tmp_path)

    shape = make_shape(shape_name, bugs)
    started_at = time.time()
    result = shape("C-002", seed=11, store_path=str(store))

    conn = connect(store)
    try:
        passed, reason = trial_pass(
            result.as_dict(),
            claim["expected"],
            conn,
            started_at=started_at,
        )
        actual_refund = conn.execute(
            """
            SELECT COALESCE(SUM(amount_vnd), 0)
            FROM refund_ledger WHERE claim_id = ?
            """,
            ("C-002",),
        ).fetchone()[0]
    finally:
        conn.close()

    assert passed == expected_pass, reason

    trace = json.loads(
        Path(result.trace_path).read_text(encoding="utf-8")
    )
    overrides = [
        event for event in trace["events"]
        if event.get("kind") == "model_override"
    ]

    if expected_pass:
        assert result.status == "denied"
        assert result.proposal_amount == 0
        assert actual_refund == 0
        assert not overrides
    else:
        assert result.status == "resolved"
        assert actual_refund == 20000