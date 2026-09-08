"""
55 开发环境 - 资产管理 - 资产概览工具层
API 模块：/asset/overview + /asset/unregistered
来源：hsc_auto_dev123/asset_management/utils_overview.py

说明：
- 概览接口路径部分在 123 中标注 TODO，实测时以 55 环境为准修正
- 复用 55 的 base.request_wrapper（自动注入 x-sign 签名）
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

OVERVIEW_BASE = f"{BASE_URL}/asset/overview"
ASSET_BASE = f"{BASE_URL}/asset"


def get_overview_statistics():
    """获取资产概览统计卡片：GET /asset/overview/statistics"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{OVERVIEW_BASE}/statistics", msg="获取概览统计卡片",
                           params=params, headers=get_headers())


def get_overview_trend(period="7d"):
    """获取资产趋势数据：GET /asset/overview/trend?period={period}&_t={ts}"""
    params = {"period": period, "_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{OVERVIEW_BASE}/trend", msg="获取概览趋势图",
                           params=params, headers=get_headers())


def get_unregistered_assets(page_num=1, page_size=10, keyword=""):
    """获取未纳管资产列表：POST /asset/unregistered/list"""
    payload = {"pageNum": page_num, "pageSize": page_size}
    if keyword:
        payload["keyword"] = keyword
    return request_wrapper("post", f"{ASSET_BASE}/unregistered/list", msg="获取未纳管资产列表",
                           json=payload, headers=get_headers())


def register_asset(unregistered_id, asset_name="测试资产", dept_id=None, owner="",
                   owner_phone="", owner_email="", asset_value="MEDIUM", remark=""):
    """登记未纳管资产：POST /asset/unregistered/{id}/register"""
    payload = {
        "assetName": asset_name,
        "deptId": dept_id,
        "owner": owner,
        "ownerPhone": owner_phone,
        "ownerEmail": owner_email,
        "assetValue": asset_value,
        "remark": remark,
    }
    return request_wrapper("post", f"{ASSET_BASE}/unregistered/{unregistered_id}/register",
                           msg="登记未纳管资产", json=payload, headers=get_headers())


def get_unregistered_id_from_response(resp):
    """从响应中提取未纳管资产 id（容错）"""
    try:
        data = resp.json()
        if data.get("success"):
            records = data.get("result", {}).get("list", [])
            if records:
                return records[0].get("id") or records[0].get("assetId")
    except Exception:
        pass
    return None
