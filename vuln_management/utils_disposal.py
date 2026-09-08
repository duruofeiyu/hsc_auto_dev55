"""
55 开发环境 - 脆弱性管理 - 处置历史工具层（纯读）
API 模块：/vuln/disposal/list、/vuln/disposal/{id}
来源：hsc_auto_dev123/vuln_management/disposal/utils_disposal.py

说明：
- 复用 55 base.request_wrapper（自动注入 x-sign）
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

VULN_DISPOSAL_BASE = f"{BASE_URL}/vuln/disposal"


def query_disposal_history(page_num=1, page_size=10, keyword=None, condition=None):
    """处置历史列表：POST /vuln/disposal/list"""
    payload = {"pageNum": page_num, "pageSize": page_size, "condition": condition or {}}
    if keyword is not None:
        payload["keyword"] = keyword
    return request_wrapper("post", f"{VULN_DISPOSAL_BASE}/list", msg="查询处置历史列表",
                           json=payload, headers=get_headers())


def get_disposal_detail(disposal_id):
    """处置历史详情：GET /vuln/disposal/{id}?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{VULN_DISPOSAL_BASE}/{disposal_id}", msg="查询处置历史详情",
                           params=params, headers=get_headers())
