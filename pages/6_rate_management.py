"""利率管理"""
import streamlit as st
import pandas as pd
from datetime import date

from data_manager.excel_handler import (
    get_all_plans, get_rate_adjustments,
    save_rate_adjustment, get_config, set_config,
)
from core.schedule_generator import get_plan_schedule
from data_manager.data_validator import validate_rate_adjustment
from core.rate_adjustment import apply_rate_adjustment
from config.constants import RateType
from utils.id_generator import generate_adjustment_id
from utils.formatters import fmt_amount, fmt_rate

st.set_page_config(page_title="利率管理", page_icon="📈", layout="wide")
st.title("📈 利率管理")

# LPR 配置
st.subheader("当前 LPR 利率配置")
from config.settings import DEFAULT_LPR_5Y, DEFAULT_PROVIDENT_RATE
current_lpr = get_config("lpr_5y") or str(DEFAULT_LPR_5Y)
current_prov = get_config("provident_rate") or str(DEFAULT_PROVIDENT_RATE)

col1, col2 = st.columns(2)
with col1:
    new_lpr = st.number_input(
        "5年期以上 LPR (%)", value=float(current_lpr),
        step=0.05, format="%.2f", key="lpr_input",
    )
with col2:
    new_prov_rate = st.number_input(
        "公积金贷款利率 (%)", value=float(current_prov),
        step=0.05, format="%.2f", key="prov_rate_input",
    )

if st.button("更新基准利率"):
    set_config("lpr_5y", str(new_lpr), "5年期以上LPR")
    set_config("provident_rate", str(new_prov_rate), "公积金贷款利率")
    st.success("基准利率已更新！")

st.divider()

# 利率调整
st.subheader("新增利率调整")
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

# 调整表单
with st.form("rate_adj_form"):
    c1, c2 = st.columns(2)
    with c1:
        rate_type = st.selectbox(
            "调整类型",
            options=[rt.value for rt in RateType],
            format_func=lambda x: "商贷利率" if x == "commercial" else "公积金利率",
        )
    with c2:
        effective_date = st.date_input("生效日期", value=date.today())

    c3, c4 = st.columns(2)
    with c3:
        lpr_value = st.number_input("LPR 值 (%)", value=float(new_lpr), step=0.05, format="%.2f")
    with c4:
        basis_points = st.number_input("加点 (基点, 1基点=0.01%)", value=0.0, step=5.0)

    new_rate = lpr_value + basis_points / 100
    st.write(f"**新利率:** {new_rate:.2f}% = LPR {lpr_value:.2f}% + {basis_points:.0f} 基点")

    reason = st.text_input("调整原因", value="LPR调整")
    submitted = st.form_submit_button("预览调整效果", width='stretch')

if submitted:
    old_rate = float(plan["commercial_rate"]) if rate_type == "commercial" else float(plan["provident_rate"])
    start_date = pd.to_datetime(plan["start_date"]).date() if isinstance(plan["start_date"], str) else plan["start_date"]

    valid, msg = validate_rate_adjustment(new_rate, effective_date, start_date)
    if not valid:
        st.error(msg)
        st.stop()

    # 找到生效期数
    schedule["due_date_dt"] = pd.to_datetime(schedule["due_date"])
    eff_rows = schedule[schedule["due_date_dt"] >= pd.Timestamp(effective_date)]
    if eff_rows.empty:
        st.error("生效日期超出还款计划范围。")
        st.stop()

    effective_period = int(eff_rows.iloc[0]["period"])

    new_schedule, summary = apply_rate_adjustment(
        plan_id, schedule.drop(columns=["due_date_dt"]),
        effective_period, new_rate,
        plan["repayment_method"], start_date, int(plan["repayment_day"]),
    )

    st.subheader("调整效果预览")
    c1, c2, c3 = st.columns(3)
    c1.metric("利率变化", fmt_rate(new_rate), delta=f"{new_rate - old_rate:+.2f}%")
    c2.metric("月供变化", fmt_amount(summary["new_monthly_payment"]),
              delta=f"{summary['monthly_change']:+,.2f}")
    c3.metric("剩余利息变化", fmt_amount(summary["new_remaining_interest"]),
              delta=f"{summary['interest_change']:+,.2f}")

    if st.button("确认调整并更新计划", type="primary"):
        # 保存调整记录
        adj_record = {
            "adjustment_id": generate_adjustment_id(),
            "plan_id": plan_id,
            "effective_date": effective_date.strftime("%Y-%m-%d"),
            "effective_period": effective_period,
            "rate_type": rate_type,
            "old_rate": old_rate,
            "new_rate": new_rate,
            "lpr_value": lpr_value,
            "basis_points": basis_points,
            "reason": reason,
        }
        save_rate_adjustment(adj_record)

        st.success("利率调整已确认！")
        st.rerun()

# 历史调整记录
st.divider()
st.subheader("历史利率调整记录")
adjustments = get_rate_adjustments(plan_id)
if adjustments.empty:
    st.info("暂无利率调整记录。")
else:
    display = adjustments.copy()
    col_map = {
        "effective_date": "生效日期",
        "rate_type": "类型",
        "old_rate": "旧利率(%)",
        "new_rate": "新利率(%)",
        "lpr_value": "LPR(%)",
        "basis_points": "加点",
        "reason": "原因",
    }
    display_cols = [c for c in col_map if c in display.columns]
    display = display[display_cols].rename(columns=col_map)
    if "类型" in display.columns:
        display["类型"] = display["类型"].map({"commercial": "商贷", "provident": "公积金"}).fillna(display["类型"])
    st.dataframe(display, width='stretch')
