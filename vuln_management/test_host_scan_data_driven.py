"""
55 开发环境 - 脆弱性管理 - 主机漏洞扫描任务 - 数据驱动测试
数据：data/vuln_host_scan.yaml
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
from vuln_management.utils_host_scan import (
    HOST_SCAN_BASE, build_host_scan_payload, query_host_scan_tasks,
    create_host_scan_task, delete_host_scan_task, batch_delete_host_scan_tasks,
    get_host_scan_detail,
)

host_scan_data = load_yaml_data("vuln_host_scan.yaml")


def _new_name(prefix="主机扫描"):
    return unique_name(prefix=prefix)


def _query_payload(input_dict):
    default = {
        "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
        "condition": {}, "keyword": "", "keywordFields": ["taskNo", "taskName", "createBy"],
    }
    default.update(input_dict)
    return default


@allure.epic("HSC 脆弱性管理")
@allure.feature("主机漏洞扫描任务")
@allure.story("创建主机漏洞扫描任务 - 数据驱动")
class TestCreateHostScanDataDriven:

    @allure.title("创建主机漏洞扫描任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", host_scan_data["test_create_host_scan"], ids=lambda x: x["name"])
    def test_create_host_scan(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("task_name", _new_name())
        payload = build_host_scan_payload(**kwargs)

        task_id = None
        try:
            with allure.step(f"Step 1: 调用创建接口 - {test_case['name']}"):
                resp = create_host_scan_task(payload)

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
                    delete_host_scan_task(task_id)


@allure.epic("HSC 脆弱性管理")
@allure.feature("主机漏洞扫描任务")
@allure.story("查询主机漏洞扫描任务列表 - 数据驱动")
class TestQueryHostScanDataDriven:

    @allure.title("查询主机漏洞扫描任务列表 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", host_scan_data["test_query_host_scan"], ids=lambda x: x["name"])
    def test_query_host_scan(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_host_scan_tasks(_query_payload(test_input))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"]


@allure.epic("HSC 脆弱性管理")
@allure.feature("主机漏洞扫描任务")
@allure.story("删除主机漏洞扫描任务 - 数据驱动")
class TestDeleteHostScanDataDriven:

    @allure.title("删除主机漏洞扫描任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", host_scan_data["test_delete_host_scan"], ids=lambda x: x["name"])
    def test_delete_host_scan(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_host_scan_task(test_input["task_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 脆弱性管理")
@allure.feature("主机漏洞扫描任务")
@allure.story("主机漏洞扫描任务生命周期闭环")
class TestHostScanLifecycle:

    @allure.title("创建→详情→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_host_scan_full_lifecycle(self):
        task_id = None
        try:
            with allure.step("Step 1: 创建主机漏洞扫描任务"):
                task_id = assert_success(create_host_scan_task(build_host_scan_payload(
                    task_name=_new_name())), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_host_scan_detail(task_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 删除"):
                assert_success(delete_host_scan_task(task_id), "闭环删除")
                task_id = None
        finally:
            if task_id:
                delete_host_scan_task(task_id)

    @allure.title("批量删除主机漏洞扫描任务（数组）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_batch_delete_host_scan(self):
        ids = []
        try:
            with allure.step("Step 1: 创建 2 个任务"):
                for _ in range(2):
                    tid = assert_success(create_host_scan_task(build_host_scan_payload(
                        task_name=_new_name())), "批量删除前置创建")
                    ids.append(tid)
            with allure.step("Step 2: 批量删除"):
                assert_success(batch_delete_host_scan_tasks(ids), "批量删除")
            ids = []
        finally:
            for tid in ids:
                delete_host_scan_task(tid)


@allure.epic("HSC 脆弱性管理")
@allure.feature("主机漏洞扫描任务")
@allure.story("安全探测")
class TestHostScanSecurity:

    @allure.title("安全探测-SQL注入任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_host_scan_sql_injection(self):
        payload = build_host_scan_payload(task_name="' OR '1'='1")
        resp = create_host_scan_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_host_scan_task(data["result"])

    @allure.title("安全探测-XSS任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_host_scan_xss(self):
        payload = build_host_scan_payload(task_name="<script>alert(1)</script>")
        resp = create_host_scan_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_host_scan_task(data["result"])


@allure.epic("HSC 脆弱性管理")
@allure.feature("主机漏洞扫描任务")
@allure.story("未授权访问")
class TestHostScanNoAuth:

    @allure.title("无 Token 创建主机漏洞扫描任务")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_host_scan_no_token(self):
        resp = request_no_auth("post", HOST_SCAN_BASE, msg="无Token创建主机漏洞扫描任务",
                               json=build_host_scan_payload(task_name=_new_name()))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应创建成功: {data}"
