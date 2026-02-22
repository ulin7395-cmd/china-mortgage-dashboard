"""格式化表格组件"""
import pandas as pd
import streamlit as st


def render_repayment_table(schedule: pd.DataFrame, show_all: bool = False):
    """渲染还款计划表格"""
    if schedule.empty:
        st.info("暂无还款计划数据")
        return

    display_df = schedule.copy()

    # 列重命名
    col_map = {
        "period": "期数",
        "due_date": "还款日",
        "monthly_payment": "月供(元)",
        "principal": "本金(元)",
        "interest": "利息(元)",
        "remaining_principal": "剩余本金(元)",
        "cumulative_principal": "累计本金(元)",
        "cumulative_interest": "累计利息(元)",
        "applied_rate": "利率(%)",
        "is_paid": "已还",
        "actual_pay_date": "实际还款日",
    }

    display_cols = [c for c in col_map if c in display_df.columns]
    display_df = display_df[display_cols].rename(columns=col_map)

    # 格式化数值列
    money_cols = ["月供(元)", "本金(元)", "利息(元)", "剩余本金(元)", "累计本金(元)", "累计利息(元)"]
    for col in money_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}")

    if "利率(%)" in display_df.columns:
        display_df["利率(%)"] = display_df["利率(%)"].apply(lambda x: f"{x:.2f}")

    if "已还" in display_df.columns:
        display_df["已还"] = display_df["已还"].apply(lambda x: "✅" if x else "")

    if not show_all and len(display_df) > 24:
        st.dataframe(display_df, width='stretch', height=600)
    else:
        st.dataframe(display_df, width='stretch')


def render_comparison_table(comparison_df: pd.DataFrame):
    """渲染方案对比表"""
    if comparison_df.empty:
        st.info("暂无对比数据")
        return

    display = comparison_df.copy()
    money_cols = ["贷款总额", "首月月供", "末月月供", "平均月供", "总还款额", "总利息"]
    for col in money_cols:
        if col in display.columns:
            display[col] = display[col].apply(lambda x: f"{x:,.2f} 元")

    type_map = {"commercial": "商业贷款", "provident": "公积金贷款", "combined": "组合贷款"}
    method_map = {"equal_installment": "等额本息", "equal_principal": "等额本金"}

    if "贷款类型" in display.columns:
        display["贷款类型"] = display["贷款类型"].map(type_map).fillna(display["贷款类型"])
    if "还款方式" in display.columns:
        display["还款方式"] = display["还款方式"].map(method_map).fillna(display["还款方式"])

    st.dataframe(display, width='stretch')
