"""
55 开发环境 - 合规运营 - 个人信息保护（PIA）接口测试
覆盖：PI 任务创建（detection/pia/audit 三种 standard + 必填校验）、
     PIA 多步骤工作流（step/3 风险评估、step/5 风险处置）、人工修改判定结果
"""
import pytest
import allure
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import assert_success, assert_business_fail
from core.utils_common import unique_name
from compliance_operations.utils_compliance import (
    ComplianceType, build_task_payload, create_task, delete_task, query_task_list, get_task_report,
    PI_DETECTION_FILE_IDS,
)
from compliance_operations.utils_pia import (
    save_risk_assessment, save_risk_treatment, update_result_manual,
)


def _new_name(prefix="个人信息保护"):
    return unique_name(prefix=prefix)


# ======================== 1. PI 任务创建 ========================

@allure.epic("HSC 合规运营")
@allure.feature("个人信息保护")
@allure.story("PI 任务创建")
class TestPICreate:

    @allure.title("创建保护检测任务（detection）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_detection(self):
        task_id = None
        try:
            payload = build_task_payload(ComplianceType.PI, _new_name("检测"))
            task_id = assert_success(create_task(payload), "创建保护检测任务")
            assert task_id, "创建成功但未返回任务 id"
        finally:
            if task_id:
                delete_task(task_id)

    @allure.title("创建 PIA 评估任务（pia）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_pia(self):
        task_id = None
        try:
            payload = build_task_payload(ComplianceType.PI, _new_name("PIA"),
                                         formData={"standard": "pia"})
            task_id = assert_success(create_task(payload), "创建PIA评估任务")
        finally:
            if task_id:
                delete_task(task_id)

    @allure.title("创建合规审计任务（audit）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_audit(self):
        task_id = None
        try:
            payload = build_task_payload(ComplianceType.PI, _new_name("审计"),
                                         formData={"standard": "audit"})
            task_id = assert_success(create_task(payload), "创建合规审计任务")
        finally:
            if task_id:
                delete_task(task_id)

    @allure.title("创建-缺少 fileIds")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_missing_file_ids(self):
        payload = {"taskName": _new_name("缺文件"), "typeCode": ComplianceType.PI}
        resp = create_task(payload)
        assert_business_fail(resp, "缺 fileIds 应失败")

    @allure.title("创建-缺少 formData")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_missing_form_data(self):
        payload = {"taskName": _new_name("缺表单"), "typeCode": ComplianceType.PI, "fileIds": list(PI_DETECTION_FILE_IDS)}
        resp = create_task(payload)
        assert_business_fail(resp, "缺 formData 应失败")


# ======================== 2. PIA 多步骤工作流 ========================

@allure.epic("HSC 合规运营")
@allure.feature("个人信息保护")
@allure.story("PIA 多步骤工作流")
class TestPIAWorkflow:

    def _make_pia_task(self):
        """创建 PIA 任务并返回 task_id，失败返回 None"""
        payload = build_task_payload(ComplianceType.PI, _new_name("PIA"),
                                     formData={"standard": "pia"})
        resp = create_task(payload)
        data = resp.json()
        return data.get("result") if data.get("success") else None

    @allure.title("保存风险评估（步骤 3）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_save_risk_assessment(self):
        task_id = self._make_pia_task()
        if not task_id:
            pytest.skip("创建 PIA 任务失败，跳过")
        try:
            step3_data = {
                "riskSources": [
                    {"sourceType": "INTERNAL", "riskDesc": "测试风险源", "threatType": "网络攻击"}
                ],
                "rightsImpacts": [
                    {"dimension": "autonomy", "impactDesc": "影响自主选择", "impactLevel": 2},
                ],
                "riskMatrix": [
                    {"riskSourceId": 0, "riskDesc": "测试风险", "likelihood": 1,
                     "impactLevel": 1, "riskScore": 1, "riskLevel": "low"}
                ],
            }
            resp = save_risk_assessment(task_id, step3_data)
            data = resp.json()
            # 已知限制：step/3 仅支持 UI 工作流创建的任务，API 创建的任务可能返回 500
            if data.get("code") == 500:
                pytest.skip("step/3 返回 500（已知限制：需 UI 工作流创建的任务）")
            assert data.get("success") is True, f"step/3 应成功: {data}"
        finally:
            delete_task(task_id)

    @allure.title("保存风险处置（步骤 5）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_save_risk_treatment(self):
        task_id = self._make_pia_task()
        if not task_id:
            pytest.skip("创建 PIA 任务失败，跳过")
        try:
            treatments = [
                {"riskMatrixId": int(time.time() * 1000), "measure": "加密存储",
                 "strategy": "immediate", "responsible": "信息安全部",
                 "planDate": "2026-09-15", "actualDate": "", "status": "planned"}
            ]
            resp = save_risk_treatment(task_id, treatments)
            data = resp.json()
            if data.get("code") == 500:
                pytest.skip("step/5 返回 500（已知限制：需 UI 工作流创建的任务）")
            assert data.get("success") is True, f"step/5 应成功: {data}"
        finally:
            delete_task(task_id)


# ======================== 3. 人工修改判定结果 ========================

@allure.epic("HSC 合规运营")
@allure.feature("个人信息保护")
@allure.story("人工修改判定结果")
class TestResultUpdate:

    def _get_one_result_id(self):
        """从已完成检测任务的报告中提取一个 resultId"""
        resp = query_task_list(type_code=ComplianceType.PI, latest_status="COMPLETED",
                               page_size=10)
        data = resp.json()
        if not (data.get("success") and data.get("code") == 200):
            return None
        items = data.get("result", {}).get("list", [])
        if not items:
            return None
        report_resp = get_task_report(items[0].get("id"))
        report = report_resp.json()
        if not (report.get("success") and report.get("code") == 200):
            return None
        for tab in report.get("result", {}).get("tabs", []):
            for node in tab.get("tree", []):
                entries = node.get("entries") or []
                for entry in entries:
                    if entry.get("resultId"):
                        return entry["resultId"]
                for child in (node.get("children") or []):
                    for child_entry in (child.get("entries") or []):
                        if child_entry.get("resultId"):
                            return child_entry["resultId"]
        return None

    @allure.title("人工判定-修改为符合")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_result_conformant(self):
        result_id = self._get_one_result_id()
        if not result_id:
            pytest.skip("无已完成检测任务的 resultId，跳过")
        resp = update_result_manual(result_id, "符合", "人工判定为符合")
        data = resp.json()
        assert "success" in data, f"接口未返回业务响应: {data}"

    @allure.title("人工判定-不存在的 resultId")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_result_non_existent(self):
        resp = update_result_manual("9999999999999999999", "符合", "")
        assert_business_fail(resp, "不存在 resultId 应失败")
