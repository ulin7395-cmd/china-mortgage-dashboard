"""提前还款计算"""
import math
from datetime import date
from typing import Dict, Tuple, Optional

import pandas as pd

from config.constants import RepaymentMethod, PrepaymentMethod, LoanType
from core.calculator import generate_schedule, calc_equal_installment, generate_combined_schedule


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
        if repayment_method == RepaymentMethod.EQUAL_INSTALLMENT.value:
            new_monthly = old_monthly  # 等额本息缩短年限保持月供不变
        # 等额本金的 new_monthly 就是 calc_shorten_term 返回的首月月供
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


def split_combined_schedule(schedule: pd.DataFrame, plan_id: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    从组合贷合并的 schedule 中反推商贷和公积金各自的剩余本金。
    注意：这只是近似值，真实拆分需要初始参数分别计算。

    返回：(商贷剩余本金估算, 公积金剩余本金估算)
    """
    # 组合贷的真实拆分需要初始的商贷和公积金金额、利率分别计算
    # 这里只是辅助函数，用于估算
    # 实际使用时，应该从 plan 中获取初始参数重新生成
    return pd.DataFrame(), pd.DataFrame()


def apply_combined_prepayment(
    plan_id: str,
    plan: pd.Series,
    schedule: pd.DataFrame,
    prepay_period: int,
    prepay_type: str,  # "commercial" / "provident" / "both"
    amount_commercial: float,
    amount_provident: float,
    method: str,
    start_date: date,
    repayment_day: int,
) -> Tuple[pd.DataFrame, Dict]:
    """
    组合贷提前还款：分别处理商贷和公积金部分，然后合并

    Args:
        plan_id: 方案ID
        plan: 贷款方案 Series（需要包含 commercial_amount, provident_amount, commercial_rate, provident_rate 等）
        schedule: 当前合并的还款计划
        prepay_period: 提前还款期数
        prepay_type: 还款类型 "commercial"/"provident"/"both"
        amount_commercial: 商贷提前还款金额
        amount_provident: 公积金提前还款金额
        method: 提前还款方式 "shorten_term"/"reduce_payment"
        start_date: 贷款起始日期
        repayment_day: 还款日

    Returns:
        (新合并计划, 汇总信息)
    """
    from core.calculator import generate_schedule

    # 已还部分保留
    paid_part = schedule[schedule["period"] < prepay_period].copy()

    # 先分别获取到 prepay_period 时的商贷和公积金状态
    # 方法：重新生成两部分到 prepay_period 前的计划
    commercial_principal_initial = float(plan["commercial_amount"])
    provident_principal_initial = float(plan["provident_amount"])
    commercial_rate = float(plan["commercial_rate"])
    provident_rate = float(plan["provident_rate"])
    repayment_method = plan["repayment_method"]
    term_months = int(plan["term_months"])

    # 1. 生成商贷完整计划，取到 prepay_period 时的状态
    sch_c_full = generate_schedule(
        plan_id + "_c", commercial_principal_initial, commercial_rate, term_months,
        repayment_method, start_date, repayment_day
    )
    # 2. 生成公积金完整计划
    sch_p_full = generate_schedule(
        plan_id + "_p", provident_principal_initial, provident_rate, term_months,
        repayment_method, start_date, repayment_day
    )

    # 3. 找到 prepay_period 时的剩余本金
    if prepay_period == 1:
        rem_before_c = float(sch_c_full.iloc[0]["remaining_principal"]) + float(sch_c_full.iloc[0]["principal"])
        rem_before_p = float(sch_p_full.iloc[0]["remaining_principal"]) + float(sch_p_full.iloc[0]["principal"])
    else:
        prev_c = sch_c_full[sch_c_full["period"] == prepay_period - 1]
        prev_p = sch_p_full[sch_p_full["period"] == prepay_period - 1]
        rem_before_c = float(prev_c.iloc[0]["remaining_principal"]) if not prev_c.empty else 0
        rem_before_p = float(prev_p.iloc[0]["remaining_principal"]) if not prev_p.empty else 0

    # 4. 对商贷部分提前还款（如果需要）
    sch_c_result = None
    info_c = {}
    if prepay_type in ["commercial", "both"] and amount_commercial > 0:
        sch_c_result, info_c = apply_prepayment(
            plan_id + "_c", sch_c_full, prepay_period, amount_commercial,
            method, commercial_rate, repayment_method, start_date, repayment_day
        )
    else:
        sch_c_result = sch_c_full.copy()
        info_c = {"interest_saved": 0, "new_monthly_payment": 0}

    # 5. 对公积金部分提前还款（如果需要）
    sch_p_result = None
    info_p = {}
    if prepay_type in ["provident", "both"] and amount_provident > 0:
        sch_p_result, info_p = apply_prepayment(
            plan_id + "_p", sch_p_full, prepay_period, amount_provident,
            method, provident_rate, repayment_method, start_date, repayment_day
        )
    else:
        sch_p_result = sch_p_full.copy()
        info_p = {"interest_saved": 0, "new_monthly_payment": 0}

    # 6. 合并两个计划 - 按 period 对齐合并
    # 创建 period 到数据的映射
    c_by_period = {row["period"]: row for _, row in sch_c_result.iterrows()}
    p_by_period = {row["period"]: row for _, row in sch_p_result.iterrows()}

    all_periods = sorted(set(list(c_by_period.keys()) + list(p_by_period.keys())))

    # 合并记录
    combined_records = []
    for period in all_periods:
        c_row = c_by_period.get(period)
        p_row = p_by_period.get(period)

        if c_row is not None and p_row is not None:
            # 两部分都有数据，直接合并
            record = c_row.copy()
            for col in ["monthly_payment", "principal", "interest",
                        "remaining_principal", "cumulative_principal", "cumulative_interest"]:
                record[col] = c_row[col] + p_row[col]
        elif c_row is not None:
            # 只有商贷有数据（公积金已还清）
            record = c_row.copy()
        else:
            # 只有公积金有数据（商贷已还清）
            record = p_row.copy()

        combined_records.append(record)

    combined = pd.DataFrame(combined_records)
    combined["applied_rate"] = commercial_rate
    combined = combined.round(2)
    combined["plan_id"] = plan_id

    # 7. 汇总信息
    total_rem_before = rem_before_c + rem_before_p
    total_rem_after = (rem_before_c - amount_commercial) + (rem_before_p - amount_provident)
    total_saved = info_c.get("interest_saved", 0) + info_p.get("interest_saved", 0)

    # 计算新月供（首月）
    row_c = sch_c_result[sch_c_result["period"] == prepay_period]
    row_p = sch_p_result[sch_p_result["period"] == prepay_period]
    old_monthly = 0
    new_monthly = 0
    if not row_c.empty:
        old_monthly += float(sch_c_full[sch_c_full["period"] == prepay_period].iloc[0]["monthly_payment"])
        new_monthly += float(row_c.iloc[0]["monthly_payment"])
    if not row_p.empty:
        old_monthly += float(sch_p_full[sch_p_full["period"] == prepay_period].iloc[0]["monthly_payment"])
        new_monthly += float(row_p.iloc[0]["monthly_payment"])

    old_term_remaining = term_months - prepay_period + 1
    new_term_remaining = max(len(sch_c_result), len(sch_p_result)) - prepay_period + 1

    prepay_info = {
        "remaining_principal_before": round(total_rem_before, 2),
        "remaining_principal_after": round(total_rem_after, 2),
        "old_term_remaining": old_term_remaining,
        "new_term_remaining": new_term_remaining,
        "old_monthly_payment": round(old_monthly, 2),
        "new_monthly_payment": round(new_monthly, 2),
        "interest_saved": round(total_saved, 2),
        "prepayment_type": prepay_type,
        "amount_commercial": round(amount_commercial, 2),
        "amount_provident": round(amount_provident, 2),
        "interest_saved_commercial": round(info_c.get("interest_saved", 0), 2),
        "interest_saved_provident": round(info_p.get("interest_saved", 0), 2),
    }

    return combined, prepay_info
