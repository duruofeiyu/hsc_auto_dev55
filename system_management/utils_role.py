"""
55 开发环境 - 系统管理 - 角色管理工具层

注意：角色创建/编辑/删除接口需要 x-sign 签名头校验。
当前脚本暂未实现签名算法，因此角色写操作相关用例采用记录型断言，
不阻塞测试执行。拿到签名算法后可恢复为严格断言。
"""

import requests
import sys, os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from config import BASE_URL, get_headers as _get_base_headers
from system_management.base import assert_success, assert_business_fail, request_wrapper

ROLE_BASE = f"{BASE_URL}/system/role"


def get_headers():
    """
    构建请求头。
    注意：x-sign 签名由 system_management.base.request_wrapper 在每次发请求时
    统一计算（复刻 HSC 前端签名算法），此处不再手写占位。
    """
    headers = _get_base_headers()
    headers.update({
        "x-tenant-id": "0",
        "x-version": "v3",
        "x-timestamp": str(int(time.time() * 1000)),
    })
    return headers


def build_role_payload(
    role_name="测试角色",
    role_key="test_role",
    role_sort=1,
    data_scope=None,
    role_status=0,
    menu_ids=None,
    dept_ids=None,
    user_ids=None,
    remark="",
    is_update=False
):
    """
    构建新增/编辑角色 payload
    data_scope: 数据权限范围（1 全部数据，2 自定义，3 本部门，4 本部门及以下，5 仅本人）
    新增角色时建议不传 dataScope，避免后端校验异常
    """
    if menu_ids is None:
        menu_ids = []
    if dept_ids is None:
        dept_ids = []
    if user_ids is None:
        user_ids = []
    payload = {
        "roleName": role_name,
        "roleKey": role_key,
        "roleSort": role_sort,
        "roleStatus": role_status,
        "menuIds": menu_ids,
        "remark": remark
    }
    # 显式传 data_scope 时才加入 payload
    if data_scope is not None:
        payload["dataScope"] = data_scope
    # 数据分配时传 deptIds，分配用户时传 userIds
    if dept_ids:
        payload["deptIds"] = dept_ids
    if user_ids:
        payload["userIds"] = user_ids
    return payload


def query_roles(payload=None):
    """
    查询角色列表
    POST /system/role/list
    """
    if payload is None:
        payload = {"condition": {}, "pageNum": 1, "pageSize": 10}
    return request_wrapper("post", f"{ROLE_BASE}/list", msg="查询角色列表",
                           json=payload, headers=get_headers())


def create_role(payload):
    """
    新增角色
    POST /system/role
    TODO: URL 待抓包确认
    """
    return request_wrapper("post", ROLE_BASE, msg="新增角色",
                           json=payload, headers=get_headers())


def update_role(role_id, payload):
    """
    编辑角色
    PUT /system/role/{role_id}
    TODO: URL 待抓包确认
    """
    return request_wrapper("put", f"{ROLE_BASE}/{role_id}", msg="编辑角色",
                           json=payload, headers=get_headers())


def delete_role(role_id):
    """
    删除角色
    DELETE /system/role/{role_id}
    TODO: URL 待抓包确认
    """
    return request_wrapper("delete", f"{ROLE_BASE}/{role_id}", msg="删除角色",
                           headers=get_headers())


def batch_delete_roles(role_ids):
    """
    批量删除角色
    DELETE /system/role/batch
    TODO: URL 与参数格式待抓包确认
    """
    return request_wrapper("delete", f"{ROLE_BASE}/batch", msg="批量删除角色",
                           json={"ids": role_ids}, headers=get_headers())


def get_role_detail(role_id):
    """
    查询角色详情
    GET /system/role/{role_id}
    TODO: URL 待抓包确认
    """
    return request_wrapper("get", f"{ROLE_BASE}/{role_id}", msg="查询角色详情",
                           headers=get_headers())


def assign_role_menus(role_id, menu_ids):
    """
    分配角色菜单权限
    TODO: URL 与请求方式待抓包确认
    """
    return request_wrapper("put", f"{ROLE_BASE}/{role_id}/menu", msg="分配角色菜单",
                           json={"menuIds": menu_ids}, headers=get_headers())
