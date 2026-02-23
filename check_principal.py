"""检查等额本金计算"""
# 直接手动计算验证

principal = 4540000
term = 360

monthly_principal = principal / term
print(f"贷款总额: {principal:,.0f} 元")
print(f"期数: {term} 期")
print(f"每月应还本金: {monthly_principal:,.2f} 元")
print()

# 验证：12611.11 * 360 = 4,540,000 吗？
total = monthly_principal * term
print(f"验证: {monthly_principal:,.2f} × {term} = {total:,.0f}")
print(f"误差: {total - principal:,.2f} 元")
