"""Shape C: orchestrator with read-only investigators."""

from __future__ import annotations

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    budget = Budget()
    trace = Trace(make_run_id("orchestrator", claim_id, seed))

    def finish_result(
        status: str,
        proposal: int = 0,
        reason: str | None = None,
    ) -> RunResult:
        # Only controlled status and numeric amount enter the trace.
        trace.add(
            "decision",
            {"status": status, "proposal_amount": proposal},
        )
        complete(
            budget,
            seed=seed,
            purpose="draft",
            prompt=f"status={status}; proposal={proposal}",
        )
        return finish(
            conn,
            shape="orchestrator",
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

        # Do not trace the full claim: its ticket is untrusted text.
        if not claim.get("found"):
            return finish_result("failed", reason="unknown_claim")

        if not claim.get("order_id"):
            return finish_result("needs_info", reason="missing_order_id")

        # Fixed task and empty facts avoid forwarding parent context.
        handoff = make_handoff(
            request_id=f"REQ-{claim_id}",
            claim_id=claim_id,
            task="check_applicable_policy",
            facts={},
            allowed_tools=["lookup_order", "lookup_policy"],
        )
        trace.add("handoff", safe_dump(handoff))

        investigated = run_readonly_investigators(
            conn,
            budget,
            handoff,
            principal_id=claim["principal_id"],
        )
        tools = investigated["tools"]
        order_view = tools.get("lookup_order", {})

        # Trace a small explicit selection, not investigator output wholesale.
        trace.add(
            "investigator",
            {
                "visible": bool(order_view.get("visible")),
                "policy_count": len(
                    (tools.get("lookup_policy") or {}).get("policies") or []
                ),
            },
        )

        if not order_view.get("visible"):
            return finish_result(
                "escalated",
                reason=order_view.get("reason"),
            )

        # Money is computed from structured order data, never ticket text.
        budget.add_tool(tool_cost())
        quote = compute_compensation(conn, order_view["order"])
        proposal = int(quote["amount_vnd"])
        trace.add("quote", {"amount_vnd": proposal})

        if proposal <= 0:
            return finish_result("denied", reason=quote.get("reason"))

        # Full quote: the host applies approval and prior-refund caps.
        # InjectedCrash deliberately propagates to the caller.
        outcome = issue_refund(
            conn,
            claim_id,
            proposal,
            crash_at=crash_at,
        )
        trace.add(
            "host_result",
            {
                "ok": bool(outcome["ok"]),
                "conflict": bool(outcome.get("conflict")),
            },
        )

        if outcome["ok"]:
            return finish_result("resolved", proposal)

        status = "failed" if outcome.get("conflict") else "denied"
        return finish_result(status, proposal, outcome.get("reason"))

    finally:
        # Also flush the sanitized trace when an injected crash propagates.
        try:
            trace.write()
        finally:
            conn.close()