#!/usr/bin/env python3
"""
从 UI 登录态自动导出接口认证信息，消灭手工 F12 抓包粘贴。

方法（v4，深度诊断后定稿）：用 Playwright 加载已保存的登录态 (storage_state)，
在浏览器里真实触发一次 API 请求，同时拦截浏览器真实发出的
`Authorization` 和 `X-Access-Token` 两个头，写入项目根：
  - token.txt         : Authorization 头的值（兼容 HSC_TOKEN 环境变量逻辑）
  - auth_headers.json : { "Authorization": ..., "X-Access-Token": ... }

关键发现（沙箱决定性对照实验 2026-08-21）：
  - HSC 接口认证只靠 `Authorization` + `X-Access-Token` 两个请求头（值同 JWT，172 字符）。
  - 浏览器会话 Cookie 与认证无关（HSC cookie 里只有 HMACCOUNT/Hm_lvt 等统计类，无 satoken/JSESSIONID）。
  - v3 曾把 Cookie 也写进 auth_headers.json 并由 get_headers 附加，验证属于画蛇添足，已去除。

前提：先成功运行过 UI 登录冒烟，生成 ui/tests/.auth/state.json。
用法：
    cd /Users/a1-6/hsc_auto
    ./venv/bin/python ui/tests/export_token.py     # 或 python3 ui/tests/export_token.py
"""
import os
import sys
import json
import argparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("需要 playwright：请先安装（pip install playwright 或 ./venv/bin/pip install playwright）。")

HERE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = HERE                                  # ui/tests/
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))  # hsc_auto/

# 复用 config 里的 UI 前端地址 + 环境标识，避免写死（必须先于下方文件名引用）
sys.path.insert(0, PROJECT_ROOT)
from config import (  # noqa: E402
    UI_WEB_BASE_URL,
    ENV,
    UI_TEST_USER,
    UI_TEST_PASSWORD,
    UI_ROLE_USERS,
    UI_ROLE_PASSWORDS,
)
from login_page import LoginPage  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="从 UI 登录态导出接口认证 token")
    parser.add_argument(
        "--role", default=None,
        help="角色 key（对应 config.UI_ROLE_USERS 的 key）。"
             "不传则导出默认 token（用 state.json，对应 chenyh 业务账号）；"
             "传 admin/system_security/operation 等则用 state_<role>.json 导出 auth_headers_<ENV>_<role>.json",
    )
    args = parser.parse_args()
    role = args.role

    # 按角色+环境选择 state 文件与导出文件（带 ENV 后缀隔离 55/123）：
    #   无 role -> state_{ENV}.json / auth_headers_{ENV}.json（默认业务 token）
    #   有 role -> state_{ENV}_{role}.json / auth_headers_{ENV}_{role}.json
    STATE_FILE = os.path.join(UI_DIR, ".auth", f"state_{ENV}_{role}.json" if role else f"state_{ENV}.json")
    TOKEN_FILE = os.path.join(PROJECT_ROOT, ".secrets", f"token_{ENV}.txt")
    AUTH_HEADERS_FILE = os.path.join(
        PROJECT_ROOT, ".secrets",
        f"auth_headers_{ENV}_{role}.json" if role else f"auth_headers_{ENV}.json",
    )
    os.makedirs(os.path.dirname(AUTH_HEADERS_FILE), exist_ok=True)

    # state 不存在则自动登录生成（按 role 选用对应账号，避免手动先跑登录冒烟）
    if not os.path.exists(STATE_FILE):
        if role:
            user = UI_ROLE_USERS.get(role)
            password = UI_ROLE_PASSWORDS.get(role)
        else:
            user, password = UI_TEST_USER, UI_TEST_PASSWORD
        if not password:
            sys.exit(
                f"未找到登录态文件：{STATE_FILE}\n"
                f"且角色 {role or '默认(chenyh)'} 的密码未注入，无法自动登录。\n"
                f"请先设置对应明文密码环境变量后重试。"
            )
        print(f">>> 登录态缺失，自动登录角色 {role or '默认'}（账号 {user}）生成 {STATE_FILE}")
        try:
            # 注意：sync_playwright 已在模块顶部导入。
            # 这里不要再写 `from playwright.sync_api import sync_playwright`——
            # 函数内的 import 会让该名字在整个 main() 里变成「局部变量」，
            # 于是 state 文件已存在（不走进这个分支）时，
            # 后面的 sync_playwright() 会抛 UnboundLocalError。
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                ctx = browser.new_context(ignore_https_errors=True)
                page = ctx.new_page()
                LoginPage(page).login_with_captcha(user, password, save_state=False)
                ctx.storage_state(path=STATE_FILE)
                browser.close()
            print(f">>> 已生成登录态：{STATE_FILE}")
        except Exception as e:
            sys.exit(f"自动登录失败：{e}")

    # 同时收集 Authorization 与 X-Access-Token（去重保序）
    captured_auth = []
    captured_xat = []

    def on_request(request):
        if "hsc-system-api" not in request.url:
            return
        a = request.headers.get("authorization")
        x = request.headers.get("x-access-token")
        if a and a not in captured_auth:
            captured_auth.append(a)
        if x and x not in captured_xat:
            captured_xat.append(x)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=STATE_FILE, ignore_https_errors=True
        )
        page = context.new_page()
        page.on("request", on_request)

        # 1) 进首页，触发 SPA 初始化与首批 API（token 就是从这里抓到的）
        # 注意：HSC 前端是 history 路由，地址里写 "/#/xxx" 的 hash 会被忽略、落到首页，
        # 所以这里只开根路径，不再拼 hash；要用路径式地址请直接写 "/system/xxx"。
        try:
            page.goto(UI_WEB_BASE_URL + "/", wait_until="networkidle", timeout=20000)
        except Exception as e:
            print("首页加载超时（忽略，继续）：", e)
        page.wait_for_timeout(2500)

        # 2) 再进一个业务页，多触发一轮数据接口（同样用路径式，不带 hash）
        # 说明：具体业务路由由后端菜单下发（/hsc-system-api/system/auth/routes），
        # 各环境菜单可能不同，故这里不做硬编码跳转，只依赖首页那批请求即可。
        page.wait_for_timeout(1500)

        browser.close()

    if not captured_auth:
        sys.exit(
            "未能拦截到任何带 Authorization 头的 API 请求。\n"
            "可能登录态已失效，请重新运行 UI 登录冒烟后再执行本脚本：\n"
            "  ./venv/bin/pytest ui/tests/test_login.py -v -s\n"
            "  ./venv/bin/python ui/tests/export_token.py"
        )

    # 取最后一次拦截到的值（通常是当前会话最新有效的 token）
    auth_value = captured_auth[-1]
    xat_value = captured_xat[-1] if captured_xat else auth_value

    # 写出 token.txt（兼容原 load_token / HSC_TOKEN 逻辑）
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(auth_value)

    # 写出完整认证头，供 get_headers() 复用
    auth_headers = {
        "Authorization": auth_value,
        "X-Access-Token": xat_value,
    }
    with open(AUTH_HEADERS_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_headers, f, ensure_ascii=False, indent=2)

    print(f"Token 已导出 -> {TOKEN_FILE}")
    print(f"认证头已导出 -> {AUTH_HEADERS_FILE}")
    print(f"Authorization / X-Access-Token 各捕获 {len(captured_auth)} / {len(captured_xat)} 次（值相同 JWT）")
    print(f"Token 前缀：{auth_value[:20]}...")


if __name__ == "__main__":
    main()
