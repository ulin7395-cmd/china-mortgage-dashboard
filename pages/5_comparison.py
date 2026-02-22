"""方案对比"""
import streamlit as st
import pandas as pd
from datetime import date

from data_manager.excel_handler import get_all_plans, get_repayment_schedule
from core.comparison import compare_plans, compare_repayment_methods
from core.inflation import adjust_for_inflation, calc_real_cost
from components.charts import (
    create_comparison_bar, create_multi_schedule_line,
    create_separate_principal_interest_lines,
)
from components.tables import render_comparison_table
from utils.formatters import fmt_amount

st.set_page_config(page_title="方案对比", page_icon="⚖️", layout="wide")
st.title("⚖️ 方案对比")

plans = get_all_plans()
if plans.empty or len(plans) < 1:
    st.info("请先创建至少一个贷款方案。")
    st.stop()

tab_plans, tab_methods = st.tabs(["方案横向对比", "等额本息 vs 等额本金"])

with tab_plans:
    plan_names = plans["plan_name"].tolist()
    selected = st.multiselect(
        "选择对比方案（2-4个）", plan_names,
        default=plan_names[:min(2, len(plan_names))],
    )

    if len(selected) < 2:
        st.warning("请至少选择2个方案进行对比。")
    else:
        selected_plans = plans[plans["plan_name"].isin(selected)]
        plan_list = selected_plans.to_dict("records")

        schedules = {}
        for p in plan_list:
            sch = get_repayment_schedule(p["plan_id"])
            if not sch.empty:
                for col in ["monthly_payment", "principal", "interest", "remaining_principal",
                            "cumulative_principal", "cumulative_interest"]:
                    sch[col] = pd.to_numeric(sch[col], errors="coerce").fillna(0)
                schedules[p["plan_id"]] = sch

        comp_df = compare_plans(plan_list, schedules)
        if not comp_df.empty:
            st.subheader("关键指标对比")
            render_comparison_table(comp_df)

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                fig_bar = create_comparison_bar(comp_df)
                st.plotly_chart(fig_bar, width='stretch')

            with col2:
                named_schedules = {}
                for p in plan_list:
                    if p["plan_id"] in schedules:
                        named_schedules[p["plan_name"]] = schedules[p["plan_id"]]

                fig_line = create_multi_schedule_line(
                    named_schedules, "monthly_payment", "月供对比", "金额(元)"
                )
                st.plotly_chart(fig_line, width='stretch')

            # 剩余本金对比
            fig_rem = create_multi_schedule_line(
                named_schedules, "remaining_principal", "剩余本金对比", "剩余本金(元)"
            )
            st.plotly_chart(fig_rem, width='stretch')

            st.divider()
            st.subheader("每期本金与利息对比")

            # 本金和利息分开对比（折线图）
            fig_pi = create_separate_principal_interest_lines(
                named_schedules, "各方案每期本金与利息对比"
            )
            st.plotly_chart(fig_pi, width='stretch')

            # 通胀调整
            st.divider()
            st.subheader("通胀调整后的实际成本")
            inflation_rate = st.slider("年通胀率(%)", 0.0, 10.0, 2.5, 0.1)

            for p in plan_list:
                if p["plan_id"] in schedules:
                    sch = schedules[p["plan_id"]]
                    total_payment = sch["monthly_payment"].sum()
                    total_interest = sch["interest"].sum()
                    term = len(sch)
                    real = calc_real_cost(total_payment, total_interest, term, inflation_rate)
                    with st.expander(f"**{p['plan_name']}**"):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("名义总还款", fmt_amount(real["nominal_total_payment"]))
                        c2.metric("实际购买力", fmt_amount(real["real_total_payment_pv"]))
                        c3.metric("通胀侵蚀", fmt_amount(real["inflation_erosion"]))

with tab_methods:
    st.subheader("等额本息 vs 等额本金 快速对比")

    c1, c2, c3 = st.columns(3)
    with c1:
        comp_amount = st.number_input("贷款金额(元)", value=1000000.0, step=10000.0, key="comp_amt")
    with c2:
        comp_rate = st.number_input("年利率(%)", value=3.45, step=0.01, format="%.2f", key="comp_rate")
    with c3:
        comp_years = st.number_input("贷款年限", value=30, min_value=1, max_value=30, key="comp_years")

    if st.button("开始对比", type="primary"):
        result = compare_repayment_methods(
            comp_amount, comp_rate, comp_years * 12, date.today(),
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 等额本息")
            ei = result["equal_installment"]
            st.metric("月供(固定)", fmt_amount(ei["月供(固定)"]))
            st.metric("总利息", fmt_amount(ei["总利息"]))
            st.metric("总还款额", fmt_amount(ei["总还款额"]))

        with col2:
            st.markdown("#### 等额本金")
            ep = result["equal_principal"]
            st.metric("首月月供", fmt_amount(ep["首月月供"]))
            st.metric("末月月供", fmt_amount(ep["末月月供"]))
            st.metric("总利息", fmt_amount(ep["总利息"]))
            st.metric("总还款额", fmt_amount(ep["总还款额"]))

        st.success(f"等额本金比等额本息少付利息: **{fmt_amount(result['利息差额'])}**")

        # 月供对比图
        named = {
            "等额本息": result["equal_installment"]["schedule"],
            "等额本金": result["equal_principal"]["schedule"],
        }
        fig = create_multi_schedule_line(named, "monthly_payment", "月供对比", "金额(元)")
        st.plotly_chart(fig, width='stretch')

        # 本金和利息对比图
        fig_pi = create_separate_principal_interest_lines(named, "本金与利息对比")
        st.plotly_chart(fig_pi, width='stretch')

        fig2 = create_multi_schedule_line(named, "remaining_principal", "剩余本金对比", "剩余本金(元)")
        st.plotly_chart(fig2, width='stretch')
