"""Derived Financial & Operational Signals Engine.
Computes auditable mathematical signals from filed statements, strictly referencing
the exact source claim IDs used in the calculations.
"""

from typing import Any


class DerivedSignalsEngine:
    """Calculates derived signals (YoY revenue change, negative equity, employee trends)."""

    def compute_signals(self, sections: dict[str, Any]) -> dict[str, Any]:
        """Compute derived signals and attach auditable based_on claim IDs."""
        signals: dict[str, Any] = {}

        accounts = sections.get("annual_accounts", {})
        account_claims = accounts.get("claims", {})
        legal_claims = sections.get("legal_identity", {}).get("claims", {})

        # 1. YoY Revenue Change
        curr_rev_obj = account_claims.get("revenue")
        prev_rev_obj = account_claims.get("previous_year_revenue")

        if curr_rev_obj and prev_rev_obj:
            curr_val = curr_rev_obj.get("value")
            prev_val = prev_rev_obj.get("value")
            if (
                isinstance(curr_val, (int, float))
                and isinstance(prev_val, (int, float))
                and prev_val > 0
            ):
                pct_change = (curr_val - prev_val) / prev_val
                pct_formatted = round(pct_change * 100, 1)
                direction = "increased" if pct_change > 0 else "decreased"
                signals["yoy_revenue_change"] = {
                    "value": round(pct_change, 4),
                    "percentage": f"{pct_formatted}%",
                    "description": f"Annual revenue {direction} by {abs(pct_formatted)}% year-over-year",
                    "based_on": [curr_rev_obj["claim_id"], prev_rev_obj["claim_id"]],
                    "status": "available",
                }

        # 2. Negative Equity Flag (Solvency Risk)
        equity_obj = account_claims.get("equity")
        if equity_obj:
            eq_val = equity_obj.get("value")
            if isinstance(eq_val, (int, float)):
                is_negative = eq_val < 0
                signals["negative_equity"] = {
                    "value": is_negative,
                    "description": (
                        "Negative equity detected, potential balance sheet insolvency risk"
                        if is_negative
                        else "Solvent equity reserves reported"
                    ),
                    "based_on": [equity_obj["claim_id"]],
                    "status": "available",
                }

        # 3. Operating Profit Margin
        rev_obj = account_claims.get("revenue")
        op_res_obj = account_claims.get("operating_result")
        if rev_obj and op_res_obj:
            r_val = rev_obj.get("value")
            op_val = op_res_obj.get("value")
            if (
                isinstance(r_val, (int, float))
                and isinstance(op_val, (int, float))
                and r_val > 0
            ):
                margin = op_val / r_val
                margin_pct = round(margin * 100, 1)
                signals["operating_margin"] = {
                    "value": round(margin, 4),
                    "percentage": f"{margin_pct}%",
                    "description": f"Operating profit margin of {margin_pct}%",
                    "based_on": [rev_obj["claim_id"], op_res_obj["claim_id"]],
                    "status": "available",
                }

        # 4. Workforce Scale & Trend
        emp_obj = legal_claims.get("employee_count")
        if emp_obj:
            emp_val = emp_obj.get("value", 0)
            if isinstance(emp_val, int):
                scale_desc = (
                    "Enterprise (>250 employees)"
                    if emp_val >= 250
                    else "Medium enterprise (50-249 employees)"
                    if emp_val >= 50
                    else "Small business (10-49 employees)"
                    if emp_val >= 10
                    else "Micro business (1-9 employees)"
                    if emp_val > 0
                    else "No registered employees"
                )
                signals["workforce_scale"] = {
                    "value": emp_val,
                    "classification": scale_desc,
                    "based_on": [emp_obj["claim_id"]],
                    "status": "available",
                }

        return signals
