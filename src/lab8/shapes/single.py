"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import get_claim_view, tool_cost


class _Trace:
    """Local alias so a crash can still flush. Wraps lab8.trace.Trace."""

    def __init__(self, run_id: str) -> None:
        from lab8.trace import Trace

        self._inner = Trace(run_id)

    def add(self, kind: str, payload: dict) -> None:
        self._inner.add(kind, payload)

    def write(self) -> str:
        return self._inner.write()

    @property
    def run_id(self) -> str:
        return self._inner.run_id


class _SingleAgentDecider:
    def __init__(self, claim_view: dict[str, Any], seed: int, budget: Budget, trace: _Trace):
        self.claim_view = claim_view
        self.seed = seed
        self.budget = budget
        self.trace = trace
        self.order: dict[str, Any] | None = None
        self.quote: dict[str, Any] | None = None
        self.refund_history: dict[str, Any] | None = None

    def decide(self, seen: dict[str, Any]) -> dict[str, Any]:
        if not self.claim_view.get("order_id"):
            complete(self.budget, seed=self.seed, purpose="decide", prompt="missing_order_id")
            self.trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
            return {"final": {"status": "needs_info", "reason": "missing_order_id"}}

        last_tool = seen.get("last_tool")
        last_result = seen.get("last_result")

        if last_tool == "lookup_order":
            if not last_result or not last_result.get("visible"):
                complete(self.budget, seed=self.seed, purpose="decide", prompt="order_not_visible")
                reason = (last_result or {}).get("reason", "order_not_visible")
                self.trace.add("decision", {"status": "escalated", "reason": reason})
                return {"final": {"status": "escalated", "reason": reason}}
            self.order = dict(last_result["order"])
            self.trace.add("react_obs", {"order_visible": True, "status": self.order.get("status")})

            complete(self.budget, seed=self.seed, purpose="decide", prompt="lookup_refund_history")
            return {
                "tool": "lookup_refund_history",
                "args": {
                    "order_id": self.claim_view["order_id"],
                    "principal_id": self.claim_view["principal_id"],
                },
            }

        if last_tool == "lookup_refund_history":
            self.refund_history = last_result
            self.trace.add("react_obs", {"refund_history": last_result})
            complete(self.budget, seed=self.seed, purpose="decide", prompt="compute_compensation")
            return {
                "tool": "compute_compensation",
                "args": {"order": self.order},
            }

        if last_tool == "compute_compensation":
            self.quote = last_result
            self.trace.add("react_obs", {"quote": last_result})
            complete(self.budget, seed=self.seed, purpose="decide", prompt="finalize")
            return {
                "final": {
                    "status": "quote_ready",
                    "quote": self.quote,
                    "order": self.order,
                }
            }

        # Initial step: lookup order
        complete(self.budget, seed=self.seed, purpose="decide", prompt="lookup_order")
        return {
            "tool": "lookup_order",
            "args": {
                "order_id": self.claim_view["order_id"],
                "principal_id": self.claim_view["principal_id"],
            },
        }


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    run_id = make_run_id("single", claim_id, seed)
    trace = _Trace(run_id)

    claim_view = get_claim_view(conn, claim_id)
    budget.add_tool(tool_cost())

    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    ticket = claim_view.get("ticket", "")
    complete(budget, seed=seed, purpose="parse", prompt=ticket)

    decider = _SingleAgentDecider(claim_view, seed, budget, trace)
    outcome = run_react(
        conn,
        budget,
        observation={"claim": claim_view},
        decide=decider.decide,
        max_steps=8,
        worker=True,
    )

    if outcome.get("stopped") == "step_cap":
        trace.add("decision", {"status": "failed", "reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    final = outcome.get("final", {})
    status = final.get("status")

    if status == "needs_info":
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("reason", "missing_order_id"),
        )

    if status == "escalated":
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add("decision", {"status": "escalated"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("reason"),
        )

    if status == "quote_ready":
        quote_payload = final["quote"]
        proposal = int(quote_payload["amount_vnd"])
        trace.add("quote", quote_payload)
        complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

        if proposal <= 0:
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="denied",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason=quote_payload.get("reason"),
            )

        try:
            outcome_refund = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        except InjectedCrash:
            trace.add("crash", {"at": crash_at})
            trace.write()
            raise

        if not outcome_refund["ok"]:
            refund_status = "failed" if outcome_refund["conflict"] else "denied"
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status=refund_status,
                proposal_amount=proposal,
                budget=budget,
                trace=trace,
                error_reason=outcome_refund["reason"],
            )

        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="resolved",
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=None,
        )

    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="failed",
        proposal_amount=0,
        budget=budget,
        trace=trace,
        error_reason=final.get("reason", "unexpected_status"),
    )
