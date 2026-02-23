"""主仪表盘"""
import streamlit as st
import pandas as pd

from config.constants import LoanType
from config.settings import COLORS
from data_manager.excel_handler import get_all_plans, get_prepayments
from core.schedule_generator import get_plan_schedule, generate_single_component_schedule
from components.charts import (
    create_principal_interest_pie, create_monthly_payment_line,
    create_stacked_area, create_remaining_principal_line, create_cumulative_chart,
)
from utils.formatters import fmt_amount, fmt_percent, fmt_months


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
combined_schedule = get_plan_schedule(plan_id)

if combined_schedule.empty:
    st.warning("该方案暂无还款计划数据。")
    st.stop()

# 确保数值类型
for col in ["monthly_payment", "principal", "interest", "remaining_principal",
            "cumulative_principal", "cumulative_interest"]:
    combined_schedule[col] = pd.to_numeric(combined_schedule[col], errors="coerce").fillna(0)

combined_schedule["is_paid"] = combined_schedule["is_paid"].astype(bool)

# 获取提前还款记录，用于图表标注
prepayments = get_prepayments(plan_id)
prepayment_periods = []
if not prepayments.empty:
    prepayment_periods = prepayments["prepayment_period"].astype(int).tolist()

# 根据贷款类型处理数据
is_combined = plan["loan_type"] == LoanType.COMBINED.value

# 准备数据模块
schedules = {}
schedule_titles = {}

if is_combined:
    # 组合贷：分别生成商贷、公积金、综合三个schedule
    from datetime import datetime
    start_date = pd.to_datetime(plan["start_date"]).date()
    repayment_day = int(plan["repayment_day"])
    term_months = int(plan["term_months"])
    repayment_method = plan["repayment_method"]

    # 分别生成带提前还款事件的商贷和公积金schedule
    commercial_schedule = generate_single_component_schedule(
        plan, prepayments, "commercial",
        start_date, repayment_day, repayment_method, term_months
    )
    provident_schedule = generate_single_component_schedule(
        plan, prepayments, "provident",
        start_date, repayment_day, repayment_method, term_months
    )

    schedules["combined"] = combined_schedule
    schedule_titles["combined"] = "综合汇总"
    schedules["commercial"] = commercial_schedule
    schedule_titles["commercial"] = "商业贷款"
    schedules["provident"] = provident_schedule
    schedule_titles["provident"] = "公积金贷款"
else:
    # 单一贷款类型
    schedules["single"] = combined_schedule
    if plan["loan_type"] == LoanType.COMMERCIAL.value:
        schedule_titles["single"] = "商业贷款"
    elif plan["loan_type"] == LoanType.PROVIDENT.value:
        schedule_titles["single"] = "公积金贷款"
    else:
        schedule_titles["single"] = "贷款详情"


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sum_prepayment_amount(prepayments: pd.DataFrame, scope: str) -> float:
    if prepayments is None or prepayments.empty:
        return 0.0
    df = prepayments.copy()
    if "prepayment_type" not in df.columns:
        df["prepayment_type"] = "both"
    df["prepayment_type"] = df["prepayment_type"].replace({"combined": "both"}).fillna("both")

    if scope == "commercial":
        df = df[df["prepayment_type"].isin(["commercial", "both"])]
        if "amount_commercial" in df.columns:
            return df["amount_commercial"].apply(_to_float).sum()
        return df["amount"].apply(_to_float).sum() if "amount" in df.columns else 0.0
    if scope == "provident":
        df = df[df["prepayment_type"].isin(["provident", "both"])]
        if "amount_provident" in df.columns:
            return df["amount_provident"].apply(_to_float).sum()
        return df["amount"].apply(_to_float).sum() if "amount" in df.columns else 0.0

    if "amount" in df.columns:
        return df["amount"].apply(_to_float).sum()
    total = 0.0
    if "amount_commercial" in df.columns:
        total += df["amount_commercial"].apply(_to_float).sum()
    if "amount_provident" in df.columns:
        total += df["amount_provident"].apply(_to_float).sum()
    return total


def render_schedule_module(
    sch: pd.DataFrame,
    title: str,
    prefix: str,
    color: str = None,
    prepayment_periods: list = None,
    original_principal: float = None,
    prepayments: pd.DataFrame = None,
    scope: str = "combined",
):
    """渲染单个贷款模块的统计和图表"""
    with st.container(border=True):
        st.subheader(title)

        # 获取当前主题
        theme_base = st.get_option("theme.base")
        template = "loan_dashboard_dark" if theme_base == "dark" else "loan_dashboard_light"

        # 确保数值类型
        for col in ["monthly_payment", "principal", "interest", "remaining_principal",
                    "cumulative_principal", "cumulative_interest"]:
            sch[col] = pd.to_numeric(sch[col], errors="coerce").fillna(0)

        sch["is_paid"] = sch["is_paid"].astype(bool)

        # 计算统计数据
        if original_principal is not None:
            total_principal = original_principal
        else:
            if len(sch) > 0:
                total_principal = float(sch.iloc[0]["remaining_principal"]) + float(sch.iloc[0]["principal"])
            else:
                total_principal = 0

        total_interest = sch["interest"].sum()
        
        paid_mask = sch["is_paid"] == True
        paid_principal = sch.loc[paid_mask, "principal"].sum()
        paid_principal += _sum_prepayment_amount(prepayments, scope)
        paid_interest = sch.loc[paid_mask, "interest"].sum()

        if len(sch) > 0 and not paid_mask.all():
            first_unpaid = sch[~paid_mask].iloc[0]
            unpaid_principal = float(first_unpaid["remaining_principal"]) + float(first_unpaid["principal"])
        else:
            unpaid_principal = 0

        unpaid_interest = sch.loc[~paid_mask, "interest"].sum()

        paid_periods = int(paid_mask.sum())
        total_periods = len(sch)
        remaining_periods = total_periods - paid_periods
        paid_ratio = paid_principal / total_principal if total_principal > 0 else 0

        unpaid_sch = sch[~paid_mask]
        current_monthly = float(unpaid_sch.iloc[0]["monthly_payment"]) if not unpaid_sch.empty else 0

        # 概览指标
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("贷款总额", fmt_amount(total_principal))
        c2.metric("当前月供", fmt_amount(current_monthly))
        c3.metric("已还比例", fmt_percent(paid_ratio))
        c4.metric("剩余期数", fmt_months(remaining_periods))

        c5, c6, c7, c8, c9 = st.columns(5)
        c5.metric("总利息", fmt_amount(total_interest))
        c6.metric("已还本金", fmt_amount(paid_principal))
        c7.metric("已还利息", fmt_amount(paid_interest))
        c8.metric("剩余本金", fmt_amount(unpaid_principal))
        c9.metric("剩余利息", fmt_amount(unpaid_interest))

        if prepayment_periods:
            st.info(f"💡 已记录 {len(prepayment_periods)} 次提前还款，发生在第 {', '.join([str(p) for p in prepayment_periods])} 期")

        # 图表
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            fig_pie = create_principal_interest_pie(
                paid_principal, paid_interest, unpaid_principal, unpaid_interest, template=template
            )
            st.plotly_chart(fig_pie, use_container_width=True, key=f"{prefix}_pie")

        with col2:
            fig_line = create_monthly_payment_line(sch, prepayment_periods, [], template=template)
            st.plotly_chart(fig_line, use_container_width=True, key=f"{prefix}_line")

        col3, col4 = st.columns(2)

        with col3:
            fig_area = create_stacked_area(sch, template=template)
            st.plotly_chart(fig_area, use_container_width=True, key=f"{prefix}_area")

        with col4:
            fig_remaining = create_remaining_principal_line(sch, prepayment_periods, template=template)
            st.plotly_chart(fig_remaining, use_container_width=True, key=f"{prefix}_remaining")

        fig_cum = create_cumulative_chart(sch, template=template)
        st.plotly_chart(fig_cum, use_container_width=True, key=f"{prefix}_cum")


# 渲染各模块
for key in schedules:
    st.divider()
    if key == "commercial":
        color = COLORS["commercial"]
        original_principal = float(plan["commercial_amount"])
    elif key == "provident":
        color = COLORS["provident"]
        original_principal = float(plan["provident_amount"])
    elif key == "combined":
        color = None
        original_principal = float(plan["total_amount"])
    else:
        color = None
        original_principal = float(plan["total_amount"])
    render_schedule_module(
        schedules[key],
        schedule_titles[key],
        key,
        color,
        prepayment_periods,
        original_principal,
        prepayments,
        key,
    )
