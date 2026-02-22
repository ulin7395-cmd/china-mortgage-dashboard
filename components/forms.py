"""表单组件"""
from datetime import date, timedelta
from typing import Optional

import streamlit as st
import pandas as pd

from config.constants import LoanType, RepaymentMethod
from config.settings import (
    DEFAULT_COMMERCIAL_RATE, DEFAULT_PROVIDENT_RATE, DEFAULT_PROVIDENT_LIMIT,
)
from data_manager.excel_handler import get_config


def _get_config_with_default(key: str, default: float) -> float:
    """从 Excel 获取配置，若无则返回默认值"""
    value = get_config(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def render_loan_plan_form(
    key_prefix: str = "new",
    plan_data: Optional[pd.Series] = None,
) -> dict | None:
    """渲染贷款方案创建/编辑表单，返回表单数据 dict 或 None（未提交）

    Args:
        key_prefix: 用于表单控件的 key 前缀
        plan_data: 如果是编辑模式，传入现有方案的 pd.Series
    """
    is_edit = plan_data is not None

    if is_edit:
        st.subheader("编辑贷款方案")
    else:
        st.subheader("新建贷款方案")

    # 从 Excel 读取配置的默认值
    default_commercial_rate = _get_config_with_default("lpr_5y", DEFAULT_COMMERCIAL_RATE)
    default_provident_rate = _get_config_with_default("provident_rate", DEFAULT_PROVIDENT_RATE)
    default_provident_limit = _get_config_with_default("provident_limit", DEFAULT_PROVIDENT_LIMIT)

    # 编辑模式：从现有数据读取，否则使用默认值
    if is_edit:
        default_plan_name = plan_data["plan_name"]
        default_loan_type = plan_data["loan_type"]
        default_repayment_method = plan_data["repayment_method"]
        default_total_amount = float(plan_data["total_amount"])
        default_commercial_amount = float(plan_data["commercial_amount"])
        default_provident_amount = float(plan_data["provident_amount"])
        default_term_months = int(plan_data["term_months"])
        default_commercial_rate_val = float(plan_data["commercial_rate"])
        default_provident_rate_val = float(plan_data["provident_rate"])
        default_start_date = pd.to_datetime(plan_data["start_date"]).date()
        default_repayment_day = int(plan_data["repayment_day"])
        default_notes = plan_data.get("notes", "")
    else:
        default_plan_name = "我的房贷"
        default_loan_type = LoanType.COMMERCIAL.value
        default_repayment_method = RepaymentMethod.EQUAL_INSTALLMENT.value
        default_total_amount = 1000000.0
        default_commercial_amount = 500000.0
        default_provident_amount = 500000.0
        default_term_months = 360
        default_commercial_rate_val = default_commercial_rate
        default_provident_rate_val = default_provident_rate
        default_start_date = date.today()
        default_repayment_day = 1
        default_notes = ""

    plan_name = st.text_input("方案名称", value=default_plan_name, key=f"{key_prefix}_name")

    # 贷款类型和还款方式放在 form 外部，使切换时立即触发页面重渲染
    c1, c2 = st.columns(2)
    with c1:
        loan_type = st.selectbox(
            "贷款类型",
            options=[lt.value for lt in LoanType],
            index=[lt.value for lt in LoanType].index(default_loan_type),
            format_func=lambda x: LoanType(x).label,
            key=f"{key_prefix}_type",
        )
    with c2:
        repayment_method = st.selectbox(
            "还款方式",
            options=[rm.value for rm in RepaymentMethod],
            index=[rm.value for rm in RepaymentMethod].index(default_repayment_method),
            format_func=lambda x: RepaymentMethod(x).label,
            key=f"{key_prefix}_method",
        )

    with st.form(f"{key_prefix}_loan_form"):
        # 金额（根据 loan_type 条件渲染）
        if loan_type == LoanType.COMBINED.value:
            st.info("组合贷款需分别输入商贷和公积金金额")
            c1, c2 = st.columns(2)
            with c1:
                commercial_amount = st.number_input(
                    "商贷金额(元)", min_value=0.0, value=default_commercial_amount,
                    step=10000.0, key=f"{key_prefix}_comm_amt")
            with c2:
                provident_amount = st.number_input(
                    f"公积金金额(元) (上限{default_provident_limit}万元，即{default_provident_limit * 10000:,.0f}元)",
                    min_value=0.0, value=default_provident_amount, step=10000.0,
                    max_value=default_provident_limit * 10000,
                    key=f"{key_prefix}_prov_amt")
            total_amount = commercial_amount + provident_amount
        else:
            total_amount = st.number_input(
                "贷款总额(元)", min_value=10000.0, value=default_total_amount,
                step=10000.0, key=f"{key_prefix}_total")
            if loan_type == LoanType.COMMERCIAL.value:
                commercial_amount = total_amount
                provident_amount = 0.0
            else:
                commercial_amount = 0.0
                provident_amount = total_amount

        # 利率
        c1, c2 = st.columns(2)
        with c1:
            commercial_rate = st.number_input(
                "商贷年利率(%)", min_value=0.0, max_value=20.0,
                value=default_commercial_rate_val, step=0.01, format="%.2f",
                key=f"{key_prefix}_comm_rate",
                disabled=(loan_type == LoanType.PROVIDENT.value),
            )
        with c2:
            provident_rate = st.number_input(
                "公积金年利率(%)", min_value=0.0, max_value=20.0,
                value=default_provident_rate_val, step=0.01, format="%.2f",
                key=f"{key_prefix}_prov_rate",
                disabled=(loan_type == LoanType.COMMERCIAL.value),
            )

        # 期限和日期
        c1, c2, c3 = st.columns(3)
        with c1:
            term_years = st.number_input(
                "贷款年限", min_value=1, max_value=30, value=default_term_months // 12,
                key=f"{key_prefix}_years")
        with c2:
            start_date = st.date_input(
                "起始日期", value=default_start_date,
                key=f"{key_prefix}_start")
        with c3:
            repayment_day = st.number_input(
                "每月还款日", min_value=1, max_value=28, value=default_repayment_day,
                key=f"{key_prefix}_day")

        notes = st.text_area("备注", value=default_notes, key=f"{key_prefix}_notes")

        if is_edit:
            submit_label = "保存修改"
        else:
            submit_label = "确认提交"
        submitted = st.form_submit_button(submit_label, width='stretch', type="primary")

        if submitted:
            return {
                "plan_name": plan_name,
                "loan_type": loan_type,
                "total_amount": total_amount,
                "commercial_amount": commercial_amount,
                "provident_amount": provident_amount,
                "term_months": term_years * 12,
                "repayment_method": repayment_method,
                "commercial_rate": commercial_rate,
                "provident_rate": provident_rate,
                "start_date": start_date,
                "repayment_day": repayment_day,
                "notes": notes,
            }
    return None


def render_prepayment_form(
    remaining_principal: float,
    key_prefix: str = "prepay",
) -> dict | None:
    """渲染提前还款表单"""
    with st.form(f"{key_prefix}_form"):
        st.subheader("提前还款")
        st.write(f"当前剩余本金: **{remaining_principal:,.2f} 元**")

        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input(
                "提前还款金额(元)", min_value=10000.0,
                max_value=remaining_principal - 1,
                value=min(100000.0, remaining_principal - 1),
                step=10000.0, key=f"{key_prefix}_amount",
            )
        with c2:
            prepay_date = st.date_input(
                "还款日期", value=date.today(),
                key=f"{key_prefix}_date",
            )

        method = st.radio(
            "还款方式",
            options=["shorten_term", "reduce_payment"],
            format_func=lambda x: "缩短年限（月供不变）" if x == "shorten_term" else "减少月供（期限不变）",
            key=f"{key_prefix}_method",
        )

        submitted = st.form_submit_button("模拟计算", width='stretch')

        if submitted:
            return {
                "amount": amount,
                "prepayment_date": prepay_date,
                "method": method,
            }
    return None
