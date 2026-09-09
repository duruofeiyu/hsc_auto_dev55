"""
工单派单审批全流程端到端自动化（E2E）

================================================================================
一气呵成跑通工单整个生命周期：派单 → 审批通过 → 处理 → 提交复核 → 复核通过 → 已完成。
一条命令验证全流程，无需逐条单跑，避免「用例间数据互相消耗」的串数据问题。

业务背景：
- 流程来源：~/Downloads/工单审批流程-测试任务书.md.txt（模块一/二/三/五/六）
- 多角色收口后账号映射（用户确认）：
    common_admin（ceshi/普通管理员）：派单、审批、复核
    operation（chuli/工单处理人员）：处理、提交复核

E2E 关键设计：
- 单一浏览器，按业务阶段切换 context（加载对应角色 storage_state）
- 派单描述填唯一前缀「E2E-<timestamp>」，每个阶段都按前缀精确定位同一张工单，
  彻底避开其他工单干扰，不会假绿。
- 每阶段都做"动作 → 刷新 → 状态断言"防假绿：派单→待审批→待处理→待复核→已完成
- 全程打印阶段日志，方便定位中断点。

运行：
  cd /Users/a1-6/hsc_auto_dev55
  ./venv/bin/python ui_tests/e2e_workorder_flow.py

依赖：
  - config.py 从 .env 自动加载（HSC_ENV=123 + 3 角色密码）
  - .auth/state_123_*.json 三个角色登录态文件已就位
  - 123 环境 22 条可处置漏洞（探活 2026-09-08 确认）
"""
import os
import sys
import time as _time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import UI_ROLE_STATE_FILES, UI_WEB_BASE_URL, ENV_NAME
from workorder_page import VulnListPage, WorkorderListPage, DisposalPanel

# 无头模式（CI/默认）；想肉眼跟流程：export PW_HEADLESS=false 再跑
HEADLESS = os.getenv("PW_HEADLESS", "true").lower() != "false"

# 唯一描述前缀：E2E + 时间戳 + 随机串，避开数据库其他工单串数据
_RUN_TAG = f"E2E-{_time.strftime('%H%M%S')}-{int(_time.time()*1000) % 100000:05d}"
_DESCRIPTION = f"{_RUN_TAG} 自动化端到端派单"
# 工单管理列表没有「描述」列，需用工单编号（WO+日期+序号）精准锁定每条工单。
# 阶段 1 派单后立刻抓取新工单编号；阶段 2-4 都用此编号 + find_row_by_no 定位。
_NEW_WO_NO = None


def stage(tag: str, msg: str):
    print(f"\n{'=' * 70}\n[{tag}] {msg}\n{'=' * 70}")


def assert_true(cond: bool, hint: str):
    if cond:
        print(f"  ✓ {hint}")
    else:
        raise AssertionError(f"断言失败: {hint}")


def new_context(browser, role: str):
    """按角色加载 storage_state 创建新 context。"""
    sf = UI_ROLE_STATE_FILES[role]
    if not os.path.exists(sf):
        raise RuntimeError(
            f"角色 {role} 登录态文件不存在：{sf}\n"
            f"请先运行 ui_tests/test_workorder_flow.py 或 conftest fixture 登录一次"
        )
    ctx = browser.new_context(storage_state=sf, ignore_https_errors=True)
    pg = ctx.new_page()
    pg.set_default_timeout(15000)
    return ctx, pg


def run():
    print(f"# 工单全流程端到端 E2E\n"
          f"# env = {ENV_NAME} ({UI_WEB_BASE_URL})\n"
          f"# run tag = {_RUN_TAG}\n"
          f"# headless = {HEADLESS}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--ignore-certificate-errors", "--disable-dev-shm-usage"],
        )

        # ============================================================
        # 阶段 1：common_admin（派单人）—— 派单
        # ============================================================
        stage("1/4", "common_admin(ceshi) → 派单：选一条待处理漏洞 → 选派单 → 提交")
        ctx_d, pg = new_context(browser, "common_admin")
        try:
            vuln = VulnListPage(pg).open()
            panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
            panel.select_dispatch()
            panel.select_approver("普通管理员")   # 审批人 = ceshi 自身
            panel.select_handler("工单处理人员")  # 处理人 = chuli
            panel.select_level("紧急")
            panel.fill_description(_DESCRIPTION)
            panel.submit()
            panel.expect_submit_success()
            print(f"  ✓ 派单提交成功，描述标记 = {_DESCRIPTION}")

            # 派单后立刻到工单管理抓取新工单编号（按时间倒序，"待审批"首行即新工单）
            global _NEW_WO_NO
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx, no = orders.find_newest_in_status("待审批")
            _NEW_WO_NO = no
            print(f"  ✓ 抓到新工单编号 = {_NEW_WO_NO}（idx={idx}，按时间倒序在「待审批」首行）")
        finally:
            ctx_d.close()

        # ============================================================
        # 阶段 2：common_admin（审批人）—— 审批通过
        # ============================================================
        stage("2/4", f"common_admin(ceshi) → 审批通过：工单 {_NEW_WO_NO} → 审批通过")
        ctx_a, pg = new_context(browser, "common_admin")
        try:
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx = orders.find_row_by_text(_NEW_WO_NO)
            wo_text = row.inner_text().replace("\n", " | ")
            print(f"  → 找到工单行 idx={idx}: {wo_text[:200]}")
            assert_true("待审批" in wo_text, f"审批前该工单应在「待审批」, 实际: {wo_text[:120]}")
            # 点该行的「审批」按钮（用行内定位器，避免点错行）
            row.locator("button, a, .el-link", has_text="审批").first.click(timeout=10000)
            pg.wait_for_timeout(1500)
            from workorder_page import ApprovalDialog
            ApprovalDialog(pg).approve_pass()
            # 防假绿：刷新后按编号断言状态流转
            orders.refresh()
            orders.assert_row_status(_NEW_WO_NO, "待处理")
            print(f"  ✓ 审批通过，工单 {_NEW_WO_NO} 进入「待处理」状态")
        finally:
            ctx_a.close()

        # ============================================================
        # 阶段 3：operation（处理人）—— 处理 + 提交复核
        # ============================================================
        stage("3/4", f"operation(chuli) → 处理+提交复核：工单 {_NEW_WO_NO} → 已修复 → 保存 → 提交复核")
        ctx_h, pg = new_context(browser, "operation")
        try:
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx = orders.find_row_by_text(_NEW_WO_NO)
            wo_text = row.inner_text().replace("\n", " | ")
            print(f"  → 处理人视角找到工单 idx={idx}: {wo_text[:200]}")
            assert_true("待处理" in wo_text, f"处理人视角应在「待处理」, 实际: {wo_text[:120]}")
            # 该行的「处理」按钮
            row.locator("button, a, .el-link", has_text="处理").first.click(timeout=10000)
            pg.wait_for_timeout(1500)
            from workorder_page import HandleDialog
            hd = HandleDialog(pg)
            hd.select_conclusion("已修复", row_index=0)
            hd.save()
            hd.submit_review()
            # 防假绿：刷新后按编号断言状态流转
            orders.refresh()
            orders.assert_row_status(_NEW_WO_NO, "待复核")
            print(f"  ✓ 提交复核，工单 {_NEW_WO_NO} 进入「待复核」状态")
        finally:
            ctx_h.close()

        # ============================================================
        # 阶段 4：common_admin（复核人）—— 复核通过
        # ============================================================
        stage("4/4", f"common_admin(ceshi) → 复核通过：工单 {_NEW_WO_NO} → 复核通过 → 终态已完成")
        ctx_r, pg = new_context(browser, "common_admin")
        try:
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx = orders.find_row_by_text(_NEW_WO_NO)
            wo_text = row.inner_text().replace("\n", " | ")
            print(f"  → 复核人视角找到工单 idx={idx}: {wo_text[:200]}")
            assert_true("待复核" in wo_text, f"复核人视角应在「待复核」, 实际: {wo_text[:120]}")
            # 该行的「复核」按钮
            row.locator("button, a, .el-link", has_text="复核").first.click(timeout=10000)
            pg.wait_for_timeout(1500)
            from workorder_page import ReviewDialog
            ReviewDialog(pg).review_pass()
            # 防假绿：刷新后按编号断言终态
            orders.refresh()
            orders.assert_row_status(_NEW_WO_NO, "已完成")
            print(f"  ✓ 复核通过，工单 {_NEW_WO_NO} 进入「已完成」终态")
        finally:
            ctx_r.close()

        browser.close()

    print(f"\n{'=' * 70}\n"
          f"🎉 工单全流程 E2E 跑通！\n"
          f"   链路：派单 → 待审批 → 审批通过 → 待处理 → 处理+提交复核 → 待复核 → 复核通过 → 已完成\n"
          f"   run tag = {_RUN_TAG}\n"
          f"{'=' * 70}")


if __name__ == "__main__":
    try:
        run()
        sys.exit(0)
    except (AssertionError, PlaywrightTimeoutError) as e:
        print(f"\n❌ E2E 失败: {type(e).__name__}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ E2E 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)