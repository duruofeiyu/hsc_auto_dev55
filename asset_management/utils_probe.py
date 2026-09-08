"""
55 开发环境 - 资产管理 - 资产探测任务工具层
API 模块：/asset/probe
来源：hsc_auto_dev123/asset_management/discovery/utils_probe.py + apis.md

说明：
- 复用 55 的 base.request_wrapper（自动注入 x-sign 签名）
- 修改接口需传全部字段（未传字段会被清空），推荐先 get_probe_detail 再覆盖
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

PROBE_BASE = f"{BASE_URL}/asset/probe"

# 端口探测 ping 用的常用端口串（与 123 / apis.md 保持一致）
_TCP_ACK_PORTS = "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017"
_UDP_PING_PORTS = "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100"


def build_probe_payload(
    task_name="接口自动化-探测任务",
    scan_target="192.168.124.55",
    schedule_type="IMMEDIATE",
    task_status="ENABLED",
    sync_to_asset=True,
    speed=2,
    max_retries=2,
    max_send_rate=10000,
    version_intensity=4,
    host_timeout=30,
    port_timeout=10000,
    skip_host_discover=False,
    os_detect_enabled=True,
    host_detect_template=1,
    service_detect_enabled=True,
    udp_scan_enabled=False,
    ports="1-65535",
    udp_ports="137",
    exclude_ports="137",
    tcp_scan_method=1,
):
    """构建资产探测任务 payload（字段与 apis.md 第 2 节对齐）"""
    return {
        "taskName": task_name,
        "scanTarget": scan_target,
        "scheduleType": schedule_type,
        "taskStatus": task_status,
        "syncToAsset": sync_to_asset,
        "speed": speed,
        "maxRetries": max_retries,
        "maxSendRate": max_send_rate,
        "versionIntensity": version_intensity,
        "hostTimeout": host_timeout,
        "portTimeout": port_timeout,
        "skipHostDiscover": skip_host_discover,
        "osDetectEnabled": os_detect_enabled,
        "hostDetectTemplate": host_detect_template,
        "serviceDetectEnabled": service_detect_enabled,
        "udpScanEnabled": udp_scan_enabled,
        "ports": ports,
        "udpPorts": udp_ports,
        "excludePorts": exclude_ports,
        "tcpScanMethod": tcp_scan_method,
        "icmpEchoPing": True,
        "icmpTimestampPing": True,
        "icmpMacPing": True,
        "tcpAckPing": True,
        "tcpAckPorts": _TCP_ACK_PORTS,
        "tcpSynPing": True,
        "tcpSynPorts": _TCP_ACK_PORTS,
        "udpPing": True,
        "udpPingPorts": _UDP_PING_PORTS,
        "arpPing": True,
    }


def query_probe_tasks(payload=None):
    """查询探测任务列表：POST /asset/probe/list"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
            "keyword": "", "keywordFields": ["taskNo", "taskName", "createBy"],
        }
    return request_wrapper("post", f"{PROBE_BASE}/list", msg="查询探测任务列表",
                           json=payload, headers=get_headers())


def create_probe_task(payload):
    """创建探测任务：POST /asset/probe"""
    return request_wrapper("post", PROBE_BASE, msg="创建探测任务",
                           json=payload, headers=get_headers())


def update_probe_task(task_id, payload):
    """修改探测任务：PUT /asset/probe/{task_id}（需传完整 payload）"""
    return request_wrapper("put", f"{PROBE_BASE}/{task_id}", msg="修改探测任务",
                           json=payload, headers=get_headers())


def delete_probe_task(task_id):
    """删除探测任务：DELETE /asset/probe/{task_id}（幂等）"""
    return request_wrapper("delete", f"{PROBE_BASE}/{task_id}", msg="删除探测任务",
                           headers=get_headers())


def get_probe_detail(task_id):
    """获取探测任务详情：GET /asset/probe/{task_id}?_t={ts}"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{PROBE_BASE}/{task_id}", msg="获取探测任务详情",
                           params=params, headers=get_headers())


def build_probe_payload_from_detail(detail):
    """从详情反构造完整修改 payload"""
    if not isinstance(detail, dict):
        return build_probe_payload()
    payload = build_probe_payload()
    for k in payload.keys():
        if k in detail:
            payload[k] = detail[k]
    return payload


def get_probe_task_list_from_response(resp):
    """从查询响应中提取任务列表（容错）"""
    try:
        data = resp.json()
        if data.get("success"):
            return data.get("result", {}).get("list", [])
    except Exception:
        pass
    return []
