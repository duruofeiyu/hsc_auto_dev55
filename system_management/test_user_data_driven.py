"""
55 开发环境 - 系统管理 - 用户管理 - 数据驱动版
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

from system_management.utils_user import (
    query_users,
    create_user,
    update_user,
    delete_user,
    batch_delete_users,
    reset_user_password,
    build_user_payload,
    USER_BASE,
)


# 加载测试数据
user_data = load_yaml_data("user_data.yaml")


def unique_account(prefix="test"):
    """生成唯一用户账号"""
    return f"{prefix}_{int(time.time() * 1000)}_{os.urandom(2).hex()}"


def unique_phone():
    """生成唯一手机号"""
    return f"138{int(time.time() * 1000) % 100000000:08d}"


@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("用户列表查询 - 数据驱动")
class TestQueryUserDataDriven:
    """用户列表查询 - 数据驱动测试"""

    @allure.title("用户列表查询 - 数据驱动")
    @pytest.mark.parametrize("test_case", user_data["test_query_user_list"], ids=lambda x: x["name"])
    def test_query_user_list(self, test_case):
        """用户列表查询 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用查询接口 - {test_case['name']}"):
            resp = query_users(test_input)
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
@allure.feature("用户管理")
@allure.story("新增用户 - 数据驱动")
class TestCreateUserDataDriven:
    """新增用户 - 数据驱动测试"""

    @allure.title("新增用户 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证新增用户功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", user_data["test_create_user"], ids=lambda x: x["name"])
    def test_create_user(self, test_case):
        """新增用户 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 生成唯一账号和手机号
        user_account = unique_account() if not test_input.get("userAccount") else test_input["userAccount"]
        phone = unique_phone() if not test_input.get("phoneNumber") else test_input["phoneNumber"]

        payload = build_user_payload(
            user_account=user_account,
            password=test_input.get("password", "XingDing@2024"),
            user_name=test_input.get("userName", "YAML测试用户"),
            phone_number=phone,
            dept_id=test_input.get("deptId", "1"),
            email=test_input.get("email", "test_yaml@qq.com"),
            user_status=test_input.get("userStatus", 0),
            role_ids=test_input.get("roleIds", ["4"])
        )

        user_id = None
        try:
            with allure.step(f"Step 1: 调用新增接口 - {test_case['name']}"):
                resp = create_user(payload)
                allure.attach(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    name="请求数据",
                    attachment_type=allure.attachment_type.JSON
                )

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    data = assert_success(resp, test_case['name'])
                    user_id = data.get("result")
                    assert user_id is not None
                else:
                    assert_business_fail(resp, test_case['name'])
        finally:
            if user_id:
                with allure.step("Step 3: 清理数据"):
                    delete_user(user_id)


@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("编辑用户 - 数据驱动")
class TestUpdateUserDataDriven:
    """编辑用户 - 数据驱动测试"""

    @allure.title("编辑用户 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证编辑用户功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", user_data["test_update_user"], ids=lambda x: x["name"])
    def test_update_user(self, test_case):
        """编辑用户 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 先创建用户
        payload = build_user_payload(
            user_account=unique_account(),
            user_name="编辑前用户",
            phone_number=unique_phone()
        )
        user_id = None
        try:
            with allure.step("Step 1: 创建待编辑用户"):
                resp_create = create_user(payload)
                data_create = assert_success(resp_create, "编辑前置创建")
                user_id = data_create.get("result")

            # 编辑
            update_payload = build_user_payload(
                user_name=test_input.get("user_name", "YAML编辑后用户"),
                phone_number=test_input.get("phone_number", unique_phone()),
                is_update=True,
                role_ids=test_input.get("role_ids", ["4"])
            )

            with allure.step(f"Step 2: 调用编辑接口 - {test_case['name']}"):
                resp = update_user(user_id, update_payload)
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
            if user_id:
                with allure.step("Step 4: 清理数据"):
                    delete_user(user_id)


@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("删除用户 - 数据驱动")
class TestDeleteUserDataDriven:
    """删除用户 - 数据驱动测试"""

    @allure.title("删除用户 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证删除用户功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", user_data["test_delete_user"], ids=lambda x: x["name"])
    def test_delete_user(self, test_case):
        """删除用户 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用删除接口 - {test_case['name']}"):
            resp = delete_user(test_input["user_id"])
            allure.attach(
                json.dumps({"user_id": test_input["user_id"]}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])


@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("重置密码 - 数据驱动")
class TestResetPasswordDataDriven:
    """重置密码 - 数据驱动测试"""

    @allure.title("重置密码 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证重置密码功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", user_data["test_reset_password"], ids=lambda x: x["name"])
    def test_reset_password(self, temp_user, test_case):
        """重置密码 - 数据驱动"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用重置密码接口 - {test_case['name']}"):
            resp = reset_user_password(temp_user, test_input.get("new_password", "NewPass@123"))
            allure.attach(
                json.dumps({"user_id": temp_user}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert_business_fail(resp, test_case['name'])
