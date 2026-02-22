from datetime import date
from dateutil.relativedelta import relativedelta


def add_months(d: date, months: int) -> date:
    """日期加 N 个月"""
    return d + relativedelta(months=months)


def get_due_date(start_date: date, period: int, repayment_day: int) -> date:
    """计算第 period 期的还款日"""
    target = start_date + relativedelta(months=period)
    # 确保还款日不超过当月最大天数
    import calendar
    max_day = calendar.monthrange(target.year, target.month)[1]
    day = min(repayment_day, max_day)
    return target.replace(day=day)


def months_between(d1: date, d2: date) -> int:
    """计算两个日期之间的月数（向上取整）"""
    delta = relativedelta(d2, d1)
    return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
