import os
import json
import requests

# HSC 55 开发环境配置
BASE_URL = "https://192.168.124.55:26400/hsc-system-api"

# ============================================================
# 测试账号配置（从环境变量读取，避免硬编码；生产环境请通过 .env 注入）
# 用法：
#   export HSC_TEST_ACCOUNT=chenyh
#   export HSC_TEST_PASSWORD=oUyRvWjNBC1/UB6ttKI0Wg==
# ============================================================
TEST_USER_ACCOUNT = os.getenv("HSC_TEST_ACCOUNT", "chenyh")
TEST_ENCRYPTED_PASSWORD = os.getenv("HSC_TEST_PASSWORD", "oUyRvWjNBC1/UB6ttKI0Wg==")

# 默认测试账号的明文密码（新增用户时使用）
DEFAULT_TEST_PASSWORD = "XingDing@2024"

# ============================================================
# UI 自动化测试账号（从环境变量读取，避免硬编码；生产环境请通过 .env 注入）
# 用法：
#   export HSC_UI_USER=chenyh
#   export HSC_UI_PASSWORD=<你的55环境真实明文密码>   # 必填，无默认值
# 注意：接口侧用的是加密串(TEST_ENCRYPTED_PASSWORD)，UI 登录必须填明文密码，不能用加密串
# ============================================================
UI_TEST_USER = os.getenv("HSC_UI_USER", "chenyh")
UI_TEST_PASSWORD = os.getenv("HSC_UI_PASSWORD", "")

# UI 登录态持久化（storage_state 会话复用），避免每条用例重复过验证码
# 默认放在 ui_tests/.auth/state.json，已纳入 .gitignore，不会入库
UI_AUTH_STATE_FILE = os.path.join(
    os.path.dirname(__file__), "ui_tests", ".auth", "state.json"
)

# HSC 前端（Web）地址：与接口 BASE_URL 不同，前端在 /hsc-system-web 下
# 实测：开发服务器 192.168.124.55:26400 的登录页为 /hsc-system-web/#/login
UI_WEB_BASE_URL = os.getenv(
    "HSC_UI_WEB_BASE_URL", "https://192.168.124.55:26400/hsc-system-web"
)

# 关闭 HTTPS 证书验证警告
requests.packages.urllib3.disable_warnings()


# 登录 Token（从浏览器 F12 抓包，粘贴到 token.txt）
def load_token():
    """
    读取 Token，按以下优先级：
    1. 环境变量 HSC_TOKEN（CI 环境 / GitHub Secrets）
    2. 本地 token.txt 文件（本地开发）
    都不存在则报错
    """
    # 优先从环境变量读取（CI 环境）
    env_token = os.getenv("HSC_TOKEN")
    if env_token:
        return env_token

    # 回退到本地 token.txt（本地开发）
    token_file = os.path.join(os.path.dirname(__file__), "token.txt")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            token = f.read().strip()
            if token:
                return token
    raise RuntimeError(
        "Token 不存在或为空，请 F12 抓包后粘贴到 " + token_file
    )


def get_headers():
    """
    构建请求头（每次动态读取 token，支持 token 刷新）
    用法: headers = get_headers()

    说明：HSC 接口认证靠 `Authorization` 与 `X-Access-Token` 两个请求头
    （同 JWT 值）。`export_token.py` 会把浏览器真实抓到的两个头写入
    项目根 `auth_headers.json`，此处优先读取；不存在时回退到 `token.txt`。
    浏览器会话 Cookie 与认证无关（HSC cookie 里只有 HMACCOUNT/Hm_lvt 等
    统计类，无 satoken/JSESSIONID），无需附加。
    """
    headers = {
        "Content-Type": "application/json;charset=UTF-8"
    }
    auth_json = os.path.join(os.path.dirname(__file__), "auth_headers.json")
    if os.path.exists(auth_json):
        try:
            with open(auth_json, "r", encoding="utf-8") as f:
                extra = json.load(f)
            auth = extra.get("Authorization")
            xat = extra.get("X-Access-Token")
            if auth:
                headers["Authorization"] = auth
            if xat:
                headers["X-Access-Token"] = xat
        except (json.JSONDecodeError, ValueError):
            pass
    # 回退到 token.txt（兼容旧逻辑 / CI 仅用 HSC_TOKEN）
    if "Authorization" not in headers or "X-Access-Token" not in headers:
        token = load_token()
        headers.setdefault("Authorization", token)
        headers.setdefault("X-Access-Token", token)
    return headers
