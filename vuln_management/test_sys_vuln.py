"""
55 开发环境 - 脆弱性管理 - 系统漏洞 - 测试
覆盖：漏洞趋势、漏洞列表、漏洞详情、漏洞处置、资产漏洞列表
"""
import pytest
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import request_no_auth, assert_success, assert_business_fail
from vuln_management.utils_sys_vuln import (
    VULN_HOST_BASE, get_vuln_trend, query_vuln_list, get_vuln_detail,
    dispose_vuln, query_asset_vuln_list,
)


def _first_vuln_id(condition=None):
    """从漏洞列表取第一条漏洞 id（用于详情/处置测试）"""
    result = assert_success(query_vuln_list(page_size=1, condition=condition), "取漏洞id")
    records = result.get("list", []) if isinstance(result, dict) else []
    return records[0].get("id") if records else None


@allure.epic("HSC 脆弱性管理")
@allure.feature("系统漏洞")
@allure.story("漏洞趋势")
class TestVulnTrend:

    @allure.title("漏洞趋势-多周期")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("period", ["7d", "30d", "90d"])
    def test_vuln_trend(self, period):
        result = assert_success(get_vuln_trend(period), f"漏洞趋势-{period}")
        assert isinstance(result, (dict, list)), "趋势 result 应为字典或数组"


@allure.epic("HSC 脆弱性管理")
@allure.feature("系统漏洞")
@allure.story("漏洞列表")
class TestVulnList:

    @allure.title("漏洞列表-默认查询")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_vuln_list_default(self):
        result = assert_success(query_vuln_list(), "漏洞列表默认查询")
        assert isinstance(result, dict), "result 应为字典"
        assert isinstance(result.get("list", []), list), "list 应为数组"

    @allure.title("漏洞列表-分页")
    @allure.severity(allure.severity_level.NORMAL)
    def test_vuln_list_pagination(self):
        result = assert_success(query_vuln_list(page_num=1, page_size=5), "漏洞列表分页")
        records = result.get("list", [])
        assert len(records) <= 5, f"返回 {len(records)} 条，超过 pageSize=5"

    @allure.title("漏洞列表-关键字查询")
    @allure.severity(allure.severity_level.NORMAL)
    def test_vuln_list_keyword(self):
        result = assert_success(query_vuln_list(keyword="OpenSSH"), "漏洞列表关键字查询")
        assert isinstance(result, dict), "result 应为字典"

    @allure.title("漏洞列表-按状态筛选")
    @allure.severity(allure.severity_level.NORMAL)
    def test_vuln_list_by_status(self):
        result = assert_success(query_vuln_list(condition={"vulnStatus": ["PENDING"]}),
                                "漏洞列表按状态筛选")
        assert isinstance(result, dict), "result 应为字典"


@allure.epic("HSC 脆弱性管理")
@allure.feature("系统漏洞")
@allure.story("漏洞详情")
class TestVulnDetail:

    @allure.title("漏洞详情-正常")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_vuln_detail(self):
        vuln_id = _first_vuln_id()
        if not vuln_id:
            pytest.skip("无可用漏洞数据，跳过详情测试")
        result = assert_success(get_vuln_detail(vuln_id), "漏洞详情")
        assert isinstance(result, dict), "result 应为字典"

    @allure.title("漏洞详情-不存在ID")
    @allure.severity(allure.severity_level.NORMAL)
    def test_vuln_detail_not_exist(self):
        resp = get_vuln_detail("9999999999999999999")
        assert_business_fail(resp, "漏洞详情-不存在ID")


@allure.epic("HSC 脆弱性管理")
@allure.feature("系统漏洞")
@allure.story("漏洞处置")
class TestVulnDispose:

    @allure.title("漏洞处置-多种处置类型")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("op_type", ["CONFIRM", "IGNORE", "FALSE_POSITIVE"])
    def test_dispose_vuln(self, op_type):
        vuln_id = _first_vuln_id({"vulnStatus": ["PENDING"]})
        if not vuln_id:
            pytest.skip("无待处理漏洞，跳过处置测试")
        assert_success(dispose_vuln(vuln_id, op_type, remark="自动化处置测试"),
                       f"漏洞处置-{op_type}")

    @allure.title("漏洞处置-非法处置类型")
    @allure.severity(allure.severity_level.NORMAL)
    def test_dispose_invalid_type(self):
        vuln_id = _first_vuln_id()
        if not vuln_id:
            pytest.skip("无可用漏洞数据，跳过非法处置测试")
        resp = dispose_vuln(vuln_id, "INVALID_TYPE", remark="非法类型")
        assert_business_fail(resp, "漏洞处置-非法类型")

    @allure.title("漏洞处置-不存在漏洞ID")
    @allure.severity(allure.severity_level.NORMAL)
    def test_dispose_not_exist(self):
        resp = dispose_vuln("9999999999999999999", "CONFIRM", remark="不存在")
        assert_business_fail(resp, "漏洞处置-不存在ID")


@allure.epic("HSC 脆弱性管理")
@allure.feature("系统漏洞")
@allure.story("资产漏洞")
class TestAssetVuln:

    @allure.title("资产漏洞列表-默认查询")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_asset_vuln_list(self):
        result = assert_success(query_asset_vuln_list(), "资产漏洞列表")
        assert isinstance(result, dict), "result 应为字典"
        assert isinstance(result.get("list", []), list), "list 应为数组"


@allure.epic("HSC 脆弱性管理")
@allure.feature("系统漏洞")
@allure.story("未授权访问")
class TestSysVulnNoAuth:

    @allure.title("无 Token 查询漏洞列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_vuln_list_no_token(self):
        resp = request_no_auth("post", f"{VULN_HOST_BASE}/list", msg="无Token查询漏洞列表",
                               json={"pageNum": 1, "pageSize": 10, "condition": {}})
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
