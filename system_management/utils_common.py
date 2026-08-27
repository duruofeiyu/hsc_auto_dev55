"""
55 开发环境 - 系统管理 - 公共工具函数
统一的唯一值生成（线程安全）、数据清理关键字、通用工具等
"""
import time
import uuid

# -------------------------------------------------------
# 线程安全的唯一值生成器
# 使用 uuid4 全量 + 时间戳前缀，保证并发不重复
# -------------------------------------------------------

def unique_name(prefix="测试"):
    """生成唯一名称（线程安全）"""
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def unique_account(prefix="test"):
    """生成唯一用户账号（线程安全）"""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def unique_code(prefix="code"):
    """生成唯一编码（线程安全）"""
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def unique_phone():
    """生成唯一手机号（线程安全）"""
    # 使用 uuid 取模，避免时间戳取模的碰撞问题
    return f"138{(int(uuid.uuid4().hex[:8], 16) % 100000000):08d}"


def unique_role_key(prefix="role"):
    """生成唯一角色标识（线程安全）"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# -------------------------------------------------------
# 树形结构工具
# -------------------------------------------------------

def find_in_tree(nodes, target_id):
    """在树形结构中递归查找指定 id"""
    for node in nodes:
        if node.get("id") == target_id:
            return True
        if find_in_tree(node.get("children") or [], target_id):
            return True
    return False


# -------------------------------------------------------
# 签名校验工具
# -------------------------------------------------------

def is_sign_error(response_data):
    """判断是否为签名校验导致的失败。

    注：2026-08-27 已复刻并实现 HSC 前端 x-sign 算法
    （system_management/utils_sign.compute_sign），并由 base.request_wrapper
    在每次请求时统一计算。实测 55 开发环境后端并不强制校验 x-sign
    （错误签名也能 200），故不再将 500「服务器开小差了」等同于签名错误
    （那多为后端 transient 故障）。此函数保留仅为兼容历史调用，现阶段恒返回 False。
    """
    return False


# -------------------------------------------------------
# 测试数据清理关键字
# -------------------------------------------------------

CLEANUP_KEYWORDS = ["test_", "e2e_", "测试", "E2E"]

# 各模块对应的关键字（用于 cleanup_test_data.py）
USER_CLEANUP_KEYWORDS = ["test_", "e2e_", "测试"]
ROLE_CLEANUP_KEYWORDS = ["test_", "e2e_", "测试", "E2E"]
DEPT_CLEANUP_KEYWORDS = ["测试"]
MENU_CLEANUP_KEYWORDS = ["测试"]
