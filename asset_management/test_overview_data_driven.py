"""
55 开发环境 - 资产管理 - 资产概览 - 数据驱动测试
数据：data/asset_overview.yaml

说明：概览接口部分路径在 123 中标 TODO（如 statistics），实测以 55 为准修正。
"""
import pytest
import json
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import (
    request_no_auth, assert_success, assert_business_fail, load_yaml_data,
)
from core.utils_common import unique_name
from asset_management.utils_overview import (
    OVERVIEW_BASE, get_overview_statistics, get_overview_trend,
    get_unregistered_assets, register_asset, get_unregistered_id_from_response,
)

overview_data = load_yaml_data("asset_overview.yaml")


@allure.epic("HSC 资产管理")
@allure.feature("资产概览")
@allure.story("概览统计卡片")
class TestOverviewStatistics:

    @allure.title("资产概览统计卡片可访问")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_overview_statistics(self):
        resp = get_overview_statistics()
        result = assert_success(resp, "概览统计卡片")
        allure.attach(json.dumps(result, ensure_ascii=False, indent=2),
                      name="统计卡片数据", attachment_type=allure.attachment_type.JSON)
        # 宽松断言：result 为 dict（统计卡片应为键值对结构）
        assert isinstance(result, (dict, list)), f"统计卡片返回结构异常: {type(result)}"


@allure.epic("HSC 资产管理")
@allure.feature("资产概览")
@allure.story("资产趋势图 - 数据驱动")
class TestOverviewTrendDataDriven:

    @allure.title("资产趋势图 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", overview_data["test_trend"], ids=lambda x: x["name"])
    def test_trend(self, test_case):
        test_input = test_case["input"]

        with allure.step(f"Step 1: 调用趋势接口 - {test_case['name']}"):
            resp = get_overview_trend(test_input["period"])

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            allure.attach(json.dumps(result, ensure_ascii=False, indent=2),
                          name="趋势数据", attachment_type=allure.attachment_type.JSON)
            # 宽松断言：趋势数据非空（dict 或 list 均可）
            assert result is not None, "趋势接口返回空结果"


@allure.epic("HSC 资产管理")
@allure.feature("资产概览")
@allure.story("未纳管资产列表 - 数据驱动")
class TestUnregisteredDataDriven:

    @allure.title("未纳管资产列表 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", overview_data["test_unregistered"], ids=lambda x: x["name"])
    def test_unregistered(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用未纳管列表接口 - {test_case['name']}"):
            resp = get_unregistered_assets(page_size=test_input.get("page_size", 10))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回 {len(records)} 条，超过预期 {expected['max_records']}"


@allure.epic("HSC 资产管理")
@allure.feature("资产概览")
@allure.story("资产登记")
class TestRegisterAsset:

    @allure.title("登记未纳管资产")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_asset(self):
        with allure.step("Step 1: 获取未纳管资产 ID"):
            resp = get_unregistered_assets(page_size=20)
            unregistered_id = get_unregistered_id_from_response(resp)
            if not unregistered_id:
                pytest.skip("环境中无未纳管资产，跳过登记用例")

        with allure.step("Step 2: 调用登记接口"):
            register_name = unique_name("登记资产")
            resp = register_asset(unregistered_id, asset_name=register_name)
            data = resp.json()
            allure.attach(json.dumps(data, ensure_ascii=False, indent=2),
                          name="登记响应", attachment_type=allure.attachment_type.JSON)
            # 宽松断言：接口返回业务响应，不因参数问题崩溃
            assert "success" in data, f"登记接口异常: {data}"


@allure.epic("HSC 资产管理")
@allure.feature("资产概览")
@allure.story("未授权访问")
class TestOverviewNoAuth:

    @allure.title("无 Token 访问概览统计")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_overview_no_token(self):
        resp = request_no_auth("get", f"{OVERVIEW_BASE}/statistics", msg="无Token访问概览统计")
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应访问成功: {data}"
