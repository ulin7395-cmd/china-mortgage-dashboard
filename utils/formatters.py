def fmt_amount(value: float, unit: str = "元") -> str:
    """格式化金额：1234567.89 -> 1,234,567.89 元"""
    if abs(value) >= 1e8:
        return f"{value / 1e8:,.2f} 亿元"
    if abs(value) >= 1e4:
        return f"{value / 1e4:,.2f} 万元"
    return f"{value:,.2f} {unit}"


def fmt_amount_wan(value: float) -> str:
    """格式化为万元"""
    return f"{value / 1e4:,.2f} 万元"


def fmt_rate(value: float) -> str:
    """格式化利率百分比：3.45 -> 3.45%"""
    return f"{value:.2f}%"


def fmt_percent(value: float) -> str:
    """格式化比例：0.3456 -> 34.56%"""
    return f"{value * 100:.2f}%"


def fmt_months(months: int) -> str:
    """格式化月数为年月：36 -> 3年"""
    years = months // 12
    remain = months % 12
    if remain == 0:
        return f"{years}年"
    if years == 0:
        return f"{remain}个月"
    return f"{years}年{remain}个月"
