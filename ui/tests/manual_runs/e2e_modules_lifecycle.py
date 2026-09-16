"""
工单全生命周期 E2E —— 按"派单入口模块"参数化（纵向扩）

================================================================================
用同一条端到端链路（派单→审批→处理→复核→已完成），分别从 4 个派单入口模块
触发，验证每个模块的派单 → 整条生命周期都跑得通。

用法（按环境批量 pytest 上限约 120s 拆批）：
  # 批 1（先跑）
  ./venv/bin/python ui/tests/e2e_modules_lifecycle.py  系统漏洞管理 网站漏洞管理
  # 批 2（后跑）
  ./venv/bin/python ui/tests/e2e_modules_lifecycle.py  弱口令管理 基线管理

依赖：
- e2e_workorder_flow.py 的链路 + VulnListPage(module=...) 已就位
- .auth/state_123_*.json 三角色登录态
- 123 环境每个模块下都有"可处置"的漏洞（探活 2026-09-09 确认）

退码：0=全绿 / 1=任一模块断言失败 / 2=异常
"""
import os
import sys
import time as _time
import traceback

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import UI_ROLE_STATE_FILES, UI_WEB_BASE_URL, ENV_NAME
from workorder_page import VulnListPage, WorkorderListPage, DisposalPanel, ApprovalDialog, HandleDialog, ReviewDialog

HEADLESS = os.getenv("PW_HEADLESS", "true").lower() != "false"
_DEFAULT_MODULES = ["系统漏洞管理", "网站漏洞管理", "弱口令管理", "基线管理"]


def stage(tag: str, msg: str):
    print(f"\n{'=' * 70}\n[{tag}] {msg}\n{'=' * 70}")


def assert_true(cond: bool, hint: str):
    if cond:
        print(f"  ✓ {hint}")
    else:
        raise AssertionError(f"断言失败: {hint}")


def new_context(browser, role: str):
    sf = UI_ROLE_STATE_FILES[role]
    if not os.path.exists(sf):
        raise RuntimeError(f"角色 {role} 登录态文件不存在: {sf}")
    ctx = browser.new_context(storage_state=sf, ignore_https_errors=True)
    pg = ctx.new_page()
    pg.set_default_timeout(15000)
    return ctx, pg


def run_one_module(browser, module: str) -> str:
    """从指定 module 派单，跑完派单→审批→处理→复核→已完成整条链路。返回工单编号。"""
    tag = f"MODULE={module}"
    desc_suffix = f"{module}-E2E-{_time.strftime('%H%M%S')}"
    no = None

    # 阶段 1：派单
    stage(f"{tag} 1/4", f"common_admin → 从「{module}」派单")
    ctx, pg = new_context(browser, "common_admin")
    try:
        vuln = VulnListPage(pg, module=module).open()
        panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
        panel.select_dispatch()
        panel.select_approver("普通管理员")
        panel.select_handler("工单处理人员")
        panel.select_level("紧急")
        panel.fill_description(desc_suffix)
        panel.submit()
        panel.expect_submit_success()
        print(f"  ✓ 派单成功 (module={module})")
        # 抓新工单编号
        orders = WorkorderListPage(pg).open()
        orders.refresh()
        row, idx, no = orders.find_newest_in_status("待审批")
        print(f"  ✓ 新工单编号 = {no}")
    finally:
        ctx.close()

    # 阶段 2：审批通过
    stage(f"{tag} 2/4", f"common_admin → 审批通过: {no}")
    ctx, pg = new_context(browser, "common_admin")
    try:
        orders = WorkorderListPage(pg).open()
        orders.refresh()
        row, idx = orders.find_row_by_text(no)
        assert_true("待审批" in row.inner_text(), f"审批前 {no} 应为待审批")
        row.locator("button, a, .el-link", has_text="审批").first.click(timeout=10000)
        pg.wait_for_timeout(1500)
        ApprovalDialog(pg).approve_pass()
        orders.refresh()
        orders.assert_row_status(no, "待处理")
        print(f"  ✓ 审批通过 → 待处理")
    finally:
        ctx.close()

    # 阶段 3：处理 + 提交复核
    stage(f"{tag} 3/4", f"operation → 处理+提交复核: {no}")
    ctx, pg = new_context(browser, "operation")
    try:
        orders = WorkorderListPage(pg).open()
        orders.refresh()
        row, idx = orders.find_row_by_text(no)
        assert_true("待处理" in row.inner_text(), f"处理人视角 {no} 应为待处理")
        row.locator("button, a, .el-link", has_text="处理").first.click(timeout=10000)
        pg.wait_for_timeout(1500)
        hd = HandleDialog(pg)
        hd.select_conclusion("已修复", row_index=0)
        hd.save()
        hd.submit_review()
        orders.refresh()
        orders.assert_row_status(no, "待复核")
        print(f"  ✓ 提交复核 → 待复核")
    finally:
        ctx.close()

    # 阶段 4：复核通过
    stage(f"{tag} 4/4", f"common_admin → 复核通过: {no}")
    ctx, pg = new_context(browser, "common_admin")
    try:
        orders = WorkorderListPage(pg).open()
        orders.refresh()
        row, idx = orders.find_row_by_text(no)
        assert_true("待复核" in row.inner_text(), f"复核人视角 {no} 应为待复核")
        row.locator("button, a, .el-link", has_text="复核").first.click(timeout=10000)
        pg.wait_for_timeout(1500)
        ReviewDialog(pg).review_pass()
        orders.refresh()
        orders.assert_row_status(no, "已完成")
        print(f"  ✓ 复核通过 → 已完成")
    finally:
        ctx.close()

    return no


def run(modules):
    print(f"# 工单全生命周期 E2E（按模块参数化）\n"
          f"# env = {ENV_NAME} ({UI_WEB_BASE_URL})\n"
          f"# headless = {HEADLESS}\n"
          f"# 本批模块: {modules}\n")
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--ignore-certificate-errors", "--disable-dev-shm-usage"],
        )
        try:
            for m in modules:
                t0 = _time.time()
                try:
                    no = run_one_module(browser, m)
                    dt = _time.time() - t0
                    print(f"\n>>> {m} 全链通过，工单 {no}（{dt:.1f}s）")
                    results.append((m, "PASS", no, dt))
                except Exception as e:
                    dt = _time.time() - t0
                    print(f"\n>>> {m} 失败: {type(e).__name__}: {e}")
                    results.append((m, "FAIL", str(e)[:80], dt))
                    traceback.print_exc()
        finally:
            browser.close()

    # 总结
    print(f"\n{'=' * 70}\n# 汇总")
    fail = [r for r in results if r[1] == "FAIL"]
    for m, st, no, dt in results:
        print(f"  {m:14s} {st:4s}  {no}  {dt:.1f}s")
    if fail:
        print(f"\n❌ {len(fail)}/{len(results)} 模块失败")
        return 1
    print(f"\n🎉 {len(results)}/{len(results)} 模块全绿")
    return 0


if __name__ == "__main__":
    # CLI: python e2e_modules_lifecycle.py [mod1 mod2 ...]
    if len(sys.argv) > 1:
        modules = sys.argv[1:]
    else:
        modules = _DEFAULT_MODULES
    try:
        sys.exit(run(modules))
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
