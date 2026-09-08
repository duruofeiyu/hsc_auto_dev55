"""
55 开发环境 - 脆弱性管理 - 脆弱性概览 - 只读接口测试
覆盖：高风险主机/网站列表、弱口令统计、基线统计、核心指标
"""
import pytest
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import request_no_auth, assert_success
from vuln_management.utils_vuln_overview import (
    VULN_BASE, query_high_risk_host_list, query_high_risk_web_list,
    get_weak_password_statistics, get_baseline_statistics, get_risk_overview_metrics,
)


@allure.epic("HSC 脆弱性管理")
@allure.feature("脆弱性概览")
@allure.story("高风险资产列表")
class TestHighRiskAssetList:

    @allure.title("高风险主机列表-默认查询")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_high_risk_host_list_default(self):
        result = assert_success(query_high_risk_host_list(), "高风险主机列表")
        assert isinstance(result, dict), "result 应为字典"
        records = result.get("list", [])
        assert isinstance(records, list), "list 应为数组"

    @allure.title("高风险主机列表-按风险总数降序")
    @allure.severity(allure.severity_level.NORMAL)
    def test_high_risk_host_list_descending(self):
        result = assert_success(query_high_risk_host_list(), "高风险主机列表降序")
        records = result.get("list", [])
        if len(records) >= 2:
            counts = [int(r.get("totalRiskCount", 0)) for r in records]
            assert counts == sorted(counts, reverse=True), f"未按风险总数降序: {counts}"

    @allure.title("高风险网站列表-默认查询")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_high_risk_web_list_default(self):
        result = assert_success(query_high_risk_web_list(), "高风险网站列表")
        assert isinstance(result, dict), "result 应为字典"
        assert isinstance(result.get("list", []), list), "list 应为数组"


@allure.epic("HSC 脆弱性管理")
@allure.feature("脆弱性概览")
@allure.story("统计卡片")
class TestStatisticsCard:

    @allure.title("弱口令统计卡片")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_weak_password_statistics(self):
        result = assert_success(get_weak_password_statistics(), "弱口令统计")
        assert isinstance(result, dict), "result 应为字典"
        total = result.get("totalCount")
        assert total is not None, "缺少 totalCount 字段"
        assert int(total) >= 0, f"totalCount 不应为负: {total}"

    @allure.title("基线统计卡片")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_baseline_statistics(self):
        result = assert_success(get_baseline_statistics(), "基线统计")
        assert isinstance(result, dict), "result 应为字典"


@allure.epic("HSC 脆弱性管理")
@allure.feature("脆弱性概览")
@allure.story("核心指标")
class TestRiskOverviewMetrics:

    @allure.title("核心指标-week")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_risk_metrics_week(self):
        result = assert_success(get_risk_overview_metrics("week"), "核心指标-week")
        assert isinstance(result, dict), "result 应为字典"
        metrics = result.get("metrics", [])
        assert isinstance(metrics, list) and metrics, "metrics 应为非空数组"

    @allure.title("核心指标-多周期")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("period", ["week", "month", "quarter", "year"])
    def test_risk_metrics_periods(self, period):
        result = assert_success(get_risk_overview_metrics(period), f"核心指标-{period}")
        assert isinstance(result, dict), "result 应为字典"

    @allure.title("核心指标-dates 与 values 长度一致")
    @allure.severity(allure.severity_level.NORMAL)
    def test_risk_metrics_dates_values_match(self):
        result = assert_success(get_risk_overview_metrics("week"), "核心指标-week")
        for m in result.get("metrics", []):
            dates = m.get("dates") or []
            values = m.get("values") or []
            assert len(dates) == len(values), \
                f"指标 {m.get('name')} dates({len(dates)}) 与 values({len(values)}) 长度不一致"


@allure.epic("HSC 脆弱性管理")
@allure.feature("脆弱性概览")
@allure.story("未授权访问")
class TestVulnOverviewNoAuth:

    @allure.title("无 Token 查询高风险主机列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_high_risk_host_no_token(self):
        resp = request_no_auth("post", f"{VULN_BASE}/host/assetList",
                               msg="无Token查询高风险主机列表",
                               json={"pageNum": 1, "pageSize": 10, "condition": {}})
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
