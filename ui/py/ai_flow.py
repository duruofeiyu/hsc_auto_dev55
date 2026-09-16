"""驱动 ui/midscene/scripts/run-yaml.js 的 Python 封装。

对外只有一个函数 + 一个结果对象：

    result = run_flow("asset_discover", vars={"EXPECT_TOTAL": "87"})
    assert result.all_passed

run-yaml.js 的输出契约（2026-09-15 实测）：
  任务块  === [i/N] 任务标题 ===
  步骤    "  ✓ [j/M] 标签 (x.xs)" / "  ✗ ..."（✗ 后跟缩进错误信息，任务内中断）
  提取    "  [提取结果] {json}"（javascript/aiQuery 的 name 结果，多行缩进 JSON）
  汇总    "[结果] P passed, F failed[, S skipped]"
  退出码  0=全过  1=有用例失败  2=环境问题（登录态/页面报错，不是用例问题）
"""
import json
import os
import re
import subprocess
import time

try:
    import allure  # 有则挂报告，没有也能裸跑
except ImportError:  # pragma: no cover
    allure = None

UI_MIDSCENE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "midscene"
)
RUN_YAML = os.path.join(UI_MIDSCENE, "scripts", "run-yaml.js")
ENSURE_AUTH = os.path.join(UI_MIDSCENE, "scripts", "ensure_auth.js")
NODE = os.getenv("HSC_NODE_BIN", "node")

# 登录态体检结果缓存（秒）：套件连续跑多条用例时，避免每条都探一次活。
# 窗口取得比 123 最短实测会话（≈6-12min）保守得多，过期后自动重检自愈。
_AUTH_TTL = 60.0
_auth_ok_at = {}  # (env, role) -> 最近一次体检通过的时间戳


def _ensure_auth(run_env, ensure=True):
    """跑流程前体检登录态（npm run auth 同款逻辑：0.3s 探活，过期自动重登）。

    为什么必须有：123 环境会话极短（JWT 无 exp，服务端控制，实测 ~10 分钟就被
    踹回 /login）且疑似单点互踢——上一秒还绿，下一条用例就全灭在登录页，
    报错还长得像用例问题。体检前置把这类失败在开跑前自愈掉。
    """
    if not ensure or os.getenv("HSC_SKIP_AUTH") == "1":
        return
    key = (run_env.get("HSC_ENV", ""), run_env.get("HSC_AUTH_ROLE", ""))
    if time.time() - _auth_ok_at.get(key, 0) < _AUTH_TTL:
        return
    proc = subprocess.run(
        [NODE, ENSURE_AUTH], cwd=UI_MIDSCENE, env=run_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise FlowError(
            "登录态体检/刷新失败（环境问题，非用例问题）：\n" + proc.stdout[-800:]
        )
    _auth_ok_at[key] = time.time()

_TASK_RE = re.compile(r"^=== \[(\d+)/(\d+)\] (.+) ===$")
_STEP_RE = re.compile(r"^\s+([✓✗]) \[\d+/\d+\] (.+?)\s+\(([\d.]+)s\)$")
_EXTRACT_RE = re.compile(r"^\s+\[提取结果\] (.*)$")
_SUMMARY_RE = re.compile(r"\[结果\] (\d+) passed, (\d+) failed(?:, (\d+) skipped)?")
# 已知日志行前缀：提取段（多行 JSON）的续行里不会出现这些；
# 注意 JSON 的收尾 `}` 在行首无缩进，不能靠缩进判断续行
_LOG_PREFIX_RE = re.compile(r"^(=== \[|\s+[✓✗] \[|\[结果\]|\[nav\]|\[env\]|\[auth\]|\[flow\]|\[提取结果\])")


class FlowError(RuntimeError):
    """流程没跑成（环境问题 / 脚本异常），区别于"用例断言失败"。"""


class FlowResult:
    def __init__(self, flow, returncode, output):
        self.flow = flow
        self.returncode = returncode
        self.output = output
        self.tasks = []          # [{title, steps:[{ok,label,secs}], results:{}, failed:bool}]
        self.summary = None      # (passed, failed, skipped)
        self._parse()

    def _parse(self):
        cur = None
        extract_buf = None
        for line in self.output.splitlines():
            m = _TASK_RE.match(line)
            if m:
                cur = {"title": m.group(3), "steps": [], "results": {}, "failed": False}
                self.tasks.append(cur)
                extract_buf = None
                continue
            m = _STEP_RE.match(line)
            if m and cur is not None:
                ok = m.group(1) == "✓"
                cur["steps"].append({"ok": ok, "label": m.group(2), "secs": float(m.group(3))})
                if not ok:
                    cur["failed"] = True
                continue
            m = _EXTRACT_RE.match(line)
            if m and cur is not None:
                data = self._loads([m.group(1)])
                if data is not None:
                    cur["results"].update(data)      # 单行 JSON 直接收
                else:
                    extract_buf = [m.group(1)]       # 多行 JSON，开始累积
                continue
            if extract_buf is not None:
                if line.strip() and not _LOG_PREFIX_RE.match(line):
                    extract_buf.append(line.strip())
                    data = self._loads(extract_buf)
                    if data is not None:
                        cur["results"].update(data)  # 累积到能解析就合并
                        extract_buf = None
                    continue
                extract_buf = None                   # 遇到下一条日志行，提取段结束
            if line.strip().startswith("✗") and cur is not None:
                cur["failed"] = True
            m = _SUMMARY_RE.search(line)
            if m:
                self.summary = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
        if extract_buf is not None and cur is not None:
            data = self._loads(extract_buf)
            if data is not None:
                cur["results"].update(data)

    @staticmethod
    def _loads(buf):
        """把累积的行拼回 JSON；拼不完整/不是对象就返回 None（继续累积）。"""
        try:
            data = json.loads("".join(buf))
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    # ---- 用例侧常用访问 ----
    @property
    def all_passed(self):
        return self.returncode == 0 and not any(t["failed"] for t in self.tasks)

    def task(self, keyword):
        """按标题关键字取任务块，取不到抛 KeyError（用例里写错立刻暴露）。"""
        hits = [t for t in self.tasks if keyword in t["title"]]
        if not hits:
            raise KeyError(f"找不到含「{keyword}」的任务，实际任务: {[t['title'] for t in self.tasks]}")
        return hits[0]


def run_flow(flow, vars=None, role=None, env=None, timeout=900, ensure_auth=True):
    """跑一个 YAML 流程并返回 FlowResult。

    flow  : flows/ 下的文件名（带不带 .yaml 都行），或任意绝对路径
    vars  : {"EXPECT_TOTAL": "87"} → --var EXPECT_TOTAL=87（数据驱动入口）
    role  : 登录角色（默认 common_admin），如 admin / operation
    env   : "55" / "123"，默认沿用 HSC_ENV 或 55
    ensure_auth: 跑前自动体检/刷新登录态（本地演示流程可传 False）
    """
    if not flow.endswith(".yaml"):
        flow += ".yaml"
    flow_abs = flow if os.path.isabs(flow) else os.path.join(UI_MIDSCENE, "flows", flow)
    if not os.path.exists(flow_abs):
        raise FileNotFoundError(f"流程文件不存在：{flow_abs}")

    cmd = [NODE, RUN_YAML, flow_abs]
    for k, v in (vars or {}).items():
        cmd += ["--var", f"{k}={v}"]

    run_env = dict(os.environ)
    if env:
        run_env["HSC_ENV"] = env
    if role:
        run_env["HSC_AUTH_ROLE"] = role

    _ensure_auth(run_env, ensure=ensure_auth)

    proc = subprocess.run(
        cmd, cwd=UI_MIDSCENE, env=run_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,  # 合流！分开捕获会乱序，✗ 行会跑到汇总后面
        text=True, timeout=timeout,
    )
    output = proc.stdout
    result = FlowResult(os.path.basename(flow_abs), proc.returncode, output)

    if allure is not None:
        allure.attach(output, name=f"flow:{result.flow}", attachment_type=allure.attachment_type.TEXT)

    if proc.returncode == 2:
        raise FlowError(
            f"环境问题（非用例失败）：{result.flow}\n"
            f"  先看输出尾部；常见修复：npm run auth（登录态）/ npm run check:env（环境体检）\n"
            f"  ---- 输出尾部 ----\n{output[-800:]}"
        )
    if proc.returncode not in (0, 1):
        raise FlowError(f"run-yaml.js 异常退出（code={proc.returncode}）：\n{output[-800:]}")
    return result
