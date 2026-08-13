import os
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

# 关闭 HTTPS 证书验证警告
requests.packages.urllib3.disable_warnings()


# 登录 Token（从浏览器 F12 抓包，粘贴到 token.txt）
def load_token():
    """从 token.txt 读取 Token，不存在则报错"""
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
    """
    token = load_token()
    return {
        "Authorization": token,
        "X-Access-Token": token,
        "Content-Type": "application/json;charset=UTF-8"
    }
