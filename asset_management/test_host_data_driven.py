"""
55 开发环境 - 资产管理 - 主机资产 - 数据驱动测试
使用 YAML 管理测试数据（data/asset_host.yaml），复用 base.request_wrapper 自动签名。

注意：asset 接口 result 为单层（result.list / result.total；create 返回 id 字符串），
assert_success 返回的就是 result 字段，直接按单层消费。
"""
import pytest
import json
import uuid
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import (
    request_wrapper, request_no_auth, assert_success, assert_business_fail,
    load_yaml_data, get_headers,
)
from core.utils_common import unique_name
from asset_management.utils_host import (
    HOST_BASE, KEYWORD_FIELDS,
    build_host_payload, query_hosts, create_host, update_host,
    delete_host, batch_delete_hosts, get_host_by_id,
)

host_data = load_yaml_data("asset_host.yaml")


def _new_host_name(prefix="主机"):
    """生成唯一主机名"""
    return unique_name(prefix=prefix)


def _new_ip():
    """生成唯一内网 IP（避免唯一约束冲突）"""
    a = int(uuid.uuid4().hex[:2], 16) % 256
    b = int(uuid.uuid4().hex[:2], 16) % 254 + 1
    return f"10.200.{a}.{b}"


def _query_payload(input_dict):
    """用默认值合并构造查询 payload"""
    default = {
        "pageNum": 1, "pageSize": 10, "keyword": "",
        "keywordFields": KEYWORD_FIELDS, "condition": {},
    }
    default.update(input_dict)
    return default


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("主机列表查询 - 数据驱动")
class TestQueryHostDataDriven:

    @allure.title("主机列表查询 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", host_data["test_query_host"], ids=lambda x: x["name"])
    def test_query_host(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_hosts(_query_payload(test_input))
            allure.attach(json.dumps(test_input, ensure_ascii=False, indent=2),
                          name="请求数据", attachment_type=allure.attachment_type.JSON)

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回 {len(records)} 条，超过预期 {expected['max_records']}"


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("新增主机 - 数据驱动")
class TestCreateHostDataDriven:

    @allure.title("新增主机 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", host_data["test_create_host"], ids=lambda x: x["name"])
    def test_create_host(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("asset_name", _new_host_name())
        kwargs.setdefault("ip", _new_ip())
        payload = build_host_payload(**kwargs)

        host_id = None
        try:
            with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
                resp = create_host(payload)
                allure.attach(json.dumps(payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    host_id = assert_success(resp, test_case['name'])
                    assert host_id, "创建成功但未返回主机 id"
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if host_id:
                with allure.step("Step 3: 清理数据"):
                    delete_host(host_id)


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("编辑主机 - 数据驱动")
class TestUpdateHostDataDriven:

    @allure.title("编辑主机 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", host_data["test_update_host"], ids=lambda x: x["name"])
    def test_update_host(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 前置创建
        create_payload = build_host_payload(asset_name=_new_host_name(), ip=_new_ip())
        host_id = None
        try:
            with allure.step("Step 1: 创建待编辑主机"):
                host_id = assert_success(create_host(create_payload), "编辑前置创建")

            # 构造完整修改 payload（先查当前值再覆盖）
            current = get_host_by_id(host_id) or {}
            kwargs = {
                "asset_name": current.get("assetName", create_payload["assetName"]),
                "ip": current.get("ip", create_payload["ip"]),
                "mac": current.get("mac", create_payload["mac"]),
                "os_name": current.get("os", create_payload["os"]),
                "owner": current.get("owner", create_payload["owner"]),
                "owner_phone": current.get("ownerPhone", create_payload["ownerPhone"]),
                "owner_email": current.get("ownerEmail", create_payload["ownerEmail"]),
                "remark": current.get("remark", create_payload["remark"]),
            }
            kwargs.update(test_input.get("payload", {}))
            for k in list(kwargs):
                if kwargs[k] == "__unique_name__":
                    kwargs[k] = _new_host_name("编辑后")
            update_payload = build_host_payload(**kwargs)

            with allure.step(f"Step 2: 调用编辑接口 - {test_case['name']}"):
                resp = update_host(host_id, update_payload)
                allure.attach(json.dumps(update_payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 3: 断言结果"):
                if expected["success"]:
                    assert_success(resp, test_case['name'])
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if host_id:
                with allure.step("Step 4: 清理数据"):
                    delete_host(host_id)


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("删除主机 - 数据驱动")
class TestDeleteHostDataDriven:

    @allure.title("删除主机 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", host_data["test_delete_host"], ids=lambda x: x["name"])
    def test_delete_host(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_host(test_input["host_id"])
            allure.attach(json.dumps({"host_id": test_input["host_id"]}, ensure_ascii=False),
                          name="请求数据", attachment_type=allure.attachment_type.JSON)

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("主机生命周期闭环")
class TestHostLifecycle:

    @allure.title("创建→查询→修改→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_host_full_lifecycle(self):
        host_id = None
        try:
            with allure.step("Step 1: 创建主机"):
                create_payload = build_host_payload(asset_name=_new_host_name(), ip=_new_ip())
                host_id = assert_success(create_host(create_payload), "闭环创建")

            with allure.step("Step 2: 查询验证创建成功"):
                found = get_host_by_id(host_id)
                assert found is not None, "创建后查询不到该主机"

            with allure.step("Step 3: 修改主机负责人"):
                current = get_host_by_id(host_id)
                update_payload = build_host_payload(
                    asset_name=current["assetName"], ip=current["ip"],
                    mac=current.get("mac"), os_name=current.get("os"),
                    owner="闭环新负责人",
                )
                assert_success(update_host(host_id, update_payload), "闭环修改")

            with allure.step("Step 4: 删除主机"):
                assert_success(delete_host(host_id), "闭环删除")
                deleted_id = host_id
                host_id = None

            with allure.step("Step 5: 验证删除后查询不到"):
                assert get_host_by_id(deleted_id) is None, "删除后仍能查询到该主机"
        finally:
            if host_id:
                delete_host(host_id)

    @allure.title("批量删除主机")
    @allure.severity(allure.severity_level.NORMAL)
    def test_batch_delete_hosts(self):
        ids = []
        try:
            with allure.step("Step 1: 创建 2 台主机"):
                for _ in range(2):
                    hid = assert_success(create_host(build_host_payload(
                        asset_name=_new_host_name(), ip=_new_ip())), "批量删除前置创建")
                    ids.append(hid)
            with allure.step("Step 2: 批量删除"):
                assert_success(batch_delete_hosts(ids), "批量删除")
            ids = []
        finally:
            for hid in ids:
                delete_host(hid)


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("安全探测")
class TestHostSecurity:

    @allure.title("安全探测-SQL注入名称（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_host_sql_injection(self):
        """验证注入字符串不会导致接口崩溃（500），行为可预期并记录"""
        payload = build_host_payload(asset_name="' OR '1'='1", ip=_new_ip())
        resp = create_host(payload)
        data = resp.json()
        allure.attach(json.dumps(data, ensure_ascii=False, indent=2),
                      name="注入响应", attachment_type=allure.attachment_type.JSON)
        # 核心断言：接口返回了业务响应（HTTP 200 + 有 success 字段），未因注入崩溃
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_host(data["result"])

    @allure.title("安全探测-XSS名称（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_host_xss(self):
        payload = build_host_payload(asset_name="<script>alert(1)</script>", ip=_new_ip())
        resp = create_host(payload)
        data = resp.json()
        allure.attach(json.dumps(data, ensure_ascii=False, indent=2),
                      name="XSS响应", attachment_type=allure.attachment_type.JSON)
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_host(data["result"])


@allure.epic("HSC 资产管理")
@allure.feature("主机资产")
@allure.story("未授权访问")
class TestHostNoAuth:

    @allure.title("无 Token 查询主机列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_host_no_token(self):
        resp = request_no_auth("post", f"{HOST_BASE}/list", msg="无Token查询主机列表",
                               json=_query_payload({}))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
