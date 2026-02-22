"""指标卡片组件"""
import streamlit as st

from utils.formatters import fmt_amount, fmt_percent, fmt_months, fmt_rate


def render_overview_metrics(
    total_amount: float,
    current_monthly: float,
    paid_ratio: float,
    remaining_months: int,
    total_interest: float,
    paid_principal: float,
):
    """渲染概览指标卡片"""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("贷款总额", fmt_amount(total_amount))
    with c2:
        st.metric("当前月供", fmt_amount(current_monthly))
    with c3:
        st.metric("已还比例", fmt_percent(paid_ratio))
    with c4:
        st.metric("剩余期数", fmt_months(remaining_months))

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("总利息", fmt_amount(total_interest))
    with c6:
        st.metric("已还本金", fmt_amount(paid_principal))
    with c7:
        st.metric("利息占比", fmt_percent(total_interest / (total_amount + total_interest)) if total_amount + total_interest > 0 else "0%")
    with c8:
        st.metric("已还期数", f"{int((1 - remaining_months / (remaining_months + paid_ratio * remaining_months / (1 - paid_ratio))) * 100) if paid_ratio < 1 and paid_ratio > 0 else 0}期" if paid_ratio > 0 else "0期")


def render_plan_summary_metrics(plan: dict, schedule_stats: dict):
    """渲染单个方案的摘要指标"""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("贷款总额", fmt_amount(plan["total_amount"]))
        st.metric("贷款利率", fmt_rate(plan.get("commercial_rate", 0)))
    with c2:
        st.metric("月供", fmt_amount(schedule_stats.get("current_monthly", 0)))
        st.metric("总利息", fmt_amount(schedule_stats.get("total_interest", 0)))
    with c3:
        st.metric("已还期数", f"{schedule_stats.get('paid_periods', 0)}期")
        st.metric("剩余期数", f"{schedule_stats.get('remaining_periods', 0)}期")
