"""
登录页对象（Page Object 模式）

选择器均经 ui_tests/debug_login.py 在 55 环境实测确认：
- 账号输入框 placeholder="账号"
- 密码输入框 placeholder="密码"
- 验证码输入框 placeholder="验证码"
- 验证码图片：位于 .code-input 容器内、src 以 data:image/png 开头（100x32 内联图）
- 登录页真实路径：/hsc-system-web/ 重定向到 /login

注意：页面存在「账号登录」「绑定登录」两组表单，占位符重复，
因此所有 get_by_placeholder 一律用 .first 锁定默认可见的「账号登录」表单。
"""
import base64
import re

from base_page import BasePage
from playwright.sync_api import Page, expect
from config import UI_AUTH_STATE_FILE
from utils_captcha import recognize_captcha


class LoginPage(BasePage):
    # 定位器（类常量，集中管理，改文案只改这里）
    # 仅取第一组（账号登录表单）；绑定表单的重复占位符由 .first 自动跳过
    ACCOUNT_INPUT = "账号"
    PASSWORD_INPUT = "密码"
    CAPTCHA_INPUT = "验证码"
    LOGIN_BUTTON = "登录"  # 精确匹配，避免误命中「绑定并登录」

    # HSC 验证码格式（实测：4 位字母数字；ddddocr 偶尔会读出中文等垃圾，须校验后丢弃）
    CAPTCHA_PATTERN = re.compile(r"^[A-Za-z0-9]{4,5}$")

    def open(self):
        """打开 HSC 登录页（/hsc-system-web/ 会重定向到 /login）"""
        super().open("")
        # 等登录表单的账号输入框出现，确保页面渲染完成
        self.page.get_by_placeholder(self.ACCOUNT_INPUT).first.wait_for(timeout=15000)

    def login(self, user: str, password: str):
        """无验证码场景的登录（预留，当前 55 环境有验证码，请用 login_with_captcha）"""
        self._fill_credentials(user, password)
        self.page.get_by_role("button", name=self.LOGIN_BUTTON, exact=True).click()
        self._wait_login_success()
        return self

    # ---------------- 验证码登录 ----------------
    def login_with_captcha(self, user: str, password: str, save_state: bool = True, max_attempts: int = 12):
        """带验证码识别的登录（ddddocr 本地 OCR + 智能重试）。

        成功后可保存 storage_state，供后续用例复用（会话复用），
        免去每条用例重复识别验证码。

        重试策略（针对 ddddocr 识别率不稳定的情况）：
        - 读出的码若不符合 HSC 验证码格式（4~5 位字母数字，排除中文/符号垃圾），
          直接整页重载换一张新验证码，不浪费一次登录提交；
        - 每次失败也整页重载，确保拿到全新的随机验证码（点击图片刷新在 HSC 不生效）；
        - 最多尝试 max_attempts 次，远超原来的 3 次，靠「多试几张简单码」提高成功率。

        :param user: 账号
        :param password: 真实明文密码（无默认值，未设置会立即报错）
        :param save_state: 是否把登录态存到 UI_AUTH_STATE_FILE
        :param max_attempts: 最大尝试次数（默认 12）
        """
        if not password:
            raise RuntimeError(
                "UI_TEST_PASSWORD 为空！\n"
                "UI 登录需要 55 环境账号的【真实明文密码】，请通过环境变量设置：\n"
                "    export HSC_UI_PASSWORD='你的真实密码'\n"
                "（接口侧用的是加密串，UI 登录不能用加密串；此变量无默认值）"
            )

        self.open()
        last_err = ""

        for attempt in range(1, max_attempts + 1):
            # 确保登录表单已渲染
            self.page.get_by_placeholder(self.ACCOUNT_INPUT).first.wait_for(timeout=15000)
            self._fill_credentials(user, password)

            code = self._recognize_captcha_code()
            # 格式校验：ddddocr 偶尔读出中文/符号垃圾，直接丢弃换新码，不提交
            if not self.CAPTCHA_PATTERN.fullmatch(code):
                print(
                    f"[captcha] 第{attempt}次识别结果 '{code}' 格式异常（应为4~5位字母数字），"
                    "重载换一张重试"
                )
                self._reload_for_captcha()
                continue

            self.page.get_by_placeholder(self.CAPTCHA_INPUT).first.fill(code)
            self.page.get_by_role("button", name=self.LOGIN_BUTTON, exact=True).click()

            # 成功信号：精确的「登录」按钮消失（离开登录页进入系统）
            try:
                self.page.get_by_role(
                    "button", name=self.LOGIN_BUTTON, exact=True
                ).wait_for(state="hidden", timeout=5000)
                if save_state:
                    os_makedirs_auth()
                    self.page.context.storage_state(path=UI_AUTH_STATE_FILE)
                return self
            except Exception:
                last_err = self._read_error()
                print(
                    f"[captcha] 第{attempt}次登录失败（提交 '{code}'），"
                    f"重载换一张重试。页面提示：{last_err or '（无）'}"
                )
                self._reload_for_captcha()
                continue

        raise RuntimeError(
            f"登录失败：已尝试 {max_attempts} 次仍无法进入系统。"
            + (f"\n最后页面提示：{last_err}" if last_err else "")
            + "\n可能原因：① ddddocr 识别率不足（验证码干扰线过多）；"
            "② 账号/密码错误；③ 验证码图片定位不准。\n"
            "对应方案：让开发关掉 55 测试环境验证码，或改用手动 mock。"
        )

    # ---------------- 内部辅助 ----------------
    def _fill_credentials(self, user: str, password: str):
        self.page.get_by_placeholder(self.ACCOUNT_INPUT).first.fill(user)
        self.page.get_by_placeholder(self.PASSWORD_INPUT).first.fill(password)

    def _reload_for_captcha(self):
        """点击验证码图片刷新出一张全新的随机验证码。

        重要：HSC 的验证码按会话只生成一次，**整页 reload 不会换码**（实测 10 次重载
        拿到完全相同的图）；只有「点击验证码图片」才会真正触发刷新、返回新图。
        因此失败时靠点图换码，而非 reload。
        """
        img = self._captcha_img().first
        try:
            old = img.get_attribute("src")
        except Exception:
            old = None
        try:
            img.click()
        except Exception:
            # 兜底：点到图片的父容器
            try:
                img.locator("xpath=..").click()
            except Exception:
                pass
        # 等图片 src 真正变化（最多 3s），避免读到旧图
        try:
            self.page.wait_for_function(
                """(old) => {
                    const el = document.querySelector('input[placeholder="验证码"]');
                    const im = el && el.closest('.code-input')
                                 && el.closest('.code-input').querySelector('img[src^="data:image/png"]');
                    return !!im && im.src && im.src !== old;
                }""",
                arg=old,
                timeout=3000,
            )
        except Exception:
            self.page.wait_for_timeout(800)

    def _captcha_img(self):
        """定位登录表单的验证码图片（.code-input 容器内、data:image/png 内联图）"""
        return (
            self.page.get_by_placeholder(self.CAPTCHA_INPUT)
            .first.locator("xpath=ancestor::div[contains(@class,'code-input')]")
            .locator('img[src^="data:image/png"]')
        )

    def _recognize_captcha_code(self) -> str:
        """读取验证码图片的 base64 源码 → 解码 → ddddocr 离线识别。

        为什么不用「截图元素」：HSC 登录页会自动刷新验证码（img 节点被替换），
        元素截图常报 'Element is not attached to the DOM'；改用已验证的 Playwright
        定位器直接取 src 属性，比截图轻量、且不受节点渲染稳定性影响。
        """
        loc = self._captcha_img().first
        loc.wait_for(state="attached", timeout=8000)
        src = loc.get_attribute("src")
        if not src or not src.startswith("data:image/png"):
            raise RuntimeError(
                "无法读取验证码图片：_captcha_img 定位器未找到 base64 验证码图。"
                "请确认 55 环境验证码图片选择器是否变化。"
            )
        return recognize_captcha(base64.b64decode(src.split(",", 1)[1]))

    def _wait_login_success(self):
        self.page.get_by_role(
            "button", name=self.LOGIN_BUTTON, exact=True
        ).wait_for(state="hidden", timeout=8000)

    def _read_error(self) -> str:
        """抓取页面上的错误提示（Element UI message / form error），用于诊断"""
        try:
            msgs = self.page.locator(
                ".el-message__content, .el-form-item__error"
            ).all_inner_texts()
            return "；".join(m.strip() for m in msgs if m and m.strip())
        except Exception:
            return ""


def os_makedirs_auth():
    import os

    d = os.path.dirname(UI_AUTH_STATE_FILE)
    if d:
        os.makedirs(d, exist_ok=True)
