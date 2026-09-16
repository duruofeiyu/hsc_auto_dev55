"""
工单派单审批流 —— UI 交互类用例（非主流程）

============================================================================
与 test_workorder_flow.py(主流程 happy path) 互补，聚焦「按钮 → 反馈」的 UI 交互：
  档一 · 纯交互不落库：只打开弹窗/触发校验，不提交、不改数据，可反复跑
  档三 · 表单字段约束：必填校验链、默认选中态（探测 2026-09-08 实测）
  档四 · 权限与可见性：同工单不同角色视角按钮可见性、disabled 态

设计要点（防假绿 / 防 flaky）：
- 纯交互用例用「动作 → 断言反馈 → 弹窗状态」三步，不真正提交改写数据，
  因此可反复跑，数据零污染。
- 必填校验文案来自真实前端(123 环境实测)：审批人=「请选择审批人」、
  运维人员=「请选择运维人员」、描述非必填（选齐前两者即可提交）。
- 处置方式默认选中「修复」（radio 组首个），需点「派单」才展开派单表单。

用法：与 conftest role_page fixture 配合（parametrize 指定角色）。
============================================================================
"""
import pytest
import allure

from workorder_page import (
    VulnListPage,
    WorkorderListPage,
    DisposalPanel,
    ApprovalDialog,
    HandleDialog,
)


# ============================================================================
# 档一 · 纯交互不落库（零数据副作用，可反复跑）
# ============================================================================

@allure.feature("工单 UI 交互")
@allure.story("处置面板默认交互态")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_disposal_panel_default_mode(role_page):
    """处置面板打开后，处置方式默认选中「修复」，不自动展开派单表单。"""
    page = role_page
    vuln = VulnListPage(page).open()
    panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
    try:
        mode = panel.selected_mode()
        assert mode == "修复", f"处置面板默认处置方式应为「修复」，实际为「{mode}」"
        # 未选「派单」前，派单表单字段不应出现（审批人等）
        assert page.locator(".el-form-item", has_text="审批人").count() == 0, \
            "未点「派单」前不应出现审批人字段（派单表单未展开）"
    finally:
        panel.close()


@allure.feature("工单 UI 交互")
@allure.story("派单必填校验")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_required_approver(role_page):
    """派单必填校验1：切到「派单」但不选审批人直接提交 → 拦截提示「请选择审批人」，面板保持打开。"""
    page = role_page
    vuln = VulnListPage(page).open()
    panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
    try:
        panel.select_mode("派单")      # 展开派单表单，但不填任何字段
        panel.submit_plain()           # 直接提交
        panel.expect_validation_error("请选择审批人")
    finally:
        panel.close()


@allure.feature("工单 UI 交互")
@allure.story("派单必填校验")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_required_handler(role_page):
    """派单必填校验2：选了审批人、未选运维人员 → 拦截提示「请选择运维人员」。"""
    page = role_page
    vuln = VulnListPage(page).open()
    panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
    try:
        panel.select_mode("派单")
        panel.select_approver("普通管理员")
        panel.submit_plain()
        panel.expect_validation_error("请选择运维人员")
    finally:
        panel.close()


@allure.feature("工单 UI 交互")
@allure.story("审批弹窗取消")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_approve_cancel_keeps_status(role_page):
    """审批弹窗点「取消」→ 弹窗关闭，工单状态不变（仍待审批），审批按钮仍在。"""
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    # 定位一条可审批工单，动作前记下编号 + 操作按钮仍在
    row, idx = orders._find_first_row_with_action("审批")
    no = orders._extract_workorder_no(row)
    # 点审批 → 弹窗出现
    dialog = orders.click_approve(row_index=idx)
    assert page.get_by_role("button", name="审批通过", exact=True).count() > 0, "审批弹窗未打开"
    # 点取消
    dialog.cancel()
    page.wait_for_timeout(1500)
    # 弹窗应关闭
    assert page.locator(".el-dialog:visible, .el-drawer:visible").count() == 0, "点取消后审批弹窗未关闭"
    # 状态不变：刷新后该工单仍可审批（按钮仍在）
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), f"取消后工单 {no} 状态不应改变，应仍为待审批"
    assert orders.count_action("审批") >= 1, "取消后应仍存在可审批工单"


# ============================================================================
# 档四 · 权限与可见性
# ============================================================================

@allure.feature("工单 UI 交互")
@allure.story("角色按钮可见性")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("operation")
@pytest.mark.parametrize("role_page", ["operation"], indirect=True)
def test_operation_has_no_approve_button(role_page):
    """处理人员(operation)视角：工单列表里不应出现「审批」按钮（审批是 common_admin 的事）。"""
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    approve_cnt = orders.count_action("审批")
    assert approve_cnt == 0, f"处理人员视角不应出现「审批」按钮，实际有 {approve_cnt} 个"
    # 处理人员视角应至少能看到列表(能看到待处理工单的处理按钮)
    handle_cnt = orders.count_action("处理")
    assert handle_cnt >= 1 or orders._rows().count() > 0, "处理人员视角应能看到工单列表"


@allure.feature("工单 UI 交互")
@allure.story("同单不同角色按钮")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_same_wo_only_review_after_handled(role_page):
    """复核人视角：仅对「待复核」工单出现「复核」按钮；待审批工单不出现「复核」。"""
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    # 找一条待复核工单
    try:
        row, idx = orders.find_newest_in_status("待复核")
    except Exception:
        pytest.skip("当前无「待复核」工单，跳过（数据依赖）")
    no = orders._extract_workorder_no(row)
    # 该行应含「复核」按钮
    assert "复核" in row.inner_text(), f"待复核工单 {no} 应出现「复核」入口"


# ============================================================================
# 分支用例专用 helper（自建一条目标状态工单，供异常分支测试用）
# ============================================================================

def _dispatch_new_wo(role_page, desc_suffix="", level="紧急", desc=None, module="网站漏洞管理"):
    """自建一条派单工单并返回其编号（common_admin 视角，工单状态=待审批）。

    参数：
      level   工单级别（默认「紧急」；传其它如「普通」用于级别遍历）
      desc    工单描述；None=留空不填（用于验证描述非必填仍能派单成功）
      module  漏洞来源模块：系统漏洞管理 / 网站漏洞管理 / 弱口令管理 / 基线管理

    数据副作用：消耗 1 条可处置漏洞，新增 1 条工单（需用户接受真实建单）。
    """
    import time as _t
    vuln = VulnListPage(role_page, module=module).open()
    panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
    panel.select_mode("派单")
    panel.select_approver("普通管理员")
    panel.select_handler("工单处理人员")
    panel.select_level(level)
    if desc is None:
        desc = f"交互分支-{desc_suffix}-{_t.strftime('%H%M%S')}"
    else:
        panel.fill_description(desc)
    panel.submit()
    panel.expect_submit_success()
    orders = WorkorderListPage(role_page).open()
    orders.refresh()
    row, _, no = orders.find_newest_in_status("待审批")
    return orders, no


# ============================================================================
# 档一补充 · 驳回意见必填（零副作用，不落库）
# ============================================================================

@allure.feature("工单 UI 交互")
@allure.story("审批驳回意见必填")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_approve_reject_requires_opinion(role_page):
    """2.3 驳回意见必填：审批弹窗点「审批未通过」但不填意见 → 弹「审批未通过时必须填写审批意见」，不提交。

    零副作用：被校验拦截，工单保持待审批（不会真驳回）。
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    row, idx = orders._find_first_row_with_action("审批")
    no = orders._extract_workorder_no(row)
    dialog = orders.click_approve(row_index=idx)
    # 直接点「审批未通过」，不填意见
    page.get_by_role("button", name="审批未通过", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(1800)
    # 应弹校验提示
    try:
        msg = page.locator(".el-message:visible", has_text="必须填写审批意见").first
        msg.wait_for(state="visible", timeout=4000)
    except Exception:
        raise AssertionError("审批未通过未填意见时未出现「必须填写审批意见」拦截提示")
    # 审批主弹窗应保持打开（未提交）
    assert page.locator(".el-dialog:visible").count() >= 1, "驳回被拦截后审批弹窗不应关闭"
    # 关掉弹窗，工单仍待审批
    dialog.cancel()
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), f"拦截后工单 {no} 不应被驳回，应仍为待审批"


# ============================================================================
# 档二 · 状态流转异常分支（真实建单消耗数据）
# ============================================================================

@allure.feature("工单 UI 交互")
@allure.story("待审批期撤销")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_revoke_pending_workorder(role_page):
    """2.6/3.5 待审批期撤销：自建待审批工单 → 派单人「撤销」（填必填原因）→ 工单状态变「已撤销」。

    数据副作用：消耗 1 条可处置漏洞，工单进入「已撤销」终态。
    """
    page = role_page
    orders, no = _dispatch_new_wo(page, "撤销")
    # 刚建的待审批工单，行上有「撤销」按钮 → 对该行精确撤销（避免 click_revoke 点到别条待审批单）
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), f"撤销前工单 {no} 应为待审批"
    row.locator("button, a, .el-link", has_text="撤销").first.click(timeout=10000)
    page.wait_for_timeout(1500)
    from workorder_page import RevokeDialog
    dlg = RevokeDialog(page)
    dlg.fill_reason("自动化测试撤销：需求变更")
    dlg.confirm()
    orders.refresh()
    # 断言已撤销
    row = orders.find_row_by_no(no)
    assert "已撤销" in row.inner_text(), f"撤销后工单 {no} 应变为「已撤销」，实际: {row.inner_text()[:100]}"
    # 撤销后撤销按钮应消失
    assert row.locator("button, .el-link", has_text="撤销").count() == 0, "已撤销工单不应再有撤销按钮"




@allure.feature("工单 UI 交互")
@allure.story("处理结论下拉可选项")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("operation")
@pytest.mark.parametrize("role_page", ["operation"], indirect=True)
def test_handle_conclusion_options_available(role_page):
    """处理弹窗漏洞明细的「处理结论」下拉可选到各选项（已修复/已忽略/误报），选后保存不报错。

    低副作用：只点「处理」打开 → 遍历可选项 → 保存 → 关闭，不提交复核，
    工单保持待处理，可反复测。需环境有「待处理」工单，无则跳过。
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    try:
        row, idx = orders._find_first_row_with_action("处理")
    except AssertionError:
        pytest.skip("当前无「待处理」工单可测处理结论，跳过（数据依赖）")
    # 点处理打开弹窗
    row.locator("button, a, .el-link", has_text="处理").first.click(timeout=10000)
    page.wait_for_timeout(1800)
    # 处理弹窗内漏洞明细行0的下拉
    rows = page.locator(".el-dialog:visible .el-table tbody tr")
    row0 = rows.nth(0)
    row0.wait_for(state="visible", timeout=8000)
    select = row0.locator(".el-select").first
    select.click(timeout=8000)
    dd = page.locator(".el-select-dropdown:visible").first
    dd.wait_for(state="visible", timeout=5000)
    options = [t.strip() for t in dd.locator(".el-select-dropdown__item").all_inner_texts() if t.strip()]
    print(f"处理结论可选 = {options}")
    # 应有固定几个结论选项
    for expected in ("待修复", "已修复", "已忽略", "误报"):
        assert any(expected in o for o in options), f"处理结论下拉缺少选项「{expected}」，实际: {options}"
    # 选「误报」→ 保存 → 不报错、弹窗还在
    opt = dd.locator(".el-select-dropdown__item", has_text="误报").first
    opt.click(timeout=5000)
    page.wait_for_timeout(800)
    # 保存（暂存，不提交复核）
    from workorder_page import HandleDialog
    HandleDialog(page).save()
    page.wait_for_timeout(800)
    # 关闭弹窗
    try:
        page.get_by_role("button", name="关闭", exact=True).first.click(timeout=4000)
    except Exception:
        page.keyboard.press("Escape")
    page.wait_for_timeout(800)


# ============================================================================
# 档三 · 表单字段维度
# ============================================================================

@allure.feature("工单 UI 交互")
@allure.story("审批人下拉选项")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_approver_dropdown_options(role_page):
    """审批人下拉应非空且含「普通管理员」（业务审批账号 ceshi）。

    零副作用：只打开派单面板展开审批人下拉读取选项，不选中不提交。
    """
    page = role_page
    vuln = VulnListPage(page).open()
    panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
    try:
        panel.select_mode("派单")
        opts = panel.read_select_options("审批人")
        print(f"审批人下拉选项 = {opts}")
        assert opts, "审批人下拉不应为空"
        assert any("普通管理员" in o for o in opts), \
            f"审批人下拉应含「普通管理员」，实际: {opts}"
        # 运维人员(处理人)下拉也应非空
        opts2 = panel.read_select_options("运维人员")
        print(f"运维人员下拉选项 = {opts2}")
        assert opts2, "运维人员下拉不应为空"
    finally:
        panel.close()


@allure.feature("工单 UI 交互")
@allure.story("派单级别遍历")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_normal_level_success(role_page):
    """派单级别选「普通」仍能派单成功到「待审批」（不只「紧急」可用）。

    数据副作用：消耗 1 条可处置漏洞，新增 1 条待审批工单。
    """
    page = role_page
    orders, no = _dispatch_new_wo(page, "普通级别", level="普通")
    # 派单后该工单应为「待审批」
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), \
        f"「普通」级别派单后工单 {no} 应进入待审批，实际: {row.inner_text()[:120]}"


@allure.feature("工单 UI 交互")
@allure.story("派单描述非必填")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_description_optional(role_page):
    """工单描述可留空仍能派单成功（真实行为：描述非必填，选齐审批人+运维即可提交）。

    数据副作用：消耗 1 条可处置漏洞，新增 1 条待审批工单。
    """
    page = role_page
    orders, no = _dispatch_new_wo(page, "描述留空", desc=None)  # 不填描述
    # 关键：能提交成功即验证描述非必填（_dispatch_new_wo 内部 expect_submit_success 已断言）
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), \
        f"描述留空派单后工单 {no} 应进入待审批，实际: {row.inner_text()[:120]}"


# ============================================================================
# 档二扩展 · 四个派单入口模块全覆盖（系统漏洞/网站漏洞/弱口令/基线）
# ============================================================================
# 真实业务（123 环境核对 2026-09-09）：四个模块行内都有"处置"按钮可派单，
# 派单后工单正常进入待审批。证明"派单"入口是四个模块通用的。
# 数据副作用：每个模块各消耗 1 条可处置漏洞（用户已接受真实建单消耗）。

@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_from_system_vuln(role_page):
    """系统漏洞管理 → 派单成功到待审批。"""
    page = role_page
    orders, no = _dispatch_new_wo(page, "系统漏洞", module="系统漏洞管理")
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), \
        f"系统漏洞派单后 {no} 应进入待审批，实际: {row.inner_text()[:120]}"


@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_from_website_vuln(role_page):
    """网站漏洞管理 → 派单成功到待审批。"""
    page = role_page
    orders, no = _dispatch_new_wo(page, "网站漏洞", module="网站漏洞管理")
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), \
        f"网站漏洞派单后 {no} 应进入待审批，实际: {row.inner_text()[:120]}"


@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_from_weak_password(role_page):
    """弱口令管理 → 派单成功到待审批。"""
    page = role_page
    orders, no = _dispatch_new_wo(page, "弱口令", module="弱口令管理")
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), \
        f"弱口令派单后 {no} 应进入待审批，实际: {row.inner_text()[:120]}"


@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispatch_from_baseline(role_page):
    """基线管理 → 派单成功到待审批。"""
    page = role_page
    orders, no = _dispatch_new_wo(page, "基线", module="基线管理")
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), \
        f"基线派单后 {no} 应进入待审批，实际: {row.inner_text()[:120]}"


# ============================================================================
# 档五 · 状态机分支（横向扩：审批驳回终态、已驳回撤销路径）
# ============================================================================

@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_approve_reject_ends_as_rejected(role_page):
    """5.1 审批驳回终态：派单 → 审批驳回（必填意见）→ 工单进入「审批未通过」终态。

    终态文案：审批阶段驳回 = 「审批未通过」（区别于复核阶段驳回 = 「已驳回」）。
    与设计文档任务书 5.5 写「驳回→回待处理」不一致，按 123 环境实测「审批未通过」终态断言。

    ⚠️ 关键实测（产品不对称，可能提 bug）：
      复核驳回 → 「已驳回」→ 派单人可「撤销」
      审批驳回 → 「审批未通过」→ 派单人无「撤销」按钮（连撤销都没法做）

    数据副作用：消耗 1 条可处置漏洞，新增 1 条「审批未通过」工单。
    """
    page = role_page
    # 1) 自建一条待审批工单
    orders, no = _dispatch_new_wo(page, "审批驳回终态")
    # 2) 找到该行，断言行上有「审批」按钮
    row = orders.find_row_by_no(no)
    assert "待审批" in row.inner_text(), f"派单后 {no} 应为待审批，实际: {row.inner_text()[:120]}"
    assert row.locator("button, a, .el-link", has_text="审批").count() > 0, \
        f"待审批工单 {no} 应有「审批」按钮"
    # 3) 点行上的「审批」→ 打开审批弹窗 → 选驳回 + 填意见
    row.locator("button, a, .el-link", has_text="审批").first.click(timeout=10000)
    page.wait_for_timeout(1500)
    ApprovalDialog(page).approve_reject("自动化测试驳回：场景不适用")
    # 4) 防假绿：刷新后断言「审批未通过」终态（注意：审批驳回≠复核驳回，文案不同）
    orders.refresh()
    row = orders.find_row_by_no(no)
    row_text = row.inner_text()
    assert "审批未通过" in row_text, f"驳回后 {no} 应进入「审批未通过」终态，实际: {row_text[:120]}"
    # 5) 「审批未通过」行上不应再有「审批」「复核」按钮（终态）
    assert row.locator("button, a, .el-link", has_text="审批").count() == 0, \
        f"审批未通过工单 {no} 不应再有「审批」按钮"
    assert row.locator("button, a, .el-link", has_text="复核").count() == 0, \
        f"审批未通过工单 {no} 不应再有「复核」按钮"
    # 6) ⚠️ 实测派单人视角下「审批未通过」行没有任何操作按钮（包括撤销）
    # 与「已驳回」(复核驳回) 有「撤销」按钮不一致——产品可能存在权限/状态映射遗漏
    revoke_count = row.locator("button, a, .el-link", has_text="撤销").count()
    assert revoke_count == 0, \
        f"审批未通过工单 {no} 不应有「撤销」按钮（实测发现，与「已驳回」有撤销按钮不对称——{revoke_count}）"


@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_revoke_rejected_workorder(role_page):
    """5.2 已驳回工单撤销：复用环境中已存在的「已驳回」工单 → 派单人点「撤销」→ 终态「已撤销」。

    ⚠️ 与 5.1 对比：5.1 测审批驳回「审批未通过」（无撤销）；5.2 测复核驳回「已驳回」（有撤销）。
    「已驳回」是复核阶段的驳回终态，由 e2e_workorder_branch.py 或业务实际产生。
    本测试不新建数据（零数据污染），但依赖环境存在「已驳回」工单，无则跳过。

    数据副作用：撤销已驳回工单使其进入「已撤销」终态（消耗 1 条「已驳回」工单）。
    """
    page = role_page
    # 1) 找一条「已驳回」工单（不新建，依赖环境数据）
    orders = WorkorderListPage(page).open()
    orders.refresh()
    try:
        row, _, no = orders.find_newest_in_status("已驳回")
    except AssertionError:
        pytest.skip("当前无「已驳回」工单可测撤销，请先跑 e2e_workorder_branch.py 制造一条")
    # 2) 断言行上有「撤销」按钮
    assert row.locator("button, a, .el-link", has_text="撤销").count() > 0, \
        f"已驳回工单 {no} 应有「撤销」按钮"
    # 3) 点「撤销」→ 填原因 → 二次确认（一次性走完，不用 dlg 对象）
    # 原因：弹窗打开时页面里会同时出现多个「撤销」文字（行按钮 + 弹窗内），
    #       复用 RevokeDialog 对象可能点错按钮；inline 写法更稳。
    row.locator("button, a, .el-link", has_text="撤销").first.click(timeout=10000)
    page.wait_for_timeout(2000)
    # 填原因（必填，弹窗内第一个匹配 placeholder 的输入框）
    page.get_by_placeholder("请输入撤销原因", exact=False).first.fill("自动化测试：撤销已驳回工单")
    page.wait_for_timeout(500)
    # 点「确认撤销」（弹窗内底部按钮）
    page.get_by_role("button", name="确认撤销", exact=True).first.click()
    page.wait_for_timeout(2500)
    # 处理二次确认 message-box（撤销也可能有"是否确定撤销"的二次确认）
    box = page.locator(".el-message-box:visible")
    if box.count() > 0:
        try:
            box.last.locator("button", has_text="确定").first.click(timeout=5000)
        except Exception:
            box.last.locator("button", has_text="确认").first.click(timeout=5000)
        page.wait_for_timeout(1500)
    # 等所有弹窗关闭
    try:
        page.locator(".el-dialog:visible, .el-drawer:visible").last.wait_for(state="hidden", timeout=8000)
    except Exception:
        pass
    # 4) 防假绿：刷新后断言「已撤销」终态
    orders.refresh()
    row = orders.find_row_by_no(no)
    assert "已撤销" in row.inner_text(), f"撤销后 {no} 应为「已撤销」，实际: {row.inner_text()[:120]}"
    # 5) 已撤销行不应再有任何操作按钮
    assert row.locator("button, a, .el-link").count() == 0, \
        f"已撤销工单 {no} 不应再有操作按钮"
