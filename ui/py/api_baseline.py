"""接口基线取数 —— 跨层一致性断言的数据源。

背景（2026-09-16 优化）：UI 用例原先钉死期望值（探测任务 21→22、漏洞总数
2583→2585 两天就漂），维护成本高还容易误报。改为「UI 显示值 == 接口真实值」
的跨层断言后：不再有魔数、数据怎么涨都不误报、且顺带验证了"页面数据没渲染错"
（前端展示层与后端数据层的一致性，本身就是值得测的东西）。

口径备忘（实测定下，改前端别忘记同步这里）：
- 资产发现卡片「探测任务总数」= /asset/probe/list 的 total + /asset/web-map/list 的 total
  （实测 14 + 8 = 22，与页面卡片一致；页面把探测与网站测绘两类任务合计展示）
- 漏洞总览分页总数 = /vuln/host/list 的 total（实测 2585）

token 时效：接口 token 与浏览器登录态同源（export_token 拦截），123 环境实测
约 10 分钟失效。本模块遇到 401 会自动重登+重导再试一次（自愈），
不要在这里静默降级 —— 取不到基线就应让用例红，而不是跳过。
"""
import os
import subprocess
import sys

import requests
import urllib3

urllib3.disable_warnings()

HERE = os.path.dirname(os.path.abspath(__file__))                 # ui/py
UI_ROOT = os.path.dirname(HERE)                                   # ui/
ROOT = os.path.dirname(UI_ROOT)                                   # hsc_auto/
UI_MIDSCENE = os.path.join(UI_ROOT, "midscene")
ENSURE_AUTH = os.path.join(UI_MIDSCENE, "scripts", "ensure_auth.js")
EXPORT_TOKEN = os.path.join(UI_ROOT, "tests", "export_token.py")
NODE = os.getenv("HSC_NODE_BIN", "node")
VENV_PY = os.path.join(ROOT, "venv", "bin", "python")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)  # config 在仓库根


def _run(cmd, cwd, env=None):
    proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=300)
    return proc.returncode, proc.stdout


def _refresh_token(role):
    """浏览器登录态体检（过期自动重登）→ 重新导出接口 token。"""
    # 注意：HSC_AUTH_ROLE 必须显式传给子进程（2026-09-16 踩坑：构造了却没传，
    # 导致 admin 的自愈实际刷的是默认角色的登录态，重试仍 401）
    env = dict(os.environ)
    env["HSC_AUTH_ROLE"] = role
    rc1, out1 = _run([NODE, ENSURE_AUTH], cwd=UI_MIDSCENE, env=env)
    if rc1 != 0:
        raise RuntimeError(f"登录态体检失败（环境问题，非用例问题）：\n{out1[-500:]}")
    rc2, out2 = _run([VENV_PY, EXPORT_TOKEN, "--role", role], cwd=ROOT, env=env)
    if rc2 != 0:
        raise RuntimeError(f"接口 token 导出失败：\n{out2[-500:]}")


def _post_total(path, payload, role):
    import config

    url = f"{config.BASE_URL}{path}"
    for attempt in (1, 2):
        headers = config.get_headers(role)
        r = requests.post(url, json=payload, headers=headers, verify=False, timeout=15)
        try:
            j = r.json()
        except ValueError:
            raise RuntimeError(f"{path} 返回非 JSON（HTTP {r.status_code}）")
        if j.get("code") == 401 and attempt == 1:
            _refresh_token(role)   # token 过期 → 自愈一次
            continue
        if j.get("code") != 200:
            raise RuntimeError(f"{path} 取数失败：code={j.get('code')} msg={j.get('message')}")
        return int((j.get("result") or {}).get("total"))
    raise RuntimeError(f"{path} 自愈后仍 401")


_LIST_PAYLOAD = {"pageNum": 1, "pageSize": 1, "keyword": "", "keywordFields": []}


def _walk_has_path(nodes, frag):
    for n in nodes or []:
        if (n.get("path") or "") == frag:
            return True
        if _walk_has_path(n.get("children"), frag):
            return True
    return False


def role_has_route(role, path):
    """某角色的【授权路由表】里是否包含 path（/system/auth/routes 实拉）。

    这是区分「越权拦截」和「路径写错」的铁证：两者在页面上都表现为
    同一个通用「500 服务器出错」页，肉眼无法区分（2026-09-16 踩坑）。
      - 表里有 + 页面可用 → 正常
      - 表里有 + 页面不可用 → 路径/前端问题（对照历史 /hsc-system-web 前缀事故排查）
      - 表里无 + 页面不可用 → 权限拦截（预期行为）
      - 表里无 + 页面可用   → 越权漏洞（安全缺陷，提 bug）
    """
    import config

    url = f"{config.BASE_URL}/system/auth/routes"
    for attempt in (1, 2):
        headers = config.get_headers(role)
        r = requests.get(url, headers=headers, verify=False, timeout=15)
        try:
            j = r.json()
        except ValueError:
            raise RuntimeError(f"路由接口返回非 JSON（HTTP {r.status_code}）")
        if j.get("code") == 401 and attempt == 1:
            _refresh_token(role)
            continue
        if j.get("code") != 200:
            raise RuntimeError(f"路由接口取数失败：code={j.get('code')} msg={j.get('message')}")
        return _walk_has_path(j.get("result") or [], path)
    raise RuntimeError("路由接口自愈后仍 401")


def asset_discover_task_total(role="common_admin"):
    """资产发现卡片「探测任务总数」的接口基线 = 探测任务 + 网站测绘任务。"""
    probe = _post_total("/asset/probe/list", _LIST_PAYLOAD, role)
    webmap = _post_total("/asset/web-map/list", _LIST_PAYLOAD, role)
    return probe + webmap


def vuln_host_total(role="common_admin"):
    """漏洞总览分页总数「共 X 条」的接口基线。"""
    return _post_total("/vuln/host/list", {"pageNum": 1, "pageSize": 1}, role)