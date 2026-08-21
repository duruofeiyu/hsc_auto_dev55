import os
import pytest
from playwright.sync_api import sync_playwright
import allure
from config import UI_TEST_USER, UI_TEST_PASSWORD, UI_AUTH_STATE_FILE
from login_page import LoginPage

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]

# 默认无头（headless）运行——自动化/CI 标准做法，不弹浏览器窗口。
# 想肉眼看 Playwright「自己点点」时，本机执行：export PW_HEADLESS=false
HEADLESS = os.getenv("PW_HEADLESS", "true").lower() != "false"


@pytest.fixture(scope="function")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=CHROMIUM_ARGS)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.fixture(scope="session")
def auth_state():
    """登录一次（ddddocr 识别验证码），保存 storage_state 供后续用例复用。

    - 已存在登录态且未强制重登则直接复用（跳过验证码识别）。
    - 设置环境变量 HSC_FORCE_LOGIN=1 可强制重新登录（如会话过期）。
    """
    os.makedirs(os.path.dirname(UI_AUTH_STATE_FILE), exist_ok=True)
    if os.path.exists(UI_AUTH_STATE_FILE) and not os.getenv("HSC_FORCE_LOGIN"):
        return UI_AUTH_STATE_FILE
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=CHROMIUM_ARGS)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        LoginPage(page).login_with_captcha(
            UI_TEST_USER, UI_TEST_PASSWORD, save_state=True
        )
        context.close()
        browser.close()
    return UI_AUTH_STATE_FILE


@pytest.fixture(scope="function")
def authed_page(auth_state):
    """已登录的 page：直接带会话状态进入系统，跳过每次登录 + 验证码识别。

    业务用例（派单 / 审批）用这个 fixture，避免每条用例都过一遍验证码。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=CHROMIUM_ARGS)
        context = browser.new_context(
            storage_state=UI_AUTH_STATE_FILE, ignore_https_errors=True
        )
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例失败时自动截图并附加到 Allure 报告（对齐接口侧「失败有迹可循」标准）"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        try:
            page = item.funcargs.get("page") or item.funcargs.get("authed_page")
            if page is not None:
                screenshot = page.screenshot()
                allure.attach(
                    screenshot,
                    name=f"失败截图_{item.name}",
                    attachment_type=allure.attachment_type.PNG,
                )
        except Exception:
            pass

