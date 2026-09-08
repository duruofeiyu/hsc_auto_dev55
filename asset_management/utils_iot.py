"""
55 开发环境 - 资产管理 - 物联网(IoT)资产工具层
API 模块：/asset/iot
来源：hsc_auto_dev123/asset_management/utils_iot.py（接口字段与 payload 对齐 123）
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

IOT_BASE = f"{BASE_URL}/asset/iot"

# 模糊搜索字段范围（与 123 保持一致）
KEYWORD_FIELDS = ["ip", "brand", "assetName", "deptName", "mac"]

# 修改时需剔除的只读/后端维护字段
_STRIP_FIELDS = ["id", "assetType", "assetStatus", "domain", "deptId", "assetValue",
                 "source", "discoverTime", "lastScanTime", "createTime", "portCount",
                 "deptName", "tags", "iotId"]


def build_iot_payload(
    asset_name=None,
    ip=None,
    serial_number="",
    protocol="",
    firmware="",
    mac="",
    brand="",
    owner="",
    owner_phone="",
    owner_email="",
    tag_ids=None,
    remark="",
):
    """构建 IoT 资产 payload（字段与 123 get_default_iot_payload 对齐）"""
    if tag_ids is None:
        tag_ids = []
    return {
        "assetName": asset_name,
        "ip": ip,
        "serialNumber": serial_number,
        "protocol": protocol,
        "firmware": firmware,
        "mac": mac,
        "brand": brand,
        "owner": owner,
        "ownerPhone": owner_phone,
        "ownerEmail": owner_email,
        "tagIds": tag_ids,
        "remark": remark,
    }


def query_iot_assets(payload=None):
    """查询 IoT 资产列表：POST /asset/iot/list"""
    if payload is None:
        payload = {
            "pageNum": 1,
            "pageSize": 10,
            "keyword": "",
            "keywordFields": KEYWORD_FIELDS,
            "condition": {},
        }
    return request_wrapper("post", f"{IOT_BASE}/list", msg="查询IoT资产列表",
                           json=payload, headers=get_headers())


def create_iot_asset(payload):
    """新增 IoT 资产：POST /asset/iot"""
    return request_wrapper("post", IOT_BASE, msg="新增IoT资产",
                           json=payload, headers=get_headers())


def update_iot_asset(iot_id, payload):
    """编辑 IoT 资产：PUT /asset/iot/{iot_id}（需传完整 payload）"""
    return request_wrapper("put", f"{IOT_BASE}/{iot_id}", msg="编辑IoT资产",
                           json=payload, headers=get_headers())


def delete_iot_asset(iot_id):
    """删除 IoT 资产：DELETE /asset/iot/{iot_id}"""
    return request_wrapper("delete", f"{IOT_BASE}/{iot_id}", msg="删除IoT资产",
                           headers=get_headers())


def get_iot_detail(iot_id):
    """获取 IoT 资产详情：GET /asset/iot/{iot_id}?_t={ts}"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{IOT_BASE}/{iot_id}", msg="获取IoT资产详情",
                           params=params, headers=get_headers())


def build_iot_payload_from_detail(detail):
    """从详情反构造完整修改 payload（白名单：只保留模板字段）。

    注意：不能用黑名单剔除只读字段——详情返回还包含 scanAssetType/deviceType/
    rtspRealm/supplier/supplierContact/isIntranet 等模板外字段，原样塞回 PUT 会
    触发后端 500。故只从详情里取模板已有的字段。
    """
    payload = build_iot_payload()
    if isinstance(detail, dict):
        for k in list(payload.keys()):
            if k in detail:
                payload[k] = detail[k]
    return payload


def get_iot_list_from_response(resp):
    """从查询响应中提取 IoT 资产列表（容错）"""
    try:
        data = resp.json()
        if data.get("success"):
            return data.get("result", {}).get("list", [])
    except Exception:
        pass
    return []


def get_iot_id_by_name(keyword):
    """按名称关键字查询 IoT 资产 id（取第一条）"""
    resp = query_iot_assets({"pageNum": 1, "pageSize": 10, "keyword": keyword,
                             "keywordFields": KEYWORD_FIELDS, "condition": {}})
    records = get_iot_list_from_response(resp)
    return records[0].get("id") if records else None
