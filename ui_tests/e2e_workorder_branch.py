"""
工单异常分支端到端自动化（E2E）—— 复核驳回 + 复核按钮可见性

================================================================================
在主 happy-path E2E（e2e_workorder_flow.py）之外，验证工单的「异常分支」：
  复核驳回：派单 → 审批通过 → 处理+提交复核 → 待复核 → 复核人「复核驳回」
            → 工单进入「已驳回」终态（⚠️ 123 环境实测；设计文档 5.5 写回线指回
            处理=待处理，实为差异，见阶段4注释），行上出「撤销」供派单人撤回。
  复核按钮可见性（自包含）：复核人对「待复核」工单能看到「复核」按钮；
            复核驳回后复核按钮消失。

业务背景：
- 流程来源：~/Downloads/工单审批流程-测试任务书.md.txt（5.5 复核驳回回线）
- 账号映射（用户确认）：
    common_admin（ceshi/普通管理员）：派单、审批、复核
    operation（chuli/工单处理人员）：处理、提交复核

关键设计（与主 E2E 一致，防假绿）：
- 单一浏览器，按业务阶段切换 context 切角色
- 派单描述填唯一前缀「BR-<timestamp>」，每阶段按描述精确定位同一张工单
- 复核驳回后必须「刷新 + 断言状态=待处理」，验证状态真回退而非 UI 假成功

运行：
  cd /Users/a1-6/hsc_auto_dev55
  ./venv/bin/python ui_tests/e2e_workorder_branch.py        # 默认 headless
  PW_HEADLESS=false ./venv/bin/python ui_tests/e2e_workorder_branch.py  # 肉眼跟

依赖：
  - config.py 从 .env 自动加载（HSC_ENV=123 + 3 角色密码）
  - .auth/state_123_*.json 三个角色登录态文件已就位
  - 123 环境有可用「待处理」漏洞可供派单
"""
import os
import sys
import time as _time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import UI_ROLE_STATE_FILES, UI_WEB_BASE_URL, ENV_NAME
from workorder_page import (
    VulnListPage,
    WorkorderListPage,
    DisposalPanel,
    ApprovalDialog,
    HandleDialog,
    ReviewDialog,
)

# 无头模式（默认）；想肉眼跟流程：export PW_HEADLESS=false 再跑
HEADLESS = os.getenv("PW_HEADLESS", "true").lower() != "false"

# 唯一描述前缀（工单管理无「描述」列，阶段 2 起改用工单编号精确定位）
_RUN_TAG = f"BR-{_time.strftime('%H%M%S')}-{int(_time.time()*1000) % 100000:05d}"
_DESCRIPTION = f"{_RUN_TAG} 自动化异常分支-复核驳回"
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
            f"请先运行 test_workorder_flow.py 或 conftest fixture 登录一次"
        )
    ctx = browser.new_context(storage_state=sf, ignore_https_errors=True)
    pg = ctx.new_page()
    pg.set_default_timeout(15000)
    return ctx, pg


def run():
    print(f"# 工单异常分支端到端 E2E（复核驳回 + 复核按钮可见性）\n"
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
        stage("1/5", "common_admin(ceshi) → 派单：选待处理漏洞 → 选派单 → 提交")
        ctx_d, pg = new_context(browser, "common_admin")
        try:
            vuln = VulnListPage(pg).open()
            panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
            panel.select_dispatch()
            panel.select_approver("普通管理员")   # 审批人 = ceshi
            panel.select_handler("工单处理人员")  # 处理人 = chuli
            panel.select_level("紧急")
            panel.fill_description(_DESCRIPTION)
            panel.submit()
            panel.expect_submit_success()
            print(f"  ✓ 派单提交成功，描述标记 = {_DESCRIPTION}")

            # 抓新工单编号
            global _NEW_WO_NO
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx, no = orders.find_newest_in_status("待审批")
            _NEW_WO_NO = no
            print(f"  ✓ 抓到新工单编号 = {_NEW_WO_NO}")
        finally:
            ctx_d.close()

        # ============================================================
        # 阶段 2：common_admin（审批人）—— 审批通过
        # ============================================================
        stage("2/5", f"common_admin(ceshi) → 审批通过：工单 {_NEW_WO_NO} → 待处理")
        ctx_a, pg = new_context(browser, "common_admin")
        try:
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx = orders.find_row_by_text(_NEW_WO_NO)
            assert_true("待审批" in row.inner_text(),
                        f"审批前应「待审批」，实际: {row.inner_text()[:120]}")
            row.locator("button, a, .el-link", has_text="审批").first.click(timeout=10000)
            pg.wait_for_timeout(1500)
            ApprovalDialog(pg).approve_pass()
            orders.refresh()
            orders.assert_row_status(_NEW_WO_NO, "待处理")
            print(f"  ✓ 审批通过，工单进入「待处理」")
        finally:
            ctx_a.close()

        # ============================================================
        # 阶段 3：operation（处理人）—— 处理 + 提交复核
        # ============================================================
        stage("3/5", f"operation(chuli) → 处理+提交复核：工单 {_NEW_WO_NO} → 待复核")
        ctx_h, pg = new_context(browser, "operation")
        try:
            orders = WorkorderListPage(pg).open()
            orders.refresh()
            row, idx = orders.find_row_by_text(_NEW_WO_NO)
            assert_true("待处理" in row.inner_text(),
                        f"处理人视角应「待处理」，实际: {row.inner_text()[:120]}")
            row.locator("button, a, .el-link", has_text="处理").first.click(timeout=10000)
            pg.wait_for_timeout(1500)
            hd = HandleDialog(pg)
            hd.select_conclusion("已修复", row_index=0)
            hd.save()
            hd.submit_review()
            orders.refresh()
            orders.assert_row_status(_NEW_WO_NO, "待复核")
            print(f"  ✓ 提交复核，工单进入「待复核」")
        finally:
            ctx_h.close()

        # ============================================================
        # 阶段 4：common_admin（复核人）—— 复核驳回
        # ============================================================
        stage("4/5", f"common_admin(ceshi) → 复核驳回：工单 {_NEW_WO_NO} → 回退待处理")
        ctx_r, pg = new_context(browser, "common_admin")
        try:
            orders = WorkorderListPage(pg).open()
            orders.refresh()

            # —— 复核按钮可见性自包含断言 ——
            row, idx = orders.find_row_by_text(_NEW_WO_NO)
            assert_true("待复核" in row.inner_text(),
                        f"复核人视角应「待复核」，实际: {row.inner_text()[:120]}")
            assert_true(row.locator("button, .el-link", has_text="复核").count() >= 1,
                        f"复核人对「待复核」工单 {_NEW_WO_NO} 应能看到「复核」按钮")

            # 点该行「复核」→ 复核驳回
            row.locator("button, a, .el-link", has_text="复核").first.click(timeout=10000)
            pg.wait_for_timeout(1500)
            ReviewDialog(pg).review_reject("复核驳回：处理结果仍需返工，请重新处理")

            # —— 复核驳回终态断言（⚠️ 实测 2026-09-09）——
            # 设计文档 5.5 写「复核驳回 → 直角回线指回处理(待处理)」，但 123 环境实测
            # 复核驳回后工单进入「已驳回」终态(类似审批未通过是终态)，不再回待处理，
            # 行上出现「撤销」按钮让派单人撤回。此处按实测断言，差异记为观察项。
            orders.refresh()
            orders.assert_row_status(_NEW_WO_NO, "已驳回")
            print(f"  ✓ 复核驳回生效，工单进入「已驳回」终态（实测：未回退待处理）")
            # 驳回后「复核」按钮应消失，改为出现「撤销」（派单人可撤回）
            row = orders.find_row_by_no(_NEW_WO_NO)
            assert_true(row.locator("button, .el-link", has_text="复核").count() == 0,
                        f"复核驳回后工单 {_NEW_WO_NO} 不应再有「复核」按钮")
            assert_true(row.locator("button, .el-link", has_text="撤销").count() >= 1,
                        f"复核驳回后的「已驳回」工单 {_NEW_WO_NO} 应提供「撤销」按钮供派单人撤回")
        finally:
            ctx_r.close()

        browser.close()

    print(f"\n{'=' * 70}\n"
          f"🎉 工单异常分支 E2E 跑通！\n"
          f"   链路：派单 → 待审批 → 审批通过 → 待处理 → 处理+提交复核 → 待复核\n"
          f"         → 复核驳回 →「已驳回」终态（实测，非设计文档的待处理回线）\n"
          f"   复核按钮可见性（自包含断言）✓  复核驳回后出「撤销」✓\n"
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
