"""Shape A: workflow cố định; tiền do code tính, host duyệt và ghi."""

from __future__ import annotations

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import (
    compute_compensation,
    get_claim_view,
    lookup_order,
    tool_cost,
)
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("workflow", claim_id, seed))
    conn = connect(store_path)

    def complete(
        status: str,
        proposal: int = 0,
        reason: str | None = None,
    ) -> RunResult:
        trace.add(
            "decision",
            {
                "status": status,
                "proposal_amount": proposal,
                "reason": reason,
            },
        )
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    try:
        budget.add_tool(tool_cost())
        claim = get_claim_view(conn, claim_id)

        # Không ghi ticket vào trace vì có thể chứa dữ liệu nhạy cảm.
        trace.add("claim", {"found": claim["found"]})

        if not claim["found"]:
            return complete("failed", reason="unknown_claim")

        if not claim.get("order_id"):
            return complete("needs_info", reason="missing_order_id")

        budget.add_tool(tool_cost())
        order_view = lookup_order(
            conn,
            claim["order_id"],
            claim["principal_id"],
        )
        trace.add(
            "order_scope",
            {
                "visible": order_view["visible"],
                "reason": order_view["reason"],
            },
        )

        if not order_view["visible"]:
            return complete("escalated", reason=order_view["reason"])

        budget.add_tool(tool_cost())
        quote = compute_compensation(conn, order_view["order"])
        proposal = int(quote["amount_vnd"])
        trace.add("quote", quote)

        if proposal <= 0:
            return complete("denied", reason=quote["reason"])

        # Truyền quote đầy đủ.
        # Host kiểm approval, trừ khoản đã hoàn và chống ghi trùng.
        outcome = issue_refund(
            conn,
            claim_id,
            proposal,
            crash_at=crash_at,
        )
        trace.add(
            "refund",
            {
                "ok": outcome["ok"],
                "reason": outcome["reason"],
            },
        )

        if not outcome["ok"]:
            status = "failed" if outcome["conflict"] else "denied"
            return complete(status, proposal, outcome["reason"])

        return complete("resolved", proposal)

    finally:
        # Đóng kết nối kể cả khi InjectedCrash lan ra ngoài.
        conn.close()