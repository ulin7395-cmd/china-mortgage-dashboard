"""Excel 数据层测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import tempfile
import pytest
import pandas as pd
from datetime import date

from data_manager.excel_handler import (
    init_excel, read_sheet, write_sheet,
    save_plan, get_all_plans, get_plan_by_id, delete_plan,
    save_repayment_schedule, get_repayment_schedule,
    get_config, set_config, get_all_config,
)
from config.constants import SHEET_LOAN_PLANS, SHEET_CONFIG


@pytest.fixture
def temp_excel(tmp_path):
    """创建临时 Excel 文件"""
    filepath = tmp_path / "test_data.xlsx"
    init_excel(filepath)
    return filepath


class TestInitExcel:
    def test_creates_file(self, temp_excel):
        assert temp_excel.exists()

    def test_has_all_sheets(self, temp_excel):
        xls = pd.ExcelFile(temp_excel, engine="openpyxl")
        assert "贷款方案" in xls.sheet_names
        assert "还款计划" in xls.sheet_names
        assert "利率调整记录" in xls.sheet_names
        assert "提前还款记录" in xls.sheet_names
        assert "系统配置" in xls.sheet_names

    def test_default_config(self, temp_excel):
        val = get_config("lpr_5y", temp_excel)
        assert val is not None
        assert float(val) > 0


class TestPlanCRUD:
    def test_save_and_get(self, temp_excel):
        plan = {
            "plan_id": "test-001",
            "plan_name": "测试方案",
            "loan_type": "commercial",
            "total_amount": 1000000,
            "commercial_amount": 1000000,
            "provident_amount": 0,
            "term_months": 360,
            "repayment_method": "equal_installment",
            "commercial_rate": 3.45,
            "provident_rate": 0,
            "start_date": "2024-01-01",
            "repayment_day": 1,
            "status": "active",
            "notes": "",
        }
        save_plan(plan, temp_excel)

        plans = get_all_plans(temp_excel)
        assert len(plans) == 1
        assert plans.iloc[0]["plan_id"] == "test-001"

    def test_get_by_id(self, temp_excel):
        plan = {
            "plan_id": "test-002",
            "plan_name": "方案二",
            "loan_type": "commercial",
            "total_amount": 500000,
            "commercial_amount": 500000,
            "provident_amount": 0,
            "term_months": 240,
            "repayment_method": "equal_principal",
            "commercial_rate": 4.0,
            "provident_rate": 0,
            "start_date": "2024-06-01",
            "repayment_day": 15,
            "status": "active",
            "notes": "test",
        }
        save_plan(plan, temp_excel)
        result = get_plan_by_id("test-002", temp_excel)
        assert result is not None
        assert result["plan_name"] == "方案二"

    def test_delete(self, temp_excel):
        plan = {
            "plan_id": "test-del",
            "plan_name": "待删除",
            "loan_type": "commercial",
            "total_amount": 100000,
            "commercial_amount": 100000,
            "provident_amount": 0,
            "term_months": 60,
            "repayment_method": "equal_installment",
            "commercial_rate": 3.0,
            "provident_rate": 0,
            "start_date": "2024-01-01",
            "repayment_day": 1,
            "status": "active",
            "notes": "",
        }
        save_plan(plan, temp_excel)
        assert len(get_all_plans(temp_excel)) == 1

        delete_plan("test-del", temp_excel)
        assert len(get_all_plans(temp_excel)) == 0


class TestConfig:
    def test_set_and_get(self, temp_excel):
        set_config("test_key", "test_value", "测试", temp_excel)
        assert get_config("test_key", temp_excel) == "test_value"

    def test_update_existing(self, temp_excel):
        set_config("lpr_5y", "3.60", "", temp_excel)
        assert float(get_config("lpr_5y", temp_excel)) == 3.6

    def test_get_all_config(self, temp_excel):
        config_df = get_all_config(temp_excel)
        assert not config_df.empty
        assert "key" in config_df.columns
        assert "value" in config_df.columns
        # 检查默认配置存在
        keys = config_df["key"].tolist()
        assert "lpr_5y" in keys
        assert "provident_rate" in keys
        assert "inflation_rate" in keys
        assert "provident_limit" in keys
