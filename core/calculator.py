"""核心计算：等额本息、等额本金、IRR、组合贷"""
import math
from datetime import date
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
from scipy import optimize

from config.constants import RepaymentMethod, LoanType, REPAYMENT_SCHEDULE_COLUMNS
from utils.date_utils import get_due_date


def calc_equal_installment(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> Tuple[float, float]:
    """等额本息：返回 (月供, 总利息)"""
    if annual_rate == 0:
        monthly = principal / term_months
        return round(monthly, 2), 0.0
    r = annual_rate / 100 / 12
    monthly = principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)
    total_interest = monthly * term_months - principal
    return round(monthly, 2), round(total_interest, 2)


def calc_equal_principal_first_month(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> Tuple[float, float]:
    """等额本金：返回 (首月月供, 总利息)"""
    if annual_rate == 0:
        monthly = principal / term_months
        return round(monthly, 2), 0.0
    r = annual_rate / 100 / 12
    base_principal = principal / term_months
    first_interest = principal * r
    first_monthly = base_principal + first_interest
    total_interest = sum(
        (principal - i * base_principal) * r for i in range(term_months)
    )
    return round(first_monthly, 2), round(total_interest, 2)


def generate_schedule(
    plan_id: str,
    principal: float,
    annual_rate: float,
    term_months: int,
    repayment_method: str,
    start_date: date,
    repayment_day: int = 1,
    start_period: int = 1,
    existing_cumulative_principal: float = 0.0,
    existing_cumulative_interest: float = 0.0,
) -> pd.DataFrame:
    """生成还款计划表"""
    r = annual_rate / 100 / 12
    records = []
    remaining = principal
    cum_principal = existing_cumulative_principal
    cum_interest = existing_cumulative_interest

    if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
        if r == 0:
            monthly_payment = principal / term_months
        else:
            monthly_payment = principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)
    else:
        base_principal = principal / term_months

    for i in range(term_months):
        period = start_period + i
        due = get_due_date(start_date, i + 1, repayment_day)

        if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
            interest = remaining * r if r > 0 else 0
            prin = monthly_payment - interest
            payment = monthly_payment
        else:
            interest = remaining * r if r > 0 else 0
            prin = base_principal
            payment = prin + interest

        # 最后一期尾差调整
        if i == term_months - 1:
            prin = remaining
            interest = payment - prin if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value else remaining * r
            payment = prin + interest

        remaining -= prin
        if remaining < 0.005:
            remaining = 0.0

        cum_principal += prin
        cum_interest += interest

        records.append({
            "plan_id": plan_id,
            "period": period,
            "due_date": due.strftime("%Y-%m-%d"),
            "monthly_payment": round(payment, 2),
            "principal": round(prin, 2),
            "interest": round(interest, 2),
            "remaining_principal": round(remaining, 2),
            "cumulative_principal": round(cum_principal, 2),
            "cumulative_interest": round(cum_interest, 2),
            "applied_rate": annual_rate,
            "is_paid": False,
            "actual_pay_date": None,
        })

    return pd.DataFrame(records, columns=REPAYMENT_SCHEDULE_COLUMNS)


def generate_combined_schedule(
    plan_id: str,
    commercial_amount: float,
    provident_amount: float,
    commercial_rate: float,
    provident_rate: float,
    term_months: int,
    repayment_method: str,
    start_date: date,
    repayment_day: int = 1,
) -> pd.DataFrame:
    """组合贷还款计划：两部分独立计算后合并"""
    sch_c = generate_schedule(
        plan_id, commercial_amount, commercial_rate,
        term_months, repayment_method, start_date, repayment_day,
    )
    sch_p = generate_schedule(
        plan_id, provident_amount, provident_rate,
        term_months, repayment_method, start_date, repayment_day,
    )

    combined = sch_c.copy()
    for col in ["monthly_payment", "principal", "interest",
                "remaining_principal", "cumulative_principal", "cumulative_interest"]:
        combined[col] = sch_c[col] + sch_p[col]

    # 利率显示商贷利率（组合贷利率仅参考）
    combined["applied_rate"] = commercial_rate
    combined = combined.round(2)
    return combined


def calc_irr(principal: float, schedule: pd.DataFrame) -> float:
    """用 IRR 法计算真实年化率"""
    cash_flows = [-principal]
    payments = schedule["monthly_payment"].tolist()
    cash_flows.extend(payments)

    try:
        # numpy_financial 风格的 IRR
        def npv(rate):
            return sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))

        monthly_irr = optimize.brentq(npv, -0.5, 1.0)
        annual_irr = (1 + monthly_irr) ** 12 - 1
        return round(annual_irr * 100, 4)
    except (ValueError, RuntimeError):
        return 0.0


def calc_remaining_irr(
    remaining_principal: float,
    remaining_schedule: pd.DataFrame,
) -> float:
    """计算剩余部分的真实年化率"""
    if remaining_schedule.empty or remaining_principal <= 0:
        return 0.0
    return calc_irr(remaining_principal, remaining_schedule)
