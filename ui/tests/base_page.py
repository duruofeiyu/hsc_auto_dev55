"""
UI 页面对象基类（Page Object 模式）

设计思路（对齐接口侧 base.py）：
- 所有页面对象都继承 BasePage
- 只封装「页面交互」和「通用等待/断言」，不含测试数据
- 测试数据（账号、密码）从 config 读取，实现数据与代码分离
- 定位策略优先用 get_by_role / get_by_placeholder（可读、抗 DOM 结构变化）
"""
from playwright.sync_api import Page, expect
from config import UI_WEB_BASE_URL


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    # -------- 通用导航 --------
    def open(self, path: str = ""):
        """打开 HSC 前端页面。

        前端基址用 UI_WEB_BASE_URL（根路径，如 https://192.168.124.55:26400），
        与接口 BASE_URL（…/hsc-system-api）不同。
        path 用【路径式】写法，例如 '' 或 '/assetDiscover'。
        ⚠️ 不要写 '/#/xxx'（前端是 history 模式，hash 会被忽略、落到首页），
           也不要加 '/hsc-system-web' 前缀（已登录态下会渲染 500 错误页）。
        """
        hsc_url = UI_WEB_BASE_URL.rstrip("/") + path
        self.page.goto(hsc_url)

    # -------- 通用断言 --------
    def expect_visible(self, selector: str):
        """断言某个元素可见"""
        expect(self.page.locator(selector)).to_be_visible()

    def expect_text(self, selector: str, text: str):
        """断言某个元素文本等于预期"""
        expect(self.page.locator(selector)).to_have_text(text)
