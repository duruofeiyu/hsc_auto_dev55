"""
55 开发环境 - 资产管理 - 网站(Web)资产 - 数据驱动测试
数据：data/asset_web.yaml
"""
import pytest
import json
import uuid
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import (
    request_no_auth, assert_success, assert_business_fail, load_yaml_data,
)
from core.utils_common import unique_name
from asset_management.utils_web import (
    WEB_BASE, KEYWORD_FIELDS,
    build_web_payload, query_web_assets, create_web_asset,
    update_web_asset, delete_web_asset, get_web_detail,
    build_web_payload_from_detail,
)

web_data = load_yaml_data("asset_web.yaml")


def _new_web_name(prefix="Web"):
    return unique_name(prefix=prefix)


def _new_url():
    return f"https://{uuid.uuid4().hex[:8]}.example.com"


def _query_payload(input_dict):
    default = {
        "pageNum": 1, "pageSize": 10, "keyword": "",
        "keywordFields": KEYWORD_FIELDS,
    }
    default.update(input_dict)
    return default


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("Web资产列表查询 - 数据驱动")
class TestQueryWebDataDriven:

    @allure.title("Web资产列表查询 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_data["test_query_web"], ids=lambda x: x["name"])
    def test_query_web(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_web_assets(_query_payload(test_input))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回 {len(records)} 条，超过预期 {expected['max_records']}"


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("新增Web资产 - 数据驱动")
class TestCreateWebDataDriven:

    @allure.title("新增Web资产 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_data["test_create_web"], ids=lambda x: x["name"])
    def test_create_web(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("asset_name", _new_web_name())
        kwargs.setdefault("url", _new_url())
        payload = build_web_payload(**kwargs)

        web_id = None
        try:
            with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
                resp = create_web_asset(payload)
                allure.attach(json.dumps(payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    web_id = assert_success(resp, test_case['name'])
                    assert web_id, "创建成功但未返回 Web 资产 id"
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if web_id:
                with allure.step("Step 3: 清理数据"):
                    delete_web_asset(web_id)


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("编辑Web资产 - 数据驱动")
class TestUpdateWebDataDriven:

    @allure.title("编辑Web资产 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", web_data["test_update_web"], ids=lambda x: x["name"])
    def test_update_web(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        web_id = None
        try:
            with allure.step("Step 1: 创建待编辑Web资产"):
                web_id = assert_success(create_web_asset(build_web_payload(
                    asset_name=_new_web_name(), url=_new_url())), "编辑前置创建")

            with allure.step("Step 2: 获取详情构造完整 payload"):
                detail = assert_success(get_web_detail(web_id), "编辑前置详情")
                kwargs = {
                    "asset_name": detail.get("assetName"),
                    "url": detail.get("url"),
                    "asset_value": detail.get("assetValue"),
                    "is_intranet": detail.get("isIntranet"),
                    "ip_list": detail.get("ipList"),
                    "port_num": detail.get("portNum"),
                    "icp_rec_num": detail.get("icpRecNum"),
                    "ps_rec_num": detail.get("psRecNum"),
                    "owner": detail.get("owner"),
                    "owner_phone": detail.get("ownerPhone"),
                    "owner_email": detail.get("ownerEmail"),
                    "remark": detail.get("remark"),
                }
                kwargs.update(test_input.get("payload", {}))
                update_payload = build_web_payload(**kwargs)

            with allure.step(f"Step 3: 调用编辑接口 - {test_case['name']}"):
                resp = update_web_asset(web_id, update_payload)
                allure.attach(json.dumps(update_payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 4: 断言结果"):
                if expected["success"]:
                    assert_success(resp, test_case['name'])
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if web_id:
                with allure.step("Step 5: 清理数据"):
                    delete_web_asset(web_id)


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("删除Web资产 - 数据驱动")
class TestDeleteWebDataDriven:

    @allure.title("删除Web资产 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_data["test_delete_web"], ids=lambda x: x["name"])
    def test_delete_web(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_web_asset(test_input["web_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("Web资产生命周期闭环")
class TestWebLifecycle:

    @allure.title("创建→详情→修改→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_web_full_lifecycle(self):
        web_id = None
        try:
            with allure.step("Step 1: 创建Web资产"):
                web_id = assert_success(create_web_asset(build_web_payload(
                    asset_name=_new_web_name(), url=_new_url())), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_web_detail(web_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 修改负责人"):
                update_payload = build_web_payload_from_detail(detail)
                update_payload["owner"] = "闭环新负责人"
                assert_success(update_web_asset(web_id, update_payload), "闭环修改")

            with allure.step("Step 4: 删除"):
                assert_success(delete_web_asset(web_id), "闭环删除")
                web_id = None
        finally:
            if web_id:
                delete_web_asset(web_id)


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("安全探测")
class TestWebSecurity:

    @allure.title("安全探测-SQL注入URL（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_web_sql_injection(self):
        payload = build_web_payload(asset_name=_new_web_name(), url="https://x.com/' OR '1'='1")
        resp = create_web_asset(payload)
        data = resp.json()
        allure.attach(json.dumps(data, ensure_ascii=False, indent=2),
                      name="注入响应", attachment_type=allure.attachment_type.JSON)
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_web_asset(data["result"])


@allure.epic("HSC 资产管理")
@allure.feature("Web资产")
@allure.story("未授权访问")
class TestWebNoAuth:

    @allure.title("无 Token 查询Web资产列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_web_no_token(self):
        resp = request_no_auth("post", f"{WEB_BASE}/list", msg="无Token查询Web列表",
                               json=_query_payload({}))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
