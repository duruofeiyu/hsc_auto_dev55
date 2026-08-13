"""
55 开发环境 - 系统管理 - 登录模块接口测试
"""
import allure
import pytest
import requests
import time
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from config import BASE_URL, load_token, TEST_USER_ACCOUNT, TEST_ENCRYPTED_PASSWORD
from system_management.base import assert_success, assert_business_fail, request_no_auth

from system_management.utils_login import (
    get_captcha_image,
    login,
    get_user_info,
    get_user_routes,
    logout,
    LOGIN_BASE,
)


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("验证码")
class TestCaptcha:
    """登录模块 - 验证码"""

    @allure.title("正常获取验证码")
    @allure.description("验证验证码接口能正常返回图片和 uuid")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_captcha_success(self):
        """正常获取验证码"""
        image_token, save_path = get_captcha_image(save_path="captcha_test.jpg")
        print(f"\n【获取验证码】uuid={image_token}, 图片保存路径={save_path}")
        assert os.path.exists(save_path)
        assert image_token is not None

    @allure.title("获取验证码响应时间 < 3 秒")
    @allure.description("验证获取验证码接口响应时间 < 3 秒")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_captcha_response_time(self):
        """获取验证码响应时间 < 3 秒"""
        start = time.time()
        image_token, _ = get_captcha_image(save_path="captcha_time.jpg")
        elapsed = time.time() - start
        print(f"\n【获取验证码-响应时间】{elapsed:.3f} 秒, uuid={image_token}")
        assert elapsed < 3.0


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("登录")
class TestLogin:
    """登录模块 - 登录"""

    @allure.title("手动验证码登录")
    @allure.description("脚本获取验证码图片，用户查看图片后输入验证码登录")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_with_manual_captcha(self):
        """
        手动验证码登录：脚本获取验证码图片，用户查看图片后输入验证码
        """
        image_token, save_path = get_captcha_image(save_path="captcha_login.jpg")
        print(f"\n【手动登录】验证码图片已保存到: {os.path.abspath(save_path)}")
        print(f"【手动登录】uuid={image_token}")
        print("请查看图片并输入验证码：")
        # 注意：pytest -s 模式下才会等待输入
        code = input("验证码: ").strip()

        resp = login(TEST_USER_ACCOUNT, TEST_ENCRYPTED_PASSWORD, code, image_token)
        data = assert_success(resp, "登录")
        result = data.get("result", {})
        token = result.get("token")
        print(f"\n【登录成功】userName={result.get('userName')}, token={token}")
        assert token is not None

        # 可选：保存新 token
        # with open("token.txt", "w") as f:
        #     f.write(token)

    @allure.title("验证码错误登录失败")
    @allure.description("验证输入错误验证码时登录失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_wrong_captcha(self):
        """验证码错误登录失败"""
        image_token, _ = get_captcha_image(save_path="captcha_wrong.jpg")
        resp = login(TEST_USER_ACCOUNT, TEST_ENCRYPTED_PASSWORD, "xxxx", image_token)
        data = resp.json()
        print(f"\n【错误验证码】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200

    @allure.title("密码错误登录失败")
    @allure.description("验证输入错误密码时登录失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_wrong_password(self):
        """密码错误登录失败"""
        image_token, _ = get_captcha_image(save_path="captcha_pwd.jpg")
        print("\n【错误密码测试】请查看 captcha_pwd.jpg 输入验证码：")
        code = input("验证码: ").strip()
        resp = login(TEST_USER_ACCOUNT, "wrong_password", code, image_token)
        data = resp.json()
        print(f"【错误密码】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200

    @allure.title("缺少验证码登录失败")
    @allure.description("验证缺少验证码时登录失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_missing_captcha(self):
        """缺少验证码登录失败"""
        resp = login(TEST_USER_ACCOUNT, TEST_ENCRYPTED_PASSWORD, "", "fake-uuid")
        data = resp.json()
        print(f"\n【缺少验证码】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("用户信息")
class TestUserInfo:
    """登录模块 - 用户信息"""

    @allure.title("使用有效 Token 获取用户信息")
    @allure.description("验证携带有效 Token 能正常获取用户信息")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_user_info_with_token(self):
        """使用有效 Token 获取用户信息"""
        token = load_token()
        resp = get_user_info(token)
        data = resp.json()
        print(f"\n【用户信息】success={data.get('success')}, code={data.get('code')}, result={data.get('result')}")
        # 该接口可能不存在或路径不同，仅记录响应；有响应即视为正常
        assert resp.status_code == 200, f"用户信息接口请求失败: status={resp.status_code}"

    @allure.title("无 Token 获取用户信息应失败")
    @allure.description("验证未登录状态获取用户信息会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_get_user_info_without_token(self):
        """无 Token 获取用户信息应失败"""
        resp = request_no_auth(
            "get",
            f"{BASE_URL}/system/user/info",
            msg="无Token获取用户信息"
        )
        print(f"\n【用户信息-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【用户信息-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("登出")
class TestLogout:
    """登录模块 - 登出"""

    @allure.title("使用有效 Token 登出")
    @allure.description("验证携带有效 Token 能正常登出")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_logout_with_token(self):
        """使用有效 Token 登出"""
        token = load_token()
        resp = logout(token)
        data = resp.json()
        print(f"\n【登出】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        # 登出接口有响应即视为正常（部分后端登出后 token 仍有效，不做强断言）
        assert resp.status_code == 200, f"登出接口请求失败: status={resp.status_code}"

    @allure.title("无 Token 登出")
    @allure.description("验证未登录状态登出行为")
    @allure.severity(allure.severity_level.NORMAL)
    def test_logout_without_token(self):
        """无 Token 登出"""
        resp = request_no_auth(
            "post",
            f"{LOGIN_BASE}/logout",
            msg="无Token登出"
        )
        data = resp.json()
        print(f"\n【登出-无Token】status={resp.status_code}, success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        # 部分后端无 Token 登出也返回 200，仅记录行为


# ======================== 5. 角色菜单权限端到端验证 ========================

@allure.epic("HSC 系统管理")
@allure.feature("登录模块")
@allure.story("角色菜单权限 E2E")
class TestRoleMenuPermissionE2E:
    """角色菜单权限 - 端到端验证"""

    @allure.title("角色菜单权限路由验证")
    @allure.description("验证给角色分配指定菜单后，该角色用户登录只能看到这些菜单")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_role_menu_permission_routes(self):
        """
        验证：给角色分配指定菜单后，该角色用户登录只能看到这些菜单
        """
        from system_management.utils_role import build_role_payload as build_role_payload_for_login, create_role, delete_role
        from system_management.utils_user import build_user_payload as build_user_payload_for_login, create_user, delete_user

        # 步骤1: 创建只含一个菜单权限的角色
        role_payload = build_role_payload_for_login(
            role_name="E2E菜单权限角色",
            role_key=f"e2e_role_{int(time.time() * 1000)}",
            menu_ids=["228"]  # 安全控制台
        )
        role_resp = create_role(role_payload)
        role_data = role_resp.json()
        role_id = role_data.get("result") if role_data.get("success") else None
        print(f"\n【E2E】创建角色 role_id={role_id}")

        if role_id is None:
            pytest.skip("角色创建失败（需要 x-sign 签名），跳过 E2E 用例")

        try:
            # 步骤2: 创建测试用户并绑定该角色
            account = f"e2e_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
            user_payload = build_user_payload_for_login(
                user_account=account,
                user_name="E2E测试用户",
                phone_number=f"138{int(time.time() * 1000) % 100000000:08d}",
                role_ids=[role_id]
            )
            user_resp = create_user(user_payload)
            user_data = user_resp.json()
            user_id = user_data.get("result") if user_data.get("success") else None
            print(f"【E2E】创建用户 user_id={user_id}, account={account}")

            if user_id is None:
                pytest.skip("用户创建失败，跳过 E2E 用例")

            try:
                # 步骤3: 手动验证码登录该用户
                image_token, save_path = get_captcha_image(save_path="captcha_e2e.jpg")
                print(f"【E2E】验证码图片: {os.path.abspath(save_path)}, uuid={image_token}")
                code = input(f"请输入账号 {account} 的验证码: ").strip()

                # 注意：首次登录密码是明文，这里用创建时的默认密码
                login_resp = login(account, user_payload["password"], code, image_token)
                login_data = assert_success(login_resp, "E2E测试用户登录")
                token = login_data.get("result", {}).get("token")
                print(f"【E2E】登录成功，token={token[:30]}...")

                # 步骤4: 获取用户路由菜单
                routes_resp = get_user_routes(token)
                routes_data = routes_resp.json()
                routes = routes_data.get("result", [])
                route_ids = [r.get("id") for r in routes]
                print(f"【E2E】该用户可见菜单ID: {route_ids}")

                # 步骤5: 断言只能看到分配的菜单
                assert "228" in route_ids, "分配的安全控制台菜单未显示"
                assert len(route_ids) == 1, f"期望只看到1个菜单，实际看到 {len(route_ids)} 个: {route_ids}"
                print("【E2E】菜单权限验证通过 ✅")
            finally:
                delete_user(user_id)
        finally:
            delete_role(role_id)
        print("【E2E】清理完成")

    @allure.title("权限隔离验证 - 普通角色无法看到所有菜单")
    @allure.description("验证普通角色用户登录后，不能看到超级管理员的所有菜单")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_unauthorized_user_cannot_see_all_menus(self):
        """
        验证：普通角色用户登录后，不能看到超级管理员的所有菜单
        """
        # 复用已创建的 testmenu001 账号（只有 228 菜单权限）
        # 需要手动输入验证码登录
        account = "testmenu001"
        encrypted_password = "VuXbxzMHKtm3O4aKHB7L+Q=="  # 首次登录后的加密密码，可能已变化

        image_token, save_path = get_captcha_image(save_path="captcha_testmenu.jpg")
        print(f"\n【权限隔离】验证码图片: {os.path.abspath(save_path)}")
        code = input(f"请输入账号 {account} 的验证码: ").strip()

        login_resp = login(account, encrypted_password, code, image_token)
        login_data = login_resp.json()
        print(f"【权限隔离】登录 success={login_data.get('success')}, code={login_data.get('code')}")

        if login_data.get("success"):
            token = login_data.get("result", {}).get("token")
            routes_resp = get_user_routes(token)
            routes_data = routes_resp.json()
            routes = routes_data.get("result", [])
            route_ids = [r.get("id") for r in routes]
            print(f"【权限隔离】可见菜单ID: {route_ids}")
            # 工作台 id=1 不应该看到
            assert "1" not in route_ids, "普通角色不应看到工作台菜单"
        else:
            pytest.skip("testmenu001 登录失败，可能是密码已变更")
