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

## CLI 用法

本项目提供了一个命令行界面（CLI），用于执行核心的计算和数据管理任务。

### 安装

首先，请确保已安装所有依赖项：

```bash
pip install -r requirements.txt
```

### 基本用法

所有命令都通过`cli.py`脚本执行。你可以使用以下命令查看所有可用的命令：

```bash
python3 -m cli --help
```

### 命令详解

以下是所有可用命令的详细列表及其用法：

---

#### `add-plan`

添加一个新的贷款方案。

```
Usage: cli.py add-plan [OPTIONS]

Options:
  --plan-id TEXT                  Plan ID  [required]
  --plan-name TEXT                Plan name  [required]
  --loan-type [commercial|provident|combined]
                                  Loan type  [required]
  --total-amount FLOAT            Total loan amount  [required]
  --commercial-amount FLOAT       Commercial loan amount
  --provident-amount FLOAT        Provident fund loan amount
  --term-months INTEGER           Loan term in months  [required]
  --repayment-method [equal_installment|equal_principal]
                                  Repayment method  [required]
  --commercial-rate FLOAT         Commercial loan annual rate
  --provident-rate FLOAT          Provident fund loan annual rate
  --start-date TEXT               Start date (YYYY-MM-DD)  [required]
  --repayment-day INTEGER         Repayment day
  --status [active|completed|archived]
                                  Plan status
  --notes TEXT                    Notes
  --help                          Show this message and exit.
```

---

#### `add-prepayment`

添加一个新的提前还款记录。

```
Usage: cli.py add-prepayment [OPTIONS]

Options:
  --prepayment-id TEXT            Prepayment ID  [required]
  --plan-id TEXT                  Plan ID  [required]
  --prepayment-date TEXT          Prepayment date (YYYY-MM-DD)  [required]
  --prepayment-period INTEGER     Prepayment period  [required]
  --amount FLOAT                  Prepayment amount  [required]
  --method [shorten_term|reduce_payment]
                                  Prepayment method  [required]
  --help                          Show this message and exit.
```

---

#### `add-rate-adjustment`

添加一个新的利率调整记录。

```
Usage: cli.py add-rate-adjustment [OPTIONS]

Options:
  --adjustment-id TEXT            Adjustment ID  [required]
  --plan-id TEXT                  Plan ID  [required]
  --effective-date TEXT           Effective date (YYYY-MM-DD)  [required]
  --effective-period INTEGER      Effective period  [required]
  --rate-type [commercial|provident]
                                  Rate type  [required]
  --old-rate FLOAT                Old rate  [required]
  --new-rate FLOAT                New rate  [required]
  --lpr-value FLOAT               LPR value
  --basis-points INTEGER          Basis points
  --reason TEXT                   Reason
  --help                          Show this message and exit.
```

---

#### `calc-irr`

计算贷款的内部收益率（IRR）。

```
Usage: cli.py calc-irr [OPTIONS]

Options:
  --principal FLOAT     Loan principal  [required]
  --schedule-file PATH  Path to the repayment schedule CSV file  [required]
  --help                Show this message and exit.
```

---

#### `calc-remaining-irr`

计算剩余贷款的内部收益率（IRR）。

```
Usage: cli.py calc-remaining-irr [OPTIONS]

Options:
  --remaining-principal FLOAT  Remaining loan principal  [required]
  --schedule-file PATH         Path to the remaining repayment schedule CSV
                               file  [required]
  --help                       Show this message and exit.
```

---

#### `compare-methods`

比较等额本息和等额本金两种还款方式。

```
Usage: cli.py compare-methods [OPTIONS]

Options:
  --amount FLOAT   Loan amount  [required]
  --rate FLOAT     Annual interest rate  [required]
  --years INTEGER  Loan term in years  [required]
  --help           Show this message and exit.
```

---

#### `compare-plans`

比较多个贷款方案。

```
Usage: cli.py compare-plans [OPTIONS] [PLAN_IDS]...

Options:
  --help  Show this message and exit.
```

---

#### `delete-plan`

删除一个贷款方案。

```
Usage: cli.py delete-plan [OPTIONS]

Options:
  --plan-id TEXT  Plan ID  [required]
  --help          Show this message and exit.
```

---

#### `equal-installment`

计算等额本息贷款的月供和总利息。

```
Usage: cli.py equal-installment [OPTIONS]

Options:
  --principal FLOAT      Loan principal  [required]
  --annual-rate FLOAT    Annual interest rate  [required]
  --term-months INTEGER  Loan term in months  [required]
  --help                 Show this message and exit.
```

---

#### `equal-principal`

计算等额本金贷款的首月月供和总利息。

```
Usage: cli.py equal-principal [OPTIONS]

Options:
  --principal FLOAT      Loan principal  [required]
  --annual-rate FLOAT    Annual interest rate  [required]
  --term-months INTEGER  Loan term in months  [required]
  --help                 Show this message and exit.
```

---

#### `generate-combined-schedule`

生成组合贷款的还款计划表。

```
Usage: cli.py generate-combined-schedule [OPTIONS]

Options:
  --plan-id TEXT                  Plan ID  [required]
  --commercial-amount FLOAT       Commercial loan amount  [required]
  --provident-amount FLOAT        Provident fund loan amount  [required]
  --commercial-rate FLOAT         Commercial loan annual rate  [required]
  --provident-rate FLOAT          Provident fund loan annual rate  [required]
  --term-months INTEGER           Loan term in months  [required]
  --repayment-method [equal_installment|equal_principal]
                                  Repayment method  [required]
  --start-date TEXT               Start date (YYYY-MM-DD)  [required]
  --repayment-day INTEGER         Repayment day
  --help                          Show this message and exit.
```

---

#### `generate-schedule`

生成还款计划表。

```
Usage: cli.py generate-schedule [OPTIONS]

Options:
  --plan-id TEXT                  Plan ID  [required]
  --principal FLOAT               Loan principal  [required]
  --annual-rate FLOAT             Annual interest rate  [required]
  --term-months INTEGER           Loan term in months  [required]
  --repayment-method [equal_installment|equal_principal]
                                  Repayment method  [required]
  --start-date TEXT               Start date (YYYY-MM-DD)  [required]
  --repayment-day INTEGER         Repayment day
  --help                          Show this message and exit.
```

---

#### `get-config`

获取一个系统配置项。

```
Usage: cli.py get-config [OPTIONS]

Options:
  --key TEXT  Config key  [required]
  --help      Show this message and exit.
```

---

#### `get-plan`

获取一个贷款方案。

```
Usage: cli.py get-plan [OPTIONS]

Options:
  --plan-id TEXT  Plan ID  [required]
  --help          Show this message and exit.
```

---

#### `list-configs`

列出所有系统配置项。

```
Usage: cli.py list-configs [OPTIONS]

Options:
  --help  Show this message and exit.
```

---

#### `list-plans`

列出所有贷款方案。

```
Usage: cli.py list-plans [OPTIONS]

Options:
  --help  Show this message and exit.
```

---

#### `list-prepayments`

列出所有提前还款记录。

```
Usage: cli.py list-prepayments [OPTIONS]

Options:
  --plan-id TEXT  Plan ID  [required]
  --help          Show this message and exit.
```

---

#### `list-rate-adjustments`

列出所有利率调整记录。

```
Usage: cli.py list-rate-adjustments [OPTIONS]

Options:
  --plan-id TEXT  Plan ID  [required]
  --help          Show this message and exit.
```

---

#### `set-config`

设置一个系统配置项。

```
Usage: cli.py set-config [OPTIONS]

Options:
  --key TEXT          Config key  [required]
  --value TEXT        Config value  [required]
  --description TEXT  Description
  --help              Show this message and exit.
```

---

#### `update-prepayment`

更新一个提前还款记录。

```
Usage: cli.py update-prepayment [OPTIONS]

Options:
  --prepayment-id TEXT  Prepayment ID  [required]
  --updates TEXT        Updates in JSON format  [required]
  --help                Show this message and exit.
```
