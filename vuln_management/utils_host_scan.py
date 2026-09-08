"""
55 开发环境 - 脆弱性管理 - 主机漏洞扫描任务工具层
API 模块：/vuln/host-scan
来源：hsc_auto_dev123/vuln_management/vuln_scan/utils_vuln_scan_host.py（字段对齐 apis.md §11.1）

说明：
- 复用 55 base.request_wrapper（自动注入 x-sign）
- 批量删除 body 为 {"taskIds": [...]}（数组，与 baseline 的逗号字符串不同）
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

HOST_SCAN_BASE = f"{BASE_URL}/vuln/host-scan"

KEYWORD_FIELDS = ["taskNo", "taskName", "createBy"]

_TCP_PORTS = "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017"
_UDP_PORTS = "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100"


def build_host_scan_payload(
    task_name="自动化主机漏洞扫描",
    scan_target="192.168.124.123",
    schedule_type="IMMEDIATE",
    task_status="ENABLED",
    sync_to_asset=True,
    template_id="29",
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
    poc_enabled=True,
):
    """构建主机漏洞扫描任务 payload（字段对齐 apis.md §11.1.1）"""
    return {
        "taskName": task_name,
        "scanTarget": scan_target,
        "scheduleType": schedule_type,
        "taskStatus": task_status,
        "syncToAsset": sync_to_asset,
        "templateId": template_id,
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
        "pocEnabled": poc_enabled,
        "icmpEchoPing": True,
        "icmpTimestampPing": True,
        "icmpMacPing": True,
        "tcpAckPing": True,
        "tcpAckPorts": _TCP_PORTS,
        "tcpSynPing": True,
        "tcpSynPorts": _TCP_PORTS,
        "udpPing": True,
        "udpPingPorts": _UDP_PORTS,
        "arpPing": True,
    }


def query_host_scan_tasks(payload=None):
    """查询主机漏洞扫描任务列表：POST /vuln/host-scan/list"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
            "condition": {}, "keyword": "", "keywordFields": KEYWORD_FIELDS,
        }
    return request_wrapper("post", f"{HOST_SCAN_BASE}/list", msg="查询主机漏洞扫描任务列表",
                           json=payload, headers=get_headers())


def create_host_scan_task(payload):
    """创建主机漏洞扫描任务：POST /vuln/host-scan"""
    return request_wrapper("post", HOST_SCAN_BASE, msg="创建主机漏洞扫描任务",
                           json=payload, headers=get_headers())


def update_host_scan_task(task_id, payload):
    """编辑：PUT /vuln/host-scan/{id}"""
    return request_wrapper("put", f"{HOST_SCAN_BASE}/{task_id}", msg="编辑主机漏洞扫描任务",
                           json=payload, headers=get_headers())


def delete_host_scan_task(task_id):
    """删除：DELETE /vuln/host-scan/{id}"""
    return request_wrapper("delete", f"{HOST_SCAN_BASE}/{task_id}", msg="删除主机漏洞扫描任务",
                           headers=get_headers())


def batch_delete_host_scan_tasks(task_ids):
    """批量删除：DELETE /vuln/host-scan/batch，body={"taskIds": [...]}（数组）"""
    if not isinstance(task_ids, list):
        task_ids = [task_ids]
    return request_wrapper("delete", f"{HOST_SCAN_BASE}/batch", msg="批量删除主机漏洞扫描任务",
                           json={"taskIds": task_ids}, headers=get_headers())


def start_host_scan_task(task_id):
    """启动：POST /vuln/host-scan/{id}/start"""
    return request_wrapper("post", f"{HOST_SCAN_BASE}/{task_id}/start", msg="启动主机漏洞扫描任务",
                           headers=get_headers())


def stop_host_scan_task(task_id):
    """终止：POST /vuln/host-scan/{id}/stop"""
    return request_wrapper("post", f"{HOST_SCAN_BASE}/{task_id}/stop", msg="终止主机漏洞扫描任务",
                           headers=get_headers())


def get_host_scan_detail(task_id):
    """任务配置详情：GET /vuln/host-scan/{id}?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{HOST_SCAN_BASE}/{task_id}", msg="查询主机漏洞扫描任务详情",
                           params=params, headers=get_headers())


def get_host_scan_execution(task_id):
    """任务执行详情：GET /vuln/host-scan/{id}/execution?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{HOST_SCAN_BASE}/{task_id}/execution", msg="查询主机漏洞扫描执行详情",
                           params=params, headers=get_headers())


def export_host_scan_tasks(task_ids, export_format="docx"):
    """批量导出：POST /vuln/host-scan/export-zip"""
    return request_wrapper("post", f"{HOST_SCAN_BASE}/export-zip", msg="导出主机漏洞扫描任务",
                           json={"taskIds": task_ids, "format": export_format}, headers=get_headers())
