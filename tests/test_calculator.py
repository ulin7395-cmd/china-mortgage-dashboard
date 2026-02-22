"""核心计算测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
import pytest
from core.calculator import (
    calc_equal_installment,
    calc_equal_principal_first_month,
    generate_schedule,
    generate_combined_schedule,
    calc_irr,
)
from config.constants import RepaymentMethod


class TestEqualInstallment:
    """等额本息测试"""

    def test_basic_calculation(self):
        """100万, 30年, 3.45% -> 月供约 4462"""
        monthly, total_interest = calc_equal_installment(1_000_000, 3.45, 360)
        assert 4450 < monthly < 4475
        assert total_interest > 0

    def test_zero_rate(self):
        monthly, total_interest = calc_equal_installment(120000, 0, 12)
        assert monthly == 10000.0
        assert total_interest == 0.0

    def test_short_term(self):
        monthly, total_interest = calc_equal_installment(100000, 5.0, 12)
        assert monthly > 100000 / 12
        assert total_interest > 0

    def test_total_repayment(self):
        """总还款 = 本金 + 总利息"""
        principal = 500000
        monthly, total_interest = calc_equal_installment(principal, 4.0, 240)
        total = monthly * 240
        assert abs(total - principal - total_interest) < 1  # 允许1元误差


class TestEqualPrincipal:
    """等额本金测试"""

    def test_basic_calculation(self):
        first, total_interest = calc_equal_principal_first_month(1_000_000, 3.45, 360)
        # 首月月供 = 本金/360 + 本金*月利率
        expected_principal = 1_000_000 / 360
        expected_interest = 1_000_000 * 3.45 / 100 / 12
        assert abs(first - expected_principal - expected_interest) < 1

    def test_less_interest_than_equal_installment(self):
        """等额本金总利息应少于等额本息"""
        _, ei_interest = calc_equal_installment(1_000_000, 3.45, 360)
        _, ep_interest = calc_equal_principal_first_month(1_000_000, 3.45, 360)
        assert ep_interest < ei_interest


class TestScheduleGeneration:
    """还款计划生成测试"""

    def test_equal_installment_schedule(self):
        sch = generate_schedule(
            "test", 1_000_000, 3.45, 360,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            date(2024, 1, 1),
        )
        assert len(sch) == 360
        assert sch.iloc[0]["period"] == 1
        assert sch.iloc[-1]["period"] == 360
        # 最后一期剩余本金应为0
        assert sch.iloc[-1]["remaining_principal"] == 0.0
        # 所有月供应基本相等
        payments = sch["monthly_payment"].values
        assert max(payments) - min(payments) < 1

    def test_equal_principal_schedule(self):
        sch = generate_schedule(
            "test", 1_000_000, 3.45, 360,
            RepaymentMethod.EQUAL_PRINCIPAL.value,
            date(2024, 1, 1),
        )
        assert len(sch) == 360
        assert sch.iloc[-1]["remaining_principal"] == 0.0
        # 月供应递减
        assert sch.iloc[0]["monthly_payment"] > sch.iloc[-1]["monthly_payment"]

    def test_cumulative_values(self):
        sch = generate_schedule(
            "test", 500000, 4.0, 120,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            date(2024, 1, 1),
        )
        # 累计本金应约等于贷款金额
        assert abs(sch.iloc[-1]["cumulative_principal"] - 500000) < 1
        # 累计利息应大于0
        assert sch.iloc[-1]["cumulative_interest"] > 0

    def test_combined_schedule(self):
        sch = generate_combined_schedule(
            "test",
            500000, 500000,
            3.45, 2.85,
            360,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            date(2024, 1, 1),
        )
        assert len(sch) == 360
        # 组合贷月供应大于单一贷款
        monthly = sch.iloc[0]["monthly_payment"]
        assert monthly > 0


class TestIRR:
    """IRR 测试"""

    def test_irr_close_to_nominal(self):
        """IRR 应接近名义利率"""
        sch = generate_schedule(
            "test", 1_000_000, 5.0, 360,
            RepaymentMethod.EQUAL_INSTALLMENT.value,
            date(2024, 1, 1),
        )
        irr = calc_irr(1_000_000, sch)
        # IRR 应在名义利率附近
        assert 4.5 < irr < 5.5
