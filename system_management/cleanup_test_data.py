"""
55 开发环境 - 测试数据清理脚本
运行方式：
    cd /Users/a1-6/hsc_auto_dev55
    source venv/bin/activate
    python system_management/cleanup_test_data.py
"""

import sys, os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from system_management.utils_user import query_users, delete_user
from system_management.utils_role import query_roles, delete_role, update_role
from system_management.utils_dept import query_depts, delete_dept
from system_management.utils_menu import query_menu_tree, delete_menu


# ============================================================
# 安全清理：只删除符合 fixture/脚本命名规则的测试数据
# 规则：账号含 UUID 后缀（test_[0-9a-f]{10}）、名称含"测试"+UUID
# ============================================================

# 匹配 fixture 创建的账号：test_ + 10位十六进制
ACCOUNT_PATTERN = re.compile(r"^test_[0-9a-f]{10}$")
# 匹配脚本创建的账号：test_ + 时间戳 + UUID
ACCOUNT_PATTERN_LEGACY = re.compile(r"^test_\d+_[0-9a-f]{4,}$")
# 匹配名称：测试 + 时间戳 + UUID
NAME_PATTERN = re.compile(r"^测试.*_\d+_[0-9a-f]{4,}$")


def _is_test_account(account):
    """判断是否为测试账号（严格匹配，避免误删）"""
    return bool(ACCOUNT_PATTERN.match(account) or ACCOUNT_PATTERN_LEGACY.match(account))


def _is_test_name(name):
    """判断是否为测试数据名称（严格匹配，避免误删）"""
    return bool(NAME_PATTERN.match(name))


def cleanup_users():
    """清理测试用户（只删除符合命名规则的测试数据）"""
    print("\n========== 清理测试用户 ==========")
    resp = query_users({"pageNum": 1, "pageSize": 1000, "condition": {"deptCode": ""}})
    data = resp.json()
    if not data.get("success"):
        print(f"查询用户失败: {data.get('message')}")
        return

    records = data.get("result", {}).get("list", [])
    count = 0
    for user in records:
        account = user.get("userAccount", "")
        name = user.get("userName", "")
        user_id = user.get("id")
        # 严格匹配命名规则，避免误删真实数据
        if _is_test_account(account) or _is_test_name(name):
            del_resp = delete_user(user_id)
            del_data = del_resp.json()
            status = "✅" if del_data.get("success") else "❌"
            print(f"{status} 删除用户 {account}({name}), id={user_id}, msg={del_data.get('message')}")
            count += 1
            time.sleep(0.1)
    print(f"共清理 {count} 个测试用户")


def cleanup_roles():
    """清理测试角色（只删除符合命名规则的测试数据）"""
    print("\n========== 清理测试角色 ==========")
    resp = query_roles({"condition": {}, "pageNum": 1, "pageSize": 1000})
    data = resp.json()
    if not data.get("success"):
        print(f"查询角色失败: {data.get('message')}")
        return

    records = data.get("result", {}).get("list", [])
    count = 0
    for role in records:
        role_name = role.get("roleName", "")
        role_key = role.get("roleKey", "")
        role_id = role.get("id")
        # 严格匹配命名规则
        if _is_test_name(role_name) or _is_test_account(role_key) or role_key.startswith("role_"):
            # 先取消用户授权
            update_role(role_id, {
                "roleName": role_name,
                "roleKey": role_key,
                "roleSort": role.get("roleSort", 1),
                "dataScope": role.get("dataScope", 1),
                "roleStatus": role.get("roleStatus", 0),
                "menuIds": [],
                "userIds": []
            })
            del_resp = delete_role(role_id)
            del_data = del_resp.json()
            status = "✅" if del_data.get("success") else "❌"
            print(f"{status} 删除角色 {role_name}, id={role_id}, msg={del_data.get('message')}")
            count += 1
            time.sleep(0.1)
    print(f"共清理 {count} 个测试角色")


def _get_dept_depth(dept_id, records, depth=0):
    """递归计算部门层级深度"""
    if depth > 10:  # 防止循环引用
        return depth
    dept = next((d for d in records if d.get("id") == dept_id), None)
    if not dept or dept.get("parentId") == "1":
        return depth
    return _get_dept_depth(dept.get("parentId"), records, depth + 1)


def cleanup_depts():
    """清理测试部门（按层级深度倒序，先删子部门再删父部门）"""
    print("\n========== 清理测试部门 ==========")
    resp = query_depts({"condition": {}, "pageNum": 1, "pageSize": 1000})
    data = resp.json()
    if not data.get("success"):
        print(f"查询部门失败: {data.get('message')}")
        return

    records = data.get("result", {}).get("list", [])
    # 严格匹配命名规则
    test_depts = [d for d in records if _is_test_name(d.get("deptName", ""))]
    count = 0
    # 按层级深度倒序排序，先删除最深层子部门
    test_depts.sort(key=lambda d: _get_dept_depth(d.get("id"), records), reverse=True)

    for dept in test_depts:
        dept_id = dept.get("id")
        dept_name = dept.get("deptName", "")
        del_resp = delete_dept(dept_id)
        del_data = del_resp.json()
        status = "✅" if del_data.get("success") else "❌"
        print(f"{status} 删除部门 {dept_name}, id={dept_id}, msg={del_data.get('message')}")
        count += 1
        time.sleep(0.1)
    print(f"共清理 {count} 个测试部门")


def cleanup_menus():
    """清理测试菜单（只删除符合命名规则的测试数据）"""
    print("\n========== 清理测试菜单 ==========")
    resp = query_menu_tree()
    data = resp.json()
    if not data.get("success"):
        print(f"查询菜单失败: {data.get('message')}")
        return

    def collect_menus(nodes):
        result = []
        for node in nodes:
            result.append(node)
            result.extend(collect_menus(node.get("children") or []))
        return result

    all_menus = collect_menus(data.get("result", []))
    # 严格匹配命名规则
    test_menus = [m for m in all_menus if _is_test_name(m.get("menuName", ""))]
    count = 0
    # 按层级深度倒序排序，先删除子菜单
    test_menus.sort(key=lambda m: m.get("parentId") == "0")

    for menu in test_menus:
        menu_id = menu.get("id")
        menu_name = menu.get("menuName", "")
        del_resp = delete_menu(menu_id)
        del_data = del_resp.json()
        status = "✅" if del_data.get("success") else "❌"
        print(f"{status} 删除菜单 {menu_name}, id={menu_id}, msg={del_data.get('message')}")
        count += 1
        time.sleep(0.1)
    print(f"共清理 {count} 个测试菜单")


if __name__ == "__main__":
    print("开始清理 55 环境测试数据...")
    print("注意：只删除符合命名规则的测试数据，避免误删真实数据\n")
    cleanup_menus()
    cleanup_depts()
    cleanup_roles()
    cleanup_users()
    print("\n清理完成")
