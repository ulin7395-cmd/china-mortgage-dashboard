"""系统配置管理"""
import streamlit as st
import pandas as pd

from config.settings import (
    DEFAULT_COMMERCIAL_RATE, DEFAULT_PROVIDENT_RATE,
    DEFAULT_LPR_5Y, DEFAULT_INFLATION_RATE, DEFAULT_PROVIDENT_LIMIT,
)
from data_manager.excel_handler import (
    get_all_config, get_config, set_config, init_excel,
)
from utils.formatters import fmt_rate, fmt_amount

st.set_page_config(page_title="系统配置", page_icon="⚙️", layout="wide")
st.title("⚙️ 系统配置")

init_excel()

# 从 Excel 读取当前配置，若无则使用 settings.py 中的默认值
current_lpr = float(get_config("lpr_5y") or DEFAULT_LPR_5Y)
current_prov_rate = float(get_config("provident_rate") or DEFAULT_PROVIDENT_RATE)
current_inflation = float(get_config("inflation_rate") or DEFAULT_INFLATION_RATE)
current_prov_limit = float(get_config("provident_limit") or DEFAULT_PROVIDENT_LIMIT)

# 默认值说明
st.info("""
**说明**：在此页面修改的默认值将持久化保存到 Excel 中，新建贷款方案时会自动使用这些值作为默认配置。
""")

st.divider()

# 配置表单
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
        # 保存所有配置
        set_config("lpr_5y", str(new_lpr), "5年期以上LPR")
        set_config("provident_rate", str(new_prov_rate), "公积金贷款利率")
        set_config("inflation_rate", str(new_inflation), "年通胀率")
        set_config("provident_limit", str(new_prov_limit), "公积金贷款上限(万元)")
        st.success("配置已保存！新建贷款方案时将使用新的默认值。")
        st.rerun()

st.divider()

# 显示当前所有配置
st.subheader("当前配置一览")
config_df = get_all_config()

if not config_df.empty:
    # 格式化显示
    display_df = config_df.copy()

    # 添加友好列名
    display_df = display_df.rename(columns={
        "key": "配置项",
        "value": "当前值",
        "description": "说明",
        "updated_at": "更新时间"
    })

    # 美化显示
    st.dataframe(display_df, width='stretch', hide_index=True)
else:
    st.info("暂无配置数据，使用系统默认值。")
