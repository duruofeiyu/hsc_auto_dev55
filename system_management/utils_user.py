"""
55 开发环境 - 系统管理 - 用户管理工具层
"""

import requests
import sys, os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from config import BASE_URL
from system_management.base import get_headers, assert_success, assert_business_fail, request_wrapper

USER_BASE = f"{BASE_URL}/system/user"


def build_user_payload(
    user_account="test_user",
    password="XingDing@2024",
    user_name="测试用户",
    phone_number="13800000001",
    dept_id="1",
    email="test@qq.com",
    user_status=0,
    gender="",
    station="",
    role_ids=None,
    remark="",
    is_update=False
):
    """构建新增/编辑用户 payload"""
    if role_ids is None:
        role_ids = ["4"]
    payload = {
        "userName": user_name,
        "phoneNumber": phone_number,
        "deptId": dept_id,
        "email": email,
        "userStatus": user_status,
        "gender": gender,
        "station": station,
        "roleIds": role_ids,
        "remark": remark
    }
    if not is_update:
        payload["userAccount"] = user_account
        payload["password"] = password
    return payload


def query_users(payload=None):
    """
    查询用户列表
    POST /system/user/list
    """
    if payload is None:
        payload = {"pageNum": 1, "pageSize": 10, "condition": {"deptCode": ""}}
    return request_wrapper("post", f"{USER_BASE}/list", msg="查询用户列表",
                           json=payload, headers=get_headers())


def create_user(payload):
    """
    新增用户
    POST /system/user
    """
    return request_wrapper("post", USER_BASE, msg="新增用户",
                           json=payload, headers=get_headers())


def update_user(user_id, payload):
    """
    编辑用户
    PUT /system/user/{user_id}
    """
    return request_wrapper("put", f"{USER_BASE}/{user_id}", msg="编辑用户",
                           json=payload, headers=get_headers())


def delete_user(user_id):
    """
    删除用户
    DELETE /system/user/{user_id}
    """
    return request_wrapper("delete", f"{USER_BASE}/{user_id}", msg="删除用户",
                           headers=get_headers())


def batch_delete_users(user_ids):
    """
    批量删除用户
    DELETE /system/user/batch
    """
    return request_wrapper("delete", f"{USER_BASE}/batch", msg="批量删除用户",
                           json={"ids": user_ids}, headers=get_headers())


def reset_user_password(user_id, new_password="XingDing@2024"):
    """
    重置用户密码
    TODO: 路径待抓包确认
    """
    return request_wrapper("put", f"{USER_BASE}/{user_id}/password", msg="重置密码",
                           json={"password": new_password}, headers=get_headers())


def get_user_detail(user_id):
    """
    查询用户详情
    GET /system/user/{user_id}
    TODO: URL 待抓包确认
    """
    return request_wrapper("get", f"{USER_BASE}/{user_id}", msg="查询用户详情",
                           headers=get_headers())
