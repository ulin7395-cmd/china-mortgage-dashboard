"""方案对比计算"""
from typing import List, Dict

import pandas as pd

from core.calculator import calc_equal_installment, calc_equal_principal_first_month, calc_irr, generate_schedule
from core.inflation import adjust_for_inflation
from config.constants import RepaymentMethod
from datetime import date


def compare_plans(plans: List[Dict], schedules: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    对比多个方案的关键指标。
    plans: 方案字典列表
    schedules: {plan_id: schedule_df}
    返回对比表 DataFrame
    """
    rows = []
    for plan in plans:
        pid = plan["plan_id"]
        sch = schedules.get(pid, pd.DataFrame())

        total_amount = plan["total_amount"]
        term_months = plan["term_months"]

        if sch.empty:
            continue

        total_payment = sch["monthly_payment"].sum()
        total_interest = sch["interest"].sum()
        first_monthly = float(sch.iloc[0]["monthly_payment"])
        last_monthly = float(sch.iloc[-1]["monthly_payment"])
        avg_monthly = sch["monthly_payment"].mean()
        irr = calc_irr(total_amount, sch)

        rows.append({
            "方案名称": plan["plan_name"],
            "贷款类型": plan["loan_type"],
            "贷款总额": total_amount,
            "贷款期限(月)": term_months,
            "还款方式": plan["repayment_method"],
            "首月月供": round(first_monthly, 2),
            "末月月供": round(last_monthly, 2),
            "平均月供": round(avg_monthly, 2),
            "总还款额": round(total_payment, 2),
            "总利息": round(total_interest, 2),
            "利息占比": round(total_interest / total_payment * 100, 2) if total_payment > 0 else 0,
            "真实年化率(%)": irr,
        })

    return pd.DataFrame(rows)


def compare_repayment_methods(
    principal: float,
    annual_rate: float,
    term_months: int,
    start_date: date,
    plan_id: str = "compare",
) -> Dict:
    """对比等额本息 vs 等额本金"""
    ei_monthly, ei_total_interest = calc_equal_installment(principal, annual_rate, term_months)
    ep_first, ep_total_interest = calc_equal_principal_first_month(principal, annual_rate, term_months)

    sch_ei = generate_schedule(plan_id + "_ei", principal, annual_rate, term_months,
                               RepaymentMethod.EQUAL_INSTALLMENT.value, start_date)
    sch_ep = generate_schedule(plan_id + "_ep", principal, annual_rate, term_months,
                               RepaymentMethod.EQUAL_PRINCIPAL.value, start_date)

    return {
        "equal_installment": {
            "月供(固定)": ei_monthly,
            "总利息": ei_total_interest,
            "总还款额": round(ei_monthly * term_months, 2),
            "schedule": sch_ei,
        },
        "equal_principal": {
            "首月月供": ep_first,
            "末月月供": round(float(sch_ep.iloc[-1]["monthly_payment"]), 2),
            "总利息": ep_total_interest,
            "总还款额": round(sch_ep["monthly_payment"].sum(), 2),
            "schedule": sch_ep,
        },
        "利息差额": round(ei_total_interest - ep_total_interest, 2),
    }
