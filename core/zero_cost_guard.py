"""Fail-closed zero-cost policy guard. Standard-library only."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

BLOCKED_ACTIONS = {
    "payment", "transfer", "purchase", "subscription", "upgrade", "paid_api",
    "paid_hosting", "credit", "loan", "borrow", "auto_renew", "reinvestment",
    "contract_sign", "legal_sign", "withdrawal",
}

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def evaluate(action: str, estimated_cost: Any = 0, free_quota_available: bool = True,
             owner_approved: bool = False) -> Decision:
    """Only zero-cost, non-sensitive actions can pass. Owner approval cannot waive ₹0."""
    normalized = str(action or "").strip().lower().replace("-", "_").replace(" ", "_")
    try:
        cost = Decimal(str(estimated_cost))
    except (InvalidOperation, ValueError, TypeError):
        return Decision(False, "Invalid cost; fail closed.")
    if not cost.is_finite() or cost < 0:
        return Decision(False, "Invalid or negative cost; fail closed.")
    if cost > 0:
        return Decision(False, "Hard zero-spend policy: any positive cost is blocked.")
    if normalized in BLOCKED_ACTIONS:
        return Decision(False, f"Sensitive action '{normalized}' requires owner control and is blocked by this runtime.")
    if not free_quota_available:
        return Decision(False, "Free quota exhausted; stop rather than incur charges.")
    return Decision(True, "Allowed: zero-cost, non-sensitive action only.")
