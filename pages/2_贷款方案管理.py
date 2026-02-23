"""贷款方案管理"""
import streamlit as st
from datetime import date

from config.constants import LoanType, RepaymentMethod, PlanStatus
from config.settings import DEFAULT_PROVIDENT_LIMIT
from data_manager.excel_handler import (
    get_all_plans, save_plan, delete_plan,
    init_excel, get_config,
)
from data_manager.data_validator import validate_loan_plan
from core.calculator import generate_schedule, generate_combined_schedule, calc_equal_installment, calc_equal_principal_first_month
from components.forms import render_loan_plan_form
from utils.id_generator import generate_plan_id
from utils.formatters import fmt_amount


def _get_provident_limit() -> float:
    """从 Excel 获取公积金贷款上限，若无则返回默认值"""
    value = get_config("provident_limit")
    if value is None:
        return DEFAULT_PROVIDENT_LIMIT
    try:
        return float(value)
    except (ValueError, TypeError):
        return DEFAULT_PROVIDENT_LIMIT


st.set_page_config(page_title="贷款方案管理", page_icon="📋", layout="wide")
st.title("📋 贷款方案管理")

init_excel()

# 已有方案列表
tab_list, tab_new = st.tabs(["方案列表", "新建/编辑方案"])

with tab_list:
    plans = get_all_plans()
    if plans.empty:
        st.info("暂无贷款方案，请点击「新建/编辑方案」创建。")
    else:
        for _, plan in plans.iterrows():
            loan_type_label = LoanType(plan["loan_type"]).label if plan["loan_type"] in [e.value for e in LoanType] else plan["loan_type"]
            method_label = RepaymentMethod(plan["repayment_method"]).label if plan["repayment_method"] in [e.value for e in RepaymentMethod] else plan["repayment_method"]
            status_label = PlanStatus(plan["status"]).label if plan.get("status") in [e.value for e in PlanStatus] else "还款中"

            with st.container(border=True):
                col_info, col_actions = st.columns([4, 1])
                with col_info:
                    st.subheader(plan['plan_name'])
                    
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**贷款类型:** {loan_type_label}")
                    c1.write(f"**还款方式:** {method_label}")
                    c1.write(f"**贷款总额:** {fmt_amount(plan['total_amount'])}")

                    c2.write(f"**贷款期限:** {int(plan['term_months'])}个月 ({int(plan['term_months'])//12}年)")
                    c2.write(f"**起始日期:** {plan['start_date']}")
                    c2.write(f"**还款日:** 每月{int(plan['repayment_day'])}日")

                    if plan["loan_type"] == LoanType.COMBINED.value:
                        c3.write(f"**商贷金额:** {fmt_amount(plan['commercial_amount'])}")
                        c3.write(f"**公积金金额:** {fmt_amount(plan['provident_amount'])}")
                        c3.write(f"**商贷利率:** {plan['commercial_rate']:.2f}%")
                        c3.write(f"**公积金利率:** {plan['provident_rate']:.2f}%")
                    elif plan["loan_type"] == LoanType.COMMERCIAL.value:
                        c3.write(f"**商贷利率:** {plan['commercial_rate']:.2f}%")
                    else:
                        c3.write(f"**公积金利率:** {plan['provident_rate']:.2f}%")

                    if plan.get("notes"):
                        st.write(f"**备注:** {plan['notes']}")

                with col_actions:
                    st.write(f"**状态:** {status_label}")
                    st.button("编辑", key=f"edit_{plan['plan_id']}", type="primary", on_click=lambda p=plan['plan_id']: st.session_state.update(editing_plan_id=p))
                    st.button("删除", key=f"del_{plan['plan_id']}", type="secondary", on_click=lambda p=plan['plan_id']: delete_plan(p) and st.rerun())

with tab_new:
    # 检查是否在编辑模式
    editing_plan_id = st.session_state.get("editing_plan_id")
    editing_plan = None

    if editing_plan_id:
        plans = get_all_plans()
        match = plans[plans["plan_id"] == editing_plan_id]
        if not match.empty:
            editing_plan = match.iloc[0]
            st.info(f"正在编辑方案：**{editing_plan['plan_name']}**")
            if st.button("取消编辑", key="cancel_edit"):
                del st.session_state["editing_plan_id"]
                st.rerun()

    # 渲染表单
    if editing_plan is not None:
        form_data = render_loan_plan_form("edit", editing_plan)
    else:
        form_data = render_loan_plan_form("new", None)

    if form_data:
        # 校验
        provident_limit = _get_provident_limit()
        valid, msg = validate_loan_plan(
            plan_name=form_data["plan_name"],
            loan_type=form_data["loan_type"],
            total_amount=form_data["total_amount"],
            commercial_amount=form_data["commercial_amount"],
            provident_amount=form_data["provident_amount"],
            term_months=form_data["term_months"],
            repayment_method=form_data["repayment_method"],
            commercial_rate=form_data["commercial_rate"],
            provident_rate=form_data["provident_rate"],
            start_date=form_data["start_date"],
            repayment_day=form_data["repayment_day"],
            provident_limit=provident_limit,
        )

        if not valid:
            st.error(msg)
        else:
            if editing_plan is not None:
                plan_id = editing_plan_id
                st.success(f"方案「{form_data['plan_name']}」已更新！")
            else:
                plan_id = generate_plan_id()
                st.success(f"方案「{form_data['plan_name']}」创建成功！")

            # 预览月供
            lt = form_data["loan_type"]
            if lt == LoanType.COMMERCIAL.value:
                rate = form_data["commercial_rate"]
                amount = form_data["total_amount"]
            elif lt == LoanType.PROVIDENT.value:
                rate = form_data["provident_rate"]
                amount = form_data["total_amount"]
            else:
                rate = form_data["commercial_rate"]
                amount = form_data["total_amount"]

            if form_data["repayment_method"] == RepaymentMethod.EQUAL_INSTALLMENT.value:
                if lt == LoanType.COMBINED.value:
                    m1, i1 = calc_equal_installment(form_data["commercial_amount"], form_data["commercial_rate"], form_data["term_months"])
                    m2, i2 = calc_equal_installment(form_data["provident_amount"], form_data["provident_rate"], form_data["term_months"])
                    monthly, total_interest = m1 + m2, i1 + i2
                else:
                    monthly, total_interest = calc_equal_installment(amount, rate, form_data["term_months"])
                st.success(f"月供: {fmt_amount(monthly)} | 总利息: {fmt_amount(total_interest)}")
            else:
                if lt == LoanType.COMBINED.value:
                    m1, i1 = calc_equal_principal_first_month(form_data["commercial_amount"], form_data["commercial_rate"], form_data["term_months"])
                    m2, i2 = calc_equal_principal_first_month(form_data["provident_amount"], form_data["provident_rate"], form_data["term_months"])
                    first_monthly, total_interest = m1 + m2, i1 + i2
                else:
                    first_monthly, total_interest = calc_equal_principal_first_month(amount, rate, form_data["term_months"])
                st.success(f"首月月供: {fmt_amount(first_monthly)}（逐月递减） | 总利息: {fmt_amount(total_interest)}")

            # 保存方案
            plan_dict = {
                "plan_id": plan_id,
                "plan_name": form_data["plan_name"],
                "loan_type": form_data["loan_type"],
                "total_amount": form_data["total_amount"],
                "commercial_amount": form_data["commercial_amount"],
                "provident_amount": form_data["provident_amount"],
                "term_months": form_data["term_months"],
                "repayment_method": form_data["repayment_method"],
                "commercial_rate": form_data["commercial_rate"],
                "provident_rate": form_data["provident_rate"],
                "start_date": form_data["start_date"].strftime("%Y-%m-%d") if isinstance(form_data["start_date"], date) else form_data["start_date"],
                "repayment_day": form_data["repayment_day"],
                "status": PlanStatus.ACTIVE.value,
                "notes": form_data["notes"],
            }
            save_plan(plan_dict)
            st.info("方案已保存，还款计划将在需要时动态生成。")

            # 清除编辑状态
            if editing_plan_id:
                del st.session_state["editing_plan_id"]
                st.rerun()
