from datetime import date
from typing import Tuple

from config.constants import LoanType, RepaymentMethod, PrepaymentMethod
from config.settings import DEFAULT_PROVIDENT_LIMIT


def validate_loan_plan(
    plan_name: str,
    loan_type: str,
    total_amount: float,
    commercial_amount: float,
    provident_amount: float,
    term_months: int,
    repayment_method: str,
    commercial_rate: float,
    provident_rate: float,
    start_date: date,
    repayment_day: int,
    provident_limit: float = DEFAULT_PROVIDENT_LIMIT,
) -> Tuple[bool, str]:
    """校验贷款方案输入，返回 (是否合法, 错误信息)"""
    if not plan_name or not plan_name.strip():
        return False, "方案名称不能为空"

    if loan_type not in [e.value for e in LoanType]:
        return False, f"无效的贷款类型: {loan_type}"

    if repayment_method not in [e.value for e in RepaymentMethod]:
        return False, f"无效的还款方式: {repayment_method}"

    if total_amount <= 0:
        return False, "贷款总额必须大于0"

    if term_months <= 0 or term_months > 360:
        return False, "贷款期限必须在1-360个月之间"

    if not 1 <= repayment_day <= 28:
        return False, "还款日必须在1-28之间"

    if loan_type == LoanType.COMMERCIAL.value:
        if commercial_rate <= 0:
            return False, "商贷利率必须大于0"
    elif loan_type == LoanType.PROVIDENT.value:
        if provident_rate <= 0:
            return False, "公积金利率必须大于0"
        # provident_amount 是元，provident_limit 是万元，需要转换
        if provident_amount > provident_limit * 10000:
            return False, f"公积金贷款金额超过上限 {provident_limit} 万元"
    elif loan_type == LoanType.COMBINED.value:
        if commercial_rate <= 0:
            return False, "商贷利率必须大于0"
        if provident_rate <= 0:
            return False, "公积金利率必须大于0"
        if commercial_amount <= 0:
            return False, "组合贷的商贷金额必须大于0"
        if provident_amount <= 0:
            return False, "组合贷的公积金金额必须大于0"
        if abs(commercial_amount + provident_amount - total_amount) > 0.01:
            return False, "商贷金额 + 公积金金额必须等于总金额"
        # provident_amount 是元，provident_limit 是万元，需要转换
        if provident_amount > provident_limit * 10000:
            return False, f"公积金贷款金额超过上限 {provident_limit} 万元"

    return True, ""


def validate_prepayment(
    amount: float,
    remaining_principal: float,
    method: str,
) -> Tuple[bool, str]:
    """校验提前还款输入"""
    if amount <= 0:
        return False, "提前还款金额必须大于0"

    if amount >= remaining_principal:
        return False, "提前还款金额必须小于剩余本金（如需全额还清请使用结清功能）"

    if method not in [e.value for e in PrepaymentMethod]:
        return False, f"无效的提前还款方式: {method}"

    return True, ""


def validate_rate_adjustment(
    new_rate: float,
    effective_date: date,
    start_date: date,
) -> Tuple[bool, str]:
    """校验利率调整输入"""
    if new_rate <= 0 or new_rate > 20:
        return False, "利率必须在0-20%之间"

    if effective_date <= start_date:
        return False, "生效日期必须在贷款起始日之后"

    return True, ""
