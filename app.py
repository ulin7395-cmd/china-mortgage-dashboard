"""房贷可视化 Dashboard - 主入口"""
import streamlit as st

from config.settings import PAGE_TITLE, PAGE_ICON, LAYOUT
from data_manager.excel_handler import init_excel

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded",
)

# 初始化 Excel
init_excel()

st.title(f"{PAGE_ICON} {PAGE_TITLE}")

st.markdown("""
欢迎使用房贷可视化 Dashboard！本工具帮助你全面管理和分析房贷还款情况。

### 功能导航

| 页面 | 功能 |
|------|------|
| 📊 **主仪表盘** | 概览指标、图表可视化 |
| 📋 **贷款方案管理** | 创建、查看、删除贷款方案 |
| 📄 **还款明细** | 查看还款计划、标记已还 |
| 💰 **提前还款模拟** | 模拟提前还款，对比缩短年限/减少月供 |
| ⚖️ **方案对比** | 多方案横向对比、等额本息vs等额本金 |
| 📈 **利率管理** | LPR利率配置、利率调整模拟 |
| ⚙️ **系统配置** | 修改默认利率、通胀率、公积金上限等参数 |

### 快速开始

1. 进入 **贷款方案管理** 创建你的贷款方案
2. 在 **主仪表盘** 查看可视化分析
3. 使用 **提前还款模拟** 规划最优还款策略

---

### 支持功能

- **贷款类型**: 商业贷款、公积金贷款、组合贷款
- **还款方式**: 等额本息、等额本金
- **提前还款**: 缩短年限 / 减少月供两种方式对比
- **利率调整**: LPR + 基点方式调整，自动重算还款计划
- **真实年化率**: IRR 法计算
- **通胀分析**: 考虑通胀后的实际还款成本
- **数据持久化**: Excel 文件存储，自动备份
""")

# 侧边栏
with st.sidebar:
    st.markdown("### 关于")
    st.markdown("房贷可视化 Dashboard v1.0")
    st.markdown("数据存储在 `data/loan_data.xlsx`")
