"""
55 开发环境 - 脆弱性管理 - 弱口令检测任务 - 数据驱动测试
数据：data/vuln_weak_password.yaml
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
from vuln_management.utils_weak_password import (
    WEAK_SCAN_BASE, build_weak_password_payload, query_weak_password_tasks,
    create_weak_password_task, delete_weak_password_task, get_weak_password_detail,
)

weak_data = load_yaml_data("vuln_weak_password.yaml")


def _new_name(prefix="弱口令"):
    return unique_name(prefix=prefix)


@allure.epic("HSC 脆弱性管理")
@allure.feature("弱口令检测任务")
@allure.story("创建弱口令检测任务 - 数据驱动")
class TestCreateWeakPasswordDataDriven:

    @allure.title("创建弱口令检测任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", weak_data["test_create_weak_password"], ids=lambda x: x["name"])
    def test_create_weak_password(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("task_name", _new_name())
        payload = build_weak_password_payload(**kwargs)

        task_id = None
        try:
            with allure.step(f"Step 1: 调用创建接口 - {test_case['name']}"):
                resp = create_weak_password_task(payload)

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    task_id = assert_success(resp, test_case['name'])
                    assert task_id, "创建成功但未返回任务 id"
                else:
                    if expected.get("xfail") and resp.json().get("success"):
                        task_id = resp.json().get("result")
                        pytest.xfail(expected["xfail"])
                    assert_business_fail(resp, test_case['name'])
        finally:
            if task_id:
                with allure.step("Step 3: 清理数据"):
                    delete_weak_password_task(task_id)


@allure.epic("HSC 脆弱性管理")
@allure.feature("弱口令检测任务")
@allure.story("查询弱口令检测任务列表 - 数据驱动")
class TestQueryWeakPasswordDataDriven:

    @allure.title("查询弱口令检测任务列表 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", weak_data["test_query_weak_password"], ids=lambda x: x["name"])
    def test_query_weak_password(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_weak_password_tasks(keyword=test_input.get("keyword"))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"]


@allure.epic("HSC 脆弱性管理")
@allure.feature("弱口令检测任务")
@allure.story("删除弱口令检测任务 - 数据驱动")
class TestDeleteWeakPasswordDataDriven:

    @allure.title("删除弱口令检测任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", weak_data["test_delete_weak_password"], ids=lambda x: x["name"])
    def test_delete_weak_password(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_weak_password_task(test_input["task_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 脆弱性管理")
@allure.feature("弱口令检测任务")
@allure.story("弱口令检测任务生命周期闭环")
class TestWeakPasswordLifecycle:

    @allure.title("创建→详情→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_weak_password_full_lifecycle(self):
        task_id = None
        try:
            with allure.step("Step 1: 创建弱口令检测任务"):
                task_id = assert_success(create_weak_password_task(build_weak_password_payload(
                    task_name=_new_name())), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_weak_password_detail(task_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 删除"):
                assert_success(delete_weak_password_task(task_id), "闭环删除")
                task_id = None
        finally:
            if task_id:
                delete_weak_password_task(task_id)


@allure.epic("HSC 脆弱性管理")
@allure.feature("弱口令检测任务")
@allure.story("安全探测")
class TestWeakPasswordSecurity:

    @allure.title("安全探测-SQL注入任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_weak_password_sql_injection(self):
        payload = build_weak_password_payload(task_name="' OR '1'='1")
        resp = create_weak_password_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_weak_password_task(data["result"])

    @allure.title("安全探测-XSS任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_weak_password_xss(self):
        payload = build_weak_password_payload(task_name="<script>alert(1)</script>")
        resp = create_weak_password_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_weak_password_task(data["result"])


@allure.epic("HSC 脆弱性管理")
@allure.feature("弱口令检测任务")
@allure.story("未授权访问")
class TestWeakPasswordNoAuth:

    @allure.title("无 Token 创建弱口令检测任务")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_weak_password_no_token(self):
        resp = request_no_auth("post", WEAK_SCAN_BASE, msg="无Token创建弱口令检测任务",
                               json=build_weak_password_payload(task_name=_new_name()))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应创建成功: {data}"
