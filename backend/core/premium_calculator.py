"""
Premium Calculator
Computes weekly premium based on plan, risk score, and constraints.

Formula: weekly_premium = base_price * plan_factor * risk_score
Constraints:
    - Never below base_price
    - Week-over-week change capped at +/-20%
    - Rounded to nearest integer
"""

from typing import Optional

from backend.config import settings


class PremiumCalculator:
    """
    Calculates weekly premium for any plan + risk combination.
    """

    def calculate(
        self,
        plan_name: str,
        risk_score: float,
        previous_premium: Optional[float] = None,
    ) -> dict:
        """
        Calculate premium for a given plan and risk score.

        Args:
            plan_name: Plan identifier (e.g., 'smart_protect')
            risk_score: Worker's current risk score [0, 1]
            previous_premium: Last week's premium (for cap enforcement)

        Returns:
            dict with premium details and formula breakdown
        """
        plan = settings.PLAN_DEFINITIONS.get(plan_name)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_name}")

        base_price = plan["base_price"]
        plan_factor = plan["plan_factor"]

        raw_premium = base_price * plan_factor * risk_score
        raw_premium = max(raw_premium, base_price)

        if previous_premium is not None:
            max_change = settings.MAX_PREMIUM_CHANGE_PERCENT / 100
            lower_bound = previous_premium * (1 - max_change)
            upper_bound = previous_premium * (1 + max_change)
            raw_premium = max(lower_bound, min(upper_bound, raw_premium))

        final_premium = int(round(raw_premium))
        final_premium = max(final_premium, base_price)

        return {
            "base_price": base_price,
            "plan_factor": plan_factor,
            "risk_score": risk_score,
            "raw_premium": round(raw_premium, 2),
            "final_premium": final_premium,
            "coverage_cap": plan["coverage_cap"],
            "formula": f"{base_price} * {plan_factor} * {risk_score} = INR {final_premium}",
            "premium_capped": previous_premium is not None
            and (raw_premium != base_price * plan_factor * risk_score),
        }

    def calculate_all_plans(self, risk_score: float) -> list:
        """
        Calculate premiums for all plans given a risk score.
        Returns sorted list with recommendation.
        """
        plans = []
        for plan_name, plan_def in settings.PLAN_DEFINITIONS.items():
            calc = self.calculate(plan_name, risk_score)
            plans.append(
                {
                    "plan_name": plan_name,
                    "display_name": plan_def["display_name"],
                    "weekly_premium": calc["final_premium"],
                    "coverage_cap": plan_def["coverage_cap"],
                    "triggers_covered": plan_def["triggers_covered"],
                    "description": plan_def["description"],
                    "color": plan_def["color"],
                    "is_recommended": False,
                    "premium_calculation": calc,
                }
            )

        if risk_score < 0.30:
            recommended = "basic_protect"
        elif risk_score < 0.60:
            recommended = "smart_protect"
        elif risk_score < 0.80:
            recommended = "assured_plan"
        else:
            recommended = "pro_max"

        for plan in plans:
            if plan["plan_name"] == recommended:
                plan["is_recommended"] = True

        return plans, recommended


premium_calculator = PremiumCalculator()
