"""
55 开发环境 - 系统管理 - 角色管理 - 数据驱动版
使用 YAML 管理测试数据，一个用例跑多组数据
注意：角色创建/编辑/删除接口需要 x-sign 签名头校验，当前未实现签名算法，
因此角色写操作相关用例采用记录型断言，签名失败时 skip。
"""
import pytest
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
from system_management.utils_common import is_sign_error, unique_role_key, unique_name

from system_management.utils_role import (
    query_roles,
    create_role,
    update_role,
    delete_role,
    batch_delete_roles,
    get_role_detail,
    build_role_payload,
    ROLE_BASE,
)


# 加载测试数据
role_data = load_yaml_data("role_data.yaml")


def unique_role_name(prefix="角色"):
    """生成唯一角色名称"""
    return unique_name(prefix=prefix)


def try_create_role_with_sign_workaround(payload):
    """尝试创建角色；若因 x-sign 签名失败，记录行为并返回 None"""
    resp = create_role(payload)
    data = resp.json()
    if is_sign_error(data):
        print(f"\n【角色创建-签名绕过】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        return None
    assert_success(resp, "新增角色")
    return data.get("result")


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("角色列表查询 - 数据驱动")
class TestQueryRoleDataDriven:
    """角色列表查询 - 数据驱动测试"""

    @allure.title("角色列表查询 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证角色列表查询功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", role_data["test_query_role_list"], ids=lambda x: x["name"])
    def test_query_role_list(self, test_case):
        """角色列表查询 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_roles(test_input)
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


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("新增角色 - 数据驱动")
class TestCreateRoleDataDriven:
    """新增角色 - 数据驱动测试"""

    @allure.title("新增角色 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证新增角色功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", role_data["test_create_role"], ids=lambda x: x["name"])
    def test_create_role(self, test_case):
        """新增角色 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        role_name = unique_role_name() if not test_input.get("role_name") else test_input["role_name"]
        role_key = unique_role_key() if not test_input.get("role_key") else test_input["role_key"]

        payload = build_role_payload(
            role_name=role_name,
            role_key=role_key,
            role_status=test_input.get("role_status", 0),
            menu_ids=test_input.get("menu_ids")
        )

        with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
            resp = create_role(payload)
            allure.attach(
                json.dumps(payload, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if is_sign_error(data):
                pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("编辑角色 - 数据驱动")
class TestUpdateRoleDataDriven:
    """编辑角色 - 数据驱动测试"""

    @allure.title("编辑角色 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证编辑角色功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", role_data["test_update_role"], ids=lambda x: x["name"])
    def test_update_role(self, test_case):
        """编辑角色 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 先创建角色
        payload = build_role_payload(
            role_name=unique_role_name(),
            role_key=unique_role_key()
        )
        role_id = None
        try:
            with allure.step("Step 1: 创建待编辑角色"):
                role_id = try_create_role_with_sign_workaround(payload)
                if role_id is None:
                    pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")

            # 编辑
            update_payload = build_role_payload(
                role_name=test_input.get("role_name", unique_role_name("编辑后")),
                role_key=payload["roleKey"],
                role_status=test_input.get("role_status", 0),
                data_scope=test_input.get("data_scope"),
                dept_ids=test_input.get("dept_ids")
            )

            with allure.step(f"Step 2: 调用编辑接口 - {test_case['name']}"):
                resp = update_role(role_id, update_payload)
                allure.attach(
                    json.dumps(update_payload, ensure_ascii=False, indent=2),
                    name="请求数据",
                    attachment_type=allure.attachment_type.JSON
                )

            with allure.step("Step 3: 断言结果"):
                data = resp.json()
                if is_sign_error(data):
                    pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
                if expected["success"]:
                    assert_success(resp, test_case['name'])
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if role_id:
                with allure.step("Step 4: 清理数据"):
                    try:
                        update_role(role_id, build_role_payload(
                            role_name=payload["roleName"],
                            role_key=payload["roleKey"],
                            user_ids=[]
                        ))
                        delete_role(role_id)
                    except Exception:
                        pass


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("删除角色 - 数据驱动")
class TestDeleteRoleDataDriven:
    """删除角色 - 数据驱动测试"""

    @allure.title("删除角色 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证删除角色功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", role_data["test_delete_role"], ids=lambda x: x["name"])
    def test_delete_role(self, test_case):
        """删除角色 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_role(test_input["role_id"])
            allure.attach(
                json.dumps({"role_id": test_input["role_id"]}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if is_sign_error(data):
                pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("分配用户 - 数据驱动")
class TestAssignUsersDataDriven:
    """分配用户 - 数据驱动测试"""

    @allure.title("分配用户 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证分配用户功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", role_data["test_assign_users"], ids=lambda x: x["name"])
    def test_assign_users(self, temp_role, test_case):
        """分配用户 - 数据驱动"""
        if temp_role is None:
            pytest.skip("临时角色创建失败，跳过该用例")
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用分配用户接口 - {test_case['name']}"):
            resp = update_role(temp_role, build_role_payload(
                role_name="temp",
                role_key="temp",
                user_ids=test_input.get("user_ids", [])
            ))
            allure.attach(
                json.dumps({"role_id": temp_role, "user_ids": test_input.get("user_ids", [])},
                          ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if is_sign_error(data):
                pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("角色详情 - 数据驱动")
class TestGetRoleDetailDataDriven:
    """角色详情 - 数据驱动测试"""

    @allure.title("角色详情 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证角色详情功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", role_data["test_get_role_detail"], ids=lambda x: x["name"])
    def test_get_role_detail(self, temp_role, test_case):
        """角色详情 - 数据驱动"""
        if temp_role is None:
            pytest.skip("临时角色创建失败，跳过该用例")
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用详情接口 - {test_case['name']}"):
            resp = get_role_detail(temp_role)
            allure.attach(
                json.dumps({"role_id": temp_role}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])
