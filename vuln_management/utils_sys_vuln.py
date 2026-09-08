"""
55 开发环境 - 脆弱性管理 - 系统漏洞工具层
API 模块：/vuln/host（漏洞列表/详情/趋势/资产漏洞）+ /vuln/disposal（处置动作）
来源：hsc_auto_dev123/vuln_management/sys_vuln/utils_vuln_total_overview.py

说明：
- 复用 55 base.request_wrapper（自动注入 x-sign）
- list 接口 result 结构为单层：result.list + result.total（字符串）
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

VULN_HOST_BASE = f"{BASE_URL}/vuln/host"
VULN_DISPOSAL_BASE = f"{BASE_URL}/vuln/disposal"

# 处置动作类型
OPERATION_TYPES = ("FIX", "CONFIRM", "DISPATCH", "IGNORE", "FALSE_POSITIVE")


def get_vuln_trend(period="7d"):
    """漏洞趋势：GET /vuln/host/trend?period={7d|30d|90d}&_t=ts"""
    import time
    params = {"period": period, "_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{VULN_HOST_BASE}/trend", msg="查询漏洞趋势",
                           params=params, headers=get_headers())


def query_vuln_list(page_num=1, page_size=10, keyword=None, condition=None):
    """漏洞列表：POST /vuln/host/list"""
    payload = {"pageNum": page_num, "pageSize": page_size, "condition": condition or {}}
    if keyword is not None:
        payload["keyword"] = keyword
    return request_wrapper("post", f"{VULN_HOST_BASE}/list", msg="查询漏洞列表",
                           json=payload, headers=get_headers())


def get_vuln_detail(vuln_id):
    """漏洞详情：GET /vuln/host/{id}?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{VULN_HOST_BASE}/{vuln_id}", msg="查询漏洞详情",
                           params=params, headers=get_headers())


def dispose_vuln(vuln_id, operation_type, remark="", picture_path="", **extra):
    """处置漏洞：POST /vuln/disposal
    operation_type: FIX/CONFIRM/DISPATCH/IGNORE/FALSE_POSITIVE
    """
    payload = {
        "vulnId": vuln_id,
        "operationType": operation_type,
        "remark": remark,
        "picturePath": picture_path,
    }
    payload.update(extra)
    return request_wrapper("post", VULN_DISPOSAL_BASE, msg="处置漏洞",
                           json=payload, headers=get_headers())


def query_asset_vuln_list(page_num=1, page_size=10, condition=None):
    """资产漏洞列表：POST /vuln/host/assetList"""
    payload = {"pageNum": page_num, "pageSize": page_size, "condition": condition or {}}
    return request_wrapper("post", f"{VULN_HOST_BASE}/assetList", msg="查询资产漏洞列表",
                           json=payload, headers=get_headers())


def query_asset_vuln_detail_list(asset_id, page_num=1, page_size=10, order_by="vulnLevel", order_asc=False):
    """某资产下的漏洞详情列表：POST /vuln/host/detailList"""
    payload = {
        "pageNum": page_num, "pageSize": page_size,
        "condition": {"assetId": asset_id, "orderBy": order_by, "orderAsc": order_asc},
    }
    return request_wrapper("post", f"{VULN_HOST_BASE}/detailList", msg="查询资产漏洞详情列表",
                           json=payload, headers=get_headers())
