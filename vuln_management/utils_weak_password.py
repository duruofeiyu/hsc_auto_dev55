"""
55 开发环境 - 脆弱性管理 - 弱口令检测任务工具层
API 模块：/vuln/weak-scan
来源：hsc_auto_dev123/vuln_management/weak_password/utils_weak_password.py

说明：
- 复用 55 base.request_wrapper（自动注入 x-sign）
- 结果查询复用资产探测接口 /asset/probe/execution/{id}/results 与 /asset/probe/result/{id}
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

WEAK_SCAN_BASE = f"{BASE_URL}/vuln/weak-scan"

KEYWORD_FIELDS = ["taskNo", "taskName", "createBy"]

_TCP_PORTS = "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017"
_UDP_PORTS = "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100"


def build_weak_password_payload(
    task_name="自动化弱口令检测",
    scan_target="192.168.124.123",
    schedule_type="IMMEDIATE",
    task_status="ENABLED",
    sync_to_asset=True,
    strategy_id=-1,
    services="rdp,smb,ssh,mysql,redis",
    speed=2,
    max_retries=2,
    max_send_rate=10000,
    version_intensity=4,
    host_timeout=30,
    port_timeout=10000,
):
    """构建弱口令检测任务 payload（字段对齐 123 get_default_weak_scan_payload）"""
    return {
        "taskName": task_name,
        "scanTarget": scan_target,
        "scheduleType": schedule_type,
        "syncToAsset": sync_to_asset,
        "strategyId": strategy_id,
        "services": services,
        "taskStatus": task_status,
        "speed": speed,
        "maxRetries": max_retries,
        "maxSendRate": max_send_rate,
        "versionIntensity": version_intensity,
        "hostTimeout": host_timeout,
        "portTimeout": port_timeout,
        "skipHostDiscover": False,
        "osDetectEnabled": True,
        "hostDetectTemplate": 1,
        "serviceDetectEnabled": True,
        "udpScanEnabled": False,
        "ports": "1-65535",
        "udpPorts": "137",
        "excludePorts": "137",
        "tcpScanMethod": 1,
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


def query_weak_password_tasks(page_num=1, page_size=10, keyword=None):
    """查询弱口令检测任务列表：POST /vuln/weak-scan/list"""
    payload = {
        "pageNum": page_num, "pageSize": page_size, "orderBy": "create_time desc",
        "condition": {}, "keyword": keyword or "", "keywordFields": KEYWORD_FIELDS,
    }
    return request_wrapper("post", f"{WEAK_SCAN_BASE}/list", msg="查询弱口令检测任务列表",
                           json=payload, headers=get_headers())


def create_weak_password_task(payload):
    """创建：POST /vuln/weak-scan"""
    return request_wrapper("post", WEAK_SCAN_BASE, msg="创建弱口令检测任务",
                           json=payload, headers=get_headers())


def update_weak_password_task(task_id, payload):
    """编辑：PUT /vuln/weak-scan/{id}"""
    return request_wrapper("put", f"{WEAK_SCAN_BASE}/{task_id}", msg="编辑弱口令检测任务",
                           json=payload, headers=get_headers())


def delete_weak_password_task(task_id):
    """删除：DELETE /vuln/weak-scan/{id}"""
    return request_wrapper("delete", f"{WEAK_SCAN_BASE}/{task_id}", msg="删除弱口令检测任务",
                           headers=get_headers())


def start_weak_password_task(task_id):
    """启动：POST /vuln/weak-scan/{id}/start"""
    return request_wrapper("post", f"{WEAK_SCAN_BASE}/{task_id}/start", msg="启动弱口令检测任务",
                           headers=get_headers())


def stop_weak_password_task(task_id):
    """终止：POST /vuln/weak-scan/{id}/stop"""
    return request_wrapper("post", f"{WEAK_SCAN_BASE}/{task_id}/stop", msg="终止弱口令检测任务",
                           headers=get_headers())


def get_weak_password_detail(task_id):
    """任务执行详情：GET /vuln/weak-scan/{id}/execution?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEAK_SCAN_BASE}/{task_id}/execution", msg="查询弱口令检测执行详情",
                           params=params, headers=get_headers())


def get_weak_password_results(execution_id, page_num=1, page_size=10):
    """结果列表（复用资产探测接口）：POST /asset/probe/execution/{id}/results"""
    payload = {"pageNum": page_num, "pageSize": page_size}
    return request_wrapper("post", f"{BASE_URL}/asset/probe/execution/{execution_id}/results",
                           msg="查询弱口令检测结果", json=payload, headers=get_headers())
