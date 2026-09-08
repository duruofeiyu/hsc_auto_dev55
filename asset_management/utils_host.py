"""
55 开发环境 - 资产管理 - 主机资产工具层
API 模块：/asset/host
来源：hsc_auto_dev123/asset_management/utils_host.py（接口字段与 payload 对齐 123）

说明：
- 复用 55 的 base.request_wrapper（自动注入 x-sign 签名、timeout、verify=False）
- 复用 config.get_headers()（动态读取 token，优先 auth_headers.json）
- 无独立详情接口，详情通过查询列表（POST /asset/host/list）按 id 匹配获取
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

HOST_BASE = f"{BASE_URL}/asset/host"

# 模糊搜索字段范围（与 123 保持一致）
KEYWORD_FIELDS = ["assetName", "ip", "mac", "os", "deptName"]


def build_host_payload(
    asset_name="自动化测试主机",
    ip="10.200.0.1",
    mac="00:0C:29:00:00:01",
    os_name="Windows",
    dept_id=1,
    tag_ids=None,
    is_antivirus=False,
    is_xinchuang=False,
    owner="测试负责人",
    owner_phone="13800138000",
    owner_email="test@example.com",
    remark="自动化测试创建",
):
    """构建新增主机 payload（字段与 123 get_default_host_payload 对齐）"""
    if tag_ids is None:
        tag_ids = []
    return {
        "assetName": asset_name,
        "ip": ip,
        "mac": mac,
        "os": os_name,
        "deptId": dept_id,
        "tagIds": tag_ids,
        "isAntivirus": is_antivirus,
        "isXinchuang": is_xinchuang,
        "owner": owner,
        "ownerPhone": owner_phone,
        "ownerEmail": owner_email,
        "remark": remark,
    }


def query_hosts(payload=None):
    """
    查询主机列表
    POST /asset/host/list
    """
    if payload is None:
        payload = {
            "pageNum": 1,
            "pageSize": 10,
            "keyword": "",
            "keywordFields": KEYWORD_FIELDS,
            "condition": {},
        }
    return request_wrapper("post", f"{HOST_BASE}/list", msg="查询主机列表",
                           json=payload, headers=get_headers())


def create_host(payload):
    """新增主机：POST /asset/host"""
    return request_wrapper("post", HOST_BASE, msg="新增主机",
                           json=payload, headers=get_headers())


def update_host(host_id, payload):
    """编辑主机：PUT /asset/host/{host_id}（需传完整 payload）"""
    return request_wrapper("put", f"{HOST_BASE}/{host_id}", msg="编辑主机",
                           json=payload, headers=get_headers())


def delete_host(host_id):
    """删除主机：DELETE /asset/host/{host_id}"""
    return request_wrapper("delete", f"{HOST_BASE}/{host_id}", msg="删除主机",
                           headers=get_headers())


def batch_delete_hosts(host_ids):
    """批量删除主机：DELETE /asset/host/batch，body={"ids": [...]}"""
    return request_wrapper("delete", f"{HOST_BASE}/batch", msg="批量删除主机",
                           json={"ids": host_ids}, headers=get_headers())


def get_host_list_from_response(resp):
    """从查询响应中提取主机列表（容错）"""
    try:
        data = resp.json()
        if data.get("success"):
            return data.get("result", {}).get("list", [])
    except Exception:
        pass
    return []


def get_host_by_id(host_id, page_size=200):
    """从列表查询按 id 获取主机完整记录（无独立详情接口）"""
    resp = query_hosts({"pageNum": 1, "pageSize": page_size, "keyword": "",
                        "keywordFields": KEYWORD_FIELDS, "condition": {}})
    for h in get_host_list_from_response(resp):
        if h.get("id") == host_id:
            return h
    return None


def get_host_id_by_name(asset_name):
    """按资产名称精准查询 host_id"""
    resp = query_hosts({
        "pageNum": 1, "pageSize": 10, "keyword": "",
        "keywordFields": KEYWORD_FIELDS,
        "condition": {"assetName": asset_name},
    })
    for h in get_host_list_from_response(resp):
        if h.get("assetName") == asset_name:
            return h.get("id")
    return None
