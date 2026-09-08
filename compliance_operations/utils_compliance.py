"""
55 开发环境 - 合规运营 - 通用任务工具层

合并 123 框架 10 个子模块复用的 /compliance/task 接口（仅 typeCode 不同），
去重后统一为单份工具层。来源：
  gdpr / personal_info / cryptographic_compliance / cybersecurity_maturity /
  cybersecurity_task / data_security / emr_rating / evaluation /
  hospital_rating / interconnect / internet_medicine

接口清单：
- POST /compliance/task/list              任务列表（分页/关键字/状态/standard/year/targetLevel 筛选）
- POST /compliance/task                   创建任务（JSON）
- DELETE /compliance/task/{taskId}         删除任务（注：55 统一用此格式；123 的 batch?taskIds= 在 55 返回 500）
- GET  /compliance/task/{taskId}/report    报告详情
- GET  /compliance/overview/recent-tasks   合规总览最近任务
- GET  /compliance/classified-protection/result-distribution  等保结果分布统计

关键结论（55 环境实测）：
- 除 COMPLIANCE_PI 外，其余 10 个 typeCode 仅 taskName+typeCode 即可创建成功（后端对
  formData/selectedCheckRoots 等硬编码字段容错）
- COMPLIANCE_PI 强校验 fileIds + formData.standard，缺任一返回 400
- 非法 typeCode 返回 400「合规类型不存在」；空/缺 taskName 返回 500（后端未校验，缺陷）
- targetLevel/templateId 等越界值被静默放行（参数校验缺陷，测试用 xfail 标注）
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL, get_env_id
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers  # noqa: F401

COMPLIANCE_TASK_BASE = f"{BASE_URL}/compliance/task"
OVERVIEW_RECENT_TASKS_URL = f"{BASE_URL}/compliance/overview/recent-tasks"
RESULT_DISTRIBUTION_URL = f"{BASE_URL}/compliance/classified-protection/result-distribution"


# ======================== 模块类型常量 ========================

class ComplianceType:
    """合规任务类型（11 个 typeCode 全集）"""
    NS = "COMPLIANCE_NS"               # 网络安全任务书
    PI = "COMPLIANCE_PI"               # 个人信息保护
    DJPC = "COMPLIANCE_DJPC"           # 等保测评
    SM = "COMPLIANCE_SM"               # 国密合规
    HR = "COMPLIANCE_HR"               # 三甲评审
    DS = "COMPLIANCE_DS"               # 数据安全
    EMR = "COMPLIANCE_EMR"             # 电子病历评级
    MATURITY = "COMPLIANCE_MATURITY"   # 网络安全成熟度
    SH = "COMPLIANCE_SH"               # 智慧医院评级
    CONN = "COMPLIANCE_CONN"           # 互联互通
    IM = "COMPLIANCE_IM"               # 互联网诊疗


ALL_TYPE_CODES = [
    ComplianceType.NS, ComplianceType.PI, ComplianceType.DJPC, ComplianceType.SM,
    ComplianceType.HR, ComplianceType.DS, ComplianceType.EMR, ComplianceType.MATURITY,
    ComplianceType.SH, ComplianceType.CONN, ComplianceType.IM,
]


class TaskStatus:
    """任务状态"""
    ALL = "ALL"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


ALL_TASK_STATUSES = [
    TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.PENDING,
    TaskStatus.FAILED, TaskStatus.STOPPED,
]


# ======================== 个人信息保护默认配置 ========================

# 个人信息保护检查项目文件 ID（环境相关，见 config.ENV_IDS）
# 55 实测有效值 [3054]；123 原硬编码 8827 已失效，需在 123 实测后回填
PI_DETECTION_FILE_IDS = get_env_id("PI_DETECTION_FILE_IDS", [3054])

# 保护检测 8 个维度（与 55 已有「患者在线挂号与预约-保护检测」任务一致）
PI_DETECTION_DIMENSIONS = [
    "个人信息收集", "个人信息存储", "个人信息使用", "个人信息主体权利",
    "个人信息安全基本原则", "委托处理、共享、转让、公开披露", "安全事件处置", "组织管理制度",
]


# ======================== 任务列表接口 ========================

def build_list_payload(
    type_code=ComplianceType.NS,
    page_num=1,
    page_size=10,
    keyword=None,
    keyword_fields=None,
    latest_status=None,
    standard=None,
    year=None,
    target_level=None,
    task_name=None,
):
    """构建任务列表查询 payload。condition 可选字段：typeCode（必填）、
    latestStatus、standard、year、targetLevel、taskName"""
    condition = {"typeCode": type_code}
    if latest_status is not None and latest_status != TaskStatus.ALL:
        condition["latestStatus"] = latest_status
    if standard is not None:
        condition["standard"] = standard
    if year is not None:
        condition["year"] = year
    if target_level is not None:
        condition["targetLevel"] = target_level
    if task_name is not None:
        condition["taskName"] = task_name

    payload = {"pageNum": page_num, "pageSize": page_size, "condition": condition}
    if keyword is not None:
        payload["keyword"] = keyword
    if keyword_fields is not None:
        payload["keywordFields"] = keyword_fields
    return payload


def query_task_list(type_code=ComplianceType.NS, page_num=1, page_size=10,
                    keyword=None, keyword_fields=None, latest_status=None,
                    standard=None, year=None, target_level=None, task_name=None):
    """查询任务列表：POST /compliance/task/list
    响应 result: {list[], total, pageNum, pageSize, pages}"""
    payload = build_list_payload(type_code, page_num, page_size, keyword, keyword_fields,
                                 latest_status, standard, year, target_level, task_name)
    return request_wrapper("post", f"{COMPLIANCE_TASK_BASE}/list", msg="查询合规任务列表",
                           json=payload, headers=get_headers())


# ======================== 任务创建接口 ========================

def build_task_payload(type_code, task_name, **overrides):
    """
    构建创建任务 payload（按 typeCode 分发默认字段，overrides 可覆盖任意顶层字段）

    55 环境实测：除 PI 外其余 typeCode 仅 taskName+typeCode 即可创建成功，
    故此处不塞 formData/selectedCheckRoots 等硬编码 ID（避免 123 的失效 ID 问题），
    仅保留 targetLevel/templateId 等语义字段默认值，便于字段校验测试。
    """
    base = {"taskName": task_name, "typeCode": type_code}

    if type_code == ComplianceType.NS:
        base["fileIds"] = [1]
    elif type_code == ComplianceType.PI:
        base["fileIds"] = list(PI_DETECTION_FILE_IDS)
        base["systemIds"] = []
        base["formData"] = {
            "standard": "detection",
            "taskName": task_name,
            "systemIds": [],
            "dimensions": list(PI_DETECTION_DIMENSIONS),
            "dimensionNames": list(PI_DETECTION_DIMENSIONS),
        }
    elif type_code == ComplianceType.DJPC:
        base.update(templateId="1", targetLevel="等保二级", year=2026, systemIds=[], fileIds=[])
    elif type_code == ComplianceType.SM:
        base.update(templateId="5", targetLevel="3", year=2026, systemIds=[], fileIds=[1])
    elif type_code == ComplianceType.HR:
        base.update(year=2026, currentLevel="乙等", targetLevel="甲等")
    elif type_code == ComplianceType.DS:
        base.update(typeId=3, systemIds=[], fileIds=[1])
    elif type_code == ComplianceType.EMR:
        base.update(targetLevel="4", systemIds=[])
    elif type_code == ComplianceType.MATURITY:
        base.update(targetLevel="4")
    elif type_code == ComplianceType.SH:
        base.update(targetLevel="3", systemIds=[])
    elif type_code == ComplianceType.CONN:
        base.update(targetLevel="4b")
    elif type_code == ComplianceType.IM:
        base.update(systemIds=[], fileIds=[1])

    base.update(overrides)
    return base


def create_task(payload):
    """创建任务：POST /compliance/task
    响应：{"success": true, "code": 200, "result": "taskId"}"""
    return request_wrapper("post", COMPLIANCE_TASK_BASE, msg="创建合规任务",
                           json=payload, headers=get_headers())


# ======================== 任务删除接口 ========================

def delete_task(task_id):
    """删除任务：DELETE /compliance/task/{taskId}
    注：55 环境统一用此格式；123 的 batch?taskIds= 在 55 返回 500（已修正）"""
    return request_wrapper("delete", f"{COMPLIANCE_TASK_BASE}/{task_id}", msg="删除合规任务",
                           headers=get_headers())


# ======================== 报告详情接口 ========================

def get_task_report(task_id):
    """查询任务报告详情：GET /compliance/task/{taskId}/report?_t=ts
    响应 result: taskId, typeCode, taskName, status, systemNames[], systems[],
                 overview{score, conclusion, scoreLabel, resultSummary}, tabs[]"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{COMPLIANCE_TASK_BASE}/{task_id}/report",
                           msg="查询合规任务报告", params=params, headers=get_headers())


# ======================== 合规总览接口 ========================

def query_recent_tasks(status=TaskStatus.ALL, keyword=None, page_num=1, page_size=10):
    """查询最近任务列表：GET /compliance/overview/recent-tasks
    响应 result: {items[], total, pageNum, pageSize}"""
    params = {
        "status": status,
        "pageNum": page_num,
        "pageSize": page_size,
        "_t": int(time.time() * 1000),
    }
    if keyword is not None:
        params["keyword"] = keyword
    return request_wrapper("get", OVERVIEW_RECENT_TASKS_URL, msg="查询合规总览最近任务",
                           params=params, headers=get_headers())


# ======================== 等保结果分布接口 ========================

def get_result_distribution(system_id=None):
    """查询检测结果分布统计：GET /compliance/classified-protection/result-distribution
    响应 result: conformant, partialConformant, nonConformant, notApplicable,
                 undetermined, total, conformantRate, highRisk, systems[]"""
    params = {"_t": int(time.time() * 1000)}
    if system_id is not None:
        params["systemId"] = system_id
    return request_wrapper("get", RESULT_DISTRIBUTION_URL, msg="查询等保结果分布",
                           params=params, headers=get_headers())
