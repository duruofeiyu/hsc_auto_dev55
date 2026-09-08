"""
55 开发环境 - 资产管理 - 网站(Web)资产工具层
API 模块：/asset/web
来源：hsc_auto_dev123/asset_management/utils_web.py（接口字段与 payload 对齐 123）

注意：URL 与 assetName 不可重复（前端校验 + 后端唯一约束）
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

WEB_BASE = f"{BASE_URL}/asset/web"

# 模糊搜索字段范围（与 123 保持一致）
KEYWORD_FIELDS = ["ip", "domain", "url", "assetName", "owner"]

# 修改时需剔除的只读/后端维护字段
_STRIP_FIELDS = ["id", "assetType", "assetStatus", "ip", "ipListStr", "domain",
                 "deptId", "assetValue", "source", "discoverTime", "lastScanTime",
                 "createTime", "portCount", "deptName", "tags", "webId",
                 "responseCode", "serverHeader", "subDomain", "registrar", "sslEnabled"]


def build_web_payload(
    asset_name=None,
    url=None,
    asset_value="",
    is_intranet=True,
    ip_list=None,
    port_num=None,
    icp_rec_num="",
    ps_rec_num="",
    owner="",
    owner_phone="",
    owner_email="",
    remark="",
):
    """构建 Web 资产 payload（字段与 123 get_default_web_payload 对齐）"""
    if ip_list is None:
        ip_list = []
    return {
        "assetName": asset_name,
        "url": url,
        "assetValue": asset_value,
        "isIntranet": is_intranet,
        "ipList": ip_list,
        "portNum": port_num,
        "icpRecNum": icp_rec_num,
        "psRecNum": ps_rec_num,
        "owner": owner,
        "ownerPhone": owner_phone,
        "ownerEmail": owner_email,
        "remark": remark,
    }


def query_web_assets(payload=None):
    """查询 Web 资产列表：POST /asset/web/list"""
    if payload is None:
        payload = {
            "pageNum": 1,
            "pageSize": 10,
            "keyword": "",
            "keywordFields": KEYWORD_FIELDS,
        }
    return request_wrapper("post", f"{WEB_BASE}/list", msg="查询Web资产列表",
                           json=payload, headers=get_headers())


def create_web_asset(payload):
    """新增 Web 资产：POST /asset/web"""
    return request_wrapper("post", WEB_BASE, msg="新增Web资产",
                           json=payload, headers=get_headers())


def update_web_asset(web_id, payload):
    """编辑 Web 资产：PUT /asset/web/{web_id}（需传完整 payload）"""
    return request_wrapper("put", f"{WEB_BASE}/{web_id}", msg="编辑Web资产",
                           json=payload, headers=get_headers())


def delete_web_asset(web_id):
    """删除 Web 资产：DELETE /asset/web/{web_id}"""
    return request_wrapper("delete", f"{WEB_BASE}/{web_id}", msg="删除Web资产",
                           headers=get_headers())


def get_web_detail(web_id):
    """获取 Web 资产详情：GET /asset/web/{web_id}?_t={ts}"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEB_BASE}/{web_id}", msg="获取Web资产详情",
                           params=params, headers=get_headers())


def build_web_payload_from_detail(detail):
    """从详情反构造完整修改 payload（白名单：只保留模板字段）。

    与 utils_iot 同理：详情可能返回模板外字段，黑名单剔除会漏网导致 PUT 500。
    故只从详情里取模板已有的字段，统一白名单模式。
    """
    payload = build_web_payload()
    if isinstance(detail, dict):
        for k in list(payload.keys()):
            if k in detail:
                payload[k] = detail[k]
    return payload


def get_web_list_from_response(resp):
    """从查询响应中提取 Web 资产列表（容错）"""
    try:
        data = resp.json()
        if data.get("success"):
            return data.get("result", {}).get("list", [])
    except Exception:
        pass
    return []


def get_web_id_by_url(url_keyword):
    """按 URL 关键字查询 Web 资产 id（取第一条）"""
    resp = query_web_assets({"pageNum": 1, "pageSize": 10, "keyword": url_keyword,
                             "keywordFields": KEYWORD_FIELDS})
    records = get_web_list_from_response(resp)
    return records[0].get("id") if records else None
