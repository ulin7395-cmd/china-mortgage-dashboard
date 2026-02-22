"""提前还款测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
import pytest
from core.calculator import generate_schedule
from core.prepayment import (
    calc_shorten_term,
    calc_reduce_payment,
    calc_interest_saved,
    apply_prepayment,
)
from config.constants import RepaymentMethod, PrepaymentMethod


class TestShortenTerm:
    def test_term_reduced(self):
        new_term, _ = calc_shorten_term(
            remaining_principal=800000,
            prepay_amount=200000,
            annual_rate=3.45,
            old_monthly_payment=4462,
            repayment_method=RepaymentMethod.EQUAL_INSTALLMENT.value,
        )
        # 还了20万后缩短年限，新期数应小于原期数
        assert new_term < 360
        assert new_term > 0


class TestReducePayment:
    def test_payment_reduced(self):
        term, new_monthly = calc_reduce_payment(
            remaining_principal=800000,
            prepay_amount=200000,
            annual_rate=3.45,
            remaining_term=300,
            repayment_method=RepaymentMethod.EQUAL_INSTALLMENT.value,
        )
        assert term == 300  # 期数不变
        # 新月供应更低（因为本金减少了）
        # 原月供 800000的300期月供
        r = 3.45 / 100 / 12
        old_monthly = 800000 * r * (1 + r) ** 300 / ((1 + r) ** 300 - 1)
        assert new_monthly < old_monthly


class TestInterestSaved:
    def test_positive_savings(self):
        saved = calc_interest_saved(
            remaining_principal=800000,
            prepay_amount=200000,
            annual_rate=3.45,
            remaining_term=300,
            repayment_method=RepaymentMethod.EQUAL_INSTALLMENT.value,
            method=PrepaymentMethod.SHORTEN_TERM.value,
        )
        assert saved > 0

    def test_shorten_saves_more(self):
        """缩短年限通常比减少月供节省更多利息"""
        saved_shorten = calc_interest_saved(
            800000, 200000, 3.45, 300,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            PrepaymentMethod.SHORTEN_TERM.value,
        )
        saved_reduce = calc_interest_saved(
            800000, 200000, 3.45, 300,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            PrepaymentMethod.REDUCE_PAYMENT.value,
        )
        assert saved_shorten >= saved_reduce

    def test_equal_principal_shorten_term_no_error(self):
        """等额本金+缩短年限场景不应抛出 UnboundLocalError"""
        saved = calc_interest_saved(
            remaining_principal=800000,
            prepay_amount=200000,
            annual_rate=3.45,
            remaining_term=300,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL.value,
            method=PrepaymentMethod.SHORTEN_TERM.value,
        )
        assert saved > 0


class TestApplyPrepayment:
    def test_schedule_updated(self):
        sch = generate_schedule(
            "test", 1_000_000, 3.45, 360,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            date(2024, 1, 1),
        )
        new_sch, info = apply_prepayment(
            "test", sch, 13, 200000,
            PrepaymentMethod.SHORTEN_TERM.value,
            3.45, RepaymentMethod.EQUAL_INSTALLMENT.value,
            date(2024, 1, 1), 1,
        )
        # 新计划应比原计划短
        assert len(new_sch) < len(sch)
        assert info["remaining_principal_after"] < info["remaining_principal_before"]
        assert info["interest_saved"] > 0
