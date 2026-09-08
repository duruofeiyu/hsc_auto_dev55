"""
55 开发环境 - 脆弱性管理 - 处置历史 - 只读接口测试
"""
import pytest
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import request_no_auth, assert_success, assert_business_fail
from vuln_management.utils_disposal import (
    VULN_DISPOSAL_BASE, query_disposal_history, get_disposal_detail,
)


def _first_disposal_id():
    """从处置历史取第一条记录 id"""
    result = assert_success(query_disposal_history(page_size=1), "取处置历史id")
    records = result.get("list", []) if isinstance(result, dict) else []
    return records[0].get("id") if records else None


@allure.epic("HSC 脆弱性管理")
@allure.feature("处置历史")
@allure.story("处置历史列表")
class TestDisposalHistory:

    @allure.title("处置历史-默认查询")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_disposal_history_default(self):
        result = assert_success(query_disposal_history(), "处置历史默认查询")
        assert isinstance(result, dict), "result 应为字典"
        assert isinstance(result.get("list", []), list), "list 应为数组"

    @allure.title("处置历史-分页")
    @allure.severity(allure.severity_level.NORMAL)
    def test_disposal_history_pagination(self):
        result = assert_success(query_disposal_history(page_size=5), "处置历史分页")
        records = result.get("list", [])
        assert len(records) <= 5, f"返回 {len(records)} 条，超过 pageSize=5"

    @allure.title("处置历史-关键字查询")
    @allure.severity(allure.severity_level.NORMAL)
    def test_disposal_history_keyword(self):
        result = assert_success(query_disposal_history(keyword="自动化"), "处置历史关键字查询")
        assert isinstance(result, dict), "result 应为字典"


@allure.epic("HSC 脆弱性管理")
@allure.feature("处置历史")
@allure.story("处置历史详情")
class TestDisposalDetail:

    @allure.title("处置历史详情-正常")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_disposal_detail(self):
        disposal_id = _first_disposal_id()
        if not disposal_id:
            pytest.skip("无处置历史数据，跳过详情测试")
        result = assert_success(get_disposal_detail(disposal_id), "处置历史详情")
        assert isinstance(result, dict), "result 应为字典"

    @allure.title("处置历史详情-不存在ID")
    @allure.severity(allure.severity_level.NORMAL)
    def test_disposal_detail_not_exist(self):
        resp = get_disposal_detail("9999999999999999999")
        assert_business_fail(resp, "处置历史详情-不存在ID")


@allure.epic("HSC 脆弱性管理")
@allure.feature("处置历史")
@allure.story("未授权访问")
class TestDisposalNoAuth:

    @allure.title("无 Token 查询处置历史")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_disposal_history_no_token(self):
        resp = request_no_auth("post", f"{VULN_DISPOSAL_BASE}/list",
                               msg="无Token查询处置历史",
                               json={"pageNum": 1, "pageSize": 10, "condition": {}})
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
