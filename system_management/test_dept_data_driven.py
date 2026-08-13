"""
55 开发环境 - 系统管理 - 部门管理 - 数据驱动版
使用 YAML 管理测试数据，一个用例跑多组数据
"""
import pytest
import time
import json
import allure
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import (
    get_headers,
    assert_success,
    assert_business_fail,
    request_wrapper,
    load_yaml_data,
)
from config import BASE_URL
import requests

from system_management.utils_common import unique_name, unique_code
from system_management.utils_dept import (
    query_depts,
    create_dept,
    update_dept,
    delete_dept,
    batch_delete_depts,
    build_dept_payload,
    DEPT_BASE,
)


# 加载测试数据
dept_data = load_yaml_data("dept_data.yaml")


def unique_dept_name(prefix="部门"):
    """生成唯一部门名称"""
    return unique_name(prefix=prefix)


def unique_dept_code(prefix="yaml"):
    """生成唯一部门编码"""
    return unique_code(prefix=prefix)


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("部门列表查询 - 数据驱动")
class TestQueryDeptDataDriven:
    """部门列表查询 - 数据驱动测试"""

    @allure.title("部门列表查询 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证部门列表查询功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", dept_data["test_query_dept_list"], ids=lambda x: x["name"])
    def test_query_dept_list(self, test_case):
        """部门列表查询 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_depts(test_input)
            allure.attach(
                json.dumps(test_input, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = assert_success(resp, test_case['name'])
            result = data.get("result", {})
            records = result.get("list", [])

            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回记录数 {len(records)} 超过预期 {expected['max_records']}"
            if "total" in expected:
                assert result.get("total") == expected["total"], \
                    f"total 不匹配: 预期 {expected['total']}, 实际 {result.get('total')}"


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("新增部门 - 数据驱动")
class TestCreateDeptDataDriven:
    """新增部门 - 数据驱动测试"""

    @allure.title("新增部门 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证新增部门功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", dept_data["test_create_dept"], ids=lambda x: x["name"])
    def test_create_dept(self, test_case):
        """新增部门 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        dept_name = unique_dept_name() if not test_input.get("dept_name") else test_input["dept_name"]
        payload = build_dept_payload(
            dept_name=dept_name,
            parent_id=test_input.get("parent_id", "1"),
            dept_code=test_input.get("dept_code", unique_dept_code()),
            dept_status=test_input.get("dept_status", 0)
        )

        dept_id = None
        try:
            with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
                resp = create_dept(payload)
                allure.attach(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    name="请求数据",
                    attachment_type=allure.attachment_type.JSON
                )

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    data = assert_success(resp, test_case['name'])
                    dept_id = data.get("result")
                    assert dept_id is not None
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if dept_id:
                with allure.step("Step 3: 清理数据"):
                    delete_dept(dept_id)


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("编辑部门 - 数据驱动")
class TestUpdateDeptDataDriven:
    """编辑部门 - 数据驱动测试"""

    @allure.title("编辑部门 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证编辑部门功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", dept_data["test_update_dept"], ids=lambda x: x["name"])
    def test_update_dept(self, test_case):
        """编辑部门 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 先创建部门
        payload = build_dept_payload(
            dept_name=unique_dept_name(),
            dept_code=f"yaml_{os.urandom(2).hex()}"
        )
        dept_id = None
        try:
            with allure.step("Step 1: 创建待编辑部门"):
                resp_create = create_dept(payload)
                data_create = assert_success(resp_create, "编辑前置创建")
                dept_id = data_create.get("result")

            # 编辑
            update_payload = build_dept_payload(
                dept_name=test_input.get("dept_name", unique_dept_name("编辑后")),
                dept_code=payload["deptCode"],
                dept_status=test_input.get("dept_status", 0)
            )

            with allure.step(f"Step 2: 调用编辑接口 - {test_case['name']}"):
                resp = update_dept(dept_id, update_payload)
                allure.attach(
                    json.dumps(update_payload, ensure_ascii=False, indent=2),
                    name="请求数据",
                    attachment_type=allure.attachment_type.JSON
                )

            with allure.step("Step 3: 断言结果"):
                if expected["success"]:
                    assert_success(resp, test_case['name'])
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if dept_id:
                with allure.step("Step 4: 清理数据"):
                    delete_dept(dept_id)


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("删除部门 - 数据驱动")
class TestDeleteDeptDataDriven:
    """删除部门 - 数据驱动测试"""

    @allure.title("删除部门 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证删除部门功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", dept_data["test_delete_dept"], ids=lambda x: x["name"])
    def test_delete_dept(self, test_case):
        """删除部门 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_dept(test_input["dept_id"])
            allure.attach(
                json.dumps({"dept_id": test_input["dept_id"]}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("批量删除部门 - 数据驱动")
class TestBatchDeleteDeptDataDriven:
    """批量删除部门 - 数据驱动测试"""

    @allure.title("批量删除部门 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证批量删除部门功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", dept_data["test_batch_delete_depts"], ids=lambda x: x["name"])
    def test_batch_delete_depts(self, test_case):
        """批量删除部门 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用批量删除接口 - {test_case['name']}"):
            resp = batch_delete_depts(test_input["dept_ids"])
            allure.attach(
                json.dumps({"dept_ids": test_input["dept_ids"]}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("部门IP段查询 - 数据驱动")
class TestQueryDeptIpDataDriven:
    """部门IP段查询 - 数据驱动测试"""

    @allure.title("部门IP段查询 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证部门IP段查询功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", dept_data["test_query_dept_ip"], ids=lambda x: x["name"])
    def test_query_dept_ip(self, test_case):
        """部门IP段查询 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = requests.get(
                f"{BASE_URL}/system/dept-ip/list",
                params={"deptId": test_input["dept_id"], "_t": int(time.time() * 1000)},
                headers=get_headers(),
                verify=False
            )
            allure.attach(
                json.dumps({"deptId": test_input["dept_id"]}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = assert_success(resp, test_case['name'])
            result = data.get("result", [])
            if expected.get("is_list"):
                assert isinstance(result, list)
