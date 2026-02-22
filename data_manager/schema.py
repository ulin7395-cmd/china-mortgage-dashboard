from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class LoanPlan:
    plan_id: str
    plan_name: str
    loan_type: str  # commercial / provident / combined
    total_amount: float
    commercial_amount: float
    provident_amount: float
    term_months: int
    repayment_method: str  # equal_installment / equal_principal
    commercial_rate: float
    provident_rate: float
    start_date: date
    repayment_day: int = 1
    status: str = "active"
    notes: str = ""


@dataclass
class RateAdjustment:
    adjustment_id: str
    plan_id: str
    effective_date: date
    rate_type: str  # commercial / provident
    old_rate: float
    new_rate: float
    lpr_value: float = 0.0
    basis_points: float = 0.0
    reason: str = ""


@dataclass
class RepaymentRecord:
    plan_id: str
    period: int
    due_date: date
    monthly_payment: float
    principal: float
    interest: float
    remaining_principal: float
    cumulative_principal: float
    cumulative_interest: float
    applied_rate: float
    is_paid: bool = False
    actual_pay_date: Optional[date] = None


@dataclass
class PrepaymentRecord:
    prepayment_id: str
    plan_id: str
    prepayment_date: date
    amount: float
    method: str  # shorten_term / reduce_payment
    remaining_principal_before: float
    remaining_principal_after: float
    old_term_remaining: int
    new_term_remaining: int
    old_monthly_payment: float
    new_monthly_payment: float
    interest_saved: float


@dataclass
class ConfigEntry:
    key: str
    value: str
    description: str = ""
    updated_at: Optional[datetime] = None
