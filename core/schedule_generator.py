"""
还款计划动态生成器

根据贷款方案基础信息 + 事件历史（利率调整、提前还款）动态生成完整还款计划，
不再存储完整计划到 Excel，保证每次计算的准确性。
"""
from datetime import date
from typing import Optional, Tuple, Dict, List

import pandas as pd

from config.constants import RepaymentMethod, LoanType, REPAYMENT_SCHEDULE_COLUMNS
from core.calculator import generate_schedule, generate_combined_schedule
from core.prepayment import apply_prepayment
from core.rate_adjustment import apply_rate_adjustment


def _parse_date(d) -> Optional[date]:
    """解析日期，支持字符串或 date 对象"""
    if d is None or pd.isna(d):
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return date.fromisoformat(d[:10])
    return None


def generate_plan_schedule_from_events(
    plan: pd.Series,
    prepayments: Optional[pd.DataFrame] = None,
    rate_adjustments: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    根据贷款方案和事件历史动态生成完整还款计划

    Args:
        plan: 贷款方案 Series，包含所有必要字段
        prepayments: 提前还款记录 DataFrame
        rate_adjustments: 利率调整记录 DataFrame

    Returns:
        完整的还款计划 DataFrame
    """
    # 解析基础参数
    plan_id = plan["plan_id"]
    loan_type = plan["loan_type"]
    repayment_method = plan["repayment_method"]
    start_date = _parse_date(plan["start_date"])
    repayment_day = int(plan.get("repayment_day", 1))

    # 初始本金和利率
    if loan_type == LoanType.COMBINED.value:
        commercial_principal = float(plan["commercial_amount"])
        provident_principal = float(plan["provident_amount"])
        commercial_rate = float(plan["commercial_rate"])
        provident_rate = float(plan["provident_rate"])
        principal = commercial_principal + provident_principal
        annual_rate = commercial_rate  # 组合贷默认用商贷利率
    elif loan_type == LoanType.PROVIDENT.value:
        principal = float(plan["provident_amount"])
        annual_rate = float(plan["provident_rate"])
    else:
        principal = float(plan["commercial_amount"])
        annual_rate = float(plan["commercial_rate"])

    term_months = int(plan["term_months"])

    # 第一步：生成初始计划
    if loan_type == LoanType.COMBINED.value:
        schedule = generate_combined_schedule(
            plan_id,
            commercial_principal, provident_principal,
            commercial_rate, provident_rate,
            term_months, repayment_method,
            start_date, repayment_day,
        )
    else:
        schedule = generate_schedule(
            plan_id, principal, annual_rate, term_months,
            repayment_method, start_date, repayment_day,
        )

    # 收集所有事件，按期数排序
    events = []

    # 添加利率调整事件
    if rate_adjustments is not None and not rate_adjustments.empty:
        for _, ra in rate_adjustments.iterrows():
            # 兼容旧数据：如果没有 effective_period，暂时跳过
            if "effective_period" not in ra or pd.isna(ra["effective_period"]):
                continue
            events.append({
                "type": "rate_adjustment",
                "period": int(ra["effective_period"]),
                "data": ra,
            })

    # 添加提前还款事件
    if prepayments is not None and not prepayments.empty:
        for _, pp in prepayments.iterrows():
            # 兼容旧数据：如果没有 prepayment_period，暂时跳过
            if "prepayment_period" not in pp or pd.isna(pp["prepayment_period"]):
                continue
            events.append({
                "type": "prepayment",
                "period": int(pp["prepayment_period"]),
                "data": pp,
            })

    # 按期数排序事件
    events.sort(key=lambda e: e["period"])

    # 依次应用事件
    for event in events:
        event_period = event["period"]

        # 跳过已还完的期数
        if event_period < 1 or event_period > len(schedule):
            continue

        if event["type"] == "rate_adjustment":
            ra = event["data"]
            new_rate = float(ra["new_rate"])
            schedule, _ = apply_rate_adjustment(
                plan_id, schedule, event_period, new_rate,
                repayment_method, start_date, repayment_day,
            )
        elif event["type"] == "prepayment":
            pp = event["data"]
            prepay_amount = float(pp["amount"])
            method = pp["method"]
            # 获取当前执行时的利率
            current_row = schedule[schedule["period"] == event_period]
            applied_rate = float(current_row.iloc[0]["applied_rate"]) if not current_row.empty else annual_rate
            schedule, _ = apply_prepayment(
                plan_id, schedule, event_period, prepay_amount, method,
                applied_rate, repayment_method, start_date, repayment_day,
            )

    # 标记已还期数
    paid_up_to = int(plan.get("paid_up_to_period", 0))
    if paid_up_to > 0:
        schedule.loc[schedule["period"] <= paid_up_to, "is_paid"] = True

    return schedule


def get_plan_schedule(plan_id: str) -> pd.DataFrame:
    """
    从数据存储读取方案信息和事件历史，动态生成还款计划

    这是替代 get_repayment_schedule 的新入口函数

    Args:
        plan_id: 贷款方案 ID

    Returns:
        动态生成的完整还款计划 DataFrame
    """
    from data_manager.excel_handler import (
        get_plan_by_id, get_prepayments, get_rate_adjustments,
    )

    plan = get_plan_by_id(plan_id)
    if plan is None:
        return pd.DataFrame(columns=REPAYMENT_SCHEDULE_COLUMNS)

    prepayments = get_prepayments(plan_id)
    rate_adjustments = get_rate_adjustments(plan_id)

    return generate_plan_schedule_from_events(plan, prepayments, rate_adjustments)
