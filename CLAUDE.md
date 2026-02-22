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
