#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 健康检查 + 重抓引导工具（解决 token 过期导致的接口全量 401 假失败）

用法：
    ./venv/bin/python check_token.py            # 检查当前默认环境(55)
    HSC_ENV=123 ./venv/bin/python check_token.py # 检查 123 环境
    HSC_ENV=123 ./venv/bin/python check_token.py --fix   # 失效时自动尝试重抓

原理：
    HSC token 会轮换过期（无 refresh_token，登录需验证码+加密密码，无法纯接口无人值守重抓）。
    本工具调一个典型的业务鉴权接口（系统管理-用户列表）探测 token 是否仍有效：
      - HTTP 200 + success=true            -> token 有效，可直接跑用例
      - HTTP 200 + code=401 / 未授权       -> token 已过期（后端把鉴权失败放在业务体里）
      - 其它（500/502/连接失败）           -> 非 token 问题，属后端/网络不稳定

    --fix 失效时自动尝试 export_token.py 重抓（需本地已具备 playwright 登录态 state.json），
    重抓成功后再探测一次确认。CI 环境（无浏览器/无登录态）勿用 --fix。
"""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from config import BASE_URL, ENV, get_headers
import requests

PROBE_PATH = f"{BASE_URL}/system/user/list?pageNo=1&pageSize=1"


def probe_token(timeout=(5, 15)):
    """探测当前环境 token 是否有效。返回 (ok: bool, detail: str)"""
    try:
        headers = get_headers()
    except RuntimeError as e:
        # token 文件缺失/为空 → 环境未配置 token
        return False, f"未配置 token: {e}（先跑 export_token.py 或粘贴 token_{ENV}.txt）"
    try:
        resp = requests.get(PROBE_PATH, headers=headers, timeout=timeout, verify=False)
    except requests.exceptions.SSLError:
        # 环境自签名证书
        try:
            import urllib3
            urllib3.disable_warnings()
            resp = requests.get(PROBE_PATH, headers=headers, timeout=timeout, verify=False)
        except requests.RequestException as e:
            return False, f"连接失败(网络/后端): {e}"
    except requests.RequestException as e:
        return False, f"连接失败(网络/后端): {e}"

    status = resp.status_code
    try:
        data = resp.json()
    except Exception:
        return False, f"HTTP {status}（非 JSON 响应，可能网关/代理拦截）"

    biz_success = data.get("success")
    code = data.get("code")
    msg = data.get("message", "")

    # 鉴权层判定：401/403 才代表 token 无效；500/502/503 说明请求已通过鉴权层进入业务层，token 有效
    if status in (401, 403) or code in (401, 403) or "未授权" in str(msg) or code == 0 and "token" in str(msg).lower():
        return False, f"HTTP {status} / code={code} / {msg} → token 已过期或无效"
    if status >= 500 or code in (500, 502, 503):
        # 后端 5xx：鉴权已过，只是业务接口出错 → token 有效
        return True, f"HTTP {status} / code={code} / {msg}（后端5xx，但鉴权已过 → token 有效，可重试接口）"
    if biz_success is True and code == 200:
        return True, f"HTTP {status} / 业务 code={code} → token 有效"
    # 其它业务失败码（400/业务错误）通常也代表鉴权已过
    if code and code != 200:
        return True, f"HTTP {status} / 业务 code={code} / {msg}（非401，鉴权已过 → token 有效）"
    return False, f"HTTP {status} / code={code} / {msg}（无法判定，疑后端异常）"


def try_refresh():
    """调用 export_token.py 重抓（需 playwright 登录态）。返回成功与否。"""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_tests", "export_token.py")
    if not os.path.exists(script):
        print("  未找到 export_token.py，无法自动重抓")
        return False
    print("  → 调用 export_token.py 重抓 token ...")
    r = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"  重抓失败: {r.stdout[-500:] if r.stdout else ''}{r.stderr[-500:] if r.stderr else ''}")
        return False
    print("  重抓成功，已写入新 token 文件")
    return True


def main():
    fix = "--fix" in sys.argv
    env_show = ENV  # 使用 config 解析后的实际环境（含默认55）
    print(f"=== Token 健康检查（环境 {env_show}）===")
    print(f"BASE_URL: {BASE_URL}")
    print(f"探测接口: GET {PROBE_PATH}\n")

    ok, detail = probe_token()
    print(f"[{'有效' if ok else '失效'}] {detail}")

    if ok:
        print("\n✅ Token 有效，可直接跑用例。")
        return 0

    if not fix:
        print("\n❌ Token 无效。请先重抓再跑用例：")
        print(f"    HSC_ENV={env_show} ./venv/bin/python ui_tests/export_token.py")
        print("   （需先有 UI 登录态 state.json，见该脚本说明）")
        print(f"  或：HSC_ENV={env_show} ./venv/bin/python check_token.py --fix")
        return 1

    print("\n→ 尝试自动重抓 ...")
    if try_refresh():
        ok2, detail2 = probe_token()
        print(f"[{'有效' if ok2 else '仍失效'}] {detail2}")
        if ok2:
            print("\n✅ 重抓成功，token 已有效，可直接跑用例。")
            return 0
        print("\n❌ 重抓后仍无效，登录态可能已过期，请重新跑 UI 登录冒烟。")
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
