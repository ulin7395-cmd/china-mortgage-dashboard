"""调试等额本金计算"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.calculator import generate_schedule
from datetime import date

# 测试等额本金
principal = 4540000
rate = 3.1  # 假设利率
term = 360

print(f"测试等额本金: {principal:,.0f}元, {term}期, 年利率{rate}%")
print(f"期望每月本金: {principal / term:,.2f}元")
print()

sch = generate_schedule(
    "test", principal, rate, term,
    "equal_principal", date.today(), 1
)

print("前5期:")
print(sch[["period", "monthly_payment", "principal", "interest", "remaining_principal"]].head())
print()

print(f"第1期本金: {sch.iloc[0]['principal']:,.2f}")
print(f"第2期本金: {sch.iloc[1]['principal']:,.2f}")
print(f"最后1期本金: {sch.iloc[-1]['principal']:,.2f}")
