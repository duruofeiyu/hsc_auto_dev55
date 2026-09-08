"""
55 开发环境 - 合规运营 - 11 个 typeCode 参数化测试
数据：data/compliance_type_codes.yaml
覆盖：11 个 typeCode 正常创建 + 各 typeCode 特有字段（targetLevel 越界）校验
"""
import pytest
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import assert_success, assert_business_fail, load_yaml_data
from core.utils_common import unique_name
from compliance_operations.utils_compliance import (
    ComplianceType, build_task_payload, create_task, delete_task,
)

type_codes_data = load_yaml_data("compliance_type_codes.yaml")


def _new_name(prefix="合规任务"):
    return unique_name(prefix=prefix)


# ======================== 1. 11 个 typeCode 正常创建 ========================

@allure.epic("HSC 合规运营")
@allure.feature("任务类型覆盖")
@allure.story("各 typeCode 正常创建")
class TestAllTypeCodes:

    @allure.title("各 typeCode 正常创建 - {type_name}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("tc", type_codes_data["type_codes"], ids=lambda x: x["type_name"])
    def test_create_each_type_code(self, tc):
        type_code = tc["type_code"]
        task_id = None
        try:
            with allure.step(f"Step 1: 创建 {tc['type_name']} 任务"):
                payload = build_task_payload(type_code, _new_name(tc["type_name"]))
                task_id = assert_success(create_task(payload), tc['type_name'])
                assert task_id, f"{tc['type_name']} 创建成功但未返回 id"
        finally:
            if task_id:
                with allure.step("Step 2: 清理数据"):
                    delete_task(task_id)


# ======================== 2. targetLevel 越界校验（xfail 标注已知缺陷） ========================

@allure.epic("HSC 合规运营")
@allure.feature("任务类型覆盖")
@allure.story("targetLevel 越界校验")
class TestTargetLevelValidation:

    @allure.title("{tc[name]}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        "tc", type_codes_data["test_target_level_validation"], ids=lambda x: x["name"])
    def test_target_level_validation(self, tc):
        type_code = tc["type_code"]
        expected = tc["expected"]
        task_id = None
        try:
            with allure.step(f"Step 1: 创建 {tc['name']}"):
                payload = build_task_payload(type_code, _new_name(), **tc.get("override", {}))
                resp = create_task(payload)

            with allure.step("Step 2: 断言结果"):
                if expected["success"]:
                    task_id = assert_success(resp, tc['name'])
                else:
                    # 已知缺陷：越界值被静默放行（success=True）→ xfail；正确拒绝 → 通过
                    if expected.get("xfail") and resp.json().get("success"):
                        task_id = resp.json().get("result")
                        pytest.xfail(expected["xfail"])
                    assert_business_fail(resp, tc['name'])
        finally:
            if task_id:
                with allure.step("Step 3: 清理数据"):
                    delete_task(task_id)
