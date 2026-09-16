#!/usr/bin/env python3
"""
强制刷新某个角色的 UI 登录态（storage_state）。

---- 为什么需要这个脚本 ----
HSC 的 token 会过期。**「state 文件存在」不等于「登录态还有效」**：
conftest.py 的 role_page / export_token.py 都只在 state 文件【不存在】时才登录，
遇到一个已经过期的文件会静默复用 → 页面一打开就被踹回 /login，
用例全线失败，但报错信息（"当前页面是登录界面"）完全看不出是登录态的问题。

本脚本跳过「存在即复用」的判断，无条件重新登录一次并覆盖 state 文件。
调用方通常是 UI 自动化跑用例前的体检钩子（ui/midscene/scripts/ensure_auth.js）。

用法：
    cd /Users/a1-6/hsc_auto
    ./venv/bin/python ui/tests/refresh_state.py                    # 默认 common_admin
    ./venv/bin/python ui/tests/refresh_state.py --role admin
    ./venv/bin/python ui/tests/refresh_state.py --role default     # 默认业务账号(chenyh)

密码来源：项目根 .env 中的 HSC_UI_<ROLE>_PASSWORD（config.py 会自动加载）。
退出码：0 = 刷新成功；1 = 失败（含验证码识别失败 / 账号密码错）。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # ui/tests/
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))      # hsc_auto/

# config.py 在项目根，login_page.py / base_page.py 在 ui/tests/ —— 两个目录都要在路径上
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, HERE)

from config import (  # noqa: E402
    ENV,
    UI_AUTH_STATE_FILE,
    UI_ROLE_PASSWORDS,
    UI_ROLE_STATE_FILES,
    UI_ROLE_USERS,
    UI_TEST_PASSWORD,
    UI_TEST_USER,
)

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]


def _resolve(role: str):
    """把角色 key 解析成 (账号, 密码, state 文件路径)

    default = 默认业务账号（chenyh），登录态存 state_{ENV}.json —— 与
    export_token.py 不传 --role 时的口径一致；其余角色走 UI_ROLE_* 三张表。
    """
    if role == "default":
        return UI_TEST_USER, UI_TEST_PASSWORD, UI_AUTH_STATE_FILE
    if role not in UI_ROLE_USERS:
        sys.exit(f"[x] 未知角色 '{role}'，可选：default / {', '.join(UI_ROLE_USERS)}")
    return UI_ROLE_USERS[role], UI_ROLE_PASSWORDS[role], UI_ROLE_STATE_FILES[role]


def main() -> int:
    ap = argparse.ArgumentParser(description="强制刷新 UI 登录态（storage_state）")
    ap.add_argument("--role", default="common_admin",
                    help="角色 key（默认 common_admin；default=默认业务账号 chenyh）")
    ap.add_argument("--headed", action="store_true",
                    help="有头模式，肉眼看登录过程（排查验证码识别问题时用）")
    args = ap.parse_args()

    user, password, state_file = _resolve(args.role)
    if not password:
        sys.exit(
            f"[x] 角色 '{args.role}'（账号 {user}）的密码未配置。\n"
            f"    请在项目根 .env 里补上：HSC_UI_{args.role.upper()}_PASSWORD=真实明文密码"
        )

    print(f"[*] 刷新登录态：角色={args.role} 账号={user} 环境={ENV}")
    print(f"[*] 目标文件：{state_file}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("[x] 未安装 playwright，请先 ./venv/bin/pip install playwright")

    # login_page 放在 finally 里导入过晚，这里提前导入，报错更直观
    from login_page import LoginPage

    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed, args=CHROMIUM_ARGS)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            # login_with_captcha 内部已含：验证码格式校验 + 点图换码 + 失败重试（最多 12 次）
            # 2026-09-15 改动：登录成功后由 login_page 直接存到 state_path（角色专属文件），
            # 不再外层补 context.storage_state()——保存路径收敛为一个参数，避免两处不一致。
            LoginPage(page).login_with_captcha(
                user, password, save_state=True, state_path=state_file
            )
            context.close()
            browser.close()
    except Exception as e:
        sys.exit(
            f"[x] 登录失败：{e}\n"
            f"    排查方向：① .env 里 {user} 的密码是否过期；② 55 环境是否可达；"
            f"③ 验证码识别是否持续失败（可加 --headed 肉眼看一下）。"
        )

    print(f"[v] 登录态已刷新 -> {state_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
