"""
55 开发环境 - 系统管理 - 菜单管理工具层
"""

import requests
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from config import BASE_URL
from system_management.base import get_headers, assert_success, assert_business_fail, request_wrapper

MENU_BASE = f"{BASE_URL}/system/menu"


def build_menu_payload(
    menu_name="测试菜单",
    parent_id="1",
    order_num=1,
    menu_type="M",  # M 目录，C 菜单，F 按钮
    icon="asset",
    path="",
    component="",
    route_param="",
    perms="",
    is_out_link=0,
    is_cache=1,
    menu_visible=0,
    menu_status=0,
    remark=""
):
    """
    构建新增/编辑菜单 payload
    menu_type: M 目录，C 菜单，F 按钮
    """
    return {
        "menuName": menu_name,
        "parentId": parent_id,
        "orderNum": order_num,
        "menuType": menu_type,
        "icon": icon,
        "path": path,
        "component": component,
        "routeParam": route_param,
        "perms": perms,
        "isOutLink": is_out_link,
        "isCache": is_cache,
        "menuVisible": menu_visible,
        "menuStatus": menu_status,
        "remark": remark
    }


def query_menu_tree(timestamp=None):
    """
    查询菜单树
    GET /system/menu/tree?_t={timestamp}
    """
    import time
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    return request_wrapper("get", f"{MENU_BASE}/tree", msg="查询菜单树",
                           params={"_t": timestamp}, headers=get_headers())


def create_menu(payload):
    """
    新增菜单
    POST /system/menu
    """
    return request_wrapper("post", MENU_BASE, msg="新增菜单",
                           json=payload, headers=get_headers())


def update_menu(menu_id, payload):
    """
    编辑菜单
    PUT /system/menu/{menu_id}
    """
    return request_wrapper("put", f"{MENU_BASE}/{menu_id}", msg="编辑菜单",
                           json=payload, headers=get_headers())


def delete_menu(menu_id):
    """
    删除菜单
    DELETE /system/menu/{menu_id}
    """
    return request_wrapper("delete", f"{MENU_BASE}/{menu_id}", msg="删除菜单",
                           headers=get_headers())
