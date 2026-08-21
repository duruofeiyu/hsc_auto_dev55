from playwright.sync_api import Page, expect
from config import UI_TEST_USER, UI_TEST_PASSWORD
from login_page import LoginPage


def test_hsc_login(page: Page):
    """HSC 前端登录冒烟：用 ddddocr 识别验证码完成登录，断言进入系统"""
    LoginPage(page).login_with_captcha(UI_TEST_USER, UI_TEST_PASSWORD)
    # 登录成功：精确的「登录」按钮消失（离开登录页），系统首页主体渲染
    expect(page.get_by_role("button", name="登录", exact=True)).to_be_hidden()
    expect(page.locator("body")).to_be_visible()
