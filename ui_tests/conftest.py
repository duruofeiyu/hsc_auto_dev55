import os
import pytest
from playwright.sync_api import sync_playwright
import allure
from config import UI_TEST_USER, UI_TEST_PASSWORD, UI_AUTH_STATE_FILE
from login_page import LoginPage


def pytest_configure(config):
    """注册自定义 marker，避免 pytest 未注册警告，并支持按角色筛选用例。"""
    config.addinivalue_line(
        "markers",
        "role(name): 声明用例使用的账号角色（如 admin/common_admin/operation），用于筛选与报告可视化",
    )


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


@pytest.fixture(scope="function")
def role_page(request):
    """按角色登录 / 复用登录态的 page（权限收口后的多角色测试核心 fixture）。

    用法 —— 在用例上用 parametrize 标注需要的角色：
        @pytest.mark.parametrize("role_page", ["common_admin"], indirect=True)
        def test_dispatch(role_page):
            WorkorderListPage(role_page).open()...

    - 首次：用该角色账号密码登录（ddddocr 识别验证码），保存独立 storage_state；
    - 之后：直接复用该角色 storage_state，跳过验证码；
    - HSC_FORCE_LOGIN=1 可强制所有角色重登（会话过期时）。
    - 角色密码未注入会立即报清晰错误，提示对应环境变量。
    """
    from config import UI_ROLE_USERS, UI_ROLE_PASSWORDS, UI_ROLE_STATE_FILES

    role = getattr(request, "param", "chenyh")
    if role not in UI_ROLE_USERS:
        raise ValueError(f"未知角色 '{role}'，可选角色：{list(UI_ROLE_USERS)}")
    user = UI_ROLE_USERS[role]
    password = UI_ROLE_PASSWORDS[role]
    state_file = UI_ROLE_STATE_FILES[role]

    # 报告可观测：在 Allure 里给本用例打上"当前角色 + 实际登录账号"标签，
    # 一眼看清每条用例跑的是哪个账号（防止多角色"假绿"串号而不自知）。
    allure.dynamic.label("role", f"{role}={user}")

    if not password:
        raise RuntimeError(
            f"角色 '{role}' 的密码未设置！\n"
            f"请通过环境变量注入：export HSC_UI_{role.upper()}_PASSWORD='真实密码'\n"
            f"（当前账号：{user}；UI 登录需 55 环境明文密码，无默认值）"
        )

    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=CHROMIUM_ARGS)
        # 已有登录态且未强制重登 -> 直接复用，跳过验证码
        if os.path.exists(state_file) and not os.getenv("HSC_FORCE_LOGIN"):
            context = browser.new_context(
                storage_state=state_file, ignore_https_errors=True
            )
            page = context.new_page()
            yield page
            context.close()
            browser.close()
            return
        # 否则登录该角色并保存独立 state 供下次复用
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        LoginPage(page).login_with_captcha(user, password, save_state=False)
        context.storage_state(path=state_file)
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
            page = (
                item.funcargs.get("page")
                or item.funcargs.get("authed_page")
                or item.funcargs.get("role_page")
            )
            if page is not None:
                screenshot = page.screenshot()
                allure.attach(
                    screenshot,
                    name=f"失败截图_{item.name}",
                    attachment_type=allure.attachment_type.PNG,
                )
        except Exception:
            pass

