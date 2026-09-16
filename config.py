import os
import json
import requests


def _load_dotenv():
    """零依赖加载项目根 .env（若存在），把密码/账号等敏感配置写进环境变量。

    - 仅读取 .env 中『当前环境变量里尚未设置』的键 → 不覆盖 CI/export 已注入的
      （保证 .github/workflows 或显式 export 的 HSC_* 优先级最高）。
    - .env 已被 .gitignore 忽略，不会入库；适合存本机测试账号明文密码。
    - 用法：在项目根建 .env，一行一个 `HSC_UI_ADMIN_PASSWORD=真实密码`。
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                # 不覆盖已存在的环境变量（CI / export 优先）
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_dotenv()

# ============================================================
# 环境切换（开发 55 / 测试 123 一键切换）
# 用法：
#   export HSC_ENV=55     # 默认，开发环境
#   export HSC_ENV=123    # 测试环境
# 也可用 HSC_BASE_URL / HSC_UI_WEB_BASE_URL 环境变量直接覆盖具体地址
# ============================================================
ENV = os.getenv("HSC_ENV", "55").lower()

_ENVIRONMENTS = {
    "55": {
        "name": "55开发环境",
        "base_url": "https://192.168.124.55:26400/hsc-system-api",
        "web_base_url": "https://192.168.124.55:26400",
    },
    "123": {
        "name": "123测试环境",
        "base_url": "https://192.168.124.123:26400/hsc-system-api",
        "web_base_url": "https://192.168.124.123:26400",
    },
}

_ENV_CFG = _ENVIRONMENTS.get(ENV, _ENVIRONMENTS["55"])
ENV_NAME = _ENV_CFG["name"]

BASE_URL = os.getenv("HSC_BASE_URL", _ENV_CFG["base_url"])

# ============================================================
# 测试账号配置（从环境变量读取，避免硬编码；生产环境请通过 .env 注入）
# 用法：
#   export HSC_TEST_ACCOUNT=chenyh
#   export HSC_TEST_PASSWORD=<接口加密口令串，从环境变量注入，切勿硬编码>
# ============================================================
TEST_USER_ACCOUNT = os.getenv("HSC_TEST_ACCOUNT", "chenyh")
TEST_ENCRYPTED_PASSWORD = os.getenv("HSC_TEST_PASSWORD", "")

# 默认测试账号的明文密码（新增用户时使用），从环境变量注入，勿硬编码
DEFAULT_TEST_PASSWORD = os.getenv("HSC_DEFAULT_TEST_PASSWORD", "")

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
# 默认放在 ui/tests/.auth/state_{ENV}.json，已纳入 .gitignore，不会入库
# （带 ENV 后缀隔离 55/123 两环境登录态，避免互相污染）
UI_AUTH_STATE_FILE = os.path.join(
    os.path.dirname(__file__), "ui", "tests", ".auth", f"state_{ENV}.json"
)

# HSC 前端（Web）地址：与接口 BASE_URL 不同——前端在【根路径】，接口在 /hsc-system-api 下。
# ⚠️ 2026-09-10 实测（55 与 123 表现一致）：
#   - 前端路由是 history 模式、base='/'\，地址里【不能】加 /hsc-system-web 前缀；
#     加了之后「已登录态」访问会渲染前端「500 非常抱歉，服务器出错了」错误页
#     （看着像后端挂了，其实接口全 200）。
#   - 该前缀只在「未登录」时看不出来：登录守卫会先把请求跳到 /login，所以
#     export_token.py / refresh_state.py / 登录用例一直跑得通，把问题掩盖了；
#     只有「已登录后直接 goto 前端路径」（如各 PageObject.open()）才会踩雷。
#   - 正确写法：UI_WEB_BASE_URL + "/assetDiscover"（路径式）；
#     旧写法 UI_WEB_BASE_URL + "/#/assetDiscover" 里的 hash 会被忽略、落到首页。
UI_WEB_BASE_URL = os.getenv("HSC_UI_WEB_BASE_URL", _ENV_CFG["web_base_url"])

# ============================================================
# UI 多角色账号（权限收口后，业务操作分散到不同角色账号）
# 每个角色从【独立环境变量】读取明文密码，无默认值（必须注入）。
# 账号名默认按角色标识，若实际账号名不同请用 HSC_UI_<ROLE>_USER 覆盖。
# 每个角色独立 storage_state 文件，统一放 ui/tests/.auth/state_<role>.json
# （该目录已被 .gitignore 忽略，不会入库）。
# 角色清单（对应 HSC 55 环境权限收口后的 5 类账号 + 原 chenyh）：
#   admin           系统管理员（全权限，用于 4.1 超管全见 / 全局配置）
#   system_security 系统安全员（密码策略 / IP 白名单 / 登录锁定 / 会话超时）
#   audit           审计管理员（审计查看，通常只读）
#   common_admin    普通管理员（派单 1.2 / 审批 2.1·2.2；账号 ceshi）
#   operation       工单执行员（工单修复 3.1 / 回退 3.2 / 执行；账号 chuli）
#   chenyh          原测试账号（当前为 common_admin，可作权限回归对照）
# ============================================================
UI_ROLE_USERS = {
    "admin":           os.getenv("HSC_UI_ADMIN_USER", "admin"),
    "system_security": os.getenv("HSC_UI_SYSTEM_SECURITY_USER", "secadmin"),
    "audit":           os.getenv("HSC_UI_AUDIT_USER", "audit"),
    "common_admin":    os.getenv("HSC_UI_COMMON_ADMIN_USER", "ceshi"),
    "operation":       os.getenv("HSC_UI_OPERATION_USER", "chuli"),
    "chenyh":          os.getenv("HSC_UI_USER", UI_TEST_USER),
}

UI_ROLE_PASSWORDS = {
    "admin":           os.getenv("HSC_UI_ADMIN_PASSWORD", ""),
    "system_security": os.getenv("HSC_UI_SYSTEM_SECURITY_PASSWORD", ""),
    "audit":           os.getenv("HSC_UI_AUDIT_PASSWORD", ""),
    "common_admin":    os.getenv("HSC_UI_COMMON_ADMIN_PASSWORD", ""),
    "operation":       os.getenv("HSC_UI_OPERATION_PASSWORD", ""),
    "chenyh":          os.getenv("HSC_UI_PASSWORD", UI_TEST_PASSWORD),
}

# 每个角色独立登录态（storage_state 会话复用），避免每条用例重复过验证码
# 带 ENV 后缀隔离 55/123 两环境登录态
# 运行时凭证统一目录（token_*.txt / auth_headers_*.json 收进这里，不再散落根目录）
SECRETS_DIR = os.path.join(os.path.dirname(__file__), ".secrets")
os.makedirs(SECRETS_DIR, exist_ok=True)

UI_ROLE_STATE_FILES = {
    role: os.path.join(os.path.dirname(__file__), "ui", "tests", ".auth", f"state_{ENV}_{role}.json")
    for role in UI_ROLE_USERS
}

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

    # 回退到本地 token_{ENV}.txt（本地开发，按环境隔离）
    # 兼容旧 token.txt（仅当新文件不存在时）
    base_dir = SECRETS_DIR
    token_file = os.path.join(base_dir, f"token_{ENV}.txt")
    legacy_file = os.path.join(os.path.dirname(__file__), "token.txt")
    for candidate in (token_file, legacy_file, os.path.join(os.path.dirname(__file__), f"token_{ENV}.txt")):
        if os.path.exists(candidate):
            with open(candidate, "r") as f:
                token = f.read().strip()
                if token:
                    return token
    raise RuntimeError(
        f"Token 不存在或为空，请 F12 抓包后粘贴到 {token_file}（当前环境 {ENV}）"
    )


# 接口测试按角色区分 token 文件（权限收口后，系统管理类接口需对应角色 token）
# 权限矩阵（已与用户核对 2026-09-08，纠正此前“全部 admin”的错误假设）：
#   - 系统管理员 admin    ：用户管理、部门管理（组织类操作）
#   - 系统安全员 secadmin ：角色管理、菜单管理（权限/菜单类操作）
# 因此 system_management 按子模块拆分角色：
#   - 用户 / 部门  → SYSTEM_ADMIN_ROLE（admin）
#   - 角色 / 菜单  → SYSTEM_SECURITY_ROLE（system_security / secadmin）
# 其他业务模块（资产/脆弱性/合规）仍用默认 token（chenyh，业务权限未变）。
SYSTEM_ADMIN_ROLE = os.getenv("HSC_SYSTEM_ADMIN_ROLE", "admin")
SYSTEM_SECURITY_ROLE = os.getenv("HSC_SYSTEM_SECURITY_ROLE", "system_security")


def get_headers(role: str = None):
    """
    构建请求头（每次动态读取 token，支持 token 刷新）
    用法:
        headers = get_headers()              # 默认 token（chenyh，业务模块用）
        headers = get_headers("admin")       # 指定角色 token（系统管理模块用）

    说明：HSC 接口认证靠 `Authorization` 与 `X-Access-Token` 两个请求头
    （同 JWT 值）。按角色读取项目根 `auth_headers_{ENV}_{role}.json`；
    无 role 时读 `auth_headers_{ENV}.json`（兼容原有单 token 逻辑）。
    `export_token.py --role <role>` 负责导出对应文件。
    浏览器会话 Cookie 与认证无关，无需附加。
    """
    headers = {
        "Content-Type": "application/json;charset=UTF-8"
    }
    base_dir = os.path.dirname(__file__)
    # 角色化优先，其次默认，最后兼容旧的 auth_headers.json / token.txt
    if role:
        # 角色 token 必须显式导出，缺失时直接报错，避免静默回退到默认
        # (chenyh) token 导致「无权限 403」却查不出原因（权限 bug 假绿）。
        role_file = os.path.join(SECRETS_DIR, f"auth_headers_{ENV}_{role}.json")
        if not os.path.exists(role_file):
            raise RuntimeError(
                f"角色 '{role}' 的 token 文件不存在：{role_file}\n"
                f"请先用该角色账号登录并导出 token：\n"
                f"  ./venv/bin/python ui_tests/export_token.py --role {role}\n"
                f"需注入对应角色明文密码，如：export HSC_UI_{role.upper()}_PASSWORD='密码'"
            )
        candidates = [role_file]
    else:
        candidates = [
            os.path.join(SECRETS_DIR, f"auth_headers_{ENV}.json"),
            os.path.join(base_dir, f"auth_headers_{ENV}.json"),
            os.path.join(base_dir, "auth_headers.json"),
        ]
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                extra = json.load(f)
            auth = extra.get("Authorization")
            xat = extra.get("X-Access-Token")
            if auth:
                headers["Authorization"] = auth
            if xat:
                headers["X-Access-Token"] = xat
            if "Authorization" in headers and "X-Access-Token" in headers:
                break
        except (json.JSONDecodeError, ValueError):
            continue
    # 回退到 token.txt（兼容旧逻辑 / CI 仅用 HSC_TOKEN）
    if "Authorization" not in headers or "X-Access-Token" not in headers:
        token = load_token()
        headers.setdefault("Authorization", token)
        headers.setdefault("X-Access-Token", token)
    return headers


# ============================================================
# 业务数据 ID 环境隔离（跨环境 ID 不同的硬编码值集中在此）
# 55 为已实测有效值；123 需明天在 123 环境实测后回填（留空则 get_env_id 返回 None）
# ============================================================
ENV_IDS = {
    "55": {
        # 系统管理：研发部（父部门）ID，用于「新增下级部门」「查询部门IP段」
        "PARENT_DEPT_ID": "2082053606579658754",
        # 脆弱性管理：基线核查「DB2_配置规范_(Linux)」模板 ID
        "BASELINE_TEMPLATE_ID": "332358588846572071",
        # 合规运营：个人信息保护检测文件 ID（123 原硬编码 8827 已失效）
        "PI_DETECTION_FILE_IDS": [3054],
    },
    "123": {
        # 系统管理：研发部（父部门）ID。123 环境 chenyh 账号无系统管理权限（部门/用户列表 403），
        # 该模块在 123 跑不了，故留空；如需在 123 跑 system_management 需换有权限账号后实测回填。
        "PARENT_DEPT_ID": "",
        # 脆弱性管理：基线模板「DB2_配置规范_(Linux)」ID。实测 123 与 55 同值（共享种子数据）。
        "BASELINE_TEMPLATE_ID": "332358588846572071",
        # 合规运营：个人信息保护检测文件 ID。实测 123 有效值（123 框架原硬编码，55 的 3054 在 123 无效）。
        "PI_DETECTION_FILE_IDS": [8827],
    },
}


def get_env_id(key, default=None):
    """按当前环境读取业务数据 ID，不存在时返回 default"""
    ids = ENV_IDS.get(ENV, ENV_IDS["55"])
    return ids.get(key, default)


def resolve_env_placeholders(obj):
    """
    递归替换数据结构中的 `__KEY__` 占位符为当前环境对应的 ENV_IDS 值。
    用于 YAML 数据驱动文件里跨环境 ID 的环境化（业务测试代码零改动）。
    用法：YAML 里写 parent_id: "__PARENT_DEPT_ID__"，加载后自动替换为真实 ID。
    """
    if isinstance(obj, dict):
        return {k: resolve_env_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_env_placeholders(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("__") and obj.endswith("__"):
        key = obj.strip("__")
        val = get_env_id(key)
        # 仅替换 ENV_IDS 中实际存在的环境 ID 占位符（如 __PARENT_DEPT_ID__）；
        # 未知占位符（如测试标记 __unique_name__）原样保留，交给测试代码自行处理，
        # 否则会误伤测试专用标记导致业务字段被清空。
        return val if val is not None else obj
    return obj
