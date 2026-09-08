"""
55 开发环境 - 合规运营 - 个人信息保护 PIA 多步骤工具层

来源：hsc_auto_dev123/compliance_operations/personal_info/utils_personal_info.py

接口清单：
- POST /personal-info-protection/pia/{taskId}/step/3   保存风险评估（步骤 3）
- POST /personal-info-protection/pia/{taskId}/step/5   保存风险处置（步骤 5）
- PUT  /compliance/result/{resultId}                   人工修改判定结果

已知限制（123 沿用）：step/3、step/5 接口仅支持 UI 工作流创建的任务，
API 创建的任务调用可能返回 500，测试中做兼容处理。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL, get_headers
from core.base import request_wrapper

PIP_BASE = f"{BASE_URL}/personal-info-protection/pia"
COMPLIANCE_RESULT_BASE = f"{BASE_URL}/compliance/result"


def save_risk_assessment(task_id, step3_data):
    """保存风险评估（步骤 3）：POST /personal-info-protection/pia/{taskId}/step/3
    step3_data: {riskSources[], rightsImpacts[], riskMatrix[]}"""
    return request_wrapper("post", f"{PIP_BASE}/{task_id}/step/3", msg="保存PIA风险评估",
                           json=step3_data, headers=get_headers())


def save_risk_treatment(task_id, treatments):
    """保存风险处置（步骤 5）：POST /personal-info-protection/pia/{taskId}/step/5
    treatments: [{riskMatrixId, measure, strategy, responsible, planDate, actualDate, status}]"""
    return request_wrapper("post", f"{PIP_BASE}/{task_id}/step/5", msg="保存PIA风险处置",
                           json=treatments, headers=get_headers())


def update_result_manual(result_id, result, remark=""):
    """人工修改判定结果：PUT /compliance/result/{resultId}
    result: "符合"/"部分符合"/"不符合"/"不适用"；remark: 备注"""
    return request_wrapper("put", f"{COMPLIANCE_RESULT_BASE}/{result_id}",
                           msg="人工修改判定结果",
                           json={"result": result, "remark": remark}, headers=get_headers())
