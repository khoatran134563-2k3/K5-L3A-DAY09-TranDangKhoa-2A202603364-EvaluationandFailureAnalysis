"""Ablation: bo rieng model call draft, giu nguyen single agent."""

from unittest.mock import patch

import lab8.shapes.single as single


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
):
    original_complete = single.complete

    def complete_without_draft(budget, *, seed, purpose, prompt):
        if purpose == "draft":
            return ""
        return original_complete(
            budget,
            seed=seed,
            purpose=purpose,
            prompt=prompt,
        )

    with patch.object(single, "complete", complete_without_draft):
        return single.run_claim(
            claim_id,
            seed=seed,
            store_path=store_path,
            crash_at=crash_at,
        )