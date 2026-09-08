"""
55 开发环境 - 合规运营 - 管理系统接口测试
覆盖：系统 CRUD（multipart）、关联资产下拉选项、根据 ID 查资产、未授权访问
"""
import pytest
import allure
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.base import request_no_auth, assert_success
from compliance_operations.utils_system import (
    COMPLIANCE_SYSTEM_BASE, build_system_payload, create_system, update_system,
    delete_system, query_systems, get_asset_options, get_assets_by_ids,
)


# ======================== 1. 系统生命周期闭环 ========================

@allure.epic("HSC 合规运营")
@allure.feature("管理系统")
@allure.story("系统生命周期闭环")
class TestSystemLifecycle:

    @allure.title("创建→查询→编辑→删除 全流程闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_system_full_lifecycle(self):
        system_id = None
        try:
            with allure.step("Step 1: 创建系统"):
                payload = build_system_payload()
                resp = create_system(payload)
                system_id = assert_success(resp, "创建系统")
                assert system_id, "创建成功但未返回 systemId"

            with allure.step("Step 2: 查询列表验证出现"):
                result = assert_success(query_systems(), "查询系统列表")
                found = any(i.get("id") == system_id for i in result.get("list", []))
                assert found, f"新创建系统 {system_id} 应在列表中查到"

            with allure.step("Step 3: 编辑系统"):
                payload["description"] = "编辑后描述"
                assert_success(update_system(system_id, payload), "编辑系统")

            with allure.step("Step 4: 删除系统"):
                assert_success(delete_system(system_id), "删除系统")
                system_id = None
        finally:
            if system_id:
                delete_system(system_id)

    @allure.title("创建-自定义字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_system_custom_fields(self):
        system_id = None
        try:
            payload = build_system_payload(
                deploy_location="住院部机房",
                website_url="https://example.com",
                description="自定义字段测试系统",
                filing_number="F-2026-001",
                assessment_org="测试评估机构",
            )
            system_id = assert_success(create_system(payload), "创建自定义系统")
        finally:
            if system_id:
                delete_system(system_id)


# ======================== 2. 关联资产接口 ========================

@allure.epic("HSC 合规运营")
@allure.feature("管理系统")
@allure.story("关联资产")
class TestAssetOptions:

    @allure.title("获取关联资产下拉选项")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_asset_options(self):
        with allure.step("Step 1: 查询资产下拉选项"):
            resp = get_asset_options()
        with allure.step("Step 2: 断言结果"):
            result = assert_success(resp, "资产下拉选项")
            assert isinstance(result, list), "资产选项应为列表"

    @allure.title("根据资产 ID 查询资产详情")
    @allure.severity(allure.severity_level.NORMAL)
    def test_assets_by_ids(self):
        with allure.step("Step 1: 获取资产选项"):
            result = assert_success(get_asset_options(), "获取资产选项")
        if not result:
            pytest.skip("无资产数据，跳过")
        asset_id = result[0].get("id")
        with allure.step("Step 2: 根据 ID 查询详情"):
            detail = assert_success(get_assets_by_ids([asset_id]), "根据ID查资产")
            assert isinstance(detail, list), "资产详情应为列表"


# ======================== 3. 未授权访问 ========================

@allure.epic("HSC 合规运营")
@allure.feature("管理系统")
@allure.story("未授权访问")
class TestSystemNoAuth:

    @allure.title("无 Token 查询系统列表")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_systems_no_token(self):
        resp = request_no_auth("post", f"{COMPLIANCE_SYSTEM_BASE}/list", msg="无Token查系统列表",
                               json={"pageNum": 1, "pageSize": 10})
        data = resp.json()
        assert not (data.get("success") and data.get("code") == 200), \
            f"无 Token 不应查询成功: {data}"
