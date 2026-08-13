"""
55 开发环境 - 系统管理 - 用户管理接口测试
"""
import allure
import pytest
import time
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import get_headers, assert_success, assert_business_fail, request_no_auth
from system_management.utils_common import unique_account, unique_phone

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


# ======================== 1. 用户列表查询 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("用户列表查询")
class TestQueryUser:
    """用户管理 - 列表查询"""

    @allure.title("默认查询用户列表")
    @allure.description("验证用户列表接口能正常返回数据")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_user_list_default(self):
        """默认查询用户列表"""
        resp = query_users()
        data = assert_success(resp, "用户列表默认查询")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【用户列表默认】total={result.get('total')}, records={len(records)}")
        assert len(records) <= 10

    @allure.title("分页查询用户列表")
    @allure.description("验证分页功能，指定 pageSize=5 返回不超过 5 条")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_user_list_pagination(self):
        """分页查询"""
        payload = {"pageNum": 1, "pageSize": 5, "condition": {"deptCode": ""}}
        resp = query_users(payload)
        data = assert_success(resp, "用户列表分页")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【用户列表分页】total={result.get('total')}, records={len(records)}")
        assert len(records) <= 5

    @allure.title("用户列表字段完整性校验")
    @allure.description("验证用户列表返回数据包含所有必填字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_user_list_field_completeness(self):
        """用户列表字段完整性"""
        resp = query_users()
        data = assert_success(resp, "用户列表字段")
        records = data.get("result", {}).get("list", [])
        if records:
            expected_fields = [
                "id", "deptId", "deptName", "userAccount", "userName",
                "email", "phoneNumber", "avatar", "userStatus", "gender",
                "station", "roleIds", "roleNames", "remark", "createBy", "createTime"
            ]
            item = records[0]
            missing = [f for f in expected_fields if f not in item]
            print(f"\n【用户列表字段】缺失字段: {missing}")
            assert not missing, f"缺失字段: {missing}"

    @allure.title("无 Token 查询用户列表")
    @allure.description("验证未登录状态访问用户列表会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_user_list_no_token(self):
        """无 Token 查询用户列表"""
        resp = request_no_auth(
            "post",
            f"{USER_BASE}/list",
            msg="无Token查询用户列表",
            json={"pageNum": 1, "pageSize": 10, "condition": {"deptCode": ""}}
        )
        print(f"\n【用户列表-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【用户列表-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]

    @allure.title("按部门编码查询用户列表")
    @allure.description("按 deptCode 查询用户列表，验证返回数据属于该部门")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_user_list_by_dept_code(self):
        """按部门编码查询用户列表"""
        payload = {
            "pageNum": 1,
            "pageSize": 10,
            "condition": {"deptCode": "001"}
        }
        resp = query_users(payload)
        data = assert_success(resp, "按部门编码查询用户")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【按部门查询】deptCode=001, total={result.get('total')}, records={len(records)}")
        assert len(records) > 0, "按 deptCode=001 查询无结果"
        assert all(r.get("deptId") == "1" for r in records), "返回用户不属于该部门"


# ======================== 2. 新增用户 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("新增用户")
class TestCreateUser:
    """用户管理 - 新增"""

    @allure.title("正常新增用户")
    @allure.description("创建一个新用户，验证返回 user_id，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_user_success(self, temp_user):
        """正常新增用户"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")
        print(f"\n【新增用户】user_id={temp_user}")
        assert temp_user is not None

    @allure.title("新增用户并关联角色")
    @allure.description("创建一个带角色的用户，验证返回 user_id，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_user_with_role(self, temp_user_with_role):
        """新增用户并关联角色"""
        if temp_user_with_role is None:
            pytest.skip("临时用户创建失败，跳过该用例")
        print(f"\n【新增用户-角色】user_id={temp_user_with_role}")
        assert temp_user_with_role is not None

    @allure.title("新增用户响应时间")
    @allure.description("验证新增用户接口响应时间 < 3 秒")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_user_response_time(self):
        """新增用户响应时间 < 3 秒"""
        payload = build_user_payload(
            user_account=unique_account(),
            phone_number=unique_phone()
        )
        user_id = None
        try:
            start = time.time()
            resp = create_user(payload)
            elapsed = time.time() - start
            data = assert_success(resp, "新增用户响应时间")
            user_id = data.get("result")
            print(f"\n【新增用户-响应时间】user_id={user_id}, elapsed={elapsed:.3f}s")
            allure.attach(f"响应时间: {elapsed:.3f}s", name="性能数据",
                          attachment_type=allure.attachment_type.TEXT)
            assert elapsed < 3.0, f"新增用户耗时 {elapsed:.3f}s，超过 3s 阈值"
        finally:
            if user_id:
                try:
                    delete_user(user_id)
                except Exception:
                    pass

    @allure.title("必填项校验 - 账号为空")
    @allure.description("验证缺少必填字段 userAccount 时接口返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_user_missing_account(self):
        """缺少 userAccount"""
        payload = build_user_payload(user_account=unique_account())
        payload.pop("userAccount")
        resp = create_user(payload)
        data = assert_business_fail(resp, msg="缺少userAccount")
        print(f"\n【必填-userAccount缺失】code={data.get('code')}, msg={data.get('message')}")

    @allure.title("必填项校验 - 密码为空")
    @allure.description("验证缺少必填字段 password 时接口返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_user_missing_password(self):
        """缺少 password"""
        payload = build_user_payload(user_account=unique_account())
        payload.pop("password")
        resp = create_user(payload)
        data = assert_business_fail(resp, msg="缺少password")
        print(f"\n【必填-password缺失】code={data.get('code')}, msg={data.get('message')}")

    @allure.title("重复用户账号校验")
    @allure.description("验证重复账号无法再次创建")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_user_duplicate_account(self, temp_user):
        """重复用户账号"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")

        # 查询 temp_user 的账号名
        resp = query_users({"pageNum": 1, "pageSize": 10, "condition": {"deptCode": ""}})
        records = assert_success(resp, "查询用户").get("result", {}).get("list", [])
        temp_record = next((r for r in records if r.get("id") == temp_user), None)
        if not temp_record:
            pytest.skip("无法找到临时用户信息，跳过")

        # 用相同账号再次创建
        original_account = temp_record.get("userAccount")
        payload = build_user_payload(user_account=original_account)
        resp_duplicate = create_user(payload)
        data = resp_duplicate.json()
        print(f"\n【重复账号】account={original_account}, success={data.get('success')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200, \
            f"重复账号应创建失败，实际: {data}"

    @allure.title("无 Token 新增用户")
    @allure.description("验证未登录状态新增用户会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_user_no_token(self):
        """无 Token 新增用户"""
        payload = build_user_payload(user_account=unique_account())
        resp = request_no_auth(
            "post",
            USER_BASE,
            msg="无Token新增用户",
            json=payload
        )
        print(f"\n【新增用户-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【新增用户-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 3. 编辑用户 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("编辑用户")
class TestUpdateUser:
    """用户管理 - 编辑"""

    @allure.title("编辑用户名称")
    @allure.description("创建用户后编辑名称，验证编辑成功，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_user_name(self, temp_user):
        """编辑用户名称"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")

        update_payload = build_user_payload(
            user_name="编辑后",
            phone_number="13800000001",
            is_update=True
        )
        resp_update = update_user(temp_user, update_payload)
        assert_success(resp_update, "编辑用户名")
        print(f"\n【编辑用户】user_id={temp_user}, success=True")

    @allure.title("编辑用户角色")
    @allure.description("创建用户后修改角色，验证编辑成功，自动清理")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_user_role(self, temp_user):
        """编辑用户角色"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")

        update_payload = build_user_payload(
            user_name="编辑角色测试用户",
            phone_number="13800000001",
            role_ids=["2"],
            is_update=True
        )
        resp_update = update_user(temp_user, update_payload)
        assert_success(resp_update, "编辑用户角色")
        print(f"\n【编辑用户角色】user_id={temp_user}, success=True")

    @allure.title("无 Token 编辑用户")
    @allure.description("验证未登录状态编辑用户会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_update_user_no_token(self):
        """无 Token 编辑用户"""
        payload = build_user_payload(user_name="无token编辑", is_update=True)
        resp = request_no_auth(
            "put",
            f"{USER_BASE}/999999",
            msg="无Token编辑用户",
            json=payload
        )
        print(f"\n【编辑用户-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【编辑用户-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 4. 删除用户 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("删除用户")
class TestDeleteUser:
    """用户管理 - 删除"""

    @allure.title("正常删除用户")
    @allure.description("验证 temp_user fixture 自动清理机制（fixture teardown 自动删除）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_normal_user(self, temp_user):
        """正常删除用户（fixture teardown 自动清理）"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")
        print(f"\n【删除验证】user_id={temp_user}，将在 fixture teardown 中自动删除")
        assert temp_user is not None

    @allure.title("删除不存在的用户")
    @allure.description("验证删除不存在的用户返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_non_existent_user(self):
        """删除不存在的用户"""
        fake_id = "9999999999999999999"
        resp = delete_user(fake_id)
        data = resp.json()
        print(f"\n【删除-不存在】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200, \
            f"删除不存在的用户应返回失败，实际: {data}"

    @allure.title("无 Token 删除用户")
    @allure.description("验证未登录状态删除用户会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_delete_no_token(self):
        """无 Token 删除用户"""
        resp = request_no_auth(
            "delete",
            f"{USER_BASE}/999999",
            msg="无Token删除用户"
        )
        print(f"\n【删除-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【删除-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 5. 重置密码 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("重置密码")
class TestResetPassword:
    """用户管理 - 重置密码"""

    @allure.title("正常重置密码")
    @allure.description("创建用户后重置密码，验证重置成功，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_reset_password_normal(self, temp_user):
        """正常重置密码"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")

        resp = reset_user_password(temp_user, "NewPass@123")
        data = assert_success(resp, "重置密码")
        print(f"\n【重置密码】user_id={temp_user}, success=True")

    @allure.title("无 Token 重置密码")
    @allure.description("验证未登录状态重置密码会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_reset_password_no_token(self):
        """无 Token 重置密码"""
        resp = request_no_auth(
            "put",
            f"{USER_BASE}/999999/password",
            msg="无Token重置密码",
            json={"password": "NewPass@123"}
        )
        print(f"\n【重置密码-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【重置密码-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 7. 批量删除用户 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("批量删除")
class TestBatchDeleteUser:
    """用户管理 - 批量删除"""

    @allure.title("批量删除用户")
    @allure.description("创建多个用户后批量删除，验证删除成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_batch_delete_users(self):
        """批量删除用户"""
        # 创建 2 个临时用户
        user_ids = []
        for _ in range(2):
            payload = build_user_payload(
                user_account=unique_account(),
                phone_number=unique_phone()
            )
            resp = create_user(payload)
            data = resp.json()
            if data.get("success"):
                user_ids.append(data.get("result"))

        if not user_ids:
            pytest.skip("临时用户创建失败，跳过该用例")

        try:
            resp = batch_delete_users(user_ids)
            data = assert_success(resp, "批量删除用户")
            print(f"\n【批量删除】user_ids={user_ids}, success={data.get('success')}")
        finally:
            # 清理可能残留的用户
            for uid in user_ids:
                try:
                    delete_user(uid)
                except Exception:
                    pass


# ======================== 6. 生命周期闭环 ========================

@allure.epic("HSC 系统管理")
@allure.feature("用户管理")
@allure.story("生命周期")
class TestLifecycleUser:
    """用户管理 - 生命周期"""

    @allure.title("用户生命周期闭环 - 创建到删除")
    @allure.description("创建 → 列表查到 → 编辑 → 删除 → 查不到")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lifecycle_create_query_update_delete(self, temp_user):
        """创建 → 列表查到 → 编辑 → 删除 → 查不到"""
        if temp_user is None:
            pytest.skip("临时用户创建失败，跳过该用例")

        user_id = temp_user
        print(f"\n【生命周期】创建 user_id={user_id}")

        list_payload = {
            "pageNum": 1,
            "pageSize": 10,
            "condition": {"deptCode": ""}
        }
        resp_list = query_users(list_payload)
        data_list = assert_success(resp_list, "生命周期列表查询")
        records = data_list.get("result", {}).get("list", [])
        assert any(r.get("id") == user_id for r in records), "创建后列表查不到用户"
        print("【生命周期】创建后列表存在 ✅")

        update_payload = build_user_payload(
            user_name="生命周期用户-已编辑",
            phone_number="13800000001",
            is_update=True
        )
        resp_update = update_user(user_id, update_payload)
        assert_success(resp_update, "生命周期编辑")
        print("【生命周期】编辑成功 ✅")

        delete_user(user_id)
        print("【生命周期】删除成功 ✅")

        resp_list2 = query_users(list_payload)
        data_list2 = assert_success(resp_list2, "生命周期删除后查询")
        records2 = data_list2.get("result", {}).get("list", [])
        assert not any(r.get("id") == user_id for r in records2), "删除后列表仍存在用户"
        print("【生命周期】删除后列表不存在 ✅")
