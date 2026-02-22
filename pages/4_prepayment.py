"""提前还款模拟"""
import streamlit as st
import pandas as pd
from datetime import date

from data_manager.excel_handler import (
    get_all_plans, save_prepayment,
)
from core.schedule_generator import get_plan_schedule
from data_manager.data_validator import validate_prepayment
from core.prepayment import apply_prepayment, calc_shorten_term, calc_reduce_payment, calc_interest_saved
from components.forms import render_prepayment_form
from components.charts import create_monthly_payment_line, create_remaining_principal_line, create_multi_schedule_line
from utils.id_generator import generate_prepayment_id
from utils.formatters import fmt_amount, fmt_months

st.set_page_config(page_title="提前还款模拟", page_icon="💰", layout="wide")
st.title("💰 提前还款模拟")

plans = get_all_plans()
active_plans = plans[plans["status"] == "active"] if not plans.empty and "status" in plans.columns else plans

if active_plans.empty:
    st.info("暂无活跃的贷款方案。")
    st.stop()

plan_names = active_plans["plan_name"].tolist()
plan_ids = active_plans["plan_id"].tolist()

selected_name = st.selectbox("选择方案", plan_names)
plan_id = plan_ids[plan_names.index(selected_name)]
plan = active_plans[active_plans["plan_id"] == plan_id].iloc[0]

schedule = get_plan_schedule(plan_id)
if schedule.empty:
    st.warning("暂无还款计划。")
    st.stop()

for col in ["monthly_payment", "principal", "interest", "remaining_principal"]:
    schedule[col] = pd.to_numeric(schedule[col], errors="coerce").fillna(0)
schedule["is_paid"] = schedule["is_paid"].astype(bool)

# 计算当前状态
paid_mask = schedule["is_paid"] == True
unpaid = schedule[~paid_mask]
if unpaid.empty:
    st.success("该方案已全部还清！")
    st.stop()

current_period = int(unpaid.iloc[0]["period"])
remaining_principal = float(unpaid.iloc[0]["remaining_principal"]) + float(unpaid.iloc[0]["principal"])
remaining_term = len(unpaid)
current_monthly = float(unpaid.iloc[0]["monthly_payment"])

annual_rate = float(plan["commercial_rate"]) if plan["loan_type"] != "provident" else float(plan["provident_rate"])

st.write(f"**当前期数:** 第 {current_period} 期 | **剩余本金:** {fmt_amount(remaining_principal)} | **剩余期数:** {remaining_term}期 | **当前月供:** {fmt_amount(current_monthly)}")

st.divider()

# 提前还款表单
form_data = render_prepayment_form(remaining_principal)

if form_data:
    amount = form_data["amount"]
    method = form_data["method"]

    valid, msg = validate_prepayment(amount, remaining_principal, method)
    if not valid:
        st.error(msg)
        st.stop()

    st.subheader("模拟结果")

    # 两种方式对比
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 缩短年限")
        new_term_s, new_monthly_s = calc_shorten_term(
            remaining_principal, amount, annual_rate,
            current_monthly, plan["repayment_method"],
        )
        saved_s = calc_interest_saved(
            remaining_principal, amount, annual_rate,
            remaining_term, plan["repayment_method"], "shorten_term",
        )
        st.metric("新剩余期数", fmt_months(new_term_s), delta=f"-{remaining_term - new_term_s}期")
        st.metric("月供不变", fmt_amount(current_monthly))
        st.metric("节省利息", fmt_amount(saved_s))

    with col2:
        st.markdown("#### 减少月供")
        new_term_r, new_monthly_r = calc_reduce_payment(
            remaining_principal, amount, annual_rate,
            remaining_term, plan["repayment_method"],
        )
        saved_r = calc_interest_saved(
            remaining_principal, amount, annual_rate,
            remaining_term, plan["repayment_method"], "reduce_payment",
        )
        st.metric("期数不变", fmt_months(new_term_r))
        st.metric("新月供", fmt_amount(new_monthly_r), delta=f"{new_monthly_r - current_monthly:,.2f} 元")
        st.metric("节省利息", fmt_amount(saved_r))

    st.divider()

    # 预览新还款计划
    st.subheader("预览新还款计划（与原计划对比）")
    start_date = pd.to_datetime(plan["start_date"]).date() if isinstance(plan["start_date"], str) else plan["start_date"]

    new_schedule, prepay_info = apply_prepayment(
        plan_id, schedule, current_period, amount, method,
        annual_rate, plan["repayment_method"],
        start_date, int(plan["repayment_day"]),
    )

    # 准备对比数据
    comparison_schedules = {
        "原计划": schedule,
        "提前还款后": new_schedule,
    }

    # 月供对比图
    fig_payment = create_multi_schedule_line(
        comparison_schedules,
        y_col="monthly_payment",
        title="月供对比（原计划 vs 提前还款后）",
        y_label="月供金额(元)",
    )
    st.plotly_chart(fig_payment, width='stretch')

    # 剩余本金对比图
    fig_principal = create_multi_schedule_line(
        comparison_schedules,
        y_col="remaining_principal",
        title="剩余本金对比（原计划 vs 提前还款后）",
        y_label="剩余本金(元)",
    )
    st.plotly_chart(fig_principal, width='stretch')

    # 确认执行
    if st.button("确认提前还款并更新计划", type="primary"):
        # 保存提前还款记录
        prepay_record = {
            "prepayment_id": generate_prepayment_id(),
            "plan_id": plan_id,
            "prepayment_date": form_data["prepayment_date"].strftime("%Y-%m-%d"),
            "prepayment_period": current_period,
            "amount": amount,
            "method": method,
            **prepay_info,
        }
        save_prepayment(prepay_record)

        st.success("提前还款已确认，还款计划已更新！")
        st.rerun()
