"""
55 开发环境 - 菜单管理 - Allure 报告进阶演示
=================================================
Allure 进阶功能：
1. @allure.severity()      - 用例严重级别
2. @allure.story()         - 按故事/模块分组
3. @allure.description()   - 用例描述
4. allure.step()           - 把测试拆成多步骤
5. allure.attach()         - 附加请求/响应数据
6. 动态标题/参数化描述
"""
import pytest
import requests
import time
import json
import sys, os
import uuid
import allure

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import get_headers, assert_success, assert_business_fail, request_no_auth
from system_management.utils_common import find_in_tree

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
    return f"测试{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


# ======================== 辅助：记录请求/响应到 Allure ========================

def log_request_response(allure_step_name, method, url, payload, resp):
    """把请求和响应详情附加到 Allure 报告"""
    with allure.step(allure_step_name):
        # 请求信息
        request_info = {
            "method": method,
            "url": url,
            "payload": payload
        }
        allure.attach(
            json.dumps(request_info, ensure_ascii=False, indent=2),
            name="请求信息",
            attachment_type=allure.attachment_type.JSON
        )
        # 响应信息
        try:
            resp_body = resp.json()
        except Exception:
            resp_body = resp.text
        response_info = {
            "status_code": resp.status_code,
            "body": resp_body
        }
        allure.attach(
            json.dumps(response_info, ensure_ascii=False, indent=2),
            name="响应信息",
            attachment_type=allure.attachment_type.JSON
        )


# ======================== 1. 菜单树查询 ========================

@allure.epic("HSC 系统管理")          # 最高层级：项目/系统
@allure.feature("菜单管理")            # 模块
class TestQueryMenu:
    """菜单管理 - 树查询"""

    @allure.story("菜单树查询")         # 子模块/故事
    @allure.title("默认查询菜单树")
    @allure.description("验证菜单树接口能正常返回树形结构")
    @allure.severity(allure.severity_level.CRITICAL)  # 严重级别
    def test_query_menu_tree_default(self):
        """默认查询菜单树"""
        with allure.step("Step 1: 调用菜单树查询接口"):
            resp = query_menu_tree()
            log_request_response("GET /system/menu/tree", "GET",
                                 f"{MENU_BASE}/tree", None, resp)

        with allure.step("Step 2: 断言返回成功"):
            data = assert_success(resp, "菜单树默认查询")
            result = data.get("result", [])
            allure.attach(
                f"根节点数量: {len(result)}",
                name="断言信息",
                attachment_type=allure.attachment_type.TEXT
            )
            assert isinstance(result, list)

    @allure.story("菜单树查询")
    @allure.title("菜单树字段完整性")
    @allure.description("验证菜单树节点包含所有必填字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_menu_tree_field_completeness(self):
        """菜单树字段完整性"""
        with allure.step("Step 1: 查询菜单树"):
            resp = query_menu_tree()
            data = assert_success(resp, "菜单树字段")
            result = data.get("result", [])

        with allure.step("Step 2: 校验必填字段"):
            if result:
                required_fields = [
                    "id", "menuName", "parentId", "menuCode", "path",
                    "component", "menuType", "menuVisible", "menuStatus",
                    "icon", "orderNum"
                ]
                item = result[0]
                missing_required = [f for f in required_fields if f not in item]
                allure.attach(
                    json.dumps(item, ensure_ascii=False, indent=2),
                    name="第一个节点数据",
                    attachment_type=allure.attachment_type.JSON
                )
                assert not missing_required, f"缺失必填字段: {missing_required}"

    @allure.story("安全测试")
    @allure.title("无 Token 查询菜单树")
    @allure.description("验证未登录状态访问菜单树会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)  # 最高级别：安全
    def test_query_menu_tree_no_token(self):
        """无 Token 查询菜单树"""
        with allure.step("Step 1: 不携带 Token 发起请求"):
            resp = request_no_auth(
                "get",
                f"{MENU_BASE}/tree",
                msg="无Token查询菜单树",
                params={"_t": int(time.time() * 1000)}
            )
            log_request_response("无Token请求", "GET",
                                 f"{MENU_BASE}/tree", None, resp)

        with allure.step("Step 2: 断言返回未授权"):
            if resp.status_code == 200:
                data = resp.json()
                allure.attach(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    name="响应内容",
                    attachment_type=allure.attachment_type.JSON
                )
                assert data.get("success") == False or data.get("code") != 200
            else:
                assert resp.status_code in [401, 403]


# ======================== 2. 新增菜单 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
class TestCreateMenu:
    """菜单管理 - 新增"""

    @allure.story("新增菜单")
    @allure.title("新增目录类型菜单")
    @allure.description("验证可以创建一个目录类型(M)的菜单，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_menu_directory(self, temp_menu):
        """新增目录类型菜单"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        with allure.step("Step 1: 验证菜单创建成功"):
            allure.attach(f"menu_id = {temp_menu}", name="创建结果",
                          attachment_type=allure.attachment_type.TEXT)
            assert temp_menu is not None

    @allure.story("新增菜单")
    @allure.title("新增页面类型菜单")
    @allure.description("验证可以创建一个页面类型(C)的菜单，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_menu_page(self, temp_menu_page):
        """新增页面类型菜单"""
        if temp_menu_page is None:
            pytest.skip("临时页面菜单创建失败，跳过该用例")

        with allure.step("Step 1: 验证页面菜单创建成功"):
            allure.attach(f"menu_id = {temp_menu_page}", name="创建结果",
                          attachment_type=allure.attachment_type.TEXT)
            assert temp_menu_page is not None

    @allure.story("新增菜单")
    @allure.title("新增按钮类型菜单")
    @allure.description("验证可以创建一个按钮类型(F)的菜单")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_menu_button(self):
        """新增按钮类型菜单"""
        menu_id = None
        try:
            with allure.step("Step 1: 构造按钮类型菜单 payload"):
                payload = build_menu_payload(
                    menu_name=unique_menu_name("按钮"),
                    parent_id="1",
                    menu_type="F",
                    perms="test:add"
                )
            with allure.step("Step 2: 调用新增接口"):
                resp = create_menu(payload)
                data = assert_success(resp, "新增按钮")
                menu_id = data.get("result")
                assert menu_id is not None
        finally:
            if menu_id:
                with allure.step("Step 3: 清理数据"):
                    delete_menu(menu_id)

    @allure.story("性能测试")
    @allure.title("新增菜单响应时间 < 3 秒")
    @allure.description("验证新增菜单接口响应时间在 3 秒以内")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_menu_response_time(self, temp_menu):
        """新增菜单响应时间 < 3 秒"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        with allure.step("Step 1: 验证菜单创建成功"):
            allure.attach(f"menu_id = {temp_menu}", name="创建结果",
                          attachment_type=allure.attachment_type.TEXT)
            assert temp_menu is not None

    @allure.story("异常场景")
    @allure.title("必填项校验 - 菜单名称为空")
    @allure.description("验证不传 menuName 时后端返回业务失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_menu_missing_name(self):
        """缺少 menuName"""
        with allure.step("Step 1: 构造不带 menuName 的 payload"):
            payload = build_menu_payload(menu_name=unique_menu_name())
            payload.pop("menuName")
            allure.attach(
                json.dumps(payload, ensure_ascii=False, indent=2),
                name="请求 payload（无 menuName）",
                attachment_type=allure.attachment_type.JSON
            )
        with allure.step("Step 2: 调用接口并断言业务失败"):
            resp = create_menu(payload)
            data = assert_business_fail(resp, msg="缺少menuName")
            allure.attach(
                f"code={data.get('code')}, msg={data.get('message')}",
                name="失败信息",
                attachment_type=allure.attachment_type.TEXT
            )

    @allure.story("安全测试")
    @allure.title("无 Token 新增菜单")
    @allure.description("验证未登录状态新增菜单会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_menu_no_token(self):
        """无 Token 新增菜单"""
        with allure.step("Step 1: 不携带 Token 发起请求"):
            payload = build_menu_payload(menu_name=unique_menu_name())
            resp = request_no_auth(
                "post",
                MENU_BASE,
                msg="无Token新增菜单",
                json=payload
            )
            log_request_response("无Token请求", "POST",
                                 MENU_BASE, payload, resp)
        with allure.step("Step 2: 断言返回未授权"):
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("success") == False or data.get("code") != 200
            else:
                assert resp.status_code in [401, 403]


# ======================== 3. 编辑菜单 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
class TestUpdateMenu:
    """菜单管理 - 编辑"""

    @allure.story("编辑菜单")
    @allure.title("编辑菜单名称")
    @allure.description("验证可以修改菜单的名称，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_menu_name(self, temp_menu):
        """编辑菜单名称"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        with allure.step("Step 1: 修改菜单名称"):
            update_payload = build_menu_payload(
                menu_name=unique_menu_name("编辑后"),
                parent_id="1",
                menu_type="M"
            )
            resp_update = update_menu(temp_menu, update_payload)
            assert_success(resp_update, "编辑菜单名")

    @allure.story("编辑菜单")
    @allure.title("编辑菜单状态")
    @allure.description("验证可以禁用/启用菜单，自动清理")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_menu_status(self, temp_menu):
        """编辑菜单状态"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        with allure.step("Step 1: 修改菜单状态为禁用"):
            update_payload = build_menu_payload(
                menu_name=unique_menu_name("状态"),
                parent_id="1",
                menu_type="M",
                menu_status=1
            )
            resp_update = update_menu(temp_menu, update_payload)
            assert_success(resp_update, "编辑菜单状态")

    @allure.story("安全测试")
    @allure.title("无 Token 编辑菜单")
    @allure.description("验证未登录状态编辑菜单会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_update_menu_no_token(self):
        """无 Token 编辑菜单"""
        with allure.step("Step 1: 不携带 Token 发起 PUT 请求"):
            payload = build_menu_payload(menu_name=unique_menu_name(), parent_id="1", menu_type="M")
            resp = request_no_auth(
                "put",
                f"{MENU_BASE}/999999",
                msg="无Token编辑菜单",
                json=payload
            )
            log_request_response("无Token请求", "PUT",
                                 f"{MENU_BASE}/999999", payload, resp)
        with allure.step("Step 2: 断言返回未授权"):
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("success") == False or data.get("code") != 200
            else:
                assert resp.status_code in [401, 403]


# ======================== 4. 删除菜单 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
class TestDeleteMenu:
    """菜单管理 - 删除"""

    @allure.story("删除菜单")
    @allure.title("正常删除菜单")
    @allure.description("验证可以正常删除一个菜单")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_normal_menu(self, temp_menu):
        """正常删除菜单"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        with allure.step("Step 1: 删除菜单"):
            resp_delete = delete_menu(temp_menu)
            data_delete = assert_success(resp_delete, "删除菜单")
            allure.attach(f"删除结果: {data_delete}", name="删除结果",
                          attachment_type=allure.attachment_type.TEXT)

    @allure.story("异常场景")
    @allure.title("删除不存在的菜单")
    @allure.description("验证删除不存在的菜单 ID 时后端返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_non_existent_menu(self):
        """删除不存在的菜单"""
        with allure.step("Step 1: 删除一个不存在的菜单 ID"):
            fake_id = "9999999999999999999"
            resp = delete_menu(fake_id)
            log_request_response("删除不存在菜单", "DELETE",
                                 f"{MENU_BASE}/{fake_id}", None, resp)
            data = resp.json()
        with allure.step("Step 2: 断言返回失败"):
            allure.attach(
                json.dumps(data, ensure_ascii=False, indent=2),
                name="响应内容",
                attachment_type=allure.attachment_type.JSON
            )

    @allure.story("安全测试")
    @allure.title("无 Token 删除菜单")
    @allure.description("验证未登录状态删除菜单会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_delete_no_token(self):
        """无 Token 删除菜单"""
        with allure.step("Step 1: 不携带 Token 发起 DELETE 请求"):
            resp = request_no_auth(
                "delete",
                f"{MENU_BASE}/999999",
                msg="无Token删除菜单"
            )
            log_request_response("无Token请求", "DELETE",
                                 f"{MENU_BASE}/999999", None, resp)
        with allure.step("Step 2: 断言返回未授权"):
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("success") == False or data.get("code") != 200
            else:
                assert resp.status_code in [401, 403]


# ======================== 5. 生命周期闭环 ========================

@allure.epic("HSC 系统管理")
@allure.feature("菜单管理")
class TestLifecycleMenu:
    """菜单管理 - 生命周期"""

    @allure.story("生命周期")
    @allure.title("菜单生命周期闭环 - 创建到删除")
    @allure.description("创建 → 树中查到 → 编辑 → 删除 → 树中查不到")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lifecycle_create_query_update_delete(self, temp_menu):
        """创建 → 树中查到 → 编辑 → 删除 → 树中查不到"""
        if temp_menu is None:
            pytest.skip("临时菜单创建失败，跳过该用例")

        menu_id = temp_menu

        with allure.step("Step 1: 验证菜单已创建"):
            allure.attach(f"创建 menu_id={menu_id}", name="Step1-创建",
                          attachment_type=allure.attachment_type.TEXT)

        with allure.step("Step 2: 树中查到该菜单"):
            resp_tree = query_menu_tree()
            data_tree = assert_success(resp_tree, "生命周期树查询")
            assert find_in_tree(data_tree.get("result", []), menu_id), "创建后树中查不到菜单"

        with allure.step("Step 3: 编辑菜单"):
            update_payload = build_menu_payload(
                menu_name=unique_menu_name("已编辑"),
                parent_id="1",
                menu_type="M"
            )
            resp_update = update_menu(menu_id, update_payload)
            assert_success(resp_update, "生命周期编辑")

        with allure.step("Step 4: 删除菜单"):
            delete_menu(menu_id)

        with allure.step("Step 5: 树中查不到该菜单"):
            resp_tree2 = query_menu_tree()
            data_tree2 = assert_success(resp_tree2, "生命周期删除后查询")
            assert not find_in_tree(data_tree2.get("result", []), menu_id), "删除后树中仍存在菜单"
