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
    """判断是否为签名校验导致的 500/服务器开小差了"""
    msg = response_data.get("message", "")
    return "服务器开小差了" in msg or response_data.get("code") == 500


# -------------------------------------------------------
# 测试数据清理关键字
# -------------------------------------------------------

CLEANUP_KEYWORDS = ["test_", "e2e_", "测试", "E2E"]

# 各模块对应的关键字（用于 cleanup_test_data.py）
USER_CLEANUP_KEYWORDS = ["test_", "e2e_", "测试"]
ROLE_CLEANUP_KEYWORDS = ["test_", "e2e_", "测试", "E2E"]
DEPT_CLEANUP_KEYWORDS = ["测试"]
MENU_CLEANUP_KEYWORDS = ["测试"]
