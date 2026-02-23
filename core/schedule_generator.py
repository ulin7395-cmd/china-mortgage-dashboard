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


def _mark_is_paid_by_date(schedule: pd.DataFrame) -> pd.DataFrame:
    """根据 due_date <= today 自动标记 is_paid"""
    today = date.today()
    schedule["is_paid"] = pd.to_datetime(schedule["due_date"]).dt.date <= today
    return schedule


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

    # ========== 组合贷特殊处理：分别维护商贷和公积金两个独立 schedule ==========
    if loan_type == LoanType.COMBINED.value:
        from core.calculator import generate_schedule

        # 生成初始独立计划
        sch_c = generate_schedule(
            plan_id + "_c", commercial_principal, commercial_rate, term_months,
            repayment_method, start_date, repayment_day
        )
        sch_p = generate_schedule(
            plan_id + "_p", provident_principal, provident_rate, term_months,
            repayment_method, start_date, repayment_day
        )

        # 依次应用事件到两个独立 schedule
        for event in events:
            event_period = event["period"]

            max_len = max(len(sch_c), len(sch_p))
            if event_period < 1 or event_period > max_len:
                continue

            if event["type"] == "prepayment":
                pp = event["data"]
                prepayment_type = pp.get("prepayment_type")
                method = pp["method"]

                if prepayment_type in ["commercial", "both"]:
                    amount_c = float(pp.get("amount_commercial", 0))
                    if amount_c > 0:
                        sch_c, _ = apply_prepayment(
                            plan_id + "_c", sch_c, event_period, amount_c, method,
                            commercial_rate, repayment_method, start_date, repayment_day
                        )

                if prepayment_type in ["provident", "both"]:
                    amount_p = float(pp.get("amount_provident", 0))
                    if amount_p > 0:
                        sch_p, _ = apply_prepayment(
                            plan_id + "_p", sch_p, event_period, amount_p, method,
                            provident_rate, repayment_method, start_date, repayment_day
                        )

        # 最后合并两个 schedule
        c_by_period = {row["period"]: row for _, row in sch_c.iterrows()}
        p_by_period = {row["period"]: row for _, row in sch_p.iterrows()}
        all_periods = sorted(set(list(c_by_period.keys()) + list(p_by_period.keys())))

        combined_records = []
        for period in all_periods:
            c_row = c_by_period.get(period)
            p_row = p_by_period.get(period)

            if c_row is not None and p_row is not None:
                record = c_row.copy()
                for col in ["monthly_payment", "principal", "interest",
                            "remaining_principal", "cumulative_principal", "cumulative_interest"]:
                    record[col] = c_row[col] + p_row[col]
            elif c_row is not None:
                record = c_row.copy()
            else:
                record = p_row.copy()

            combined_records.append(record)

        schedule = pd.DataFrame(combined_records)
        schedule["applied_rate"] = commercial_rate
        schedule = schedule.round(2)
        schedule["plan_id"] = plan_id

        _mark_is_paid_by_date(schedule)
        return schedule

    # ========== 普通贷款处理 ==========
    # 第一步：生成初始计划
    schedule = generate_schedule(
        plan_id, principal, annual_rate, term_months,
        repayment_method, start_date, repayment_day,
    )

    # 依次应用事件
    for event in events:
        event_period = event["period"]

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

            # 普通贷款提前还款
            current_row = schedule[schedule["period"] == event_period]
            applied_rate = float(current_row.iloc[0]["applied_rate"]) if not current_row.empty else annual_rate
            schedule, _ = apply_prepayment(
                plan_id, schedule, event_period, prepay_amount, method,
                applied_rate, repayment_method, start_date, repayment_day,
            )

    _mark_is_paid_by_date(schedule)
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


def generate_single_component_schedule(
    plan: pd.Series,
    prepayments: pd.DataFrame,
    which: str,
    start_date: date,
    repayment_day: int,
    repayment_method: str,
    term_months: int,
) -> pd.DataFrame:
    """为组合贷的某一部分生成完整 schedule，应用所有相关的提前还款事件

    Args:
        plan: 贷款方案 Series
        prepayments: 提前还款记录 DataFrame
        which: "commercial" 或 "provident"
        start_date: 起始日期
        repayment_day: 还款日
        repayment_method: 还款方式
        term_months: 贷款期数
    """
    if which == "commercial":
        principal = float(plan["commercial_amount"])
        rate = float(plan["commercial_rate"])
        suffix = "_c"
        target_types = ["commercial", "both"]
        amount_key = "amount_commercial"
    else:
        principal = float(plan["provident_amount"])
        rate = float(plan["provident_rate"])
        suffix = "_p"
        target_types = ["provident", "both"]
        amount_key = "amount_provident"

    plan_id = plan["plan_id"]

    sch = generate_schedule(
        plan_id + suffix, principal, rate, term_months,
        repayment_method, start_date, repayment_day
    )

    if not prepayments.empty:
        relevant_pp = prepayments[
            prepayments["prepayment_type"].isin(target_types)
        ].copy()

        if not relevant_pp.empty:
            relevant_pp = relevant_pp.sort_values("prepayment_period")

            for _, pp in relevant_pp.iterrows():
                event_period = int(pp["prepayment_period"])
                amount = float(pp.get(amount_key, 0))
                method = pp["method"]

                if event_period < 1 or event_period > len(sch):
                    continue

                if amount > 0:
                    sch, _ = apply_prepayment(
                        plan_id + suffix, sch, event_period, amount, method,
                        rate, repayment_method, start_date, repayment_day
                    )

    _mark_is_paid_by_date(sch)
    return sch
