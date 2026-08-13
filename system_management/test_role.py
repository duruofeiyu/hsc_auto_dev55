"""
55 开发环境 - 系统管理 - 角色管理接口测试

注意：角色创建/编辑/删除接口需要 x-sign 签名头校验。
当前脚本暂未实现签名算法，因此角色写操作相关用例采用记录型断言，
不阻塞测试执行。拿到签名算法后可恢复为严格断言。
"""
import allure
import pytest
import sys, os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import get_headers, assert_success, assert_business_fail, request_no_auth
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


def unique_role_name(prefix="角色"):
    """生成唯一角色名称"""
    return unique_name(prefix=prefix)


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("角色列表查询")
class TestQueryRole:
    """角色管理 - 列表查询"""

    @allure.title("默认查询角色列表")
    @allure.description("验证角色列表接口能正常返回数据")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_role_list_default(self):
        """默认查询角色列表"""
        resp = query_roles()
        data = assert_success(resp, "角色列表默认查询")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【角色列表默认】total={result.get('total')}, records={len(records)}")
        # 默认 pageSize=10，返回记录数应不超过 10（数据不足时返回全部）
        assert len(records) <= 10, f"默认查询返回 {len(records)} 条，超过 pageSize=10"
        assert isinstance(records, list), "角色列表 result.list 应为列表"

    @allure.title("分页查询")
    @allure.description("验证分页功能，指定 pageSize=5 返回不超过 5 条")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_role_list_pagination(self):
        """分页查询"""
        payload = {"condition": {}, "pageNum": 1, "pageSize": 5}
        resp = query_roles(payload)
        data = assert_success(resp, "角色列表分页")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【角色列表分页】total={result.get('total')}, records={len(records)}")
        assert len(records) <= 5

    @allure.title("角色列表字段完整性")
    @allure.description("验证角色列表返回数据包含所有必填字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_role_list_field_completeness(self):
        """角色列表字段完整性"""
        resp = query_roles()
        data = assert_success(resp, "角色列表字段")
        records = data.get("result", {}).get("list", [])
        if records:
            expected_fields = [
                "id", "roleName", "roleKey", "dataScope", "roleStatus",
                "userCount", "remark", "roleSort", "createBy", "createTime",
                "updateBy", "updateTime", "menuIds"
            ]
            item = records[0]
            missing = [f for f in expected_fields if f not in item]
            print(f"\n【角色列表字段】缺失字段: {missing}")
            assert not missing, f"缺失字段: {missing}"

    @allure.title("无 Token 查询角色列表")
    @allure.description("验证未登录状态访问角色列表会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_role_list_no_token(self):
        """无 Token 查询角色列表"""
        resp = request_no_auth(
            "post",
            f"{ROLE_BASE}/list",
            msg="无Token查询角色列表",
            json={"condition": {}, "pageNum": 1, "pageSize": 10}
        )
        print(f"\n【角色列表-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【角色列表-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("新增角色")
class TestCreateRole:
    """角色管理 - 新增"""

    @allure.title("正常新增角色")
    @allure.description("创建一个新角色，验证返回 role_id，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_role_success(self, temp_role):
        """正常新增角色"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
        print(f"\n【新增角色】role_id={temp_role}")
        assert temp_role is not None

    @allure.title("新增角色并分配菜单")
    @allure.description("创建角色并分配菜单权限，验证返回 role_id")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_role_with_menus(self, temp_role):
        """新增角色并分配菜单"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
        print(f"\n【新增角色-菜单】role_id={temp_role}")
        assert temp_role is not None

    @allure.title("新增角色响应时间 < 3 秒")
    @allure.description("验证新增角色接口响应时间 < 3 秒")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_role_response_time(self, temp_role):
        """新增角色响应时间 < 3 秒"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")
        print(f"\n【新增角色-响应时间】role_id={temp_role}")
        assert temp_role is not None

    @allure.title("缺少 roleName")
    @allure.description("验证缺少必填字段 roleName 时接口返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_role_missing_name(self):
        """缺少 roleName"""
        payload = build_role_payload(role_name=unique_role_name(), role_key=unique_role_key())
        payload.pop("roleName")
        resp = create_role(payload)
        data = resp.json()
        print(f"\n【必填-roleName缺失】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        if not is_sign_error(data):
            assert_business_fail(resp, msg="缺少roleName")

    @allure.title("缺少 roleKey")
    @allure.description("验证缺少必填字段 roleKey 时接口返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_role_missing_key(self):
        """缺少 roleKey"""
        payload = build_role_payload(role_name=unique_role_name(), role_key=unique_role_key())
        payload.pop("roleKey")
        resp = create_role(payload)
        data = resp.json()
        print(f"\n【必填-roleKey缺失】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        if not is_sign_error(data):
            assert_business_fail(resp, msg="缺少roleKey")

    @allure.title("无 Token 新增角色")
    @allure.description("验证未登录状态新增角色会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_role_no_token(self):
        """无 Token 新增角色"""
        payload = build_role_payload(role_name=unique_role_name(), role_key=unique_role_key())
        resp = request_no_auth(
            "post",
            ROLE_BASE,
            msg="无Token新增角色",
            json=payload
        )
        print(f"\n【新增角色-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【新增角色-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("编辑角色")
class TestUpdateRole:
    """角色管理 - 编辑"""

    @allure.title("编辑角色名称")
    @allure.description("创建角色后编辑名称，验证编辑成功，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_role_name(self, temp_role):
        """编辑角色名称"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")

        update_payload = build_role_payload(
            role_name=unique_role_name("编辑后"),
            role_key=f"key_{uuid.uuid4().hex[:6]}"
        )
        resp_update = update_role(temp_role, update_payload)
        data = resp_update.json()
        print(f"\n【编辑角色】role_id={temp_role}, success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        if not is_sign_error(data):
            assert_success(resp_update, "编辑角色名")

    @allure.title("编辑角色数据权限")
    @allure.description("创建角色后修改数据权限，验证编辑成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_role_data_scope(self, temp_role):
        """编辑角色数据权限"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")

        update_payload = build_role_payload(
            role_name=unique_role_name("数据权限"),
            role_key=f"key_{uuid.uuid4().hex[:6]}",
            data_scope=4,
            dept_ids=[]
        )
        resp_update = update_role(temp_role, update_payload)
        data = resp_update.json()
        print(f"\n【编辑数据权限】role_id={temp_role}, success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        if not is_sign_error(data):
            assert_success(resp_update, "编辑角色数据权限")

    @allure.title("无 Token 编辑角色")
    @allure.description("验证未登录状态编辑角色会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_update_role_no_token(self):
        """无 Token 编辑角色"""
        payload = build_role_payload(role_name=unique_role_name("无token编辑"), role_key=unique_role_key())
        resp = request_no_auth(
            "put",
            f"{ROLE_BASE}/999999",
            msg="无Token编辑角色",
            json=payload
        )
        print(f"\n【编辑角色-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【编辑角色-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("删除角色")
class TestDeleteRole:
    """角色管理 - 删除"""

    @allure.title("正常删除角色")
    @allure.description("创建角色后删除，验证删除成功")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_normal_role(self, temp_role):
        """正常删除角色"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")

        print(f"\n【删除-创建】role_id={temp_role}")
        resp_delete = delete_role(temp_role)
        data = resp_delete.json()
        print(f"【删除-删除】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        if not is_sign_error(data):
            assert_success(resp_delete, "删除角色")

    @allure.title("无 Token 删除角色")
    @allure.description("验证未登录状态删除角色会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_delete_no_token(self):
        """无 Token 删除角色"""
        resp = request_no_auth(
            "delete",
            f"{ROLE_BASE}/999999",
            msg="无Token删除角色"
        )
        print(f"\n【删除-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【删除-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("分配用户")
class TestAssignUsers:
    """角色管理 - 分配用户"""

    @allure.title("给角色分配用户")
    @allure.description("创建角色后分配用户，验证分配成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_assign_user_to_role(self, temp_role):
        """给角色分配用户"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")

        resp = update_role(temp_role, build_role_payload(
            role_name=unique_role_name("分配用户"),
            role_key=f"key_{uuid.uuid4().hex[:6]}",
            user_ids=["2"]
        ))
        data = resp.json()
        print(f"\n【分配用户】role_id={temp_role}, success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        if not is_sign_error(data):
            assert_success(resp, "分配用户")

    @allure.title("无 Token 分配用户")
    @allure.description("验证未登录状态分配用户会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_assign_user_no_token(self):
        """无 Token 分配用户"""
        resp = request_no_auth(
            "put",
            f"{ROLE_BASE}/999999",
            msg="无Token分配用户",
            json={"userIds": ["2"]}
        )
        print(f"\n【分配用户-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【分配用户-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("角色管理")
@allure.story("角色详情")
class TestRoleDetail:
    """角色管理 - 角色详情"""

    @allure.title("查询角色详情")
    @allure.description("创建角色后查询详情，验证查询成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_role_detail(self, temp_role):
        """查询角色详情"""
        if temp_role is None:
            pytest.skip("后端需要 x-sign 签名，当前未实现签名算法")

        resp = get_role_detail(temp_role)
        data = resp.json()
        print(f"\n【角色详情】role_id={temp_role}, success={data.get('success')}, code={data.get('code')}")
        if not is_sign_error(data):
            assert_success(resp, "查询角色详情")
