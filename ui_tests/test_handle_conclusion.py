"""
处理结论「提交复核」全链路覆盖（处置面板覆盖方向的下一档）

============================================================================
业务链路（补 test_disposal_modes.py 中 test_handle_select_conclusion 的"只选+保存"层）：
  工单管理「待处理」工单 → 点「处理」→ 处理弹窗漏洞明细逐行选处理结论
  （待修复/已修复/已忽略/误报；产品要求全部漏洞都处理才能提交复核）
  → 点「保存」（暂存）→ 点「提交复核」→ 二次确认框「确认提交」
  → 工单离开「待处理」处理态、进入「待复核」阶段。

覆盖分层（三层覆盖法）：
  1. 存在性：已含在 test_disposal_modes.test_handle_select_conclusion（4 选项可选）。
  2. 行为闭环（本文件）：选结论 + 保存 + 提交复核 后，工单确实离开「待处理」
             可处理态（防假绿：刷新后按工单号定位，断言不再有「处理」按钮）。
  3. 规则边界（待回填）：提交复核后工单的实际终态（应变为「待复核」）需本机实跑确认，
             并在下方断言里补全精确状态词。

数据依赖：需环境存在「待处理」且含「处理」按钮的工单；无则跳过（不伪造数据）。
角色：operation（工单执行员 chuli）。
============================================================================
"""
import pytest
import allure

from workorder_page import WorkorderListPage, HandleDialog


@allure.feature("工单 UI 交互")
@allure.story("处理结论-提交复核全链路")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("operation")
@pytest.mark.parametrize("role_page", ["operation"], indirect=True)
def test_handle_conclusion_submit_review(role_page):
    """处理人员：逐行选结论 → 保存 → 提交复核 → 工单离开待处理处理态（防假绿）。

    ⚠️ TODO(回填): 提交复核后工单应变为「待复核」；本机实跑确认后，
        把下方 `still_pending` 断言强化为 `status == "待复核"`。
    数据依赖：需「待处理」且含「处理」按钮的工单，无则跳过。
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    try:
        row, _ = orders._find_first_row_with_action("处理", "待处理")
    except AssertionError:
        pytest.skip("当前无待处理工单（或都无『处理』按钮），跳过处理结论提交复核全链路测试（数据依赖）")
    no = orders._extract_workorder_no(row)
    assert no, "未能从目标工单行提取工单号（WO...），无法做防假绿定位"

    # 打开处理弹窗
    row.locator("button, a, .el-link", has_text="处理").first.click(timeout=10000)
    page.wait_for_timeout(1800)
    dlg = HandleDialog(page)

    # 给明细表每一行都选一个处理结论（产品要求全部处理才能提交复核）
    rows = page.locator(".el-dialog:visible .el-table tbody tr")
    n = rows.count()
    assert n > 0, "处理弹窗漏洞明细表为空，无法选结论（数据异常）"
    for i in range(n):
        dlg.select_conclusion("已修复", row_index=i)
    page.wait_for_timeout(500)

    # 保存（暂存）→ 提交复核（含二次确认「确认提交」）
    dlg.save()
    page.wait_for_timeout(1000)
    dlg.submit_review()
    page.wait_for_timeout(1500)

    # 防假绿：回到列表刷新，按工单号定位，断言该工单已离开「待处理」可处理态
    orders2 = WorkorderListPage(page).open()
    orders2.refresh()
    still_pending = False
    try:
        target = orders2.find_row_by_no(no)
        txt = target.inner_text()
        has_handle_btn = target.locator("button, a, .el-link", has_text="处理").count() > 0
        still_pending = ("待处理" in txt) and has_handle_btn
        print(f"[处理结论全链路] 工单 {no} 提交复核后整行: {txt.replace(chr(10), ' | ')[:160]!r}")
    except AssertionError:
        # 工单已不在列表（被筛选移出待处理视图）→ 视为已离开待处理，通过
        print(f"[处理结论全链路] 工单 {no} 提交复核后已从待处理列表移除（视为已流转）")
    assert not still_pending, (
        f"工单 {no} 提交复核后仍可被「处理」（疑似未真正流转到待复核）"
    )
    # TODO(回填): 确认提交复核后该工单实际终态为「待复核」，补全精确断言
