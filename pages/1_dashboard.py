"""主仪表盘"""
import streamlit as st
import pandas as pd

from config.constants import LoanType
from config.settings import COLORS
from data_manager.excel_handler import get_all_plans, get_repayment_schedule, get_prepayments, get_rate_adjustments
from components.charts import (
    create_principal_interest_pie, create_monthly_payment_line,
    create_stacked_area, create_remaining_principal_line, create_cumulative_chart,
)
from utils.formatters import fmt_amount, fmt_percent, fmt_months, fmt_rate
from core.calculator import calc_irr, generate_schedule

st.set_page_config(page_title="主仪表盘", page_icon="📊", layout="wide")
st.title("📊 主仪表盘")

plans = get_all_plans()
active_plans = plans[plans["status"] == "active"] if not plans.empty and "status" in plans.columns else plans

if plans.empty or active_plans.empty:
    st.info("暂无贷款方案，请先在「贷款方案管理」中创建方案。")
    st.stop()

# 选择方案
plan_names = active_plans["plan_name"].tolist()
plan_ids = active_plans["plan_id"].tolist()

selected_name = st.selectbox("选择方案", plan_names)
selected_idx = plan_names.index(selected_name)
plan_id = plan_ids[selected_idx]
plan = active_plans[active_plans["plan_id"] == plan_id].iloc[0]

# 获取综合还款计划
combined_schedule = get_repayment_schedule(plan_id)

if combined_schedule.empty:
    st.warning("该方案暂无还款计划数据。")
    st.stop()

# 确保数值类型
for col in ["monthly_payment", "principal", "interest", "remaining_principal",
            "cumulative_principal", "cumulative_interest"]:
    combined_schedule[col] = pd.to_numeric(combined_schedule[col], errors="coerce").fillna(0)

combined_schedule["is_paid"] = combined_schedule["is_paid"].astype(bool)

# 根据贷款类型处理数据
is_combined = plan["loan_type"] == LoanType.COMBINED.value

# 准备数据模块
schedules = {}
schedule_titles = {}

if is_combined:
    # 组合贷：重新生成商贷和公积金各自的计划
    from datetime import datetime
    start_date = pd.to_datetime(plan["start_date"]).date()
    repayment_day = int(plan["repayment_day"])
    term_months = int(plan["term_months"])
    repayment_method = plan["repayment_method"]

    # 生成商贷部分
    commercial_schedule = generate_schedule(
        plan_id,
        float(plan["commercial_amount"]),
        float(plan["commercial_rate"]),
        term_months,
        repayment_method,
        start_date,
        repayment_day,
    )
    # 同步已还状态
    commercial_schedule["is_paid"] = combined_schedule["is_paid"]

    # 生成公积金部分
    provident_schedule = generate_schedule(
        plan_id,
        float(plan["provident_amount"]),
        float(plan["provident_rate"]),
        term_months,
        repayment_method,
        start_date,
        repayment_day,
    )
    # 同步已还状态
    provident_schedule["is_paid"] = combined_schedule["is_paid"]

    schedules["commercial"] = commercial_schedule
    schedule_titles["commercial"] = "商业贷款"
    schedules["provident"] = provident_schedule
    schedule_titles["provident"] = "公积金贷款"
    schedules["combined"] = combined_schedule
    schedule_titles["combined"] = "综合汇总"
else:
    # 单一贷款类型
    schedules["single"] = combined_schedule
    if plan["loan_type"] == LoanType.COMMERCIAL.value:
        schedule_titles["single"] = "商业贷款"
    elif plan["loan_type"] == LoanType.PROVIDENT.value:
        schedule_titles["single"] = "公积金贷款"
    else:
        schedule_titles["single"] = "贷款详情"


def render_schedule_module(sch: pd.DataFrame, title: str, prefix: str, color: str = None):
    """渲染单个贷款模块的统计和图表"""
    st.subheader(title)

    # 确保数值类型
    for col in ["monthly_payment", "principal", "interest", "remaining_principal",
                "cumulative_principal", "cumulative_interest"]:
        sch[col] = pd.to_numeric(sch[col], errors="coerce").fillna(0)

    sch["is_paid"] = sch["is_paid"].astype(bool)

    # 计算统计数据
    total_principal = sch["principal"].sum()
    total_interest = sch["interest"].sum()
    total_payment = sch["monthly_payment"].sum()

    paid_mask = sch["is_paid"] == True
    paid_principal = sch.loc[paid_mask, "principal"].sum()
    paid_interest = sch.loc[paid_mask, "interest"].sum()
    unpaid_principal = sch.loc[~paid_mask, "principal"].sum()
    unpaid_interest = sch.loc[~paid_mask, "interest"].sum()

    paid_periods = int(paid_mask.sum())
    total_periods = len(sch)
    remaining_periods = total_periods - paid_periods
    paid_ratio = paid_periods / total_periods if total_periods > 0 else 0

    # 当前月供
    unpaid_sch = sch[~paid_mask]
    current_monthly = float(unpaid_sch.iloc[0]["monthly_payment"]) if not unpaid_sch.empty else 0

    # 概览指标
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("贷款总额", fmt_amount(total_principal))
    c2.metric("当前月供", fmt_amount(current_monthly))
    c3.metric("已还比例", fmt_percent(paid_ratio))
    c4.metric("剩余期数", fmt_months(remaining_periods))

    c5, c6, c7 = st.columns(3)
    c5.metric("总利息", fmt_amount(total_interest))
    c6.metric("已还本金", fmt_amount(paid_principal))
    c7.metric("已还利息", fmt_amount(paid_interest))

    # 图表
    col1, col2 = st.columns(2)

    with col1:
        fig_pie = create_principal_interest_pie(
            paid_principal, paid_interest, unpaid_principal, unpaid_interest,
        )
        st.plotly_chart(fig_pie, width='stretch', key=f"{prefix}_pie")

    with col2:
        fig_line = create_monthly_payment_line(sch, [], [])
        st.plotly_chart(fig_line, width='stretch', key=f"{prefix}_line")

    col3, col4 = st.columns(2)

    with col3:
        fig_area = create_stacked_area(sch)
        st.plotly_chart(fig_area, width='stretch', key=f"{prefix}_area")

    with col4:
        fig_remaining = create_remaining_principal_line(sch)
        st.plotly_chart(fig_remaining, width='stretch', key=f"{prefix}_remaining")

    # 累计还款
    fig_cum = create_cumulative_chart(sch)
    st.plotly_chart(fig_cum, width='stretch', key=f"{prefix}_cum")


# 渲染综合概览（仅组合贷显示）
if is_combined:
    st.divider()
    st.header("📊 综合概览")

    # 综合统计
    total_amount = float(plan["total_amount"])
    total_interest = combined_schedule["interest"].sum()

    paid_mask = combined_schedule["is_paid"] == True
    paid_principal = combined_schedule.loc[paid_mask, "principal"].sum()
    paid_interest = combined_schedule.loc[paid_mask, "interest"].sum()

    paid_periods = int(paid_mask.sum())
    total_periods = len(combined_schedule)
    paid_ratio = paid_periods / total_periods if total_periods > 0 else 0

    # 真实年化率
    irr = calc_irr(total_amount, combined_schedule)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("贷款总额", fmt_amount(total_amount))
    c2.metric("总利息", fmt_amount(total_interest))
    c3.metric("已还本金", fmt_amount(paid_principal))
    c4.metric("真实年化率(IRR)", fmt_rate(irr))

# 渲染各模块
for key in schedules:
    st.divider()
    if key == "commercial":
        color = COLORS["commercial"]
    elif key == "provident":
        color = COLORS["provident"]
    else:
        color = None
    render_schedule_module(schedules[key], schedule_titles[key], key, color)
