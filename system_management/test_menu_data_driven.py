"""
55 开发环境 - 菜单管理 - 数据驱动版
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

from system_management.utils_menu import (
    query_menu_tree,
    create_menu,
    update_menu,
    delete_menu,
    build_menu_payload,
    MENU_BASE,
)


# 加载测试数据
menu_data = load_yaml_data("menu_data.yaml")


def unique_menu_name(prefix):
    """生成唯一菜单名"""
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("新增菜单 - 数据驱动")
class TestCreateMenuDataDriven:
    """新增菜单 - 数据驱动测试"""

    @allure.title("新增菜单 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证新增菜单功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", menu_data["test_create_menu"], ids=lambda x: x["name"])
    def test_create_menu(self, test_case):
        """新增菜单 - 数据驱动"""
        # 准备数据
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 如果 menu_name 为空，用空字符串；否则加唯一后缀
        menu_name = test_input["menu_name"]
        if menu_name and "数据驱动" in menu_name:
            menu_name = unique_menu_name(menu_name)

        payload = build_menu_payload(
            menu_name=menu_name,
            parent_id=test_input.get("parent_id", "1"),
            menu_type=test_input.get("menu_type", "M"),
            path=test_input.get("path", ""),
            component=test_input.get("component", ""),
            perms=test_input.get("perms", "")
        )

        menu_id = None
        try:
            # 执行请求
            with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
                resp = create_menu(payload)
                allure.attach(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    name="请求数据",
                    attachment_type=allure.attachment_type.JSON
                )

            # 断言
            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    data = assert_success(resp, test_case['name'])
                    menu_id = data.get("result")
                    assert menu_id is not None
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            # 清理
            if menu_id:
                with allure.step("Step 3: 清理数据"):
                    delete_menu(menu_id)


@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("菜单树查询 - 数据驱动")
class TestQueryMenuDataDriven:
    """菜单树查询 - 数据驱动测试"""

    @allure.title("菜单树查询 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证菜单树查询功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", menu_data.get("test_query_menu_tree", []), ids=lambda x: x["name"])
    def test_query_menu_tree(self, test_case):
        """菜单树查询 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            if test_input.get("no_token"):
                from system_management.base import request_no_auth
                resp = request_no_auth(
                    "get",
                    f"{MENU_BASE}/tree",
                    msg="无Token查询菜单树",
                    params={"_t": int(time.time() * 1000)}
                )
            else:
                resp = query_menu_tree(timestamp=test_input.get("_t", 0))
            allure.attach(
                json.dumps(test_input, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                data = assert_success(resp, test_case['name'])
                result = data.get("result", [])
                if expected.get("is_list"):
                    assert isinstance(result, list)
            else:
                if resp.status_code == 200:
                    data = resp.json()
                    assert data.get("success") == False or data.get("code") != 200
                else:
                    assert resp.status_code in expected.get("status_codes", [401, 403])


@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("编辑菜单 - 数据驱动")
class TestUpdateMenuDataDriven:
    """编辑菜单 - 数据驱动测试"""

    @allure.title("编辑菜单 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证编辑菜单功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", menu_data.get("test_update_menu", []), ids=lambda x: x["name"])
    def test_update_menu(self, test_case):
        """编辑菜单 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 先创建菜单
        payload = build_menu_payload(
            menu_name=unique_menu_name("编辑前"),
            parent_id="1",
            menu_type="M"
        )
        menu_id = None
        try:
            with allure.step("Step 1: 创建待编辑菜单"):
                resp_create = create_menu(payload)
                data_create = assert_success(resp_create, "编辑前置创建")
                menu_id = data_create.get("result")

            # 编辑
            update_payload = build_menu_payload(
                menu_name=test_input.get("menu_name", unique_menu_name("编辑后")),
                parent_id="1",
                menu_type="M",
                path=test_input.get("path", ""),
                menu_visible=test_input.get("menu_visible", 0),
                menu_status=test_input.get("menu_status", 0)
            )

            with allure.step(f"Step 2: 调用编辑接口 - {test_case['name']}"):
                resp = update_menu(menu_id, update_payload)
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
            if menu_id:
                with allure.step("Step 4: 清理数据"):
                    delete_menu(menu_id)


@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("删除菜单 - 数据驱动")
class TestDeleteMenuDataDriven:
    """删除菜单 - 数据驱动测试"""

    @allure.title("删除菜单 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证删除菜单功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", menu_data.get("test_delete_menu", []), ids=lambda x: x["name"])
    def test_delete_menu(self, test_case):
        """删除菜单 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_menu(test_input["menu_id"])
            allure.attach(
                json.dumps({"menu_id": test_input["menu_id"]}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("响应时间 - 数据驱动")
class TestMenuResponseDataTimeDataDriven:
    """菜单模块响应时间 - 数据驱动测试"""

    @allure.title("菜单响应时间 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证菜单接口响应时间")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", menu_data.get("test_create_menu_response_time", []), ids=lambda x: x["name"])
    def test_menu_response_time(self, test_case):
        """菜单响应时间 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用接口 - {test_case['name']}"):
            import time as _time
            start = _time.time()

            if "新增" in test_case['name']:
                payload = build_menu_payload(
                    menu_name=test_input.get("menu_name", unique_menu_name("响应")),
                    parent_id=test_input.get("parent_id", "1"),
                    menu_type=test_input.get("menu_type", "M")
                )
                resp = create_menu(payload)
            else:
                resp = query_menu_tree()

            elapsed = _time.time() - start
            allure.attach(
                json.dumps({"elapsed": f"{elapsed:.3f}s"}, ensure_ascii=False, indent=2),
                name="响应时间",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            assert_success(resp, test_case['name'])
            if "max_time" in expected:
                assert elapsed < expected["max_time"], \
                    f"响应时间 {elapsed:.3f}s 超过预期 {expected['max_time']}s"
