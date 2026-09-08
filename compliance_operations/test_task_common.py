"""
55 开发环境 - 合规运营 - 通用任务 CRUD 数据驱动测试
数据：data/compliance_task.yaml
以 COMPLIANCE_NS 为代表 typeCode，覆盖 /compliance/task 通用 CRUD + 生命周期 + 安全 + 未授权 + 只读接口
"""
import pytest
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import (
    request_no_auth, assert_success, assert_business_fail, load_yaml_data,
)
from core.utils_common import unique_name
from compliance_operations.utils_compliance import (
    COMPLIANCE_TASK_BASE, ComplianceType, TaskStatus, ALL_TASK_STATUSES,
    build_task_payload, create_task, delete_task, query_task_list, get_task_report,
    query_recent_tasks, get_result_distribution,
)

task_data = load_yaml_data("compliance_task.yaml")


def _new_name(prefix="合规任务"):
    return unique_name(prefix=prefix)


def _build_payload(test_input):
    """根据测试数据构造创建 payload，支持缺字段场景"""
    type_code = test_input.get("type_code") or ComplianceType.NS
    if test_input.get("missing_type_code"):
        return {"taskName": _new_name()}
    if test_input.get("missing_task_name"):
        return {"typeCode": type_code}
    task_name = test_input.get("task_name")
    if task_name is None:
        task_name = _new_name()
    return build_task_payload(type_code, task_name)


# ======================== 1. 创建任务（数据驱动） ========================

@allure.epic("HSC 合规运营")
@allure.feature("通用任务")
@allure.story("创建任务 - 数据驱动")
class TestCreateTaskDataDriven:

    @allure.title("创建任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", task_data["test_create_task"], ids=lambda x: x["name"])
    def test_create_task(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        payload = _build_payload(test_input)
        task_id = None
        try:
            with allure.step(f"Step 1: 调用创建接口 - {test_case['name']}"):
                resp = create_task(payload)

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
                    delete_task(task_id)


# ======================== 2. 查询任务列表（数据驱动） ========================

@allure.epic("HSC 合规运营")
@allure.feature("通用任务")
@allure.story("查询任务列表 - 数据驱动")
class TestQueryTaskDataDriven:

    @allure.title("查询任务列表 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", task_data["test_query_task"], ids=lambda x: x["name"])
    def test_query_task(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_task_list(
                type_code=ComplianceType.NS,
                keyword=test_input.get("keyword"),
                keyword_fields=test_input.get("keyword_fields"),
                latest_status=test_input.get("latest_status"),
            )

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            assert isinstance(result, dict), "查询结果应为字典"
            assert "list" in result and "total" in result, "结果应含 list 与 total 字段"


# ======================== 3. 删除任务（数据驱动） ========================

@allure.epic("HSC 合规运营")
@allure.feature("通用任务")
@allure.story("删除任务 - 数据驱动")
class TestDeleteTaskDataDriven:

    @allure.title("删除任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", task_data["test_delete_task"], ids=lambda x: x["name"])
    def test_delete_task(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_task(test_input["task_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


# ======================== 4. 任务生命周期闭环 ========================

@allure.epic("HSC 合规运营")
@allure.feature("通用任务")
@allure.story("任务生命周期闭环")
class TestTaskLifecycle:

    @allure.title("创建→查询→报告→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_task_full_lifecycle(self):
        task_name = _new_name()
        task_id = None
        try:
            with allure.step("Step 1: 创建任务"):
                task_id = assert_success(create_task(build_task_payload(
                    ComplianceType.NS, task_name)), "闭环创建")

            with allure.step("Step 2: 查询列表验证出现"):
                result = assert_success(query_task_list(
                    type_code=ComplianceType.NS, task_name=task_name), "闭环查询")
                found = any(i.get("id") == task_id for i in result.get("list", []))
                assert found, f"新创建任务 {task_id} 应在列表中查到"

            with allure.step("Step 3: 查询报告"):
                report = assert_success(get_task_report(task_id), "闭环报告")
                assert report.get("taskId") == task_id, "报告 taskId 应一致"
                assert report.get("typeCode") == ComplianceType.NS, "报告 typeCode 应一致"

            with allure.step("Step 4: 删除"):
                assert_success(delete_task(task_id), "闭环删除")
                task_id = None
        finally:
            if task_id:
                delete_task(task_id)

    @allure.title("批量创建后逐个删除")
    @allure.severity(allure.severity_level.NORMAL)
    def test_batch_create_and_delete(self):
        ids = []
        try:
            with allure.step("Step 1: 批量创建 3 个任务"):
                for i in range(3):
                    tid = assert_success(create_task(build_task_payload(
                        ComplianceType.NS, _new_name(f"批量{i}"))), "批量创建")
                    ids.append(tid)
            with allure.step("Step 2: 逐个删除"):
                for tid in ids:
                    assert_success(delete_task(tid), "批量删除")
            ids = []
        finally:
            for tid in ids:
                delete_task(tid)


# ======================== 5. 安全探测 ========================

@allure.epic("HSC 合规运营")
@allure.feature("通用任务")
@allure.story("安全探测")
class TestTaskSecurity:

    @allure.title("安全探测-SQL注入任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_task_sql_injection(self):
        payload = build_task_payload(ComplianceType.NS, "' OR '1'='1")
        resp = create_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_task(data["result"])

    @allure.title("安全探测-XSS任务名（代表用例）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_task_xss(self):
        payload = build_task_payload(ComplianceType.NS, "<script>alert(1)</script>")
        resp = create_task(payload)
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"
        if data.get("success") and data.get("result"):
            delete_task(data["result"])


# ======================== 6. 未授权访问 ========================

@allure.epic("HSC 合规运营")
@allure.feature("通用任务")
@allure.story("未授权访问")
class TestTaskNoAuth:

    @allure.title("无 Token 创建任务")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_task_no_token(self):
        resp = request_no_auth("post", COMPLIANCE_TASK_BASE, msg="无Token创建任务",
                               json=build_task_payload(ComplianceType.NS, _new_name()))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应创建成功: {data}"


# ======================== 7. 合规总览只读接口 ========================

@allure.epic("HSC 合规运营")
@allure.feature("合规总览")
@allure.story("最近任务列表")
class TestComplianceOverview:

    @allure.title("查询合规总览最近任务")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_recent_tasks(self):
        with allure.step("Step 1: 查询最近任务"):
            resp = query_recent_tasks(status=TaskStatus.ALL, page_num=1, page_size=10)
        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, "合规总览最近任务")
            # 响应结构可能为 items[] 或 list[]，两种都兼容
            assert isinstance(result, dict), "最近任务结果应为字典"


# ======================== 8. 等保结果分布只读接口 ========================

@allure.epic("HSC 合规运营")
@allure.feature("等保测评")
@allure.story("结果分布统计")
class TestResultDistribution:

    @allure.title("查询等保结果分布统计")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_result_distribution(self):
        with allure.step("Step 1: 查询结果分布"):
            resp = get_result_distribution()
        with allure.step("Step 2: 断言结果"):
            assert_success(resp, "等保结果分布统计")
