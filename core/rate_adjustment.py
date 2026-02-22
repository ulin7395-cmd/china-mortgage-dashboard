"""利率调整处理"""
from datetime import date
from typing import Tuple, Dict

import pandas as pd

from core.calculator import generate_schedule
from utils.date_utils import add_months


def apply_rate_adjustment(
    plan_id: str,
    schedule: pd.DataFrame,
    effective_period: int,
    new_rate: float,
    repayment_method: str,
    start_date: date,
    repayment_day: int,
) -> Tuple[pd.DataFrame, Dict]:
    """
    从 effective_period 开始用新利率重新生成后续还款计划。
    返回 (新完整计划, 调整影响摘要)
    """
    # 保留生效前的已有记录
    before = schedule[schedule["period"] < effective_period].copy()

    if before.empty:
        remaining = schedule.iloc[0]["remaining_principal"] + schedule.iloc[0]["principal"]
        cum_p = 0.0
        cum_i = 0.0
    else:
        last = before.iloc[-1]
        remaining = float(last["remaining_principal"])
        cum_p = float(last["cumulative_principal"])
        cum_i = float(last["cumulative_interest"])

    old_rate = float(schedule[schedule["period"] == effective_period].iloc[0]["applied_rate"]) \
        if not schedule[schedule["period"] == effective_period].empty \
        else float(schedule.iloc[0]["applied_rate"])

    remaining_term = len(schedule) - effective_period + 1
    new_start = add_months(start_date, effective_period - 1)

    after = generate_schedule(
        plan_id, remaining, new_rate, remaining_term,
        repayment_method, new_start, repayment_day,
        start_period=effective_period,
        existing_cumulative_principal=cum_p,
        existing_cumulative_interest=cum_i,
    )

    full = pd.concat([before, after], ignore_index=True)

    # 计算影响
    old_remaining_interest = schedule[schedule["period"] >= effective_period]["interest"].sum()
    new_remaining_interest = after["interest"].sum()

    old_monthly = float(schedule[schedule["period"] == effective_period].iloc[0]["monthly_payment"]) \
        if not schedule[schedule["period"] == effective_period].empty else 0
    new_monthly = float(after.iloc[0]["monthly_payment"]) if not after.empty else 0

    summary = {
        "old_rate": old_rate,
        "new_rate": new_rate,
        "old_monthly_payment": round(old_monthly, 2),
        "new_monthly_payment": round(new_monthly, 2),
        "monthly_change": round(new_monthly - old_monthly, 2),
        "old_remaining_interest": round(old_remaining_interest, 2),
        "new_remaining_interest": round(new_remaining_interest, 2),
        "interest_change": round(new_remaining_interest - old_remaining_interest, 2),
    }

    return full, summary
