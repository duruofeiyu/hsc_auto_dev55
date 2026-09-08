"""
55 开发环境 - 脆弱性管理 - 脆弱性概览工具层（纯读）
API 模块：/vuln/host、/vuln/web、/vuln/weakpass、/vuln/baseline、/risk
来源：hsc_auto_dev123/vuln_management/vuln_overview/utils_vuln.py（对齐 apis.md §11.4）

说明：
- 复用 55 base.request_wrapper（自动注入 x-sign）
- 概览四卡 + 核心指标，均为只读接口
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

VULN_BASE = f"{BASE_URL}/vuln"
RISK_BASE = f"{BASE_URL}/risk"


def query_high_risk_host_list(payload=None):
    """高风险主机列表：POST /vuln/host/assetList"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10,
            "condition": {"orderBy": "totalRiskCount", "orderAsc": False},
        }
    return request_wrapper("post", f"{VULN_BASE}/host/assetList", msg="查询高风险主机列表",
                           json=payload, headers=get_headers())


def query_high_risk_web_list(payload=None):
    """高风险网站列表：POST /vuln/web/assetList"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10,
            "condition": {"orderBy": "totalRiskCount", "orderAsc": False},
        }
    return request_wrapper("post", f"{VULN_BASE}/web/assetList", msg="查询高风险网站列表",
                           json=payload, headers=get_headers())


def get_weak_password_statistics():
    """弱口令统计卡片：GET /vuln/weakpass/statistics?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{VULN_BASE}/weakpass/statistics", msg="查询弱口令统计",
                           params=params, headers=get_headers())


def get_baseline_statistics():
    """基线统计卡片：GET /vuln/baseline/statistics?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{VULN_BASE}/baseline/statistics", msg="查询基线统计",
                           params=params, headers=get_headers())


def get_risk_overview_metrics(time_range="week"):
    """核心指标：GET /risk/overview/metrics?timeRange={week|month|quarter|year}&_t=ts"""
    import time
    params = {"timeRange": time_range, "_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{RISK_BASE}/overview/metrics", msg="查询风险核心指标",
                           params=params, headers=get_headers())
