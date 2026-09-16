"""
处置面板 5 处置方式 + 处理结论 4 选项 覆盖补全
（用户 2026-09-09 选定方向：补齐处置面板覆盖）

============================================================================
覆盖分层（三层覆盖法）：
  1. 存在性：处置面板 5 个处置方式 radio（修复/确认/派单/忽略/误报）都存在；
             处理弹窗「处理结论」4 选项（待修复/已修复/已忽略/误报）都可选。
  2. 行为闭环：每种处置方式提交后，该漏洞的【状态】确实发生变化（防假绿：刷新后按
             稳定特征锁定同一条漏洞、比对状态，而非简单数全局计数——
             派单类处置会让漏洞离开待处理列表，但修复/确认/忽略/误报通常仍留在列表、
             仅状态流转）。每种处理结论都可被选中并保存成功。
  3. 规则边界（待回填）：各处置方式/处理结论的【实际终态】需本机实跑后补全精确断言
                        （见各测试 TODO 注释）。本沙箱无法连内网 HSC 环境，
                        故先交付可运行骨架，用户实跑后回填终态。

数据副作用：每个处置方式用例消耗 1 条可处置漏洞（直接改变其状态，不建工单）；
            处理结论选择用例只「保存」不「提交复核」，不消耗工单、可反复跑。
============================================================================
"""
import re
import pytest
import allure

from workorder_page import (
    VulnListPage,
    WorkorderListPage,
    DisposalPanel,
    HandleDialog,
)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
# 已知状态词（按此顺序在行文本里识别漏洞状态；新增词在此补充）
STATUS_WORDS = (
    "待处理", "待修复", "已修复", "修复中", "已确认", "已忽略",
    "误报", "已派单", "处理中", "已完成", "已关闭", "已撤销",
)


def _stable_core(text: str) -> str:
    """去掉状态词与空白，得到「锁定同一条漏洞」的稳定特征串。

    处置前后只有状态列会变，其余列（资产/IP/CVE/编号）不变，故去掉状态词后
    两行文本应一致，可据此在刷新后的列表里找回同一条漏洞（防假绿核心）。
    """
    core = text
    for w in STATUS_WORDS:
        core = core.replace(w, "")
    return re.sub(r"\s+", "", core)


def _extract_status(text: str) -> str:
    """从行文本里识别第一个命中的状态词；未命中返回『(未知状态)』。"""
    for w in STATUS_WORDS:
        if w in text:
            return w
    return "(未知状态)"


def _dump_statuses(page, limit=8):
    """打印当前列表前若干行状态样本，便于用户实跑后回填实际终态。"""
    rows = page.locator(".el-table tbody tr")
    out = []
    for i in range(min(rows.count(), limit)):
        out.append(rows.nth(i).inner_text().replace("\n", " | ")[:90])
    return out


def _dispose_and_assert(page, module, mode, reason=None):
    """对首个可处置漏洞执行某处置方式，断言【该漏洞自身状态】确实发生变化（防假绿）。

    关键修正（2026-09-09）：原先断言「待处理计数 -1」是错的——只有「派单」会让漏洞
    离开待处理列表；修复/确认/忽略/误报通常仍留在列表、只改变状态列。因此改为：
      1. 处置前抓取首条可处置漏洞的稳定特征串(core)与状态；
      2. 提交后刷新页面；
      3. 用 core 在刷新后的列表里找回**同一条**漏洞，比对状态是否改变 /
         是否已离开待处理视图。这才是真正的「防假绿」校验。

    返回探测信息供回填。⚠️ 实际终态（已修复/已确认/已忽略/误报）需用户实跑后从打印里回填。
    """
    vuln = VulnListPage(page, module=module).open()
    before = vuln.count_disposable_rows()
    assert before > 0, f"{module} 无可处置漏洞，无法测试处置方式「{mode}」"
    before_text = vuln.first_disposable_row_text()
    core = _stable_core(before_text)
    before_status = _extract_status(before_text)
    panel = vuln.open_dispose_panel(row_index=0)
    panel.submit_mode(mode, reason=reason)
    # 刷新后校验（防假绿：产品非实时，必须刷新后复核真实持久状态）
    page.reload()
    page.wait_for_load_state("networkidle", timeout=15000)
    page.wait_for_timeout(1500)
    after = VulnListPage(page, module=module).count_disposable_rows()
    after_text = VulnListPage(page, module=module).find_disposed_item_by_core(core)
    if after_text is None:
        # 已离开待处理列表视图（派单类处置常见）→ 视为已生效
        new_status = "(已离开待处理列表视图)"
        left = True
    else:
        new_status = _extract_status(after_text)
        left = False
    print(f"[处置-{mode}] 待处理计数 before={before} after={after}")
    print(f"[处置-{mode}] 目标漏洞 处置前状态={before_status!r} 处置后状态={new_status!r} 是否离开列表={left}")
    print(f"[处置-{mode}] 处置前整行: {before_text.replace(chr(10), ' | ')[:220]!r}")
    if after_text is not None:
        print(f"[处置-{mode}] 处置后整行: {after_text.replace(chr(10), ' | ')[:220]!r}")
    # 防假绿核心断言：出现了「处置成功」提示后，目标漏洞必须真正离开待处理
    # （要么离开列表，要么状态不再是「待处理」）。若仍停在「待处理」，说明处置
    # 未真正持久生效，需要人工确认产品行为。
    assert left or new_status != "待处理", (
        f"处置「{mode}」已出现成功提示，但目标漏洞状态仍为「{new_status}」"
        f"（处置未真正生效 / 该方式本就不离开待处理——请查看上面打印的整行文本确认实际终态）"
    )
    # TODO(回填): 确认「{mode}」处置后该漏洞的实际终态({new_status})，补全精确断言
    return {"before": before, "after": after, "before_status": before_status,
            "new_status": new_status, "left": left}


# ---------------------------------------------------------------------------
# 1) 存在性：处置面板 5 处置方式
# ---------------------------------------------------------------------------
@allure.feature("工单 UI 交互")
@allure.story("处置面板处置方式存在性")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_disposal_panel_five_modes_present(role_page):
    """处置面板应同时提供 5 个处置方式：修复/确认/派单/忽略/误报。"""
    page = role_page
    vuln = VulnListPage(page).open()
    panel: DisposalPanel = vuln.open_dispose_panel(row_index=0)
    try:
        for m in ("修复", "确认", "派单", "忽略", "误报"):
            assert panel.is_mode_present(m), f"处置面板缺少处置方式 radio「{m}」"
        # 默认选中态（与 test_disposal_panel_default_mode 互证）
        assert panel.selected_mode() == "修复", "处置面板默认处置方式应为「修复」"
    finally:
        panel.close()


# ---------------------------------------------------------------------------
# 2) 行为闭环：每种处置方式提交后离开待处理
# ---------------------------------------------------------------------------
@allure.feature("工单 UI 交互")
@allure.story("处置方式-修复")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispose_mode_fix(role_page):
    """处置方式「修复」：选修复→提交→该漏洞状态发生流转（防假绿：刷新后比对同一条）。

    ⚠️ TODO(回填): 修复后漏洞的实际终态（如「已修复」/「修复中」）需本机实跑从打印里确认。
    数据副作用：消耗 1 条可处置漏洞。
    """
    _dispose_and_assert(role_page, "网站漏洞管理", "修复")


@allure.feature("工单 UI 交互")
@allure.story("处置方式-确认")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispose_mode_confirm(role_page):
    """处置方式「确认」：选确认→提交→该漏洞状态发生流转（防假绿：刷新后比对同一条）。

    ⚠️ TODO(回填): 确认后实际终态（如「已确认」）需本机实跑从打印里确认。
    数据副作用：消耗 1 条可处置漏洞。
    """
    _dispose_and_assert(role_page, "网站漏洞管理", "确认")


@allure.feature("工单 UI 交互")
@allure.story("处置方式-忽略")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispose_mode_ignore(role_page):
    """处置方式「忽略」：选忽略→填原因→提交→该漏洞状态发生流转（防假绿：刷新后比对同一条）。

    ⚠️ TODO(回填): 忽略后实际终态（如「已忽略」）需本机实跑从打印里确认。
    数据副作用：消耗 1 条可处置漏洞。
    """
    _dispose_and_assert(role_page, "网站漏洞管理", "忽略", reason="自动化测试：确认误报后忽略")


@allure.feature("工单 UI 交互")
@allure.story("处置方式-误报")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.role("common_admin")
@pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
def test_dispose_mode_false_positive(role_page):
    """处置方式「误报」：选误报→填原因→提交→该漏洞状态发生流转（防假绿：刷新后比对同一条）。

    ⚠️ TODO(回填): 误报后实际终态（如「误报」）需本机实跑从打印里确认。
    数据副作用：消耗 1 条可处置漏洞。
    """
    _dispose_and_assert(role_page, "网站漏洞管理", "误报", reason="自动化测试：验证为误报")


# ---------------------------------------------------------------------------
# 3) 存在性 + 行为闭环：处理结论 4 选项均可选中并保存
# ---------------------------------------------------------------------------
@allure.feature("工单 UI 交互")
@allure.story("处理结论选项可选择性")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("conclusion", ["待修复", "已修复", "已忽略", "误报"])
@pytest.mark.role("operation")
@pytest.mark.parametrize("role_page", ["operation"], indirect=True)
def test_handle_select_conclusion(role_page, conclusion):
    """处理弹窗漏洞明细「处理结论」4 选项均可选中并保存成功（不提交复核，可反复跑）。

    ⚠️ 仅验证「选择+保存」层级的行为闭环；各结论提交复核并复核通过后
       驱动漏洞到达的【实际终态】需全链路实跑后补全（见 TODO）。
    需环境有「待处理」工单，无则跳过。
    """
    page = role_page
    orders = WorkorderListPage(page).open()
    orders.refresh()
    try:
        row, _ = orders._find_first_row_with_action("处理")
    except AssertionError:
        pytest.skip("当前无待处理工单，跳过处理结论选择测试（数据依赖）")
    row.locator("button, a, .el-link", has_text="处理").first.click(timeout=10000)
    page.wait_for_timeout(1800)
    dlg = HandleDialog(page)
    dlg.select_conclusion(conclusion, row_index=0)
    page.wait_for_timeout(500)
    dlg.save()
    page.wait_for_timeout(1000)
    # 保存后处理弹窗应仍在（未提交复核，不应关闭/不应报错）
    assert page.locator(".el-dialog:visible").count() >= 1, \
        f"选「{conclusion}」并保存后处理弹窗应仍在（保存非提交）"
    # 关闭弹窗
    try:
        page.get_by_role("button", name="关闭", exact=True).first.click(timeout=4000)
    except Exception:
        page.keyboard.press("Escape")
    page.wait_for_timeout(800)
