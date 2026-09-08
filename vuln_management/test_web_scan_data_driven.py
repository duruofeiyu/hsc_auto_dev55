"""
55 开发环境 - 脆弱性管理 - Web 漏洞扫描任务 - 数据驱动测试
数据：data/vuln_web_scan.yaml
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
from vuln_management.utils_web_scan import (
    WEB_SCAN_BASE, build_web_scan_payload, query_web_scan_tasks,
    create_web_scan_task, update_web_scan_task, delete_web_scan_task,
    batch_delete_web_scan_tasks, get_web_scan_detail,
)

web_scan_data = load_yaml_data("vuln_web_scan.yaml")


def _new_name(prefix="Web扫描"):
    return unique_name(prefix=prefix)


def _query_payload(input_dict):
    default = {
        "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
        "condition": {}, "keyword": "", "keywordFields": ["taskNo", "taskName", "createBy"],
    }
    default.update(input_dict)
    return default


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("创建 Web 漏洞扫描任务 - 数据驱动")
class TestCreateWebScanDataDriven:

    @allure.title("创建 Web 漏洞扫描任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_scan_data["test_create_web_scan"], ids=lambda x: x["name"])
    def test_create_web_scan(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("task_name", _new_name())
        payload = build_web_scan_payload(**kwargs)

        task_id = None
        try:
            with allure.step(f"Step 1: 调用创建接口 - {test_case['name']}"):
                resp = create_web_scan_task(payload)

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
                    delete_web_scan_task(task_id)


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("查询 Web 漏洞扫描任务列表 - 数据驱动")
class TestQueryWebScanDataDriven:

    @allure.title("查询 Web 漏洞扫描任务列表 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_scan_data["test_query_web_scan"], ids=lambda x: x["name"])
    def test_query_web_scan(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_web_scan_tasks(_query_payload(test_input))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"]


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("删除 Web 漏洞扫描任务 - 数据驱动")
class TestDeleteWebScanDataDriven:

    @allure.title("删除 Web 漏洞扫描任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_scan_data["test_delete_web_scan"], ids=lambda x: x["name"])
    def test_delete_web_scan(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_web_scan_task(test_input["task_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("编辑 Web 漏洞扫描任务（已知缺陷）")
class TestUpdateWebScan:

    @allure.title("编辑 Web 漏洞扫描任务 - PUT 500 已知缺陷回归")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_web_scan_500(self):
        """apis.md §11.2.3：PUT /vuln/web-scan/{id} 对任何字段修改均返回 500。
        若后端已修复（非 500），则用例 XPASS，提示移除 xfail 标注。"""
        task_id = None
        try:
            with allure.step("Step 1: 创建待编辑任务"):
                task_id = assert_success(create_web_scan_task(build_web_scan_payload(
                    task_name=_new_name())), "编辑前置创建")

            with allure.step("Step 2: 调用编辑接口"):
                update_payload = build_web_scan_payload(task_name=_new_name("编辑后"))
                resp = update_web_scan_task(task_id, update_payload)

            with allure.step("Step 3: 断言（已知缺陷：500）"):
                is_500 = resp.status_code == 500 or resp.json().get("status") == 500
                if is_500:
                    pytest.xfail("已知缺陷：Web 漏洞扫描任务 PUT 修改返回 500（apis.md §11.2.3）")
                # 后端已修复，正常断言成功
                assert_success(resp, "编辑 Web 漏洞扫描任务")
        finally:
            if task_id:
                delete_web_scan_task(task_id)


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("Web 漏洞扫描任务生命周期闭环")
class TestWebScanLifecycle:

    @allure.title("创建→详情→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_web_scan_full_lifecycle(self):
        task_id = None
        try:
            with allure.step("Step 1: 创建 Web 漏洞扫描任务"):
                task_id = assert_success(create_web_scan_task(build_web_scan_payload(
                    task_name=_new_name())), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_web_scan_detail(task_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 删除"):
                assert_success(delete_web_scan_task(task_id), "闭环删除")
                task_id = None
        finally:
            if task_id:
                delete_web_scan_task(task_id)

    @allure.title("批量删除 Web 漏洞扫描任务（数组）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_batch_delete_web_scan(self):
        ids = []
        try:
            with allure.step("Step 1: 创建 2 个任务"):
                for _ in range(2):
                    tid = assert_success(create_web_scan_task(build_web_scan_payload(
                        task_name=_new_name())), "批量删除前置创建")
                    ids.append(tid)
            with allure.step("Step 2: 批量删除"):
                assert_success(batch_delete_web_scan_tasks(ids), "批量删除")
            ids = []
        finally:
            for tid in ids:
                delete_web_scan_task(tid)


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("安全探测")
class TestWebScanSecurity:

    @allure.title("安全探测-SQL注入任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_web_scan_sql_injection(self):
        payload = build_web_scan_payload(task_name="' OR '1'='1")
        resp = create_web_scan_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_web_scan_task(data["result"])

    @allure.title("安全探测-XSS任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_web_scan_xss(self):
        payload = build_web_scan_payload(task_name="<script>alert(1)</script>")
        resp = create_web_scan_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_web_scan_task(data["result"])


@allure.epic("HSC 脆弱性管理")
@allure.feature("Web漏洞扫描任务")
@allure.story("未授权访问")
class TestWebScanNoAuth:

    @allure.title("无 Token 创建 Web 漏洞扫描任务")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_web_scan_no_token(self):
        resp = request_no_auth("post", WEB_SCAN_BASE, msg="无Token创建Web漏洞扫描任务",
                               json=build_web_scan_payload(task_name=_new_name()))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应创建成功: {data}"
