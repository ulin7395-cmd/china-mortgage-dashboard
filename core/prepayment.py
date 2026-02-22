"""提前还款计算"""
import math
from datetime import date
from typing import Dict, Tuple

import pandas as pd

from config.constants import RepaymentMethod, PrepaymentMethod
from core.calculator import generate_schedule, calc_equal_installment


def calc_shorten_term(
    remaining_principal: float,
    prepay_amount: float,
    annual_rate: float,
    old_monthly_payment: float,
    repayment_method: str,
) -> Tuple[int, float]:
    """缩短年限：月供不变，计算新期数。返回 (新剩余期数, 新月供)"""
    new_principal = remaining_principal - prepay_amount
    r = annual_rate / 100 / 12

    if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
        if r == 0:
            new_term = math.ceil(new_principal / old_monthly_payment)
        else:
            # M = P * r * (1+r)^n / ((1+r)^n - 1)
            # 解 n: n = -ln(1 - P*r/M) / ln(1+r)
            ratio = new_principal * r / old_monthly_payment
            if ratio >= 1:
                # 月供不足以覆盖利息，无法缩短
                new_term = math.ceil(new_principal / old_monthly_payment)
            else:
                new_term = math.ceil(-math.log(1 - ratio) / math.log(1 + r))
        new_monthly = old_monthly_payment
    else:
        # 等额本金：保持每月还的本金不变
        old_base = old_monthly_payment - remaining_principal * r  # 近似
        if old_base <= 0:
            old_base = remaining_principal / 360  # fallback
        new_term = math.ceil(new_principal / old_base)
        new_monthly = old_base + new_principal * r  # 新首月月供

    return max(new_term, 1), round(new_monthly, 2)


def calc_reduce_payment(
    remaining_principal: float,
    prepay_amount: float,
    annual_rate: float,
    remaining_term: int,
    repayment_method: str,
) -> Tuple[int, float]:
    """减少月供：期数不变，计算新月供。返回 (剩余期数, 新月供)"""
    new_principal = remaining_principal - prepay_amount
    r = annual_rate / 100 / 12

    if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
        if r == 0:
            new_monthly = new_principal / remaining_term
        else:
            new_monthly = new_principal * r * (1 + r) ** remaining_term / ((1 + r) ** remaining_term - 1)
    else:
        base = new_principal / remaining_term
        new_monthly = base + new_principal * r  # 新首月

    return remaining_term, round(new_monthly, 2)


def calc_interest_saved(
    remaining_principal: float,
    prepay_amount: float,
    annual_rate: float,
    remaining_term: int,
    repayment_method: str,
    method: str,
) -> float:
    """计算提前还款节省的利息"""
    r = annual_rate / 100 / 12

    # 原方案剩余总利息
    if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
        if r == 0:
            original_total_interest = 0
        else:
            monthly = remaining_principal * r * (1 + r) ** remaining_term / ((1 + r) ** remaining_term - 1)
            original_total_interest = monthly * remaining_term - remaining_principal
    else:
        base = remaining_principal / remaining_term
        original_total_interest = sum(
            (remaining_principal - i * base) * r for i in range(remaining_term)
        )

    # 新方案剩余总利息
    new_principal = remaining_principal - prepay_amount
    if method == PrepaymentMethod.SHORTEN_TERM.value:
        # 先算出原月供
        if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
            if r == 0:
                old_mp = remaining_principal / remaining_term
            else:
                old_mp = remaining_principal * r * (1 + r) ** remaining_term / ((1 + r) ** remaining_term - 1)
            new_term, _ = calc_shorten_term(
                remaining_principal, prepay_amount, annual_rate,
                old_mp, repayment_method,
            )
            new_total_interest = old_mp * new_term - new_principal
        else:
            # 等额本金：计算原首月月供，然后调用 calc_shorten_term
            if r == 0:
                old_mp = remaining_principal / remaining_term
            else:
                old_base = remaining_principal / remaining_term
                old_mp = old_base + remaining_principal * r
            new_term, new_monthly_first = calc_shorten_term(
                remaining_principal, prepay_amount, annual_rate,
                old_mp, repayment_method,
            )
            base = new_principal / new_term
            new_total_interest = sum(
                (new_principal - i * base) * r for i in range(new_term)
            )
    else:
        new_term = remaining_term
        if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
            if r == 0:
                new_monthly = new_principal / new_term
            else:
                new_monthly = new_principal * r * (1 + r) ** new_term / ((1 + r) ** new_term - 1)
            new_total_interest = new_monthly * new_term - new_principal
        else:
            base = new_principal / new_term
            new_total_interest = sum(
                (new_principal - i * base) * r for i in range(new_term)
            )

    saved = original_total_interest - new_total_interest
    return round(max(saved, 0), 2)


def apply_prepayment(
    plan_id: str,
    schedule: pd.DataFrame,
    prepay_period: int,
    prepay_amount: float,
    method: str,
    annual_rate: float,
    repayment_method: str,
    start_date: date,
    repayment_day: int,
) -> Tuple[pd.DataFrame, Dict]:
    """
    执行提前还款：保留已还部分，从提前还款点重新生成后续计划。
    返回 (新完整还款计划, 提前还款记录信息)
    """
    # 已还部分保留
    paid_part = schedule[schedule["period"] < prepay_period].copy()

    # 找到提前还款前的剩余本金
    if prepay_period == 1:
        remaining_before = schedule.iloc[0]["remaining_principal"] + schedule.iloc[0]["principal"]
    else:
        prev = schedule[schedule["period"] == prepay_period - 1]
        if prev.empty:
            prev = schedule[schedule["period"] < prepay_period].iloc[-1:]
        remaining_before = float(prev.iloc[0]["remaining_principal"])

    remaining_after = remaining_before - prepay_amount
    old_remaining_term = len(schedule) - prepay_period + 1

    # 旧月供
    current_row = schedule[schedule["period"] == prepay_period]
    old_monthly = float(current_row.iloc[0]["monthly_payment"]) if not current_row.empty else 0

    if method == PrepaymentMethod.SHORTEN_TERM.value:
        new_term, new_monthly = calc_shorten_term(
            remaining_before, prepay_amount, annual_rate,
            old_monthly, repayment_method,
        )
        new_monthly = old_monthly  # 缩短年限保持月供不变
    else:
        new_term, new_monthly = calc_reduce_payment(
            remaining_before, prepay_amount, annual_rate,
            old_remaining_term, repayment_method,
        )

    interest_saved = calc_interest_saved(
        remaining_before, prepay_amount, annual_rate,
        old_remaining_term, repayment_method, method,
    )

    # 累计值
    cum_p = float(paid_part["cumulative_principal"].iloc[-1]) if not paid_part.empty else 0
    cum_i = float(paid_part["cumulative_interest"].iloc[-1]) if not paid_part.empty else 0

    # 生成新的后续还款计划
    from utils.date_utils import add_months
    new_start = add_months(start_date, prepay_period - 1)
    new_schedule = generate_schedule(
        plan_id, remaining_after, annual_rate, new_term,
        repayment_method, new_start, repayment_day,
        start_period=prepay_period,
        existing_cumulative_principal=cum_p,
        existing_cumulative_interest=cum_i,
    )

    full_schedule = pd.concat([paid_part, new_schedule], ignore_index=True)

    prepay_info = {
        "remaining_principal_before": round(remaining_before, 2),
        "remaining_principal_after": round(remaining_after, 2),
        "old_term_remaining": old_remaining_term,
        "new_term_remaining": new_term,
        "old_monthly_payment": round(old_monthly, 2),
        "new_monthly_payment": round(new_monthly, 2),
        "interest_saved": interest_saved,
    }

    return full_schedule, prepay_info
