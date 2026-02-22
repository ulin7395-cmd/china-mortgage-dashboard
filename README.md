# 房贷可视化 Dashboard

一个功能完整的房贷（按揭贷款）可视化管理工具，支持等额本息、等额本金、组合贷计算，以及提前还款、利率调整等场景分析。

## 功能特性

- 📊 **贷款计算**：支持等额本息、等额本金、组合贷（商业+公积金）
- 📈 **可视化图表**：还款明细、本金利息占比、剩余本金趋势
- 💸 **提前还款**：支持两种方式（缩短年限/减少月供），自动计算节省利息
- 📉 **利率调整**：模拟 LPR 变动对还款计划的影响
- 📋 **方案对比**：多方案横向对比，选择最优贷款方案
- 💾 **数据持久化**：Excel 存储，自动备份
- 🎯 **通胀分析**：考虑货币贬值的真实成本测算

## 技术栈

- **UI 框架**：Streamlit
- **图表**：Plotly Express
- **数据处理**：Pandas
- **计算引擎**：NumPy + SciPy (IRR 计算)
- **数据存储**：Excel (openpyxl)

## 快速开始

### 环境要求

- Python 3.9+

### 安装与运行

```bash
# 1. 克隆项目
cd loan_dashboard

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行应用
streamlit run app.py
```

应用启动后会自动打开浏览器访问 `http://localhost:8501`。

## 项目结构

```
loan_dashboard/
├── app.py                 # 应用入口
├── pages/                 # Streamlit 页面（数字前缀控制侧边栏顺序）
│   ├── 1_贷款方案.py
│   ├── 2_还款计划.py
│   ├── 3_提前还款.py
│   ├── 4_利率调整.py
│   └── 5_方案对比.py
├── components/            # 可复用 UI 组件
│   ├── charts.py          # Plotly 图表
│   ├── forms.py           # 表单组件
│   ├── tables.py          # 表格展示
│   └── metrics.py         # 指标卡片
├── core/                  # 业务逻辑核心
│   ├── calculator.py      # 贷款计算核心
│   ├── prepayment.py      # 提前还款逻辑
│   ├── rate_adjustment.py # 利率调整逻辑
│   ├── comparison.py      # 方案对比
│   └── inflation.py       # 通胀分析
├── data_manager/          # 数据持久层
│   ├── excel_handler.py   # Excel 读写操作
│   ├── validation.py      # 数据校验
│   └── schemas.py         # 数据模型
├── config/                # 配置与枚举
│   ├── constants.py       # 枚举定义
│   └── settings.py        # 全局配置
├── utils/                 # 工具函数
│   ├── formatters.py      # 格式化工具
│   ├── date_utils.py      # 日期处理
│   └── id_generator.py    # ID 生成
├── data/                  # 数据存储目录
│   └── loan_data.xlsx     # Excel 数据库（自动生成）
└── tests/                 # 单元测试
    ├── test_calculator.py
    └── test_prepayment.py
```

## 常用命令

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run app.py

# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_calculator.py -v

# 运行特定测试
pytest tests/test_calculator.py::TestEqualInstallment::test_basic_calculation -v
```

## 数据存储说明

所有数据存储在 `data/loan_data.xlsx` 中，包含 5 个 Sheet：

1. **贷款方案** - 贷款基本信息（金额、期限、利率等）
2. **还款计划** - 每期还款明细
3. **利率调整记录** - 历史利率变更记录
4. **提前还款记录** - 历史提前还款记录
5. **系统配置** - 全局配置项

每次写入前会自动创建时间戳备份（保留最近 5 个备份）。

## 核心设计决策

- **绝对导入**：所有导入从项目根目录开始（如 `from core.calculator import ...`）
- **Excel 单数据源**：通过 `excel_handler.py` 统一管理读写
- **组合贷计算**：商贷和公积金分别计算后合并还款列
- **变更处理**：利率调整和提前还款保留已还期数，仅重新生成未来部分
- **IRR 计算**：使用 `scipy.optimize.brentq` 求解内部收益率

## License

MIT License
