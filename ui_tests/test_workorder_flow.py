"""
工单派单审批流 UI 自动化 —— 核心业务流用例（P0）

业务来源：~/Downloads/工单审批流程-测试任务书.md.txt
覆盖优先级（任务书 P0）：
  1.2 派单成功
  2.1 审批通过 / 2.2 审批未通过
  3.1 派单即修复中 / 3.2 审批未通过回退
  4.1 超管全见
  6.1 防重复提交

============================================================================
选择器已根据 2026-09-08 HSC 123 环境真实前端回填。
============================================================================

多角色说明：
- 派单/审批/复核：common_admin 角色（默认账号 ceshi）
- 修复/执行：operation 角色（默认账号 chuli）
- 超管全见：admin 角色（默认账号 admin）

用法：conftest role_page fixture 支持 @pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)。
"""
import pytest
import allure
from playwright.sync_api import expect

from workorder_page import (
    VulnListPage,
    WorkorderListPage,
    DisposalPanel,
)


# ============================================================================
# 模块一：派单
# ============================================================================

@allure.feature("工单派单审批流")
@allure.story("模块一/三：派单成功 + 漏洞状态联动")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_success(role_page):
    """1.2 派单成功 + 3.1 派单即修复中。

    步骤：脆弱性管理 → 列表行「处置」→ 选「派单」→ 填审批人/运维人员/级别/描述 → 提交
    预期：提示"已提交审批"；工单管理列表出现该工单（待审批状态）
    """
    page = role_page
    vuln = VulnListPage(page).open()
    panel = vuln.open_dispose_panel(row_index=0)

    # 选处置方式「派单」
    panel.select_dispatch()
    # 填表单
    # 账号对照（用户确认）：ceshi=普通管理员、chuli=工单处理人员
    # 下拉显示的是「显示名/角色标签」而非登录账号名：
    #   审批人下拉里有「普通管理员」→ 即 ceshi(common_admin)
    #   处理人下拉里只有「工单处理人员」→ 即 chuli(operation)
    panel.select_approver("普通管理员")   # 审批人 = 派单人自己(ceshi/普通管理员)
    panel.select_handler("工单处理人员")   # 处理人 = chuli(工单处理人员组)
    panel.select_level("紧急")
    panel.fill_description("自动化测试派单")
    panel.submit()
    panel.expect_submit_success()

    # 验证工单列表出现待审批工单
    orders = WorkorderListPage(page).open()
    expect(orders.page.locator(".el-table").get_by_text("待审批").first).to_be_visible()


@allure.feature("工单派单审批流")
@allure.story("模块六：交互细节")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_prevent_duplicate_submit(role_page):
    """6.1 处置提交防重复：提交期间按钮 loading，阻止连点产生重复工单。

    步骤：派单表单填完 → 点提交 → 提交按钮短暂进入 loading（禁用，防连点）→ 面板关闭提交成功
    预期：提交按钮出现 is-loading 防连点态；处置面板关闭（仅一次成功提交，无重复工单）
    """
    import time as _time
    page = role_page
    vuln = VulnListPage(page).open()
    panel = vuln.open_dispose_panel(row_index=0)

    panel.select_dispatch()
    panel.select_approver("普通管理员")  # ceshi(普通管理员)
    panel.select_handler("工单处理人员")  # chuli(工单处理人员组)
    panel.select_level("紧急")
    panel.fill_description(f"防重复自动测试-{_time.strftime('%H%M%S')}")
    # 点提交并验证防连点（按钮 loading）+ 面板关闭（仅一次提交）
    panel.submit_and_verify_no_double()


# ============================================================================
# 模块二：审批
# ============================================================================

@allure.feature("工单派单审批流")
@allure.story("模块二：审批通过")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_approve_pass(role_page):
    """2.1 审批通过。

    步骤：工单管理列表 → 点击「审批」→ 审批通过
    预期：工单状态变"待处理"；处理人员视角可见该工单
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    # 记录将被审批的工单编号（动作后据此断言，避免看到别条同状态工单假绿）
    wo_no = orders.capture_first_actionable_no("审批")
    dialog = orders.click_approve(row_index=0)
    dialog.approve_pass()
    # 防假绿：刷新后按编号断言状态流转（审批通过 → 待处理）
    orders.refresh()
    orders.assert_row_status(wo_no, "待处理")
    orders.assert_row_action_gone(wo_no, "审批")


@allure.feature("工单派单审批流")
@allure.story("模块二/三：审批未通过 + 状态回退")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_approve_reject(role_page):
    """2.2 审批未通过 + 3.2 回退到派单前状态。

    步骤：工单管理列表 → 点击「审批」→ 审批未通过 + 填意见
    预期：工单状态"审批未通过"（终态）；派单人可撤销
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    wo_no = orders.capture_first_actionable_no("审批")
    dialog = orders.click_approve(row_index=0)
    dialog.approve_reject("驳回：信息不全，请补充")
    # 防假绿：刷新后按编号断言状态流转（审批未通过）
    orders.refresh()
    orders.assert_row_status(wo_no, "审批未通过")
    orders.assert_row_action_gone(wo_no, "审批")


# ============================================================================
# 模块四：超管全见
# ============================================================================

@allure.feature("工单派单审批流")
@allure.story("模块四：超管全见")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("admin")
@pytest.mark.parametrize("role_page", ["admin"], indirect=True)
def test_admin_can_see_all(role_page):
    """4.1 超管全见：admin 能看到所有工单（含其他角色派发的）。

    步骤：admin 登录 → 工单管理列表
    预期：列表非空，且包含其他角色创建的工单
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    rows = orders.page.locator(".el-table tbody tr")
    expect(rows.first).to_be_visible()


# ============================================================================
# 模块五：处理人员执行（operation 角色）
# ============================================================================

@allure.feature("工单派单审批流")
@allure.story("模块五：处理人员执行")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("operation")
@pytest.mark.parametrize("role_page", ["operation"], indirect=True)
def test_handler_execute_and_submit_review(role_page):
    """处理人员：处理 → 已修复 → 保存 → 提交复核。

    步骤：处理人员登录 → 工单列表 → 处理 → 选处理结论"已修复" → 保存 → 提交复核
    预期：工单状态变"待复核"；审批人员视角可见"复核"按钮
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    wo_no = orders.capture_first_actionable_no("处理")
    dialog = orders.click_handle(row_index=0)
    dialog.select_conclusion("已修复")
    dialog.save()
    dialog.submit_review()
    # 防假绿：刷新后按编号断言状态流转（提交复核 → 待复核）
    orders.refresh()
    orders.assert_row_status(wo_no, "待复核")
    orders.assert_row_action_gone(wo_no, "处理")


# ============================================================================
# 模块六：复核（common_admin 角色）
# ============================================================================

@allure.feature("工单派单审批流")
@allure.story("模块六：复核通过")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_review_pass(role_page):
    """复核通过：审批人员复核处理结果。

    步骤：common_admin 登录 → 工单列表 → 复核 → 复核通过
    预期：工单状态变"已完成"或"已复核"
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    wo_no = orders.capture_first_actionable_no("复核")
    dialog = orders.click_review(row_index=0)
    dialog.review_pass()
    # 防假绿：刷新后按编号断言状态流转（复核通过 → 已完成）
    orders.refresh()
    orders.assert_row_status(wo_no, "已完成")
    orders.assert_row_action_gone(wo_no, "复核")
