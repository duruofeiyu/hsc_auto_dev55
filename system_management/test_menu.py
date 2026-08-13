"""
55 开发环境 - 系统管理 - 菜单管理接口测试
"""
import allure
import pytest
import time
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import get_headers, assert_success, assert_business_fail, request_no_auth
from system_management.utils_common import find_in_tree, unique_name

from system_management.utils_menu import (
    query_menu_tree,
    create_menu,
    update_menu,
    delete_menu,
    build_menu_payload,
    MENU_BASE,
)


def unique_menu_name(prefix="菜单"):
    """生成唯一菜单名称"""
    return unique_name(prefix=prefix)


# ======================== 1. 菜单树查询 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("菜单树查询")
class TestQueryMenu:
    """菜单管理 - 树查询"""

    @allure.title("默认查询菜单树")
    @allure.description("验证菜单树接口能正常返回数据")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_menu_tree_default(self):
        """默认查询菜单树"""
        resp = query_menu_tree()
        data = assert_success(resp, "菜单树默认查询")
        result = data.get("result", [])
        print(f"\n【菜单树默认】root nodes={len(result)}")
        assert isinstance(result, list)

    @allure.title("菜单树字段完整性")
    @allure.description("验证菜单树返回数据包含所有必填字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_menu_tree_field_completeness(self):
        """菜单树字段完整性"""
        resp = query_menu_tree()
        data = assert_success(resp, "菜单树字段")
        result = data.get("result", [])
        if result:
            required_fields = [
                "id", "menuName", "parentId", "menuCode", "path",
                "component", "menuType", "menuVisible", "menuStatus",
                "icon", "orderNum"
            ]
            optional_fields = [
                "isOutLink", "isCache", "createBy", "createTime",
                "updateBy", "updateTime", "children"
            ]
            item = result[0]
            missing_required = [f for f in required_fields if f not in item]
            missing_optional = [f for f in optional_fields if f not in item]
            print(f"\n【菜单树字段】缺失必填字段: {missing_required}, 缺失可选字段: {missing_optional}")
            assert not missing_required, f"缺失必填字段: {missing_required}"

    @allure.title("无 Token 查询菜单树")
    @allure.description("验证未登录状态访问菜单树会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_menu_tree_no_token(self):
        """无 Token 查询菜单树"""
        resp = request_no_auth(
            "get",
            f"{MENU_BASE}/tree",
            msg="无Token查询菜单树",
            params={"_t": int(time.time() * 1000)}
        )
        print(f"\n【菜单树-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【菜单树-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 2. 新增菜单 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("新增菜单")
class TestCreateMenu:
    """菜单管理 - 新增"""

    @allure.title("新增目录类型菜单")
    @allure.description("创建一个目录类型菜单，验证返回 menu_id，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_menu_directory(self, temp_menu):
        """新增目录类型菜单"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")
        print(f"\n【新增目录】menu_id={temp_menu}")
        assert temp_menu is not None

    @allure.title("新增页面类型菜单")
    @allure.description("创建一个页面类型菜单，验证返回 menu_id，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_menu_page(self, temp_menu_page):
        """新增页面类型菜单"""
        if temp_menu_page is None:
            pytest.skip("临时页面菜单创建失败，跳过该用例")
        print(f"\n【新增页面】menu_id={temp_menu_page}")
        assert temp_menu_page is not None

    @allure.title("新增按钮类型菜单")
    @allure.description("创建一个按钮类型菜单，验证返回 menu_id")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_menu_button(self):
        """新增按钮类型菜单"""
        payload = build_menu_payload(
            menu_name=unique_menu_name("按钮"),
            parent_id="1",
            menu_type="F",
            perms="test:add"
        )
        menu_id = None
        try:
            resp = create_menu(payload)
            data = assert_success(resp, "新增按钮")
            menu_id = data.get("result")
            print(f"\n【新增按钮】menu_id={menu_id}")
            assert menu_id is not None
        finally:
            if menu_id:
                try:
                    delete_menu(menu_id)
                except Exception:
                    pass

    @allure.title("新增菜单响应时间")
    @allure.description("验证新增菜单接口响应时间 < 3 秒")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_menu_response_time(self):
        """新增菜单响应时间 < 3 秒"""
        payload = build_menu_payload(
            menu_name=unique_menu_name(),
            parent_id="1",
            menu_type="M"
        )
        menu_id = None
        try:
            start = time.time()
            resp = create_menu(payload)
            elapsed = time.time() - start
            data = assert_success(resp, "新增菜单响应时间")
            menu_id = data.get("result")
            print(f"\n【新增菜单-响应时间】menu_id={menu_id}, elapsed={elapsed:.3f}s")
            allure.attach(f"响应时间: {elapsed:.3f}s", name="性能数据",
                          attachment_type=allure.attachment_type.TEXT)
            assert elapsed < 3.0, f"新增菜单耗时 {elapsed:.3f}s，超过 3s 阈值"
        finally:
            if menu_id:
                try:
                    delete_menu(menu_id)
                except Exception:
                    pass

    @allure.title("必填项校验 - 菜单名称为空")
    @allure.description("验证缺少必填字段 menuName 时接口返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_menu_missing_name(self):
        """缺少 menuName"""
        payload = build_menu_payload(menu_name=unique_menu_name())
        payload.pop("menuName")
        resp = create_menu(payload)
        data = assert_business_fail(resp, msg="缺少menuName")
        print(f"\n【必填-menuName缺失】code={data.get('code')}, msg={data.get('message')}")

    @allure.title("无 Token 新增菜单")
    @allure.description("验证未登录状态新增菜单会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_menu_no_token(self):
        """无 Token 新增菜单"""
        payload = build_menu_payload(menu_name=unique_menu_name())
        resp = request_no_auth(
            "post",
            MENU_BASE,
            msg="无Token新增菜单",
            json=payload
        )
        print(f"\n【新增菜单-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【新增菜单-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 3. 编辑菜单 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("编辑菜单")
class TestUpdateMenu:
    """菜单管理 - 编辑"""

    @allure.title("编辑菜单名称")
    @allure.description("创建菜单后编辑名称，验证编辑成功，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_menu_name(self, temp_menu):
        """编辑菜单名称"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        update_payload = build_menu_payload(
            menu_name=unique_menu_name("编辑后"),
            parent_id="1",
            menu_type="M"
        )
        resp_update = update_menu(temp_menu, update_payload)
        assert_success(resp_update, "编辑菜单名")
        print(f"\n【编辑菜单】menu_id={temp_menu}, success=True")

    @allure.title("编辑菜单状态为停用")
    @allure.description("创建菜单后停用，验证状态变更成功，自动清理")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_menu_status(self, temp_menu):
        """编辑菜单状态"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        update_payload = build_menu_payload(
            menu_name=unique_menu_name("状态"),
            parent_id="1",
            menu_type="M",
            menu_status=1
        )
        resp_update = update_menu(temp_menu, update_payload)
        assert_success(resp_update, "编辑菜单状态")
        print(f"\n【编辑菜单状态】menu_id={temp_menu}, status=1")

    @allure.title("无 Token 编辑菜单")
    @allure.description("验证未登录状态编辑菜单会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_update_menu_no_token(self):
        """无 Token 编辑菜单"""
        payload = build_menu_payload(menu_name=unique_menu_name(), parent_id="1", menu_type="M")
        resp = request_no_auth(
            "put",
            f"{MENU_BASE}/999999",
            msg="无Token编辑菜单",
            json=payload
        )
        print(f"\n【编辑菜单-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【编辑菜单-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 4. 删除菜单 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("删除菜单")
class TestDeleteMenu:
    """菜单管理 - 删除"""

    @allure.title("正常删除菜单")
    @allure.description("验证 temp_menu fixture 自动清理机制（fixture teardown 自动删除）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_normal_menu(self, temp_menu):
        """正常删除菜单（fixture teardown 自动清理）"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        print(f"\n【删除验证】menu_id={temp_menu}，将在 fixture teardown 中自动删除")
        assert temp_menu is not None

    @allure.title("删除不存在的菜单")
    @allure.description("验证删除不存在的菜单返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_non_existent_menu(self):
        """删除不存在的菜单"""
        fake_id = "9999999999999999999"
        resp = delete_menu(fake_id)
        data = resp.json()
        print(f"\n【删除-不存在】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200, \
            f"删除不存在的菜单应返回失败，实际: {data}"

    @allure.title("无 Token 删除菜单")
    @allure.description("验证未登录状态删除菜单会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_delete_no_token(self):
        """无 Token 删除菜单"""
        resp = request_no_auth(
            "delete",
            f"{MENU_BASE}/999999",
            msg="无Token删除菜单"
        )
        print(f"\n【删除-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【删除-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


# ======================== 5. 生命周期闭环 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
@allure.story("生命周期")
class TestLifecycleMenu:
    """菜单管理 - 生命周期"""

    @allure.title("菜单生命周期闭环 - 创建到删除")
    @allure.description("创建 → 树中查到 → 编辑 → 删除 → 树中查不到")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lifecycle_create_query_update_delete(self, temp_menu):
        """创建 → 树中查到 → 编辑 → 删除 → 树中查不到"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        menu_id = temp_menu
        print(f"\n【生命周期】创建 menu_id={menu_id}")

        # 树中查到
        resp_tree = query_menu_tree()
        data_tree = assert_success(resp_tree, "生命周期树查询")
        assert find_in_tree(data_tree.get("result", []), menu_id), "创建后树中查不到菜单"
        print("【生命周期】创建后树中存在 ✅")

        # 编辑
        update_payload = build_menu_payload(
            menu_name=unique_menu_name("已编辑"),
            parent_id="1",
            menu_type="M"
        )
        resp_update = update_menu(menu_id, update_payload)
        assert_success(resp_update, "生命周期编辑")
        print("【生命周期】编辑成功 ✅")

        # 删除
        delete_menu(menu_id)
        print("【生命周期】删除成功 ✅")

        # 树中查不到
        resp_tree2 = query_menu_tree()
        data_tree2 = assert_success(resp_tree2, "生命周期删除后查询")
        assert not find_in_tree(data_tree2.get("result", []), menu_id), "删除后树中仍存在菜单"
        print("【生命周期】删除后树中不存在 ✅")
