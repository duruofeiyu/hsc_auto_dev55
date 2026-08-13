"""
55 开发环境 - 系统管理 - 登录模块 - 数据驱动版
使用 YAML 管理测试数据，一个用例跑多组数据
"""
import pytest
import time
import json
import allure
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import (
    assert_success,
    assert_business_fail,
    request_wrapper,
    load_yaml_data,
)
from config import BASE_URL, load_token, TEST_USER_ACCOUNT, TEST_ENCRYPTED_PASSWORD
import requests

from system_management.utils_login import (
    get_captcha_image,
    login,
    get_user_info,
    get_user_routes,
    logout,
    LOGIN_BASE,
)


# 加载测试数据
login_data = load_yaml_data("login_data.yaml")


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("验证码 - 数据驱动")
class TestCaptchaDataDriven:
    """验证码 - 数据驱动测试"""

    @allure.title("获取验证码 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证获取验证码功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", login_data["test_captcha"], ids=lambda x: x["name"])
    def test_get_captcha(self, test_case):
        """获取验证码 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用获取验证码接口 - {test_case['name']}"):
            start = time.time()
            image_token, save_path = get_captcha_image(save_path=test_input.get("save_path", "captcha_test.jpg"))
            elapsed = time.time() - start
            allure.attach(
                json.dumps({"save_path": test_input.get("save_path")}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )
            allure.attach(
                json.dumps({"image_token": image_token, "elapsed": f"{elapsed:.3f}s"}, ensure_ascii=False, indent=2),
                name="响应数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            if expected.get("has_image_token"):
                assert image_token is not None
            if expected.get("file_exists"):
                assert os.path.exists(save_path)
            if "max_time" in expected:
                assert elapsed < expected["max_time"], f"响应时间 {elapsed:.3f}s 超过预期 {expected['max_time']}s"


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("登录 - 数据驱动")
class TestLoginDataDriven:
    """登录 - 数据驱动测试"""

    @allure.title("登录 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证登录功能")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.parametrize("test_case", login_data["test_login"], ids=lambda x: x["name"])
    def test_login(self, test_case):
        """登录 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        # 先获取验证码
        image_token, _ = get_captcha_image(save_path="captcha_login.jpg")

        with allure.step(f"Step 1: 调用登录接口 - {test_case['name']}"):
            resp = login(
                test_input.get("user_account", TEST_USER_ACCOUNT),
                test_input.get("password", TEST_ENCRYPTED_PASSWORD),
                test_input.get("captcha", "xxxx"),
                test_input.get("image_token", image_token)
            )
            allure.attach(
                json.dumps(test_input, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if expected["success"]:
                assert_success(resp, test_case['name'])
            else:
                assert data.get("success") == False or data.get("code") != 200, \
                    f"应登录失败，实际: {data}"


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("用户信息 - 数据驱动")
class TestUserInfoDataDriven:
    """用户信息 - 数据驱动测试"""

    @allure.title("用户信息 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证用户信息功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", login_data["test_user_info"], ids=lambda x: x["name"])
    def test_get_user_info(self, test_case):
        """用户信息 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用用户信息接口 - {test_case['name']}"):
            if test_input.get("use_token"):
                token = load_token()
                resp = get_user_info(token)
            else:
                resp = requests.get(
                    f"{BASE_URL}/system/user/info",
                    headers={"Content-Type": "application/json;charset=UTF-8"},
                    verify=False
                )
            allure.attach(
                json.dumps({"use_token": test_input.get("use_token")}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if expected["success"]:
                assert data.get("success") == True or data.get("code") == 200
            else:
                if resp.status_code == 200:
                    assert data.get("success") == False or data.get("code") != 200
                else:
                    assert resp.status_code in expected.get("status_codes", [401, 403])


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("用户路由 - 数据驱动")
class TestUserRoutesDataDriven:
    """用户路由 - 数据驱动测试"""

    @allure.title("用户路由 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证用户路由功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("test_case", login_data["test_user_routes"], ids=lambda x: x["name"])
    def test_get_user_routes(self, test_case):
        """用户路由 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用用户路由接口 - {test_case['name']}"):
            if test_input.get("use_token"):
                token = load_token()
                resp = get_user_routes(token)
            else:
                resp = requests.get(
                    f"{BASE_URL}/system/user/routes",
                    headers={"Content-Type": "application/json;charset=UTF-8"},
                    verify=False
                )
            allure.attach(
                json.dumps({"use_token": test_input.get("use_token")}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if expected["success"]:
                assert data.get("success") == True or data.get("code") == 200
            else:
                if resp.status_code == 200:
                    assert data.get("success") == False or data.get("code") != 200
                else:
                    assert resp.status_code in expected.get("status_codes", [401, 403])


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("登出 - 数据驱动")
class TestLogoutDataDriven:
    """登出 - 数据驱动测试"""

    @allure.title("登出 - 数据驱动")
    @allure.description("从 YAML 读取多组数据，验证登出功能")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("test_case", login_data["test_logout"], ids=lambda x: x["name"])
    def test_logout(self, test_case):
        """登出 - 数据驱动"""
        test_input = test_case["input"]
        expected = test_case["expected"]

        with allure.step(f"Step 1: 调用登出接口 - {test_case['name']}"):
            if test_input.get("use_token"):
                token = load_token()
                resp = logout(token)
            else:
                resp = requests.post(
                    f"{LOGIN_BASE}/logout",
                    headers={"Content-Type": "application/json;charset=UTF-8"},
                    verify=False
                )
            allure.attach(
                json.dumps({"use_token": test_input.get("use_token")}, ensure_ascii=False, indent=2),
                name="请求数据",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Step 2: 断言结果"):
            data = resp.json()
            if expected["success"]:
                assert data.get("success") == True or data.get("code") == 200
            else:
                assert data.get("success") == False or data.get("code") != 200
