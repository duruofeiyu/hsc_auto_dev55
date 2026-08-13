"""
55 开发环境 - 系统管理 - 部门管理工具层
"""

import requests
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from config import BASE_URL
from system_management.base import get_headers, assert_success, assert_business_fail, request_wrapper

DEPT_BASE = f"{BASE_URL}/system/dept"


def build_dept_payload(
    dept_name="测试部门",
    parent_id="1",
    dept_code="",
    order_num=1,
    leader="",
    region="",
    address="",
    dept_status=0,
    remark="",
    dept_ips=None
):
    """构建新增/编辑部门 payload"""
    if dept_ips is None:
        dept_ips = []
    return {
        "deptName": dept_name,
        "parentId": parent_id,
        "deptCode": dept_code,
        "orderNum": order_num,
        "leader": leader,
        "region": region,
        "address": address,
        "deptStatus": dept_status,
        "remark": remark,
        "deptIps": dept_ips
    }


def query_depts(payload=None):
    """
    查询部门列表
    POST /system/dept/list
    """
    if payload is None:
        payload = {"condition": {}, "pageNum": 1, "pageSize": 10}
    return request_wrapper("post", f"{DEPT_BASE}/list", msg="查询部门列表",
                           json=payload, headers=get_headers())


def create_dept(payload):
    """
    新增部门
    POST /system/dept
    """
    return request_wrapper("post", DEPT_BASE, msg="新增部门",
                           json=payload, headers=get_headers())


def update_dept(dept_id, payload):
    """
    编辑部门
    PUT /system/dept/{dept_id}
    TODO: URL 与请求方式待抓包确认
    """
    return request_wrapper("put", f"{DEPT_BASE}/{dept_id}", msg="编辑部门",
                           json=payload, headers=get_headers())


def delete_dept(dept_id):
    """
    删除部门
    DELETE /system/dept/{dept_id}
    TODO: URL 与请求方式待抓包确认
    """
    return request_wrapper("delete", f"{DEPT_BASE}/{dept_id}", msg="删除部门",
                           headers=get_headers())


def batch_delete_depts(dept_ids):
    """
    批量删除部门
    前端可能是逐个调用 DELETE /system/dept/{id}
    返回最后一个响应
    """
    last_resp = None
    for dept_id in dept_ids:
        last_resp = delete_dept(dept_id)
        data = last_resp.json()
        if not data.get("success"):
            return last_resp
    return last_resp
