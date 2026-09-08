"""
55 开发环境 - 资产管理 - 物联网(IoT)资产 - 数据驱动测试
数据：data/asset_iot.yaml
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
from asset_management.utils_iot import (
    IOT_BASE, KEYWORD_FIELDS,
    build_iot_payload, query_iot_assets, create_iot_asset,
    update_iot_asset, delete_iot_asset, get_iot_detail,
    build_iot_payload_from_detail,
)

iot_data = load_yaml_data("asset_iot.yaml")


def _new_iot_name(prefix="IoT"):
    return unique_name(prefix=prefix)


def _new_ip():
    a = int(uuid.uuid4().hex[:2], 16) % 256
    b = int(uuid.uuid4().hex[:2], 16) % 254 + 1
    return f"10.201.{a}.{b}"


def _query_payload(input_dict):
    default = {
        "pageNum": 1, "pageSize": 10, "keyword": "",
        "keywordFields": KEYWORD_FIELDS, "condition": {},
    }
    default.update(input_dict)
    return default


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("IoT资产列表查询 - 数据驱动")
class TestQueryIotDataDriven:

    @allure.title("IoT资产列表查询 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", iot_data["test_query_iot"], ids=lambda x: x["name"])
    def test_query_iot(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_iot_assets(_query_payload(test_input))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回 {len(records)} 条，超过预期 {expected['max_records']}"


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("新增IoT资产 - 数据驱动")
class TestCreateIotDataDriven:

    @allure.title("新增IoT资产 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", iot_data["test_create_iot"], ids=lambda x: x["name"])
    def test_create_iot(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("asset_name", _new_iot_name())
        kwargs.setdefault("ip", _new_ip())
        payload = build_iot_payload(**kwargs)

        iot_id = None
        try:
            with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
                resp = create_iot_asset(payload)
                allure.attach(json.dumps(payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    iot_id = assert_success(resp, test_case['name'])
                    assert iot_id, "创建成功但未返回 IoT 资产 id"
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if iot_id:
                with allure.step("Step 3: 清理数据"):
                    delete_iot_asset(iot_id)


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("编辑IoT资产 - 数据驱动")
class TestUpdateIotDataDriven:

    @allure.title("编辑IoT资产 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", iot_data["test_update_iot"], ids=lambda x: x["name"])
    def test_update_iot(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        iot_id = None
        try:
            with allure.step("Step 1: 创建待编辑IoT资产"):
                iot_id = assert_success(create_iot_asset(build_iot_payload(
                    asset_name=_new_iot_name(), ip=_new_ip())), "编辑前置创建")

            with allure.step("Step 2: 获取详情构造完整 payload"):
                detail = assert_success(get_iot_detail(iot_id), "编辑前置详情")
                kwargs = {
                    "asset_name": detail.get("assetName"),
                    "ip": detail.get("ip"),
                    "serial_number": detail.get("serialNumber"),
                    "protocol": detail.get("protocol"),
                    "firmware": detail.get("firmware"),
                    "mac": detail.get("mac"),
                    "brand": detail.get("brand"),
                    "owner": detail.get("owner"),
                    "owner_phone": detail.get("ownerPhone"),
                    "owner_email": detail.get("ownerEmail"),
                    "tag_ids": detail.get("tagIds"),
                    "remark": detail.get("remark"),
                }
                kwargs.update(test_input.get("payload", {}))
                update_payload = build_iot_payload(**kwargs)

            with allure.step(f"Step 3: 调用编辑接口 - {test_case['name']}"):
                resp = update_iot_asset(iot_id, update_payload)
                allure.attach(json.dumps(update_payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 4: 断言结果"):
                if expected["success"]:
                    assert_success(resp, test_case['name'])
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if iot_id:
                with allure.step("Step 5: 清理数据"):
                    delete_iot_asset(iot_id)


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("删除IoT资产 - 数据驱动")
class TestDeleteIotDataDriven:

    @allure.title("删除IoT资产 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", iot_data["test_delete_iot"], ids=lambda x: x["name"])
    def test_delete_iot(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_iot_asset(test_input["iot_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("IoT资产生命周期闭环")
class TestIotLifecycle:

    @allure.title("创建→详情→修改→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_iot_full_lifecycle(self):
        iot_id = None
        try:
            with allure.step("Step 1: 创建IoT资产"):
                iot_id = assert_success(create_iot_asset(build_iot_payload(
                    asset_name=_new_iot_name(), ip=_new_ip(), brand="闭环品牌")), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_iot_detail(iot_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 修改品牌"):
                update_payload = build_iot_payload_from_detail(detail)
                update_payload["brand"] = "闭环新品牌"
                assert_success(update_iot_asset(iot_id, update_payload), "闭环修改")

            with allure.step("Step 4: 删除"):
                assert_success(delete_iot_asset(iot_id), "闭环删除")
                iot_id = None
        finally:
            if iot_id:
                delete_iot_asset(iot_id)


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("安全探测")
class TestIotSecurity:

    @allure.title("安全探测-SQL注入名称（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_iot_sql_injection(self):
        payload = build_iot_payload(asset_name="' OR '1'='1", ip=_new_ip())
        resp = create_iot_asset(payload)
        data = resp.json()
        allure.attach(json.dumps(data, ensure_ascii=False, indent=2),
                      name="注入响应", attachment_type=allure.attachment_type.JSON)
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_iot_asset(data["result"])


@allure.epic("HSC 资产管理")
@allure.feature("IoT资产")
@allure.story("未授权访问")
class TestIotNoAuth:

    @allure.title("无 Token 查询IoT资产列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_iot_no_token(self):
        resp = request_no_auth("post", f"{IOT_BASE}/list", msg="无Token查询IoT列表",
                               json=_query_payload({}))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
