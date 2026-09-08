"""
55 开发环境 - 资产管理 - 资产探测任务 - 数据驱动测试
数据：data/probe_task.yaml

说明：参数校验类用例 expected=false（期望后端拒绝），部分为 123「已提 bug」，
迁移到 55 后作回归验证——若仍 success=true 则用例失败，暴露缺陷未修复。
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
from asset_management.utils_probe import (
    PROBE_BASE, build_probe_payload, query_probe_tasks, create_probe_task,
    update_probe_task, delete_probe_task, get_probe_detail,
)

probe_data = load_yaml_data("probe_task.yaml")


def _new_probe_name(prefix="探测任务"):
    return unique_name(prefix=prefix)


def _query_payload(input_dict):
    default = {
        "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
        "keyword": "", "keywordFields": ["taskNo", "taskName", "createBy"],
    }
    default.update(input_dict)
    return default


def _detail_to_kwargs(detail):
    """详情 camelCase → build_probe_payload snake_case 参数映射"""
    if not isinstance(detail, dict):
        return {}
    return {
        "task_name": detail.get("taskName"),
        "scan_target": detail.get("scanTarget"),
        "schedule_type": detail.get("scheduleType"),
        "task_status": detail.get("taskStatus"),
        "sync_to_asset": detail.get("syncToAsset"),
        "speed": detail.get("speed"),
        "max_retries": detail.get("maxRetries"),
        "max_send_rate": detail.get("maxSendRate"),
        "version_intensity": detail.get("versionIntensity"),
        "host_timeout": detail.get("hostTimeout"),
        "port_timeout": detail.get("portTimeout"),
        "skip_host_discover": detail.get("skipHostDiscover"),
        "os_detect_enabled": detail.get("osDetectEnabled"),
        "host_detect_template": detail.get("hostDetectTemplate"),
        "service_detect_enabled": detail.get("serviceDetectEnabled"),
        "udp_scan_enabled": detail.get("udpScanEnabled"),
        "ports": detail.get("ports"),
        "udp_ports": detail.get("udpPorts"),
        "exclude_ports": detail.get("excludePorts"),
        "tcp_scan_method": detail.get("tcpScanMethod"),
    }


@allure.epic("HSC 资产管理")
@allure.feature("资产探测任务")
@allure.story("探测任务列表查询 - 数据驱动")
class TestQueryProbeDataDriven:

    @allure.title("探测任务列表查询 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", probe_data["test_query_probe"], ids=lambda x: x["name"])
    def test_query_probe(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_probe_tasks(_query_payload(test_input))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回 {len(records)} 条，超过预期 {expected['max_records']}"


@allure.epic("HSC 资产管理")
@allure.feature("资产探测任务")
@allure.story("创建探测任务 - 数据驱动")
class TestCreateProbeDataDriven:

    @allure.title("创建探测任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", probe_data["test_create_probe"], ids=lambda x: x["name"])
    def test_create_probe(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("task_name", _new_probe_name())
        payload = build_probe_payload(**kwargs)

        task_id = None
        try:
            with allure.step(f"Step 1: 调用创建接口 - {test_case['name']}"):
                resp = create_probe_task(payload)
                allure.attach(json.dumps(payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    task_id = assert_success(resp, test_case['name'])
                    assert task_id, "创建成功但未返回任务 id"
                else:
                    if expected.get("xfail") and resp.json().get("success"):
                        task_id = resp.json().get("result")  # 记录已创建任务id，finally清理脏数据
                        pytest.xfail(expected["xfail"])
                    assert_business_fail(resp, test_case['name'])
        finally:
            if task_id:
                with allure.step("Step 3: 清理数据"):
                    delete_probe_task(task_id)


@allure.epic("HSC 资产管理")
@allure.feature("资产探测任务")
@allure.story("编辑探测任务 - 数据驱动")
class TestUpdateProbeDataDriven:

    @allure.title("编辑探测任务 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", probe_data["test_update_probe"], ids=lambda x: x["name"])
    def test_update_probe(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        task_id = None
        try:
            with allure.step("Step 1: 创建待编辑任务"):
                task_id = assert_success(create_probe_task(build_probe_payload(
                    task_name=_new_probe_name())), "编辑前置创建")

            with allure.step("Step 2: 获取详情构造完整 payload"):
                detail = assert_success(get_probe_detail(task_id), "编辑前置详情")
                kwargs = _detail_to_kwargs(detail)
                kwargs.update(test_input.get("payload", {}))
                for k in list(kwargs):
                    if kwargs[k] == "__unique_name__":
                        kwargs[k] = _new_probe_name("编辑后")
                update_payload = build_probe_payload(**kwargs)

            with allure.step(f"Step 3: 调用编辑接口 - {test_case['name']}"):
                resp = update_probe_task(task_id, update_payload)
                allure.attach(json.dumps(update_payload, ensure_ascii=False, indent=2),
                              name="请求数据", attachment_type=allure.attachment_type.JSON)

            with allure.step("Step 4: 断言结果"):
                if expected["success"]:
                    assert_success(resp, test_case['name'])
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if task_id:
                with allure.step("Step 5: 清理数据"):
                    delete_probe_task(task_id)


@allure.epic("HSC 资产管理")
@allure.feature("资产探测任务")
@allure.story("删除探测任务 - 数据驱动")
class TestDeleteProbeDataDriven:

    @allure.title("删除探测任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", probe_data["test_delete_probe"], ids=lambda x: x["name"])
    def test_delete_probe(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_probe_task(test_input["task_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 资产管理")
@allure.feature("资产探测任务")
@allure.story("探测任务生命周期闭环")
class TestProbeLifecycle:

    @allure.title("创建→详情→修改→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_probe_full_lifecycle(self):
        task_id = None
        try:
            with allure.step("Step 1: 创建探测任务"):
                task_id = assert_success(create_probe_task(build_probe_payload(
                    task_name=_new_probe_name())), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_probe_detail(task_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 修改任务状态为禁用"):
                kwargs = _detail_to_kwargs(detail)
                kwargs["task_status"] = "DISABLED"
                assert_success(update_probe_task(task_id, build_probe_payload(**kwargs)), "闭环修改")

            with allure.step("Step 4: 删除"):
                assert_success(delete_probe_task(task_id), "闭环删除")
                task_id = None
        finally:
            if task_id:
                delete_probe_task(task_id)


@allure.epic("HSC 资产管理")
@allure.feature("资产探测任务")
@allure.story("未授权访问")
class TestProbeNoAuth:

    @allure.title("无 Token 查询探测任务列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_probe_no_token(self):
        resp = request_no_auth("post", f"{PROBE_BASE}/list", msg="无Token查询探测任务列表",
                               json=_query_payload({}))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
