from __future__ import annotations

from difflib import unified_diff
from typing import Any

from app.core.constants import dt_to_iso
from app.models import AppSession, SessionCostResult
from app.schemas.session import (
    CostDiffResponse,
    CostFieldDelta,
    JsonDiffItem,
    SessionCompareSummary,
    TerraformDiffResponse,
)


def build_session_summary(session: AppSession) -> SessionCompareSummary:
    return SessionCompareSummary(
        sessionId=str(session.id),
        versionNo=session.version_no,
        status=session.status,
        createdAt=dt_to_iso(session.created_at),
    )


def collect_json_diff(before: Any, after: Any, path: str = "$") -> list[JsonDiffItem]:
    if isinstance(before, dict) and isinstance(after, dict):
        items: list[JsonDiffItem] = []
        all_keys = sorted(set(before.keys()) | set(after.keys()))
        for key in all_keys:
            next_path = f"{path}.{key}"
            if key not in before:
                items.append(JsonDiffItem(path=next_path, changeType="added", after=after[key]))
            elif key not in after:
                items.append(JsonDiffItem(path=next_path, changeType="removed", before=before[key]))
            else:
                items.extend(collect_json_diff(before[key], after[key], next_path))
        return items

    if isinstance(before, list) and isinstance(after, list):
        if before == after:
            return []
        return [JsonDiffItem(path=path, changeType="changed", before=before, after=after)]

    if before != after:
        return [JsonDiffItem(path=path, changeType="changed", before=before, after=after)]

    return []


def build_terraform_diff(before_code: str | None, after_code: str | None) -> TerraformDiffResponse:
    before_lines = (before_code or "").splitlines()
    after_lines = (after_code or "").splitlines()
    diff = "\n".join(
        unified_diff(before_lines, after_lines, fromfile="base.tf", tofile="target.tf", lineterm="")
    )
    return TerraformDiffResponse(changed=(before_code or "") != (after_code or ""), diff=diff)


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def build_cost_delta(before: Any, after: Any) -> CostFieldDelta:
    before_num = to_float(before)
    after_num = to_float(after)
    if before_num is None and after_num is None:
        return CostFieldDelta(before=None, after=None, delta=None)
    if before_num is None or after_num is None:
        return CostFieldDelta(before=before_num, after=after_num, delta=None)
    return CostFieldDelta(before=before_num, after=after_num, delta=round(after_num - before_num, 2))


def build_cost_diff(
    before_cost: SessionCostResult | None,
    after_cost: SessionCostResult | None,
) -> CostDiffResponse:
    before_breakdown = before_cost.cost_breakdown_json if before_cost else {}
    after_breakdown = after_cost.cost_breakdown_json if after_cost else {}
    cost_keys = sorted(set(before_breakdown.keys()) | set(after_breakdown.keys()))

    breakdown = {key: build_cost_delta(before_breakdown.get(key), after_breakdown.get(key)) for key in cost_keys}
    assumptions_before = before_cost.assumption_json if before_cost else {}
    assumptions_after = after_cost.assumption_json if after_cost else {}
    assumptions_changed = collect_json_diff(assumptions_before, assumptions_after)

    monthly_before = before_cost.monthly_total if before_cost else None
    monthly_after = after_cost.monthly_total if after_cost else None
    monthly_total = build_cost_delta(monthly_before, monthly_after)

    changed = (
        monthly_total.before != monthly_total.after
        or any(item.before != item.after for item in breakdown.values())
        or bool(assumptions_changed)
    )
    return CostDiffResponse(
        changed=changed,
        monthlyTotal=monthly_total,
        breakdown=breakdown,
        assumptionsChanged=assumptions_changed,
    )
