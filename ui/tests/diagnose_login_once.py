#!/usr/bin/env python3
"""单次登录诊断：回答「手动登得上、脚本登不进」的真正原因。

原理：脚本的成功判定是"登录按钮消失"，失败时页面提示抓取经常是空（选择器未必
命中 HSC 真实 toast），所以直接**抓登录接口的请求/响应原文**——服务器返回的
code/msg 才是终审证据（验证码错误 / 账号或密码错误 / 已锁定 / 其实成功了）。

用法：
    cd ~/hsc_auto
    ./venv/bin/python ui/tests/diagnose_login_once.py                 # 默认 common_admin
    ./venv/bin/python ui/tests/diagnose_login_once.py --role admin
注意：密码从 config（项目根 .env）读取，输出里自动打码，不会泄露到终端历史。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))   # hsc_auto/（config.py）
sys.path.insert(0, HERE)                    # ui/tests/（login_page 等）

from playwright.sync_api import sync_playwright  # noqa: E402
from config import ENV, UI_ROLE_USERS, UI_ROLE_PASSWORDS  # noqa: E402
from login_page import LoginPage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default="common_admin")
    args = ap.parse_args()

    user = UI_ROLE_USERS.get(args.role)
    pwd = UI_ROLE_PASSWORDS.get(args.role)
    if not user or not pwd:
        sys.exit(f"[x] 角色 {args.role} 的账号/密码未配置")
    print(f"[*] 环境={ENV} 角色={args.role} 账号={user} 密码=***（长度 {len(pwd)}）")

    captured = []

    def mask(s):
        return s.replace(pwd, "****") if pwd else s

    def on_response(resp):
        url = resp.url
        if any(k in url.lower() for k in ("login", "auth", "captcha", "token")):
            try:
                body = resp.text()[:400]
            except Exception:
                body = "(不可读)"
            captured.append({
                "method": resp.request.method,
                "url": url,
                "status": resp.status,
                "post": mask((resp.request.post_data or "")[:300]),
                "resp": mask(body),
            })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.on("response", on_response)

        lp = LoginPage(page)
        lp.open()
        lp._fill_credentials(user, pwd)

        # 最多换 3 次图，拿一个格式合法的 OCR 结果（换图不消耗登录尝试）
        code = ""
        for i in range(3):
            code = lp._recognize_captcha_code()
            if LoginPage.CAPTCHA_PATTERN.fullmatch(code):
                break
            lp._reload_for_captcha()
        print(f"[*] 本次提交验证码 OCR 结果：'{code}' "
              f"（格式合法={bool(LoginPage.CAPTCHA_PATTERN.fullmatch(code))}）")

        page.get_by_placeholder("验证码").first.fill(code)
        lp._wait_login_button_ready()
        page.get_by_role("button", name="登录", exact=True).click()
        page.wait_for_timeout(5000)

        print(f"\n[*] 提交后 URL：{page.url}")
        btn_left = page.get_by_role("button", name="登录", exact=True).count()
        print(f"[*] 登录按钮还在？ {btn_left > 0}（False=登录成功进了系统）")
        print(f"[*] 页面错误提示：{lp._read_error() or '（无——注意：这不代表服务器没报错，见下面接口原文）'}")

        print(f"\n=== 登录相关接口原文（{len(captured)} 条）===")
        for c in captured:
            print(f"\n{c['method']} {c['status']} {c['url']}")
            if c["post"]:
                print(f"  请求体: {c['post']}")
            print(f"  响应体: {c['resp']}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
