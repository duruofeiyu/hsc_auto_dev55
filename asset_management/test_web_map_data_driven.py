"""
55 开发环境 - 资产管理 - 网站测绘任务 - 数据驱动测试
数据：data/web_map_task.yaml
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
from asset_management.utils_web_map import (
    WEB_MAP_BASE, build_web_map_payload, query_web_map_tasks, create_web_map_task,
    update_web_map_task, delete_web_map_task, get_web_map_detail, get_web_map_execution,
)

web_map_data = load_yaml_data("web_map_task.yaml")


def _new_web_map_name(prefix="网站测绘"):
    return unique_name(prefix=prefix)


def _query_payload(input_dict):
    default = {
        "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
        "keyword": "", "keywordFields": ["taskNo", "taskName", "createBy"],
    }
    default.update(input_dict)
    return default


def _detail_to_kwargs(detail):
    """详情 camelCase → build_web_map_payload snake_case 参数映射"""
    if not isinstance(detail, dict):
        return {}
    return {
        "task_name": detail.get("taskName"),
        "scan_target": detail.get("scanTarget"),
        "schedule_type": detail.get("scheduleType"),
        "task_status": detail.get("taskStatus"),
        "sync_to_asset": detail.get("syncToAsset"),
        "scan_range": detail.get("scanRange"),
        "scan_depth": detail.get("scanDepth"),
        "crawl_strategy": detail.get("crawlStrategy"),
        "scan_level": detail.get("scanLevel"),
        "max_crawl_duration": detail.get("maxCrawlDuration"),
        "concurrency": detail.get("concurrency"),
        "rate_limit": detail.get("rateLimit"),
        "connect_timeout": detail.get("connectTimeout"),
        "retries": detail.get("retries"),
        "max_response_size_mb": detail.get("maxResponseSizeMb"),
        "enable_js": detail.get("enableJs"),
        "enable_jsluice": detail.get("enableJsluice"),
        "enable_form_filling": detail.get("enableFormFilling"),
        "form_fill_values": detail.get("formFillValues"),
        "user_agent": detail.get("userAgent"),
        "custom_headers": detail.get("customHeaders"),
        "enable_auth_scan": detail.get("enableAuthScan"),
        "schedule_config": detail.get("scheduleConfig"),
    }


@allure.epic("HSC 资产管理")
@allure.feature("网站测绘任务")
@allure.story("网站测绘任务列表查询 - 数据驱动")
class TestQueryWebMapDataDriven:

    @allure.title("网站测绘任务列表查询 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_map_data["test_query_web_map"], ids=lambda x: x["name"])
    def test_query_web_map(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_web_map_tasks(_query_payload(test_input))

        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, test_case['name'])
            records = result.get("list", []) if isinstance(result, dict) else []
            if "max_records" in expected:
                assert len(records) <= expected["max_records"], \
                    f"返回 {len(records)} 条，超过预期 {expected['max_records']}"


@allure.epic("HSC 资产管理")
@allure.feature("网站测绘任务")
@allure.story("创建网站测绘任务 - 数据驱动")
class TestCreateWebMapDataDriven:

    @allure.title("创建网站测绘任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_map_data["test_create_web_map"], ids=lambda x: x["name"])
    def test_create_web_map(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        kwargs = dict(test_input.get("payload", {}))
        kwargs.setdefault("task_name", _new_web_map_name())
        payload = build_web_map_payload(**kwargs)

        task_id = None
        try:
            with allure.step(f"Step 1: 调用创建接口 - {test_case['name']}"):
                resp = create_web_map_task(payload)
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
                    delete_web_map_task(task_id)


@allure.epic("HSC 资产管理")
@allure.feature("网站测绘任务")
@allure.story("编辑网站测绘任务 - 数据驱动")
class TestUpdateWebMapDataDriven:

    @allure.title("编辑网站测绘任务 - 数据驱动")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", web_map_data["test_update_web_map"], ids=lambda x: x["name"])
    def test_update_web_map(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        task_id = None
        try:
            with allure.step("Step 1: 创建待编辑任务"):
                task_id = assert_success(create_web_map_task(build_web_map_payload(
                    task_name=_new_web_map_name())), "编辑前置创建")

            with allure.step("Step 2: 获取详情构造完整 payload"):
                detail = assert_success(get_web_map_detail(task_id), "编辑前置详情")
                kwargs = _detail_to_kwargs(detail)
                kwargs.update(test_input.get("payload", {}))
                for k in list(kwargs):
                    if kwargs[k] == "__unique_name__":
                        kwargs[k] = _new_web_map_name("编辑后")
                update_payload = build_web_map_payload(**kwargs)

            with allure.step(f"Step 3: 调用编辑接口 - {test_case['name']}"):
                resp = update_web_map_task(task_id, update_payload)
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
                    delete_web_map_task(task_id)


@allure.epic("HSC 资产管理")
@allure.feature("网站测绘任务")
@allure.story("删除网站测绘任务 - 数据驱动")
class TestDeleteWebMapDataDriven:

    @allure.title("删除网站测绘任务 - 数据驱动")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", web_map_data["test_delete_web_map"], ids=lambda x: x["name"])
    def test_delete_web_map(self, test_case):
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_web_map_task(test_input["task_id"])

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 资产管理")
@allure.feature("网站测绘任务")
@allure.story("网站测绘任务生命周期闭环")
class TestWebMapLifecycle:

    @allure.title("创建→详情→修改→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_web_map_full_lifecycle(self):
        task_id = None
        try:
            with allure.step("Step 1: 创建网站测绘任务"):
                task_id = assert_success(create_web_map_task(build_web_map_payload(
                    task_name=_new_web_map_name())), "闭环创建")

            with allure.step("Step 2: 详情验证"):
                detail = assert_success(get_web_map_detail(task_id), "闭环详情")
                assert isinstance(detail, dict), "详情应为字典"

            with allure.step("Step 3: 修改任务状态为禁用"):
                kwargs = _detail_to_kwargs(detail)
                kwargs["task_status"] = "DISABLED"
                assert_success(update_web_map_task(task_id, build_web_map_payload(**kwargs)), "闭环修改")

            with allure.step("Step 4: 删除"):
                assert_success(delete_web_map_task(task_id), "闭环删除")
                task_id = None
        finally:
            if task_id:
                delete_web_map_task(task_id)

    @allure.title("执行状态接口可访问性探测")
    @allure.severity(allure.severity_level.NORMAL)
    def test_web_map_execution_endpoint(self):
        task_id = None
        try:
            task_id = assert_success(create_web_map_task(build_web_map_payload(
                task_name=_new_web_map_name())), "执行状态前置创建")
            resp = get_web_map_execution(task_id)
            data = resp.json()
            allure.attach(json.dumps(data, ensure_ascii=False, indent=2),
                          name="执行状态响应", attachment_type=allure.attachment_type.JSON)
            # 宽松断言：接口返回业务响应（success 字段存在），不因任务未完成而 500
            assert "success" in data or "code" in data, f"执行状态接口异常: {data}"
        finally:
            if task_id:
                delete_web_map_task(task_id)


@allure.epic("HSC 资产管理")
@allure.feature("网站测绘任务")
@allure.story("未授权访问")
class TestWebMapNoAuth:

    @allure.title("无 Token 查询网站测绘任务列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_web_map_no_token(self):
        resp = request_no_auth("post", f"{WEB_MAP_BASE}/list", msg="无Token查询网站测绘任务列表",
                               json=_query_payload({}))
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
