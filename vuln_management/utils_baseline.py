"""
55 开发环境 - 脆弱性管理 - 基线核查任务工具层
API 模块：/vuln/baseline-scan
来源：hsc_auto_dev123/vuln_management/baseline/utils_baseline_scan.py（字段与 payload 对齐 123 apis.md §11.3）

说明：
- 复用 55 的 base.request_wrapper（自动注入 x-sign、timeout、verify=False）
- 复用 config.get_headers()（动态读 token）
- 注意：批量删除 body 为 {"taskIds": "id1,id2"}（逗号分隔字符串），与 host-scan/web-scan 的数组不同
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL, get_env_id
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

BASELINE_SCAN_BASE = f"{BASE_URL}/vuln/baseline-scan"

KEYWORD_FIELDS = ["taskNo", "taskName", "createBy"]


def build_baseline_payload(
    task_name="自动化基线核查",
    scan_target="192.168.124.55",
    schedule_type="IMMEDIATE",
    task_status="ENABLED",
    check_type=2,
    targets_config=None,
):
    """
    构建基线核查任务 payload（字段对齐 apis.md §11.3.1）
    check_type: 2=在线基线核查
    targets_config: 列表，含 ip/protocol/port/username/password/templates
    """
    if targets_config is None:
        # DB2 模板 ID 环境相关（见 config.ENV_IDS.BASELINE_TEMPLATE_ID）
        baseline_template_id = get_env_id("BASELINE_TEMPLATE_ID", "332358588846572071")
        targets_config = [{
            "ip": scan_target,
            "protocol": "ssh",
            "port": 22,
            "username": "root",
            "password": "XingDing@2024",
            "templates": [{
                "templateId": baseline_template_id,
                "templateName": "DB2_配置规范_(Linux).zip",
                "parameters": {},
            }],
        }]
    # 若传入已是字符串（调用方已序列化，如非法 JSON 测试），直接透传
    targets_config_str = targets_config if isinstance(targets_config, str) \
        else json.dumps(targets_config, ensure_ascii=False)
    return {
        "taskName": task_name,
        "scanTarget": scan_target,
        "scheduleType": schedule_type,
        "taskStatus": task_status,
        "checkType": check_type,
        "targetsConfig": targets_config_str,
    }


def query_baseline_tasks(payload=None):
    """查询基线核查任务列表：POST /vuln/baseline-scan/list"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
            "condition": {}, "keyword": "", "keywordFields": KEYWORD_FIELDS,
        }
    return request_wrapper("post", f"{BASELINE_SCAN_BASE}/list", msg="查询基线核查任务列表",
                           json=payload, headers=get_headers())


def create_baseline_task(payload):
    """创建基线核查任务：POST /vuln/baseline-scan"""
    return request_wrapper("post", BASELINE_SCAN_BASE, msg="创建基线核查任务",
                           json=payload, headers=get_headers())


def update_baseline_task(task_id, payload):
    """编辑基线核查任务：PUT /vuln/baseline-scan/{id}"""
    return request_wrapper("put", f"{BASELINE_SCAN_BASE}/{task_id}", msg="编辑基线核查任务",
                           json=payload, headers=get_headers())


def delete_baseline_task(task_id):
    """删除基线核查任务：DELETE /vuln/baseline-scan/{id}"""
    return request_wrapper("delete", f"{BASELINE_SCAN_BASE}/{task_id}", msg="删除基线核查任务",
                           headers=get_headers())


def batch_delete_baseline_tasks(task_ids):
    """批量删除：DELETE /vuln/baseline-scan/batch，body={"taskIds": [...]}（数组）
    注意：55 环境实测为数组格式；apis.md §11.3.2 记的逗号分隔字符串会返回 500（文档已修正）"""
    if not isinstance(task_ids, list):
        task_ids = [task_ids]
    return request_wrapper("delete", f"{BASELINE_SCAN_BASE}/batch", msg="批量删除基线核查任务",
                           json={"taskIds": task_ids}, headers=get_headers())


def start_baseline_task(task_id):
    """启动：POST /vuln/baseline-scan/{id}/start"""
    return request_wrapper("post", f"{BASELINE_SCAN_BASE}/{task_id}/start", msg="启动基线核查任务",
                           headers=get_headers())


def stop_baseline_task(task_id):
    """终止：POST /vuln/baseline-scan/{id}/stop"""
    return request_wrapper("post", f"{BASELINE_SCAN_BASE}/{task_id}/stop", msg="终止基线核查任务",
                           headers=get_headers())


def get_baseline_detail(task_id):
    """任务配置详情：GET /vuln/baseline-scan/{id}?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{BASELINE_SCAN_BASE}/{task_id}", msg="查询基线核查任务详情",
                           params=params, headers=get_headers())


def get_baseline_execution(task_id):
    """任务执行详情：GET /vuln/baseline-scan/{id}/execution?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{BASELINE_SCAN_BASE}/{task_id}/execution", msg="查询基线核查执行详情",
                           params=params, headers=get_headers())


def export_baseline_tasks(task_ids, export_format="docx"):
    """批量导出：POST /vuln/baseline-scan/export-zip，body={"taskIds": [...], "format": "docx"}"""
    return request_wrapper("post", f"{BASELINE_SCAN_BASE}/export-zip", msg="导出基线核查任务",
                           json={"taskIds": task_ids, "format": export_format}, headers=get_headers())
