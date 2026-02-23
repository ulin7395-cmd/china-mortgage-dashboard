"""提前还款模拟"""
import streamlit as st
import pandas as pd
from datetime import date

from data_manager.excel_handler import (
    get_all_plans, save_prepayment, get_prepayments,
)
from core.schedule_generator import get_plan_schedule, generate_single_component_schedule
from data_manager.data_validator import validate_prepayment
from core.prepayment import apply_prepayment, apply_combined_prepayment, calc_shorten_term, calc_reduce_payment, calc_interest_saved
from components.forms import render_prepayment_form
from components.charts import create_monthly_payment_line, create_remaining_principal_line, create_multi_schedule_line
from utils.id_generator import generate_prepayment_id
from utils.formatters import fmt_amount, fmt_months
from config.constants import LoanType

st.set_page_config(page_title="提前还款模拟", page_icon="💰", layout="wide")
st.title("💰 提前还款模拟")

# 初始化 session_state
if "prepayment_form_data" not in st.session_state:
    st.session_state.prepayment_form_data = None
if "prepayment_period" not in st.session_state:
    st.session_state.prepayment_period = None
if "prepay_info" not in st.session_state:
    st.session_state.prepay_info = None
if "new_schedule" not in st.session_state:
    st.session_state.new_schedule = None
if "comparison_schedules" not in st.session_state:
    st.session_state.comparison_schedules = None
if "plan_id" not in st.session_state:
    st.session_state.plan_id = None
if "amount" not in st.session_state:
    st.session_state.amount = None
if "method" not in st.session_state:
    st.session_state.method = None

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

# 判断是否是组合贷
is_combined = plan["loan_type"] == LoanType.COMBINED.value

# 如果是组合贷，需要分别计算商贷和公积金的剩余本金
remaining_commercial = None
remaining_provident = None
if is_combined:
    start_date_plan = pd.to_datetime(plan["start_date"]).date() if isinstance(plan["start_date"], str) else plan["start_date"]
    repayment_day = int(plan["repayment_day"])
    term_months = int(plan["term_months"])
    repayment_method = plan["repayment_method"]

    # 获取历史提前还款记录，生成事件感知的 schedule
    prepayments = get_prepayments(plan_id)
    sch_c = generate_single_component_schedule(
        plan, prepayments, "commercial",
        start_date_plan, repayment_day, repayment_method, term_months
    )
    sch_p = generate_single_component_schedule(
        plan, prepayments, "provident",
        start_date_plan, repayment_day, repayment_method, term_months
    )

    # 找到当前期数的剩余本金
    paid_up_to = int(plan.get("paid_up_to_period", 0))
    current_period_estimate = paid_up_to + 1 if paid_up_to > 0 else 1

    def get_remaining_at_period(sch, period):
        if period == 1:
            return float(sch.iloc[0]["remaining_principal"]) + float(sch.iloc[0]["principal"])
        else:
            prev = sch[sch["period"] == period - 1]
            if not prev.empty:
                return float(prev.iloc[0]["remaining_principal"])
            return float(sch.iloc[-1]["remaining_principal"])

    remaining_commercial = get_remaining_at_period(sch_c, current_period_estimate)
    remaining_provident = get_remaining_at_period(sch_p, current_period_estimate)

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

# 使用当前实际执行的利率（考虑利率调整）
annual_rate = float(unpaid.iloc[0]["applied_rate"])

if is_combined:
    st.write(f"**当前期数:** 第 {current_period} 期 | **剩余本金:** 商贷 {fmt_amount(remaining_commercial)} + 公积金 {fmt_amount(remaining_provident)} = 总计 {fmt_amount(remaining_principal)} | **剩余期数:** {remaining_term}期 | **当前月供:** {fmt_amount(current_monthly)}")
else:
    st.write(f"**当前期数:** 第 {current_period} 期 | **剩余本金:** {fmt_amount(remaining_principal)} | **剩余期数:** {remaining_term}期 | **当前月供:** {fmt_amount(current_monthly)}")

st.divider()

# 提前还款表单
form_data = render_prepayment_form(
    remaining_principal,
    is_combined_loan=is_combined,
    remaining_commercial=remaining_commercial,
    remaining_provident=remaining_provident
)

# 如果有新的表单提交，保存到 session_state
if form_data:
    st.session_state.prepayment_form_data = form_data
    st.session_state.plan_id = plan_id

    amount = form_data["amount"]
    method = form_data["method"]
    prepayment_type = form_data.get("prepayment_type")
    amount_commercial = form_data.get("amount_commercial")
    amount_provident = form_data.get("amount_provident")
    prepayment_date = form_data["prepayment_date"]

    valid, msg = validate_prepayment(amount, remaining_principal, method)
    if not valid:
        st.error(msg)
        st.stop()

    # 根据用户选择的日期找到生效期数
    schedule["due_date_dt"] = pd.to_datetime(schedule["due_date"])
    eff_rows = schedule[schedule["due_date_dt"] >= pd.Timestamp(prepayment_date)]
    if eff_rows.empty:
        st.error("提前还款日期超出还款计划范围。")
        st.stop()

    prepayment_period = int(eff_rows.iloc[0]["period"])
    st.session_state.prepayment_period = prepayment_period
    st.session_state.amount = amount
    st.session_state.method = method

    st.subheader("模拟结果")

    # 根据 prepayment_period 重新计算当前状态
    prepay_row = schedule[schedule["period"] == prepayment_period]
    if prepay_row.empty:
        prepay_row = unpaid.iloc[0:1]
    else:
        prepay_row = prepay_row.iloc[0:1]

    calc_remaining_principal = float(prepay_row.iloc[0]["remaining_principal"]) + float(prepay_row.iloc[0]["principal"])
    calc_remaining_term = len(schedule) - prepayment_period + 1
    calc_current_monthly = float(prepay_row.iloc[0]["monthly_payment"])
    calc_annual_rate = float(prepay_row.iloc[0]["applied_rate"])

    st.write(f"**提前还款日:** {prepayment_date} | **对应期数:** 第 {prepayment_period} 期 | **届时剩余本金:** {fmt_amount(calc_remaining_principal)}")

    if is_combined:
        # 组合贷只显示一种方式（根据选择的method）
        st.info("组合贷提前还款已分别计算商贷和公积金部分")
        if prepayment_type == "commercial":
            st.write(f"提前还商贷: {fmt_amount(amount_commercial)}")
        elif prepayment_type == "provident":
            st.write(f"提前还公积金: {fmt_amount(amount_provident)}")
        else:
            st.write(f"同时还商贷: {fmt_amount(amount_commercial)} + 公积金: {fmt_amount(amount_provident)}")
    else:
        # 两种方式对比
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 缩短年限")
            new_term_s, new_monthly_s = calc_shorten_term(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_current_monthly, plan["repayment_method"],
            )
            saved_s = calc_interest_saved(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_remaining_term, plan["repayment_method"], "shorten_term",
            )
            st.metric("新剩余期数", fmt_months(new_term_s), delta=f"-{calc_remaining_term - new_term_s}期")
            st.metric("月供不变", fmt_amount(calc_current_monthly))
            st.metric("节省利息", fmt_amount(saved_s))

        with col2:
            st.markdown("#### 减少月供")
            new_term_r, new_monthly_r = calc_reduce_payment(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_remaining_term, plan["repayment_method"],
            )
            saved_r = calc_interest_saved(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_remaining_term, plan["repayment_method"], "reduce_payment",
            )
            st.metric("期数不变", fmt_months(new_term_r))
            st.metric("新月供", fmt_amount(new_monthly_r), delta=f"{new_monthly_r - calc_current_monthly:,.2f} 元")
            st.metric("节省利息", fmt_amount(saved_r))

    st.divider()

    # 预览新还款计划
    st.subheader("预览新还款计划（与原计划对比）")
    start_date = pd.to_datetime(plan["start_date"]).date() if isinstance(plan["start_date"], str) else plan["start_date"]

    if is_combined and prepayment_type is not None:
        # 组合贷提前还款：传入事件感知的 schedule
        amount_c = amount_commercial or 0.0
        amount_p = amount_provident or 0.0
        new_schedule, prepay_info = apply_combined_prepayment(
            plan_id, plan, schedule, prepayment_period,
            prepayment_type, amount_c, amount_p, method,
            start_date, int(plan["repayment_day"]),
            sch_c_current=sch_c, sch_p_current=sch_p,
        )
    else:
        # 普通贷款提前还款
        new_schedule, prepay_info = apply_prepayment(
            plan_id, schedule, prepayment_period, amount, method,
            calc_annual_rate, plan["repayment_method"],
            start_date, int(plan["repayment_day"]),
        )

    # 保存到 session_state
    st.session_state.new_schedule = new_schedule
    st.session_state.prepay_info = prepay_info

    # 准备对比数据
    comparison_schedules = {
        "原计划": schedule,
        "提前还款后": new_schedule,
    }
    st.session_state.comparison_schedules = comparison_schedules

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
            "prepayment_period": prepayment_period,
            "amount": amount,
            "method": method,
            **prepay_info,
        }
        save_prepayment(prepay_record)

        st.success("提前还款已确认，还款计划已更新！")
        # 清除 session_state
        for key in ["prepayment_form_data", "prepayment_period", "prepay_info",
                    "new_schedule", "comparison_schedules", "plan_id", "amount", "method"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# 如果 session_state 中有数据但没有新表单提交（即点击了确认按钮后的重新运行）
elif st.session_state.prepayment_form_data is not None and st.session_state.plan_id == plan_id:
    # 从 session_state 恢复数据
    form_data = st.session_state.prepayment_form_data
    prepayment_period = st.session_state.prepayment_period
    prepay_info = st.session_state.prepay_info
    new_schedule = st.session_state.new_schedule
    comparison_schedules = st.session_state.comparison_schedules
    amount = st.session_state.amount
    method = st.session_state.method

    prepayment_date = form_data["prepayment_date"]
    prepayment_type = form_data.get("prepayment_type")

    # 重新计算显示需要的数据
    prepay_row = schedule[schedule["period"] == prepayment_period]
    if prepay_row.empty:
        prepay_row = unpaid.iloc[0:1]
    else:
        prepay_row = prepay_row.iloc[0:1]

    calc_remaining_principal = float(prepay_row.iloc[0]["remaining_principal"]) + float(prepay_row.iloc[0]["principal"])
    calc_remaining_term = len(schedule) - prepayment_period + 1
    calc_current_monthly = float(prepay_row.iloc[0]["monthly_payment"])

    st.subheader("模拟结果")
    st.write(f"**提前还款日:** {prepayment_date} | **对应期数:** 第 {prepayment_period} 期 | **届时剩余本金:** {fmt_amount(calc_remaining_principal)}")

    if is_combined:
        st.info("组合贷提前还款已分别计算商贷和公积金部分")
        amount_commercial = form_data.get("amount_commercial")
        amount_provident = form_data.get("amount_provident")
        if prepayment_type == "commercial":
            st.write(f"提前还商贷: {fmt_amount(amount_commercial)}")
        elif prepayment_type == "provident":
            st.write(f"提前还公积金: {fmt_amount(amount_provident)}")
        else:
            st.write(f"同时还商贷: {fmt_amount(amount_commercial)} + 公积金: {fmt_amount(amount_provident)}")
    else:
        # 两种方式对比
        col1, col2 = st.columns(2)
        calc_annual_rate = float(prepay_row.iloc[0]["applied_rate"])

        with col1:
            st.markdown("#### 缩短年限")
            new_term_s, new_monthly_s = calc_shorten_term(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_current_monthly, plan["repayment_method"],
            )
            saved_s = calc_interest_saved(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_remaining_term, plan["repayment_method"], "shorten_term",
            )
            st.metric("新剩余期数", fmt_months(new_term_s), delta=f"-{calc_remaining_term - new_term_s}期")
            st.metric("月供不变", fmt_amount(calc_current_monthly))
            st.metric("节省利息", fmt_amount(saved_s))

        with col2:
            st.markdown("#### 减少月供")
            new_term_r, new_monthly_r = calc_reduce_payment(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_remaining_term, plan["repayment_method"],
            )
            saved_r = calc_interest_saved(
                calc_remaining_principal, amount, calc_annual_rate,
                calc_remaining_term, plan["repayment_method"], "reduce_payment",
            )
            st.metric("期数不变", fmt_months(new_term_r))
            st.metric("新月供", fmt_amount(new_monthly_r), delta=f"{new_monthly_r - calc_current_monthly:,.2f} 元")
            st.metric("节省利息", fmt_amount(saved_r))

    st.divider()
    st.subheader("预览新还款计划（与原计划对比）")

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
            "prepayment_period": prepayment_period,
            "amount": amount,
            "method": method,
            **prepay_info,
        }
        save_prepayment(prepay_record)

        st.success("提前还款已确认，还款计划已更新！")
        # 清除 session_state
        for key in ["prepayment_form_data", "prepayment_period", "prepay_info",
                    "new_schedule", "comparison_schedules", "plan_id", "amount", "method"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
