"""
55 开发环境 - 合规运营 - 管理系统工具层

来源：hsc_auto_dev123/compliance_operations/system_info/utils_system_info.py

接口清单：
- GET  /asset/options                         关联资产下拉选项
- GET  /asset/list-by-ids                     根据 ID 查询关联资产详情
- POST /compliance/system                     新增系统（multipart/form-data）
- POST /compliance/system/list                查询系统列表（JSON）
- PUT  /compliance/system/{id}                编辑系统（multipart/form-data）
- DELETE /compliance/system/{id}              删除系统

关键结论（55 环境实测）：
- 新增/编辑系统必须用 multipart/form-data（JSON 放在 "request" 字段、文件名 "blob"）；
  用普通 application/json 会返回 500
- 查询列表、删除、资产接口走普通 JSON/GET，可用 request_wrapper
"""
import sys
import os
import json
import time
import uuid
import random
import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL, get_headers, load_token
from core.base import request_wrapper, assert_success, assert_business_fail  # noqa: F401

COMPLIANCE_SYSTEM_BASE = f"{BASE_URL}/compliance/system"
ASSET_OPTIONS_URL = f"{BASE_URL}/asset/options"
ASSET_LIST_BY_IDS_URL = f"{BASE_URL}/asset/list-by-ids"


# ======================== multipart 请求 ========================

def _multipart_call(method, url, payload):
    """发送 multipart/form-data 请求（新增/编辑系统专用）。
    绕过 request_wrapper（它会强制覆盖 Content-Type 并算 x-sign），
    后端要求 JSON 放在名为 "request"、文件名为 "blob" 的 form 字段中。"""
    token = load_token()
    headers = {
        "Authorization": token,
        "X-Access-Token": token,
    }
    files = {"request": (None, json.dumps(payload, ensure_ascii=False), "application/json")}
    return requests.request(method, url, files=files, headers=headers, verify=False, timeout=60)


# ======================== 关联资产接口 ========================

def get_asset_options():
    """获取关联资产下拉选项：GET /asset/options?_t=ts
    响应 result: [{id, assetName, ip, assetType}, ...]"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", ASSET_OPTIONS_URL, msg="获取关联资产下拉选项",
                           params=params, headers=get_headers())


def get_assets_by_ids(asset_ids):
    """根据资产 ID 查询资产详情：GET /asset/list-by-ids?ids=id1,id2&_t=ts"""
    params = {
        "ids": ",".join(str(aid) for aid in asset_ids),
        "_t": int(time.time() * 1000),
    }
    return request_wrapper("get", ASSET_LIST_BY_IDS_URL, msg="查询关联资产详情",
                           params=params, headers=get_headers())


# ======================== 系统管理接口 ========================

def build_system_payload(system_type=None, network_segment=None, deploy_location="检验楼机房",
                         website_url="", description="自动化测试系统", filing_date="",
                         filing_number="", assessment_org="", assessment_date="",
                         asset_ids=None, archives=None):
    """构建管理系统 payload。日期格式 YYYY-MM-DD；system_type/network_segment
    默认随机生成，避免唯一性冲突。"""
    if system_type is None:
        system_type = f"自动测试系统-{uuid.uuid4().hex[:6]}"
    if network_segment is None:
        network_segment = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.0/24"
    payload = {
        "systemType": system_type,
        "networkSegment": network_segment,
        "deployLocation": deploy_location,
        "websiteUrl": website_url,
        "description": description,
        "filingDate": filing_date,
        "filingNumber": filing_number,
        "assessmentOrg": assessment_org,
        "assessmentDate": assessment_date,
        "assetIds": asset_ids if asset_ids is not None else [],
    }
    if archives is not None:
        payload["archives"] = archives
    return payload


def create_system(payload):
    """新增管理系统：POST /compliance/system（multipart）
    响应 result: "systemId" """
    return _multipart_call("POST", COMPLIANCE_SYSTEM_BASE, payload)


def update_system(system_id, payload):
    """编辑管理系统：PUT /compliance/system/{id}（multipart）"""
    return _multipart_call("PUT", f"{COMPLIANCE_SYSTEM_BASE}/{system_id}", payload)


def delete_system(system_id):
    """删除管理系统：DELETE /compliance/system/{id}"""
    return request_wrapper("delete", f"{COMPLIANCE_SYSTEM_BASE}/{system_id}",
                           msg="删除管理系统", headers=get_headers())


def query_systems(payload=None):
    """查询系统列表：POST /compliance/system/list
    Body: {"pageNum":1, "pageSize":20, "orderBy":"create_time desc"}
    响应 result: {list[], total, ...}"""
    if payload is None:
        payload = {"pageNum": 1, "pageSize": 20, "orderBy": "create_time desc"}
    return request_wrapper("post", f"{COMPLIANCE_SYSTEM_BASE}/list", msg="查询管理系统列表",
                           json=payload, headers=get_headers())
