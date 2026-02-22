from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据文件路径
DATA_DIR = PROJECT_ROOT / "data"
EXCEL_FILE = DATA_DIR / "loan_data.xlsx"
BACKUP_DIR = DATA_DIR

# 默认利率 (%)
DEFAULT_COMMERCIAL_RATE = 3.45
DEFAULT_PROVIDENT_RATE = 2.85
DEFAULT_LPR_5Y = 3.45

# 默认通胀率 (%)
DEFAULT_INFLATION_RATE = 2.5

# 公积金贷款上限 (万元) - 不同城市不同，此为常见值
DEFAULT_PROVIDENT_LIMIT = 120.0

# 页面配置
PAGE_TITLE = "房贷可视化 Dashboard"
PAGE_ICON = "🏠"
LAYOUT = "wide"

# 图表配色
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "success": "#2ca02c",
    "danger": "#d62728",
    "warning": "#bcbd22",
    "info": "#17becf",
    "principal": "#1f77b4",
    "interest": "#ff7f0e",
    "paid": "#2ca02c",
    "unpaid": "#d62728",
    "commercial": "#1f77b4",
    "provident": "#2ca02c",
}

# 金额精度
AMOUNT_PRECISION = 2
RATE_PRECISION = 4
