from enum import Enum


class LoanType(str, Enum):
    COMMERCIAL = "commercial"
    PROVIDENT = "provident"
    COMBINED = "combined"

    @property
    def label(self) -> str:
        return {
            "commercial": "商业贷款",
            "provident": "公积金贷款",
            "combined": "组合贷款",
        }[self.value]


class RepaymentMethod(str, Enum):
    EQUAL_INSTALLMENT = "equal_installment"  # 等额本息
    EQUAL_PRINCIPAL = "equal_principal"  # 等额本金

    @property
    def label(self) -> str:
        return {
            "equal_installment": "等额本息",
            "equal_principal": "等额本金",
        }[self.value]


class PrepaymentMethod(str, Enum):
    SHORTEN_TERM = "shorten_term"  # 缩短年限
    REDUCE_PAYMENT = "reduce_payment"  # 减少月供

    @property
    def label(self) -> str:
        return {
            "shorten_term": "缩短年限",
            "reduce_payment": "减少月供",
        }[self.value]


class RateType(str, Enum):
    COMMERCIAL = "commercial"
    PROVIDENT = "provident"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    @property
    def label(self) -> str:
        return {
            "active": "还款中",
            "completed": "已结清",
            "archived": "已归档",
        }[self.value]


# Sheet 名称
SHEET_LOAN_PLANS = "贷款方案"
SHEET_RATE_ADJUSTMENTS = "利率调整记录"
SHEET_REPAYMENT_SCHEDULE = "还款计划"
SHEET_PREPAYMENTS = "提前还款记录"
SHEET_CONFIG = "系统配置"

# 列定义
LOAN_PLANS_COLUMNS = [
    "plan_id", "plan_name", "loan_type", "total_amount",
    "commercial_amount", "provident_amount", "term_months",
    "repayment_method", "commercial_rate", "provident_rate",
    "start_date", "repayment_day", "status", "notes",
]

RATE_ADJUSTMENTS_COLUMNS = [
    "adjustment_id", "plan_id", "effective_date", "effective_period", "rate_type",
    "old_rate", "new_rate", "lpr_value", "basis_points", "reason",
]

REPAYMENT_SCHEDULE_COLUMNS = [
    "plan_id", "period", "due_date", "monthly_payment",
    "principal", "interest", "remaining_principal",
    "cumulative_principal", "cumulative_interest",
    "applied_rate", "is_paid", "actual_pay_date",
]

PREPAYMENTS_COLUMNS = [
    "prepayment_id", "plan_id", "prepayment_date", "prepayment_period", "amount",
    "method", "remaining_principal_before", "remaining_principal_after",
    "old_term_remaining", "new_term_remaining",
    "old_monthly_payment", "new_monthly_payment", "interest_saved",
]

CONFIG_COLUMNS = ["key", "value", "description", "updated_at"]
