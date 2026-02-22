"""通胀调整计算"""
import pandas as pd

from config.settings import DEFAULT_INFLATION_RATE


def adjust_for_inflation(
    schedule: pd.DataFrame,
    annual_inflation_rate: float = DEFAULT_INFLATION_RATE,
) -> pd.DataFrame:
    """将还款计划中的金额折算为当前购买力"""
    df = schedule.copy()
    monthly_rate = annual_inflation_rate / 100 / 12

    periods = df["period"].values
    discount_factors = [(1 + monthly_rate) ** (-p) for p in periods]

    df["real_monthly_payment"] = (df["monthly_payment"] * discount_factors).round(2)
    df["real_principal"] = (df["principal"] * discount_factors).round(2)
    df["real_interest"] = (df["interest"] * discount_factors).round(2)
    df["discount_factor"] = [round(f, 6) for f in discount_factors]

    return df


def calc_real_cost(
    total_payment: float,
    total_interest: float,
    term_months: int,
    annual_inflation_rate: float = DEFAULT_INFLATION_RATE,
) -> dict:
    """计算考虑通胀后的实际成本"""
    monthly_rate = annual_inflation_rate / 100 / 12

    # 名义总还款额的现值
    # 简化：假设等额还款
    avg_monthly = total_payment / term_months if term_months > 0 else 0
    pv = sum(avg_monthly / (1 + monthly_rate) ** i for i in range(1, term_months + 1))

    nominal_rate = total_interest / (total_payment - total_interest) * 100 if total_payment > total_interest else 0
    real_rate = ((1 + nominal_rate / 100) / (1 + annual_inflation_rate / 100) - 1) * 100

    return {
        "nominal_total_payment": round(total_payment, 2),
        "real_total_payment_pv": round(pv, 2),
        "inflation_erosion": round(total_payment - pv, 2),
        "erosion_ratio": round((total_payment - pv) / total_payment * 100, 2) if total_payment > 0 else 0,
        "nominal_interest_rate": round(nominal_rate, 2),
        "real_interest_rate": round(real_rate, 2),
    }
