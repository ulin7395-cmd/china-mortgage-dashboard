# 房贷可视化 Dashboard

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg"/>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-blue.svg"/>
  <img alt="Streamlit" src="https://img.shields.io/badge/made%20with-Streamlit-orange.svg"/>
</p>

一个功能强大、界面美观的房贷（按揭贷款）可视化管理工具，帮助您清晰地掌握还款全局，做出更优的财务决策。

## ✨ 功能亮点

- **全能计算**: 支持商业贷款、公积金贷款、组合贷，以及等额本息和等额本金两种还款方式。
- **精美图表**: 通过一系列交互式图表，直观展示还款计划、本息构成、剩余本金等关键数据。
- **提前还款模拟**: 灵活模拟“缩短年限”或“减少月供”两种提前还款策略，并精确计算可节省的利息。
- **利率变动分析**: 轻松模拟 LPR 利率调整对未来月供和总利息的影响。
- **多方案对比**: 横向对比不同贷款方案的优劣，一目了然。
- **数据持久化**: 所有方案数据安全地存储在本地 Excel 文件中，并提供自动备份功能。
- **亮暗模式**: 支持根据您的系统设置自动切换亮色和暗色主题。

## 🚀 快速开始

**环境要求**: Python 3.9+

1.  **克隆项目**
    ```bash
    git clone https://github.com/ulin7395-cmd/china-mortgage-dashboard.git
    cd china-mortgage-dashboard
    ```

2.  **安装依赖**
    ```bash
    # (推荐) 创建并激活虚拟环境
    python -m venv .venv
    source .venv/bin/activate
    
    # 安装依赖
    pip install -r requirements.txt
    ```

3.  **运行应用**
    ```bash
    streamlit run app.py
    ```
    应用启动后，浏览器将自动打开 `http://localhost:8501`。

## 📸 应用预览

| 主仪表盘 (暗色) | 方案对比 | 提前还款模拟 |
| :---: | :---: | :---: |
| <img src="assets/screenshot-dashboard-dark.png" width="400"/> | <img src="assets/screenshot-comparison.png" width="400"/> | <img src="assets/screenshot-prepayment.png" width="400"/> |

## 🛠️ 技术栈

- **前端**: Streamlit
- **图表**: Plotly
- **数据处理**: Pandas, NumPy
- **数据存储**: Excel (openpyxl)

## 📂 项目结构

```
loan_dashboard/
├── .streamlit/
│   └── config.toml      # Streamlit 主题配置
├── app.py                 # 应用主入口
├── pages/                 # 各个功能页面
├── components/            # 可复用UI组件 (图表、表单等)
├── core/                  # 核心业务逻辑 (计算、模拟等)
├── data_manager/          # 数据持久化与校验
├── config/                # 全局配置与常量
├── utils/                 # 工具函数
├── assets/                # 静态资源 (用于存放截图)
│   └── (截图文件...)
├── data/                  # 数据存储目录 (自动生成)
│   └── loan_data.xlsx
└── requirements.txt       # 项目依赖
```

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。
