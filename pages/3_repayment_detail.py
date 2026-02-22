"""还款明细"""
import streamlit as st
import pandas as pd

from data_manager.excel_handler import get_all_plans, get_repayment_schedule, mark_period_paid
from components.tables import render_repayment_table
from components.charts import create_stacked_area, create_remaining_principal_line
from core.calculator import calc_remaining_irr
from utils.formatters import fmt_amount, fmt_percent, fmt_rate

st.set_page_config(page_title="还款明细", page_icon="📄", layout="wide")
st.title("📄 还款明细")

plans = get_all_plans()
if plans.empty:
    st.info("暂无贷款方案，请先创建。")
    st.stop()

plan_names = plans["plan_name"].tolist()
plan_ids = plans["plan_id"].tolist()

selected_name = st.selectbox("选择方案", plan_names)
plan_id = plan_ids[plan_names.index(selected_name)]
plan = plans[plans["plan_id"] == plan_id].iloc[0]

schedule = get_repayment_schedule(plan_id)
if schedule.empty:
    st.warning("该方案暂无还款计划。")
    st.stop()

# 确保数值类型
for col in ["monthly_payment", "principal", "interest", "remaining_principal",
            "cumulative_principal", "cumulative_interest"]:
    if col in schedule.columns:
        schedule[col] = pd.to_numeric(schedule[col], errors="coerce").fillna(0)

schedule["is_paid"] = schedule["is_paid"].astype(bool)

# 统计
total_amount = float(plan["total_amount"])
paid_mask = schedule["is_paid"] == True
paid_principal = schedule.loc[paid_mask, "principal"].sum()
paid_interest = schedule.loc[paid_mask, "interest"].sum()
unpaid_principal = schedule.loc[~paid_mask, "principal"].sum()
unpaid_interest = schedule.loc[~paid_mask, "interest"].sum()
total_interest = schedule["interest"].sum()

paid_periods = int(paid_mask.sum())
total_periods = len(schedule)

st.subheader("还款统计")
c1, c2, c3, c4 = st.columns(4)
c1.metric("已还本金", fmt_amount(paid_principal))
c2.metric("已还利息", fmt_amount(paid_interest))
c3.metric("未还本金", fmt_amount(unpaid_principal))
c4.metric("未还利息", fmt_amount(unpaid_interest))

c5, c6, c7, c8 = st.columns(4)
c5.metric("已还占比", fmt_percent(paid_principal / total_amount) if total_amount > 0 else "0%")
c6.metric("利息占总还款", fmt_percent(total_interest / (total_amount + total_interest)) if total_amount + total_interest > 0 else "0%")
c7.metric("已还期数", f"{paid_periods}/{total_periods}")

# 剩余 IRR
remaining_schedule = schedule[~paid_mask]
remaining_principal = float(remaining_schedule.iloc[0]["remaining_principal"] + remaining_schedule.iloc[0]["principal"]) if not remaining_schedule.empty else 0
remaining_irr = calc_remaining_irr(remaining_principal, remaining_schedule)
c8.metric("剩余年化率(IRR)", fmt_rate(remaining_irr))

st.divider()

# 标记已还
st.subheader("标记还款")
unpaid_periods = schedule[~paid_mask]["period"].tolist()
if unpaid_periods:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        mark_up_to = st.selectbox(
            "标记已还至第N期",
            options=unpaid_periods,
            index=0,
        )
    with col_b:
        st.write("")
        st.write("")
        if st.button("确认标记", type="primary"):
            for p in range(1, int(mark_up_to) + 1):
                mark_period_paid(plan_id, p)
            st.success(f"已标记至第 {mark_up_to} 期")
            st.rerun()
else:
    st.success("所有期数均已还清！")

st.divider()

# 还款计划表
st.subheader("还款计划表")
show_all = st.checkbox("显示全部", value=False)
render_repayment_table(schedule, show_all=show_all)
