import uuid
from datetime import date, timedelta, datetime
from typing import Optional


def _period_start(period: str) -> date:
    today = date.today()
    if period == "週":
        return today - timedelta(days=today.weekday())
    elif period == "雙週":
        # Use a fixed Monday epoch so 2-week windows are stable across year boundaries
        _EPOCH = date(2024, 1, 1)  # known Monday
        days_since = (today - _EPOCH).days
        return _EPOCH + timedelta(days=(days_since // 14) * 14)
    else:  # 月
        return today.replace(day=1)


def get_current_period_expenses(expenses: list, budget: dict) -> list:
    """Filter expenses to the budget's current period and category."""
    start = _period_start(budget["period"])
    return [
        e for e in expenses
        if e["date"] >= start.isoformat()
        and (budget["category"] == "總計" or e["category"] == budget["category"])
    ]


def calc_budget_status(expenses: list, budgets: list, base_currency: str, fx_rates: dict) -> list:
    """Returns list of budget status dicts."""
    statuses = []
    for b in budgets:
        period_expenses = get_current_period_expenses(expenses, b)
        budget_amt_base = b["amount"] * fx_rates.get(b["currency"], 1.0)
        spent_base = sum(
            e["amount"] * fx_rates.get(e["currency"], 1.0)
            for e in period_expenses
        )
        remaining = budget_amt_base - spent_base
        pct_used = spent_base / budget_amt_base if budget_amt_base > 0 else 0.0
        statuses.append({
            "id": b["id"],
            "category": b["category"],
            "period": b["period"],
            "budget_amount": budget_amt_base,
            "spent_amount": spent_base,
            "remaining": remaining,
            "pct_used": pct_used,
            "alert": pct_used >= b.get("alert_threshold", 0.6),
            "alert_threshold": b.get("alert_threshold", 0.6),
        })
    return statuses


def get_budget_alerts(statuses: list) -> list:
    return [s for s in statuses if s["alert"]]


def generate_id(prefix: str = "item") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def generate_expense_id() -> str:
    return generate_id("exp")


def generate_budget_id() -> str:
    return generate_id("bgt")


def generate_card_id() -> str:
    return generate_id("card")
