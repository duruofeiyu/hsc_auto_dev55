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

前提：先成功运行过 UI 登录冒烟，生成 ui_tests/.auth/state.json。
用法：
    cd /Users/a1-6/hsc_auto_dev55
    ./venv/bin/python ui_tests/export_token.py     # 或 python3 ui_tests/export_token.py
"""
import os
import sys
import json

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("需要 playwright：请先安装（pip install playwright 或 ./venv/bin/pip install playwright）。")

HERE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = HERE                                  # ui_tests/
PROJECT_ROOT = os.path.dirname(HERE)           # hsc_auto_dev55/
STATE_FILE = os.path.join(UI_DIR, ".auth", "state.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.txt")
AUTH_HEADERS_FILE = os.path.join(PROJECT_ROOT, "auth_headers.json")

# 复用 config 里的 UI 前端地址，避免写死
sys.path.insert(0, PROJECT_ROOT)
from config import UI_WEB_BASE_URL  # noqa: E402


def main():
    if not os.path.exists(STATE_FILE):
        sys.exit(
            "未找到登录态文件：%s\n请先运行 UI 登录冒烟生成它：\n"
            "  ./venv/bin/python ui_tests/test_login.py -v -s" % STATE_FILE
        )

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

        # 1) 进首页，触发 SPA 初始化与首批 API
        try:
            page.goto(UI_WEB_BASE_URL + "/#/", wait_until="networkidle", timeout=20000)
        except Exception as e:
            print("首页加载超时（忽略，继续）：", e)
        page.wait_for_timeout(2500)

        # 2) 再进用户管理页，强制触发 /system/user/list 之类的数据接口
        try:
            page.goto(UI_WEB_BASE_URL + "/#/system/user", wait_until="networkidle", timeout=20000)
        except Exception as e:
            print("用户页加载超时（忽略，继续）：", e)
        page.wait_for_timeout(2500)

        browser.close()

    if not captured_auth:
        sys.exit(
            "未能拦截到任何带 Authorization 头的 API 请求。\n"
            "可能登录态已失效，请重新运行 UI 登录冒烟后再执行本脚本：\n"
            "  ./venv/bin/pytest ui_tests/test_login.py -v -s\n"
            "  ./venv/bin/python ui_tests/export_token.py"
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
