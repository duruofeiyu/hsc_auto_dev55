"""
工单/脆弱性 页面对象（Page Object 模式）—— 工单派单审批流 UI 自动化

业务来源：~/Downloads/工单审批流程-测试任务书.md.txt
核心链路：脆弱性列表「处置」→ 选「派单」→ 填审批人/运维人员/级别 → 提交(1.x)
          → 工单管理列表「审批」→ 通过/未通过(2.x)
          → 处理人员「处理」→ 已修复 → 提交复核 → 审批人员「复核」(3.x)

============================================================================
选择器已根据 2026-09-08 HSC 123 环境真实前端回填（截图核对）。
============================================================================

设计约定（对齐 login_page.py）：
- 选择器集中为类常量，改文案只改这里
- 优先 get_by_role / get_by_text，抗 DOM 结构变化
- 多角色切换通过 conftest role_page fixture 实现
"""
from playwright.sync_api import Page, expect

from base_page import BasePage


class VulnListPage(BasePage):
    """脆弱性管理列表页：派单入口在这里（点处置 → 选派单）

    真实导航（2026-09-09 123 环境核对）：
      顶部菜单「脆弱性管理」→ 左侧子菜单四个模块均支持派单：
        - 系统漏洞管理 (/assetsVuln)
        - 网站漏洞管理 (/webVuln)
        - 弱口令管理 (/weakPasswords)
        - 基线管理 (/baseLine)
      每个模块行内都有「处置」按钮；只有「待处理」状态的行处置按钮可用，
      「修复中/已确认」等行的处置按钮是 disabled。
    """

    MENU_TEXT = "脆弱性管理"
    # 支持的四个派单入口模块（左侧子菜单文案；实例化时可指定）
    SUPPORTED_MODULES = ("系统漏洞管理", "网站漏洞管理", "弱口令管理", "基线管理")
    DISPOSE_BTN = "处置"

    def __init__(self, page: Page, module: str = "网站漏洞管理"):
        super().__init__(page)
        if module not in self.SUPPORTED_MODULES:
            raise ValueError(
                f"不支持的模块: {module!r}。支持: {self.SUPPORTED_MODULES}"
            )
        self.module = module  # 左侧子菜单文案

    def open(self):
        # 先回首页，再点菜单（和实际用户路径一致，避免 hash 路由猜错）
        super().open()  # BasePage.open() 会 goto UI_WEB_BASE_URL
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(1000)
        self.page.get_by_text(self.MENU_TEXT, exact=False).first.click()
        self.page.wait_for_timeout(1200)
        # 点左侧子菜单指定模块（一步到位，不必再切 tab）
        self.page.get_by_text(self.module, exact=False).first.click(timeout=10000)
        self.page.wait_for_timeout(1500)
        # 刷新确保加载完整（该产品非实时，需刷新拿到最新）
        self.page.reload()
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(1500)
        self.page.wait_for_selector(".el-table", timeout=15000)
        return self

    def _clickable_dispose_rows(self):
        """返回所有「处置」按钮可用的行 locator 列表（跳过 disabled）。"""
        # 只取主数据表：操作列里含「处置」按钮的表格。用较精确选择器避免误抓空表/表头。
        dispose_rows = []
        rows = self.page.locator(".el-table tbody tr")
        for i in range(rows.count()):
            row = rows.nth(i)
            btns = row.locator("button", has_text=self.DISPOSE_BTN)
            try:
                if btns.count() and not btns.first.is_disabled():
                    dispose_rows.append(row)
            except Exception:
                continue
        return dispose_rows

    def open_dispose_panel(self, row_index: int = 0):
        """打开某行漏洞的处置弹窗（含派单入口），点开并校验面板真的出现。

        处置面板以 radio（修复/确认/派单/...）出现为标志。若点开的行实际没弹
        面板（后端不稳定 / 点到无效行），自动换下一个可用行重试。
        """
        available = self._clickable_dispose_rows()
        if not available:
            raise AssertionError(
                f"{self.module} 列表里没有「处置」按钮可用的行"
                "（可能全部已处理/已派单，或被状态筛选过滤）"
            )
        # 从 row_index 起尝试，最多轮询所有可用行
        attempts = available[row_index:] + available[:row_index]
        for n, row in enumerate(attempts):
            row.locator("button", has_text=self.DISPOSE_BTN).first.click(timeout=10000)
            self.page.wait_for_timeout(1800)
            # 校验处置面板真的弹出：出现「派单」radio（或 dialog/drawer 可见）
            dispatch_radio = self.page.locator("label.el-radio", has_text="派单")
            dialog_visible = self.page.locator(".el-dialog:visible, .el-drawer:visible").count() > 0
            if dispatch_radio.count() > 0 or dialog_visible:
                print(f"[VulnList/{self.module}] 已打开处置面板(第{n}个可用行)，radio数={dispatch_radio.count()}, dialog={dialog_visible}")
                return DisposalPanel(self.page)
            print(f"[VulnList/{self.module}] 第{n}个可用行点击后未弹出面板(radio={dispatch_radio.count()}, dialog={dialog_visible})，换下一行")
            # 没弹出 → 关掉可能残留的遮罩，试下一行
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(500)
        raise AssertionError(f"[{self.module}] 尝试了所有可用行，处置面板仍未弹出（后端 500/超时？）")


class DisposalPanel(BasePage):
    """处置弹窗：先选处置方式「派单」，再填审批人/运维人员/级别/描述 → 提交

    真实 DOM（2026-09-08 123 环境核对）：
      radio 处置方式：修复/确认/派单/忽略/误报（点「派单」后展开派单表单）
      审批人   = el-select 下拉，选项：chenyh/普通管理员/张达志/系统管理员/韩毅/陈元宝...
      运维人员 = el-select 下拉，选项：工单处理人员
      工单级别 = el-radio 组（默认选中一项）
      工单描述 = el-textarea，placeholder=请输入工单描述
    注意：以上 field 都带下拉/radio，点击值后要等表单联动刷新（该产品非实时）。
    """

    # 处置方式 radio（在处置 tab 顶部，切到派单才显示派单表单）
    DISPATCH_RADIO = "派单"
    MODE_FIX = "修复"
    MODE_CONFIRM = "确认"
    MODE_IGNORE = "忽略"
    MODE_FALSE_POSITIVE = "误报"
    # radio label 全名（避免点到处置方式里的其他 radio）
    # 处置方式 radio 组有：修复/确认/派单/忽略/误报
    # 工单级别 radio 组独立成组
    # 表单字段 label（el-form-item__label 文本）
    APPROVER_SELECT = "审批人"
    HANDLER_SELECT = "运维人员"
    DESCRIPTION_INPUT = "工单描述"
    # 按钮
    SUBMIT_BTN = "提交"
    CANCEL_BTN = "取消"
    # 成功提示（实际前端弹出的 Message 文案是「派单成功」）
    SUCCESS_HINT = "派单成功"

    def is_open(self) -> bool:
        """处置面板是否处于打开状态（以任一处置方式 radio 可见为标志）。"""
        return self.page.locator("label.el-radio", has_text="派单").count() > 0

    def selected_mode(self) -> str:
        """当前选中的处置方式 radio 文本（默认「修复」）。用于校验默认选中态。"""
        for lab in self.page.locator("label.el-radio").all():
            try:
                if lab.locator("input").is_checked():
                    return lab.inner_text().strip()
            except Exception:
                continue
        return ""

    def select_mode(self, mode: str):
        """选择任意处置方式 radio（派单/修复/确认/忽略/误报）。"""
        radio = self.page.locator("label.el-radio", has_text=mode)
        radio.first.click(timeout=8000)
        self.page.wait_for_timeout(1000)

    def close(self):
        """关闭处置面板（Esc / 取消兜底）。"""
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(800)
        except Exception:
            pass
        # 面板若仍开着，找「取消/关闭」按钮点掉
        if self.is_open():
            for txt in ("取消", "关闭"):
                try:
                    btn = self.page.locator("button:visible", has_text=txt)
                    if btn.count():
                        btn.first.click(timeout=3000)
                        self.page.wait_for_timeout(800)
                        break
                except Exception:
                    continue

    def expect_validation_error(self, text: str):
        """断言提交触发了指定文案的校验提示（el-message），且面板未关闭（提交未生效）。"""
        try:
            msg = self.page.locator(".el-message:visible", has_text=text).first
            msg.wait_for(state="visible", timeout=4000)
        except Exception:
            raise AssertionError(f"提交后未出现校验提示「{text}」")
        # 校验失败 → 面板应保持打开（未提交成功）
        if not self.is_open():
            raise AssertionError(f"出现校验提示「{text}」，但处置面板被关闭了（预期保持打开以让用户修正）")

    def submit_plain(self):
        """只点「提交」，不等待任何成功信号（用于测必填校验：点了应被校验拦截）。"""
        self.page.get_by_role("button", name=self.SUBMIT_BTN, exact=True).first.click()
        self.page.wait_for_timeout(1500)


    def select_dispatch(self):
        """在处置方式里选择「派单」radio，并等派单表单展开。"""
        # 用 radio label 精确定位，避免点到别处同名「派单」文本
        radio = self.page.locator("label.el-radio", has_text=self.DISPATCH_RADIO)
        radio.first.click(timeout=8000)
        # 等「审批人」字段出现（派单表单展开的标记）
        self.page.get_by_text(self.APPROVER_SELECT, exact=True).first.wait_for(timeout=8000)
        self.page.wait_for_timeout(1000)

    def select_approver(self, name: str):
        """选择审批人（下拉：chenyh/系统管理员等可选）。"""
        self._pick_select(self.APPROVER_SELECT, name)

    def select_handler(self, name: str = "工单处理人员"):
        """选择运维人员（下拉：工单处理人员）。"""
        self._pick_select(self.HANDLER_SELECT, name)

    def select_level(self, level: str):
        """选择工单级别。level 如 '紧急'/'普通' 等，按实际选项传。
        支持 el-radio 与 el-radio-button 两种形态。"""
        fi = self.page.locator(".el-form-item", has_text="工单级别").first
        # 先试 el-radio-button（文本在 inner），再试 el-radio
        target = fi.locator("label.el-radio-button", has_text=level)
        if target.count() == 0:
            target = fi.locator("label.el-radio", has_text=level)
        target.first.click(timeout=5000)
        self.page.wait_for_timeout(800)

    def fill_description(self, text: str):
        """填写工单描述（textarea）。"""
        self.page.get_by_placeholder("请输入工单描述", exact=False).first.fill(text)

    def submit(self):
        self.page.get_by_role("button", name=self.SUBMIT_BTN, exact=True).first.click()

    def submit_and_verify_no_double(self):
        """派单提交 + 验证前端防重复提交机制。

        真实行为（123 环境探测）：点「提交」后，Element UI 按钮会短暂进入
        `is-loading` 状态（期间禁用，阻止连点产生重复工单），随后面板关闭。
        loading 窗口极短（约几十~几百 ms），可能一闪而过，因此：
          - 尽力捕获 is-loading 作为防连点证据（捕获不到不判失败，避免 flaky）
          - 主要成功信号 = 面板关闭 / 成功 Message（同 expect_submit_success）
        """
        btn = self.page.get_by_role("button", name=self.SUBMIT_BTN, exact=True).first
        btn.click()
        # 尽力捕获防连点 loading 态
        try:
            self.page.locator(".el-button.is-loading", has_text=self.SUBMIT_BTN).first.wait_for(
                state="visible", timeout=1200
            )
            self.page.wait_for_timeout(200)
        except Exception:
            pass  # loading 窗口极短未捕获，不算失败
        # 主成功信号
        self.expect_submit_success()

    def expect_submit_success(self):
        """断言派单成功。

        前端成功提示是 Element Message（文案「派单成功」，短暂出现后自动消失，
        且提交后处置面板会关闭）。因此用“任一信号”判定，避免闪太快误报失败：
          信号1：成功 Message（.el-message--success 内含「派单成功」）
          信号2：处置面板关闭（派单 radio 消失），说明提交动作已完成并进入后续流程
        """
        # 信号1：成功 Message
        try:
            msg = self.page.locator(".el-message--success", has_text=self.SUCCESS_HINT).first
            msg.wait_for(state="visible", timeout=4000)
            return
        except Exception:
            pass
        # 信号2：处置面板已关闭（radio「派单」不可见）→ 视为提交成功进入流程
        radio = self.page.locator("label.el-radio", has_text=self.DISPATCH_RADIO).first
        try:
            radio.wait_for(state="hidden", timeout=6000)
        except Exception:
            raise AssertionError(
                f"派单提交后既未见成功提示'{self.SUCCESS_HINT}'，处置面板也未关闭。"
            )

    # ---------------- 内部辅助 ----------------
    def _pick_select(self, label: str, option: str):
        """通用 el-select 选择：点 label 所在 form-item 的下拉 → 选 option。"""
        fi = self.page.locator(".el-form-item", has_text=label).first
        # 点击该 form-item 内的下拉框
        fi.locator(".el-select").first.click(timeout=8000)
        self.page.wait_for_timeout(600)
        # 从弹出的 dropdown 里选 option（dropdown 渲染在 body 下）
        opt = self.page.locator(".el-select-dropdown:visible .el-select-dropdown__item", has_text=option).first
        opt.click(timeout=8000)
        self.page.wait_for_timeout(800)

    def read_select_options(self, label: str):
        """读取某表单项 el-select 下拉的全部选项文本（用于选项校验；不选中，只读）。

        返回选项列表；调用方负责在选项展开后自行处理是否关闭。
        """
        fi = self.page.locator(".el-form-item", has_text=label).first
        fi.locator(".el-select").first.click(timeout=8000)
        self.page.wait_for_timeout(700)
        dd = self.page.locator(".el-select-dropdown:visible").first
        dd.wait_for(state="visible", timeout=5000)
        opts = [t.strip() for t in dd.locator(".el-select-dropdown__item").all_inner_texts() if t.strip()]
        return opts


class WorkorderListPage(BasePage):
    """工单管理列表页：审批人/派单人/处理人/复核人各自视角"""

    MENU_TEXT = "工单管理"

    def open(self):
        super().open()  # 回首页再点菜单
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(1000)
        self.page.get_by_text(self.MENU_TEXT, exact=False).first.click()
        self.page.wait_for_timeout(1500)
        self.page.wait_for_selector(".el-table", timeout=15000)
        return self

    # ------- 状态断言辅助（按工单编号精确定位，防假绿）-------
    @staticmethod
    def _extract_workorder_no(row) -> str:
        """从行文本提取工单编号（形如 WO20260908012）。找不到返回空串。"""
        import re
        m = re.search(r"WO\d+", row.inner_text())
        return m.group(0) if m else ""

    def _rows(self):
        """限定主表格数据行（避免命中嵌套/空表）。"""
        return self.page.locator(".el-table tbody tr")

    def count_action(self, action: str) -> int:
        """统计当前列表所有行里含 action 文案的可用(非disabled)按钮数。

        用于权限/可见性用例：断言某角色视角整页是否出现某个动作按钮。
        如 operation 处理人视角在「待审批」工单上不应出现「审批」按钮。
        """
        cnt = 0
        rows = self._rows()
        for i in range(rows.count()):
            row = rows.nth(i)
            try:
                btns = row.locator("button, a, .el-link", has_text=action)
                if btns.count() == 0:
                    continue
                if not btns.first.is_disabled():
                    cnt += 1
            except Exception:
                continue
        return cnt

    def capture_first_actionable_no(self, action: str, status_hint: str = None) -> str:
        """动作前调用：返回第一条含可点 action 按钮的行的工单编号（不点击、不改状态）。

        用于动作后按编号定位断言该行状态是否真的流转（而非看到别条同状态工单假绿）。
        """
        row, _ = self._find_first_row_with_action(action, status_hint)
        no = self._extract_workorder_no(row)
        if not no:
            raise AssertionError("未能从目标行提取工单编号（WO...）")
        return no

    def refresh(self):
        """刷新工单列表（该产品非实时，动作后需刷新才见最新状态）。"""
        self.page.reload()
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(1500)
        self.page.wait_for_selector(".el-table tbody tr", timeout=15000)
        return self

    def find_row_by_no(self, workorder_no: str):
        """按工单编号定位行；找不到抛清晰错误。"""
        rows = self._rows()
        for i in range(rows.count()):
            row = rows.nth(i)
            try:
                if workorder_no in row.inner_text():
                    return row
            except Exception:
                continue
        raise AssertionError(f"工单列表里找不到工单 {workorder_no}（可能被筛选/分页，或动作未生效）")

    def find_newest_in_status(self, status: str):
        """返回列表中第一个状态含 status 关键词的行 + 工单编号。

        适用场景：列表按创建时间倒序时，"最新创建的 + 该状态"的工单就在最前面。
        用于端到端流程：派单后立刻抓新工单号，无需依赖工单描述文本定位。
        """
        import re
        rows = self._rows()
        for i in range(rows.count()):
            row = rows.nth(i)
            try:
                if status in row.inner_text():
                    m = re.search(r"WO\d+", row.inner_text())
                    if m:
                        return row, i, m.group(0)
            except Exception:
                continue
        raise AssertionError(f"工单列表里没有状态含「{status}」的行")

    def find_row_by_text(self, text: str):
        """按行文本含指定子串定位行（用于按"派单描述唯一前缀"精确定位 E2E 工单）。

        端到端流程中，多个状态阶段（待审批/待处理/待复核/已完成）需要锁同一张工单，
        用描述前缀（E2E-<timestamp>）可稳定避开数据库其他工单。
        """
        rows = self._rows()
        for i in range(rows.count()):
            row = rows.nth(i)
            try:
                if text in row.inner_text():
                    return row, i
            except Exception:
                continue
        raise AssertionError(f"工单列表里找不到含文本「{text[:40]}」的行")

    def assert_row_exists_with_status(self, text: str, status: str, timeout=10000):
        """断言含 text 的行存在且状态含 status（轮询等待产品非实时延迟）。"""
        import time as _t
        deadline = _t.time() + timeout / 1000
        while _t.time() < deadline:
            try:
                row, _ = self.find_row_by_text(text)
                if status in row.inner_text():
                    return row
            except AssertionError:
                pass
            self.page.wait_for_timeout(800)
        # 最后再试一次给出详情
        try:
            row, _ = self.find_row_by_text(text)
            raise AssertionError(
                f"工单含「{text[:30]}」在 {timeout/1000:.0f}s 内状态未变为「{status}」。当前行: "
                f"{row.inner_text().replace(chr(10), ' | ')[:150]}"
            )
        except AssertionError as e:
            raise AssertionError(str(e)) from None

    def assert_row_status(self, workorder_no: str, status: str, timeout=10000):
        """断言指定工单编号的行的状态列含 status（会轮询等待，防产品刷新延迟）。"""
        # 轮询：产品非实时，状态可能延迟几秒
        import time as _t
        deadline = _t.time() + timeout / 1000
        while _t.time() < deadline:
            try:
                row = self.find_row_by_no(workorder_no)
                if status in row.inner_text():
                    return
            except AssertionError:
                pass
            self.page.wait_for_timeout(800)
        # 最后再试一次，给出详细失败信息
        row = self.find_row_by_no(workorder_no)
        txt = row.inner_text().replace("\n", " | ")
        raise AssertionError(f"工单 {workorder_no} 在 {timeout/1000:.0f}s 内状态未变为「{status}」。当前行: {txt[:150]}")

    def assert_row_action_gone(self, workorder_no: str, action: str, timeout=10000):
        """断言指定工单编号的行已不再有 action 按钮（动作完成后原操作按钮应消失）。"""
        import time as _t
        deadline = _t.time() + timeout / 1000
        while _t.time() < deadline:
            try:
                row = self.find_row_by_no(workorder_no)
                if row.locator("button, .el-link", has_text=action).count() == 0:
                    return
            except AssertionError:
                pass
            self.page.wait_for_timeout(800)
        raise AssertionError(f"工单 {workorder_no} 动作后仍存在「{action}」按钮（可能未生效）")

    # ------- 按「状态 + 操作」定位行（不盲点第一行）-------
    def _row_status(self, row) -> str:
        """取一行的状态文本（工单状态列）。找不到返回空串。"""
        texts = row.locator("td .cell").all_inner_texts()
        # 工单状态通常在表格中部；直接拼整行文本，取含状态关键词的那段
        row_text = " ".join(t.strip() for t in texts if t.strip())
        return row_text

    def _find_first_row_with_action(self, action: str, status_hint: str = None):
        """返回第一个操作列含 action 按钮、且（可选）状态匹配 status_hint 的行。

        status_hint 是状态关键词（如「待审批」「待处理」），用于确保找对状态的行。
        找不到抛清晰错误，绝不盲点第一行。
        """
        rows = self.page.locator(".el-table tbody tr")
        for i in range(rows.count()):
            row = rows.nth(i)
            act_btns = row.locator("button, a, .el-link", has_text=action)
            if act_btns.count() == 0:
                continue
            # 跳过 disabled 按钮（点了没反应）
            try:
                if act_btns.first.is_disabled():
                    continue
            except Exception:
                pass
            if status_hint:
                # 状态列若在行文本里找不到关键词，跳过
                if status_hint not in self._row_status(row):
                    # 状态可能含前缀，用宽松匹配
                    if f"{status_hint}" not in row.inner_text():
                        continue
            return row, i
        raise AssertionError(
            f"工单列表里没有「{action}」可用操作行"
            + (f"（期望状态含「{status_hint}」）" if status_hint else "")
        )

    def _open_action_dialog(self, action: str, dialog_cls, row_index=0, status_hint=None):
        """定位含 action 的行并点开，返回 dialog 对象。"""
        row, _ = self._find_first_row_with_action(action, status_hint)
        row.locator("button, a, .el-link", has_text=action).first.click(timeout=10000)
        self.page.wait_for_timeout(1500)
        return dialog_cls(self.page)

    def open_detail_by_link(self, row_index: int = 0):
        """通过点击工单编号链接打开详情/审批弹窗。"""
        row = self.page.locator(".el-table tbody tr").nth(row_index)
        # 工单编号在第二列，是个蓝色链接
        row.locator("a").first.click()
        self.page.wait_for_selector(".el-dialog", timeout=10000)
        return ApprovalDialog(self.page)

    def click_revoke(self, row_index: int = 0, status_hint: str = None):
        """派单人视角：点击「撤销」（业务上为待审批期派单人撤回，工单变"已撤销"）。

        真实场景（任务书 2.6/3.5）：撤销作用于「待审批」工单，非"审批未通过"
        （审批未通过是终态，只能重新派单，不提供撤销）。撤销按钮只出现在派单人
        自己的可撤销工单行上，因此默认不传状态、找第一条含可用撤销按钮的行即可。
        """
        if status_hint is None:
            row, _ = self._find_first_row_with_action("撤销")
        else:
            row, _ = self._find_first_row_with_action("撤销", status_hint)
        row.locator("button, a, .el-link", has_text="撤销").first.click()
        self.page.wait_for_timeout(1500)
        return RevokeDialog(self.page)

    def click_approve(self, row_index: int = 0, status_hint: str = None):
        """审批人视角：点击「审批」。

        按钮本身只在可审批状态下出现，因此默认只找第一个有可用「审批」按钮的行，
        不依赖状态文案。若想按状态过滤可传 status_hint（如「待审批」）。
        """
        return self._open_action_dialog("审批", ApprovalDialog, row_index, status_hint)

    def click_handle(self, row_index: int = 0, status_hint: str = None):
        """处理人员视角：点击「处理」。"""
        return self._open_action_dialog("处理", HandleDialog, row_index, status_hint)

    def click_review(self, row_index: int = 0, status_hint: str = None):
        """复核人员视角：点击「复核」。"""
        return self._open_action_dialog("复核", ReviewDialog, row_index, status_hint)


class ApprovalDialog(BasePage):
    """工单审批弹窗：审批通过 / 审批未通过

    真实交互（2026-09-08 123 环境核对）：
      点「审批」→ 弹出工单审批 dialog（按钮：取消 / 审批未通过 / 审批通过）
      点「审批通过」→ 再弹二次确认 MessageBox（「确认审批通过该工单并分配给处理人？
      取消 / 确定」），需再点「确定」才算真正提交。
    成功信号：二次确认框关闭 / 审批 dialog 关闭。
    """

    APPROVE_PASS_BTN = "审批通过"
    APPROVE_REJECT_BTN = "审批未通过"
    OPINION_INPUT = "审批意见"
    CANCEL_BTN = "取消"

    def _confirm_message_box(self, timeout=6000):
        """审批通过/驳回后会有二次确认 MessageBox，点「确定」提交。"""
        box = self.page.locator(".el-message-box:visible").last
        try:
            box.wait_for(state="visible", timeout=timeout)
            confirm = box.locator("button", has_text="确定")
            if confirm.count() == 0:
                confirm = box.locator("button", has_text="确认")
            confirm.first.click(timeout=5000)
            # 等 MessageBox 关闭
            self.page.locator(".el-message-box:visible").last.wait_for(state="hidden", timeout=timeout)
        except Exception:
            # 无二次确认框 → 视为已直接提交，接受
            pass

    def approve_pass(self):
        self.page.get_by_role("button", name=self.APPROVE_PASS_BTN, exact=True).first.click()
        self._confirm_message_box()
        # 最后等审批主弹窗关闭（含 Message 一闪而过的容错）
        self.page.locator(".el-dialog:visible, .el-drawer:visible").first.wait_for(
            state="hidden", timeout=8000
        )

    def approve_reject(self, opinion: str = ""):
        """审批未通过，先填意见（未通过时必填），再点按钮并过二次确认。"""
        if opinion:
            self.page.get_by_placeholder("审批意见", exact=False).first.fill(opinion)
        self.page.get_by_role("button", name=self.APPROVE_REJECT_BTN, exact=True).first.click()
        self._confirm_message_box()
        self.page.locator(".el-dialog:visible, .el-drawer:visible").first.wait_for(
            state="hidden", timeout=8000
        )

    def cancel(self):
        self.page.get_by_role("button", name=self.CANCEL_BTN, exact=True).first.click()


class RevokeDialog(BasePage):
    """撤销工单弹窗：填撤销原因 → 确认撤销"""

    REVOKE_REASON_INPUT = "撤销原因"
    CONFIRM_REVOKE_BTN = "确认撤销"
    CANCEL_BTN = "取消"

    def fill_reason(self, reason: str):
        self.page.get_by_placeholder("请输入撤销原因", exact=False).first.fill(reason)

    def confirm(self):
        self.page.get_by_role("button", name=self.CONFIRM_REVOKE_BTN, exact=True).click()

    def cancel(self):
        self.page.get_by_role("button", name=self.CANCEL_BTN, exact=True).click()


class HandleDialog(BasePage):
    """处理工单弹窗：逐条漏洞选处理结论 → 保存 → 提交复核

    真实交互（2026-09-08 123 环境核对）：
      点「处理」→ 弹出处理工单 dialog（标题含工单编号）
      中间是「漏洞明细」表格，每一行的「处理结论」列是一个 el-select
      （默认"待修复"），需在每行下拉里选结论（待修复/已修复/已忽略/误报）
      底部按钮：保存 / 提交复核 / 关闭
      提示「全部漏洞都处理才能提交复核」→ 选完须点「保存」再点「提交复核」
    """

    CONCLUSION_SELECT = "处理结论"
    SAVE_BTN = "保存"
    SUBMIT_REVIEW_BTN = "提交复核"
    CLOSE_BTN = "关闭"
    # 处理结论选项
    CONCLUSION_PENDING = "待修复"
    CONCLUSION_FIXED = "已修复"
    CONCLUSION_IGNORED = "已忽略"
    CONCLUSION_FALSE_POSITIVE = "误报"

    def select_conclusion(self, conclusion: str, row_index: int = 0):
        """在漏洞明细表格第 row_index 行的「处理结论」下拉里选结论。

        处理结论下拉是表格行内的 el-select，不是弹窗顶部表单项。
        真实选项（123 环境）：待修复 / 已修复 / 已忽略（无法修复）/ 误报
        """
        # 必须限定 dialog 内表格，避免命中背后主列表的行
        rows = self.page.locator(".el-dialog:visible .el-table tbody tr")
        row = rows.nth(row_index)
        row.wait_for(state="visible", timeout=8000)
        # 行内只有一个 el-select（处理结论）
        select = row.locator(".el-select").first
        select.click(timeout=8000)
        # 等下拉展开，选目标结论
        dd = self.page.locator(".el-select-dropdown:visible").first
        dd.wait_for(state="visible", timeout=5000)
        opt = dd.locator(".el-select-dropdown__item", has_text=conclusion).first
        opt.wait_for(state="visible", timeout=5000)
        opt.click()
        self.page.wait_for_timeout(800)

    def save(self):
        self.page.get_by_role("button", name=self.SAVE_BTN, exact=True).click()
        self.page.wait_for_timeout(1500)  # 保存为暂存动作，成功以随后提交复核为准

    def submit_review(self):
        """提交复核（会弹出确认弹窗）。"""
        self.page.get_by_role("button", name=self.SUBMIT_REVIEW_BTN, exact=True).click()
        self._confirm_submit_review()

    def close(self):
        self.page.get_by_role("button", name=self.CLOSE_BTN, exact=True).click()

    # ---------------- 内部辅助 ----------------
    def _confirm_submit_review(self, timeout=6000):
        """提交复核后有 MessageBox 确认框（标题「提交复核确认」），按钮为「确认提交」。

        真实 MessageBox（123 环境）：「提交后，工单内容将不可再修改。... 取消 / 确认提交」
        必须点「确认提交」才真正提交。
        """
        box = self.page.locator(".el-message-box:visible").last
        try:
            box.wait_for(state="visible", timeout=timeout)
            confirm = box.locator("button", has_text="确认提交")
            if confirm.count() == 0:
                confirm = box.locator("button", has_text="确认")
            if confirm.count() == 0:
                confirm = box.locator("button", has_text="确定")
            confirm.first.click(timeout=5000)
            # 等 MessageBox 关闭
            self.page.locator(".el-message-box:visible").last.wait_for(state="hidden", timeout=timeout)
        except Exception:
            pass  # 无确认框，视为已提交


class ReviewDialog(BasePage):
    """复核工单弹窗：复核通过 / 复核驳回

    真实交互（2026-09-08 123 环境核对）：
      点行内「复核」→ 复核 dialog（含工单详情 + 漏洞明细只读，按钮：复核通过/复核驳回/关闭）
      点「复核通过」→ 弹 MessageBox「复核通过 / 复核通过，请填写复核意见 / 取消 / 确认通过」，
        内有输入框 placeholder=请输入复核意见（必填）→ 需填意见后点「确认通过」才真正提交。
      复核驳回同理（可能也要意见 + 二次确认）。
    成功信号：MessageBox 关闭 / 主弹窗关闭。
    """

    REVIEW_PASS_BTN = "复核通过"
    REVIEW_REJECT_BTN = "复核驳回"
    CLOSE_BTN = "关闭"

    def review_pass(self, opinion: str = "复核通过，处理结果符合要求"):
        """复核通过：填必填复核意见 → 二次确认点「确认通过」。"""
        self.page.get_by_role("button", name=self.REVIEW_PASS_BTN, exact=True).first.click()
        self._confirm_review_box(opinion)

    def review_reject(self, opinion: str = "复核驳回，处理结果不符合要求"):
        """复核驳回：填意见 → 二次确认。"""
        self.page.get_by_role("button", name=self.REVIEW_REJECT_BTN, exact=True).first.click()
        self._confirm_review_box(opinion)

    def close(self):
        self.page.get_by_role("button", name=self.CLOSE_BTN, exact=True).click()

    def _confirm_review_box(self, opinion: str, timeout=8000):
        """复核二次确认 MessageBox：填必填意见 → 点「确认通过/确认驳回」→ 等弹窗关闭。"""
        box = self.page.locator(".el-message-box:visible").last
        try:
            box.wait_for(state="visible", timeout=timeout)
            # 填复核意见（placeholder=请输入复核意见（必填））
            try:
                opinion_inp = box.locator("textarea, input", has_text="复核意见").first
                if opinion_inp.count() == 0:
                    opinion_inp = box.locator(".el-input__inner").first
                opinion_inp.fill(opinion)
                self.page.wait_for_timeout(300)
            except Exception:
                pass
            # 点确认按钮（确认通过 / 确认驳回 / 确定 / 确认）
            confirm = box.locator("button", has_text="确认通过")
            if confirm.count() == 0:
                confirm = box.locator("button", has_text="确认驳回")
            if confirm.count() == 0:
                confirm = box.locator("button", has_text="确定")
            if confirm.count() == 0:
                confirm = box.locator("button", has_text="确认")
            confirm.first.click(timeout=5000)
            # 等 MessageBox 关闭
            self.page.locator(".el-message-box:visible").last.wait_for(state="hidden", timeout=timeout)
        except Exception:
            pass  # 无确认框，视为已提交
