# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_calculator.py -v

# Run a specific test
pytest tests/test_calculator.py::TestEqualInstallment::test_basic_calculation -v
```

## Architecture

This is a mortgage (房贷) visualization dashboard built with Streamlit + Plotly + Pandas. All UI text is in Chinese.

### Layer structure

```
pages/          → Streamlit page UIs (numbered prefix controls sidebar order)
components/     → Reusable UI building blocks (Plotly charts, forms, tables, metric cards)
core/           → Business logic (loan math, prepayment, rate adjustment, comparison, inflation)
data_manager/   → Persistence layer (Excel CRUD with auto-backup, validation, dataclass schemas)
config/         → Enums (LoanType, RepaymentMethod, etc.), sheet/column definitions, global settings
utils/          → Formatters, date math, ID generation
```

### Data flow

Pages call components for rendering and core modules for calculations. All persistence goes through `data_manager/excel_handler.py` which reads/writes a single Excel file (`data/loan_data.xlsx`) with 5 sheets: 贷款方案, 还款计划, 利率调整记录, 提前还款记录, 系统配置.

### Key design decisions

- **All imports are absolute from project root** (e.g. `from core.calculator import ...`). Streamlit and pytest both resolve these correctly—tests use `conftest.py` to add project root to `sys.path`.
- **Excel is the sole data store.** `excel_handler.py` auto-initializes the file on first run and creates timestamped backups (keeping 5 most recent) before every write.
- **Combined loans (组合贷)** are calculated by running commercial and provident fund schedules independently, then summing the payment columns.
- **Rate adjustments and prepayments** preserve already-paid periods and regenerate only future periods from the change point, carrying forward cumulative totals.
- **IRR calculation** uses `scipy.optimize.brentq` to solve for the internal rate of return.

### Adding new pages

Create `pages/N_name.py` (N controls sidebar order). Each page must call `st.set_page_config()` at the top and read data via `excel_handler` functions.

---

## Lessons Learned: 事件溯源与状态管理

### 问题背景

在实现组合贷（组合贷）多次提前还款功能时，遇到了一个严重 Bug：第二次提前还款时，第一次提前还款的效果完全丢失了。

### 根本原因

**错误的架构设计：**

```
初始计划 → 合并 → 应用事件1 → 合并结果 → 应用事件2（重新从初始计划生成）
```

最初的实现是：
1. 先把商贷和公积金合并成一个 schedule
2. 每次提前还款时，`apply_combined_prepayment` 内部又从原始 plan **重新生成**商贷和公积金计划
3. 这导致之前的提前还款效果完全丢失

### 正确的解决方案：事件溯源 + 独立状态维护

```
商贷计划 ──┐
            ├── 分别应用事件1 ──┐
公积金计划 ──┘                   ├── 最后合并
            ├── 分别应用事件2 ──┘
```

修复后的实现：
1. **始终分别维护**商贷和公积金两个独立的 schedule
2. 每个事件（提前还款）直接应用到对应的独立 schedule 上
3. **所有事件应用完成后**，才把两个 schedule 合并显示

### 方法论总结

#### 1. 事件溯源模式的正确使用

- **事件不可变**：事件一旦保存，就不应修改
- **状态可重算**：当前状态 = 初始状态 + 按顺序应用所有事件
- **不要在中间步骤丢失上下文**：如果有多个并行实体（如组合贷的两部分），要在整个事件应用过程中保持它们的独立性

#### 2. 识别"不可拆分"的实体

- 组合贷的商贷和公积金看似是一个整体，但实际上它们是**两个独立的贷款合同**
- 它们有各自的本金、利率、提前还款规则
- 把它们合并后再试图拆分，会丢失精度和上下文

#### 3. Streamlit 状态管理的注意事项

- `st.session_state` 是跨 rerun 保存状态的唯一方式
- 表单提交 → 显示结果 → 确认保存 这种流程必须用 session_state
- 不要指望在同一个 if 块里的两个 button 能共享变量

#### 4. 代码审查 Checklist

当看到类似以下代码时要警惕：

```python
# 危险信号：每次都从原始数据重新生成
def apply_event(merged_data, event):
    original_a = get_original_a()  # 坏！
    original_b = get_original_b()  # 坏！
    # ... 应用事件到 original_a 和 original_b
```

应该改为：

```python
# 正确：传递当前状态
def apply_event(state_a, state_b, event):
    # ... 应用事件到 state_a 和 state_b
    return new_state_a, new_state_b
```

#### 5. 测试用例设计

针对事件驱动系统，必须测试：
- ✅ 单个事件
- ✅ 多个同类事件连续应用（如两次提前还款）
- ✅ 不同类型事件交替应用（如提前还款 → 利率调整 → 提前还款）
- ✅ 事件发生在已还期数的边界情况

---

## 计算逻辑总结

### 核心还款公式

**等额本息 (equal_installment):**
- 月供 = P × r × (1+r)^n / ((1+r)^n - 1)，其中 P=本金, r=月利率, n=期数
- 每期利息 = 剩余本金 × 月利率
- 每期本金 = 月供 - 每期利息

**等额本金 (equal_principal):**
- 每期本金 = P / n（固定）
- 每期利息 = 剩余本金 × 月利率
- 月供 = 每期本金 + 每期利息（逐月递减）

### 通胀调整 (`core/inflation.py`)

- **现值 PV:** 将每期月供按通胀率折现求和：`PV = Σ payment_i / (1 + r_monthly)^i`
- **实际利率:** 使用 Fisher 方程：`real_rate = (1 + nominal_rate) / (1 + inflation_rate) - 1`
  - `nominal_rate` 为贷款年化利率（非总利息/本金比率）
  - `inflation_rate` 为年通胀率
- **通胀侵蚀:** 名义总还款 - PV

### IRR 计算 (`core/calculator.py`)

- 使用 `scipy.optimize.brentq` 求解内部收益率
- 现金流：初始贷款额为正，每期月供为负
- 月度 IRR × 12 = 年化 IRR

### 提前还款 (`core/prepayment.py`)

- 缩短期限：重新计算剩余期数，月供不变
- 减少月供：期数不变，重新计算月供

### 展示指标来源

- **未还本金:** 从首个未还期的 `remaining_principal + principal` 计算（比累加更精确）
- **图表标注:** 使用 period→DataFrame索引 映射（不假设 period 从 1 开始且连续）
- **组合贷单组件 schedule:** 通过 `core/schedule_generator.generate_single_component_schedule()` 统一生成
