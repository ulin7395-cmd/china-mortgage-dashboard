"""利率与系统配置"""
import streamlit as st
import pandas as pd
from datetime import date

from data_manager.excel_handler import (
    get_all_plans, get_rate_adjustments,
    save_rate_adjustment, get_config, set_config,
    get_all_config, init_excel,
)
from core.schedule_generator import get_plan_schedule
from data_manager.data_validator import validate_rate_adjustment
from core.rate_adjustment import apply_rate_adjustment
from config.constants import RateType, LoanType
from utils.id_generator import generate_adjustment_id
from utils.formatters import fmt_amount, fmt_rate
from config.settings import DEFAULT_LPR_5Y, DEFAULT_PROVIDENT_RATE, DEFAULT_INFLATION_RATE, DEFAULT_PROVIDENT_LIMIT

st.set_page_config(page_title="利率与系统配置", page_icon="📈", layout="wide")
st.title("📈 利率与系统配置")
init_excel()

tab_rate, tab_settings = st.tabs(["利率管理", "系统配置"])

with tab_rate:
    st.subheader("当前 LPR 利率配置")
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

    if plan["loan_type"] == LoanType.COMBINED.value:
        st.error("⚠️  组合贷暂不支持利率调整功能。\n\n当前架构需要分别处理商贷和公积金部分的利率调整，敬请期待后续更新。")
        st.stop()

    schedule = get_plan_schedule(plan_id)
    if schedule.empty:
        st.warning("暂无还款计划。")
        st.stop()

    for col in ["monthly_payment", "principal", "interest", "remaining_principal"]:
        schedule[col] = pd.to_numeric(schedule[col], errors="coerce").fillna(0)

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

with tab_settings:
    current_lpr = float(get_config("lpr_5y") or DEFAULT_LPR_5Y)
    current_prov_rate = float(get_config("provident_rate") or DEFAULT_PROVIDENT_RATE)
    current_inflation = float(get_config("inflation_rate") or DEFAULT_INFLATION_RATE)
    current_prov_limit = float(get_config("provident_limit") or DEFAULT_PROVIDENT_LIMIT)

    st.info("""
**说明**：在此页面修改的默认值将持久化保存到 Excel 中，新建贷款方案时会自动使用这些值作为默认配置。
""")

    st.divider()

    with st.form("system_settings_form"):
        st.subheader("默认利率配置")

        c1, c2 = st.columns(2)
        with c1:
            new_lpr = st.number_input(
                "5年期以上 LPR (%)",
                min_value=0.0, max_value=20.0,
                value=current_lpr, step=0.05, format="%.2f",
                help="新建贷款方案时使用的默认 LPR 基准利率"
            )
        with c2:
            new_prov_rate = st.number_input(
                "公积金贷款利率 (%)",
                min_value=0.0, max_value=20.0,
                value=current_prov_rate, step=0.05, format="%.2f",
                help="新建贷款方案时使用的默认公积金利率"
            )

        st.subheader("默认参数配置")

        c3, c4 = st.columns(2)
        with c3:
            new_inflation = st.number_input(
                "年通胀率 (%)",
                min_value=-10.0, max_value=50.0,
                value=current_inflation, step=0.1, format="%.1f",
                help="用于通胀分析的默认年通胀率"
            )
        with c4:
            new_prov_limit = st.number_input(
                "公积金贷款上限 (万元)",
                min_value=0.0, max_value=500.0,
                value=current_prov_limit, step=10.0, format="%.1f",
                help="新建组合贷时公积金贷款的上限金额"
            )

        submitted = st.form_submit_button("保存配置", width='stretch', type="primary")

        if submitted:
            set_config("lpr_5y", str(new_lpr), "5年期以上LPR")
            set_config("provident_rate", str(new_prov_rate), "公积金贷款利率")
            set_config("inflation_rate", str(new_inflation), "年通胀率")
            set_config("provident_limit", str(new_prov_limit), "公积金贷款上限(万元)")
            st.success("配置已保存！新建贷款方案时将使用新的默认值。")
            st.rerun()

    st.divider()

    st.subheader("当前配置一览")
    config_df = get_all_config()

    if not config_df.empty:
        display_df = config_df.copy()
        display_df = display_df.rename(columns={
            "key": "配置项",
            "value": "当前值",
            "description": "说明",
            "updated_at": "更新时间"
        })
        st.dataframe(display_df, width='stretch', hide_index=True)
    else:
        st.info("暂无配置数据，使用系统默认值。")
