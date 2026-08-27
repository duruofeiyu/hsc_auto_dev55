"""
55 开发环境 - pytest 全局 conftest.py
提供公共 fixture、Allure 环境信息、自动日志等
"""
import os
import sys
import uuid
import time
import json
import pytest
import allure

# 将项目根目录加入 sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 关闭 HTTPS 证书验证警告
import requests
requests.packages.urllib3.disable_warnings()

from config import BASE_URL, load_token, get_headers
from logger import get_logger

logger = get_logger("conftest")


# ======================== Allure 环境信息 ========================

def pytest_sessionfinish(session, exitstatus):
    """测试结束后写入 Allure 环境信息文件"""
    try:
        env_file = os.path.join(project_root, "reports", "allure-results", "environment.properties")
        os.makedirs(os.path.dirname(env_file), exist_ok=True)
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"Environment=55开发环境\n")
            f.write(f"BaseURL={BASE_URL}\n")
            f.write(f"Python={sys.version.split()[0]}\n")
            f.write(f"Platform={sys.platform}\n")
    except Exception as e:
        print(f"\n[conftest] 写入 Allure 环境信息失败: {e}")


def pytest_configure(config):
    """注册 Allure 自定义标签的中文映射"""
    config._allure_labels = {
        "epic": "模块",
        "feature": "功能",
        "story": "场景",
        "severity": "优先级",
        "tag": "标签",
    }


# ======================== 基础 fixture ========================

@pytest.fixture(scope="session")
def headers():
    """会话级别：获取请求头（token 动态读取，支持 token 刷新）"""
    return get_headers()


@pytest.fixture(scope="session")
def token():
    """会话级别：获取 token（动态读取，每次调用重新加载）"""
    return load_token()


@pytest.fixture(scope="session")
def base_url():
    """会话级别：获取 BASE_URL"""
    return BASE_URL


# 注意：headers/token fixture 为 session 级，token 在会话开始时读取一次。
# 如需支持 token 过期自动刷新，请改为 function 级或在测试中直接调用 get_headers()。
# utils_*.py 中的 get_headers() 每次都是动态读取的，推荐在需要刷新 token 的场景直接调用。


# ======================== 工具函数 ========================

def _unique_account():
    """生成唯一用户账号"""
    return f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


def _unique_phone():
    """生成唯一手机号"""
    return f"138{int(time.time() * 1000) % 100000000:08d}"


def _unique_dept_name(prefix="部门"):
    """生成唯一部门名称"""
    return f"测试{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


def _unique_role_name(prefix="角色"):
    """生成唯一角色名称"""
    return f"测试{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


def _unique_role_key(prefix="role"):
    """生成唯一角色标识"""
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


def _unique_menu_name(prefix="菜单"):
    """生成唯一菜单名称"""
    return f"测试{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


# ======================== 用户 fixture ========================

@pytest.fixture
def temp_user():
    """
    创建一个临时用户，测试结束后自动删除。
    测试函数通过参数 temp_user 获取 user_id。
    如果创建失败（token 过期等），返回 None，调用方需判断。
    """
    from system_management.utils_user import build_user_payload, create_user, delete_user

    payload = build_user_payload(
        user_account=_unique_account(),
        user_name="fixture临时用户",
        phone_number=_unique_phone()
    )
    resp = create_user(payload)
    data = resp.json()
    user_id = data.get("result") if data.get("success") else None
    logger.info(f"[fixture] 创建临时用户 user_id={user_id}")

    yield user_id

    if user_id:
        try:
            delete_user(user_id)
            logger.info(f"[fixture] 删除临时用户 user_id={user_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时用户失败: {e}")


@pytest.fixture
def temp_user_with_role():
    """
    创建一个带角色的临时用户，测试结束后自动删除。
    """
    from system_management.utils_user import build_user_payload, create_user, delete_user

    payload = build_user_payload(
        user_account=_unique_account(),
        user_name="fixture角色用户",
        phone_number=_unique_phone(),
        role_ids=["2"]
    )
    resp = create_user(payload)
    data = resp.json()
    user_id = data.get("result") if data.get("success") else None
    logger.info(f"[fixture] 创建临时用户(带角色) user_id={user_id}")

    yield user_id

    if user_id:
        try:
            delete_user(user_id)
            logger.info(f"[fixture] 删除临时用户(带角色) user_id={user_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时用户(带角色)失败: {e}")


# ======================== 部门 fixture ========================

@pytest.fixture
def temp_dept():
    """
    创建一个临时部门，测试结束后自动删除。
    测试函数通过参数 temp_dept 获取 dept_id。
    """
    from system_management.utils_dept import build_dept_payload, create_dept, delete_dept

    payload = build_dept_payload(
        dept_name=_unique_dept_name(),
        dept_code=f"fixture_{uuid.uuid4().hex[:6]}"
    )
    resp = create_dept(payload)
    data = resp.json()
    dept_id = data.get("result") if data.get("success") else None
    logger.info(f"[fixture] 创建临时部门 dept_id={dept_id}")

    yield dept_id

    if dept_id:
        try:
            delete_dept(dept_id)
            logger.info(f"[fixture] 删除临时部门 dept_id={dept_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时部门失败: {e}")


@pytest.fixture
def temp_child_dept():
    """
    创建一个临时下级部门（父级为研发部 2082053606579658754），测试结束后自动删除。
    """
    from system_management.utils_dept import build_dept_payload, create_dept, delete_dept

    payload = build_dept_payload(
        dept_name=_unique_dept_name("下级"),
        parent_id="2082053606579658754",
        dept_code=f"fixture_child_{uuid.uuid4().hex[:6]}"
    )
    resp = create_dept(payload)
    data = resp.json()
    dept_id = data.get("result") if data.get("success") else None
    logger.info(f"[fixture] 创建临时下级部门 dept_id={dept_id}")

    yield dept_id

    if dept_id:
        try:
            delete_dept(dept_id)
            logger.info(f"[fixture] 删除临时下级部门 dept_id={dept_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时下级部门失败: {e}")


# ======================== 角色 fixture ========================

@pytest.fixture
def temp_role():
    """
    创建一个临时角色，测试结束后自动删除。
    x-sign 签名已于 2026-08-27 复刻实现（system_management/utils_sign.py），
    由 base.request_wrapper 在每次发请求时统一计算，无需在此特殊处理。
    开发环境后端偶发 500（transient 故障），创建时重试以应对。
    """
    import time as _time
    from system_management.utils_role import build_role_payload, create_role, delete_role, update_role, get_role_detail

    payload = build_role_payload(
        role_name=_unique_role_name(),
        role_key=_unique_role_key()
    )
    role_id = None
    # 开发环境后端偶发 500，重试应对 transient 故障
    for _attempt in range(5):
        resp = create_role(payload)
        data = resp.json()
        if data.get("success") and data.get("code") == 200:
            role_id = data.get("result")
            break
        if "服务器开小差了" in data.get("message", "") or data.get("code") == 500:
            _time.sleep(2)
            continue
        break  # 非 500 的业务失败（如重名），不再重试

    logger.info(f"[fixture] 创建临时角色 role_id={role_id}")

    yield role_id

    if role_id:
        try:
            # 先取消用户授权再删除（后端要求角色无用户才能删除）
            update_role(role_id, build_role_payload(
                role_name=payload["roleName"],
                role_key=payload["roleKey"],
                user_ids=[]
            ))
            delete_role(role_id)
            # 验证是否真的删除了
            verify_resp = get_role_detail(role_id)
            verify_data = verify_resp.json()
            if verify_data.get("success") and verify_data.get("result"):
                logger.warning(f"[fixture] 角色可能未实际删除: role_id={role_id}")
            else:
                logger.info(f"[fixture] 删除临时角色 role_id={role_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时角色失败: {e}")


# ======================== 菜单 fixture ========================

@pytest.fixture
def temp_menu():
    """
    创建一个临时目录类型菜单，测试结束后自动删除。
    测试函数通过参数 temp_menu 获取 menu_id。
    """
    from system_management.utils_menu import build_menu_payload, create_menu, delete_menu

    payload = build_menu_payload(
        menu_name=_unique_menu_name(),
        parent_id="1",
        menu_type="M"
    )
    resp = create_menu(payload)
    data = resp.json()
    menu_id = data.get("result") if data.get("success") else None
    logger.info(f"[fixture] 创建临时菜单 menu_id={menu_id}")

    yield menu_id

    if menu_id:
        try:
            delete_menu(menu_id)
            logger.info(f"[fixture] 删除临时菜单 menu_id={menu_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时菜单失败: {e}")


@pytest.fixture
def temp_menu_page():
    """
    创建一个临时页面类型菜单，测试结束后自动删除。
    """
    from system_management.utils_menu import build_menu_payload, create_menu, delete_menu

    payload = build_menu_payload(
        menu_name=_unique_menu_name("页面"),
        parent_id="1",
        menu_type="C",
        path="testPage",
        component="testPage/index.vue"
    )
    resp = create_menu(payload)
    data = resp.json()
    menu_id = data.get("result") if data.get("success") else None
    logger.info(f"[fixture] 创建临时页面菜单 menu_id={menu_id}")

    yield menu_id

    if menu_id:
        try:
            delete_menu(menu_id)
            logger.info(f"[fixture] 删除临时页面菜单 menu_id={menu_id}")
        except Exception as e:
            logger.warning(f"[fixture] 删除临时页面菜单失败: {e}")


# ======================== 自动日志 fixture ========================

@pytest.fixture(autouse=True)
def _auto_log_test(request):
    """
    自动记录每个用例的开始和结束（autouse=True 自动应用到所有用例）
    """
    test_name = request.node.name
    logger.info(f"{'='*20} 开始执行: {test_name} {'='*20}")
    start = time.time()

    yield

    elapsed = time.time() - start
    logger.info(f"{'='*20} 执行结束: {test_name} (耗时 {elapsed:.3f}s) {'='*20}")
