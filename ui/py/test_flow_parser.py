"""FlowResult 解析器单测（纯逻辑，无 node/浏览器/模型依赖 → CI 质量门禁可跑）。

为什么测解析器而不是跑真流程：
  test_flow_driver.py 虽不碰内网，但需要 node + chromium + 模型 key（AI 旁证任务），
  GitHub 托管 Runner 上跑不动；而驱动层历史上真正的 bug 全在【输出解析】——
  stderr 分流导致 ✗ 乱序、JSON 收尾 `}` 无缩进导致提取丢失。这些用构造样本
  即可回归，且比真流程更快更稳。样本字符串取自 2026-09-16 真实运行输出。
"""
import allure
import pytest

from ui.py.ai_flow import FlowResult

# 真实格式样本（节选自 run-yaml.js 实际输出，含全部边界：多行 JSON、
# 单行 JSON、✗ 归因、汇总行、任务间穿插日志行）
SAMPLE_PASS = """[env] 环境=123  UI=https://192.168.124.123:26400
[auth] 登录态=state_123_common_admin.json
=== [1/3] TC-A 卡片校验 ===
  ✓ [1/2] cards_present  (0.0s)
  ✓ [2/2] cards_text  (0.1s)
  [提取结果] {
  "cards_present": "三张卡片齐全",
  "cards_text": "{\\"总数\\":\\"22 个\\"}"
}

=== [2/3] TC-B 单行提取 ===
  ✓ [1/1] expect_total  (0.0s)
  [提取结果] {"expect_total": "一致：22"}

=== [3/3] TC-C AI 判断 ===
  ✓ [1/2] aiAssert: 排版没有错乱  (3.2s)
  ✗ [2/2] ai_read_total  (2.1s)
      模型返回了非法结构
[结果] 2 passed, 1 failed
"""

SAMPLE_FAIL_ATTRIBUTION = """=== [1/2] TC-1 会红的任务 ===
  ✗ [1/1] hard_assert  (0.0s)
      数值不一致：期望 999，实际 87

=== [2/2] TC-2 无辜的任务 ===
  ✓ [1/1] ok_step  (0.0s)
[结果] 1 passed, 1 failed
"""


def _mk(output, rc=0):
    return FlowResult("sample.yaml", rc, output)


@allure.feature("UI 驱动层-解析器")
class TestFlowResultParser:
    @allure.title("任务块/步骤/汇总正确解析")
    def test_task_blocks_parsed(self):
        r = _mk(SAMPLE_PASS, rc=1)  # 有 ✗ → run-yaml 退出码 1
        assert r.summary == (2, 1, 0)
        assert [t["title"] for t in r.tasks] == ["TC-A 卡片校验", "TC-B 单行提取", "TC-C AI 判断"]
        assert not r.all_passed  # 有失败任务

    @allure.title("多行 JSON 提取段解析（含无缩进收尾括号与内嵌引号）")
    def test_multiline_json_extraction(self):
        r = _mk(SAMPLE_PASS, rc=1)
        cards = r.task("卡片校验")["results"]
        assert cards["cards_present"] == "三张卡片齐全"
        assert "22" in cards["cards_text"]

    @allure.title("单行 JSON 提取段解析")
    def test_singleline_json_extraction(self):
        r = _mk(SAMPLE_PASS, rc=1)
        assert r.task("单行提取")["results"]["expect_total"] == "一致：22"

    @allure.title("✗ 归因给正确的任务（不污染前后任务）")
    def test_failure_attribution(self):
        r = _mk(SAMPLE_FAIL_ATTRIBUTION, rc=1)
        assert r.task("TC-1")["failed"] is True
        assert r.task("TC-2")["failed"] is False
        assert r.task("TC-1")["results"].get("hard_assert") is None  # 失败步无提取

    @allure.title("全绿场景：all_passed=True")
    def test_all_green(self):
        r = _mk(SAMPLE_FAIL_ATTRIBUTION.replace("✗ [1/1] hard_assert", "✓ [1/1] hard_assert")
                .replace("      数值不一致：期望 999，实际 87\n", "")
                .replace("[结果] 1 passed, 1 failed", "[结果] 2 passed, 0 failed"), rc=0)
        assert r.all_passed is True
        assert r.summary == (2, 0, 0)

    @allure.title("关键字查不到任务时抛 KeyError（防用例静默取错块）")
    def test_task_keyword_miss(self):
        r = _mk(SAMPLE_PASS, rc=1)
        with pytest.raises(KeyError):
            r.task("不存在的任务XYZ")

    @allure.title("空输出不崩（防御性）")
    def test_empty_output(self):
        r = _mk("", rc=0)
        assert r.tasks == []
        assert r.summary is None


# ---------------------------------------------------------------------------
# flow YAML 静态校验：不跑浏览器、不花模型调用，就能拦住"流程文件写坏"
# 的整类事故（历史上真出现过：aiQuery 值含 {"count": 数字} 被 js-yaml
# 当 flow mapping 解析、页面 url 忘写、步骤键名拼错等）。
# ---------------------------------------------------------------------------
import glob
import os

import yaml as _yaml

FLOWS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "midscene", "flows"
)
# 与 run-yaml.js 的 META_KEYS 保持一致（这些是"配置"不是"指令"）
META_KEYS = {"name", "continueOnError", "errorMessage", "timeout",
             "cacheable", "deepLocate", "deepThink", "context"}


@allure.feature("UI 驱动层-flow 静态校验")
class TestFlowYamlFiles:
    @allure.title("全部 flow YAML 可解析且结构合法（零依赖，CI 门禁同款）")
    def test_all_flows_parse_and_structured(self):
        flows = sorted(glob.glob(os.path.join(FLOWS_DIR, "*.yaml")))
        assert flows, f"flows 目录为空：{FLOWS_DIR}"

        for fp in flows:
            name = os.path.basename(fp)
            with open(fp, encoding="utf-8") as f:
                try:
                    data = _yaml.safe_load(f)
                except _yaml.YAMLError as e:
                    raise AssertionError(f"{name}: YAML 语法错误（js-yaml 同款解析）：{e}")

            assert isinstance(data, dict), f"{name}: 顶层必须是映射（page/tasks）"
            assert (data.get("page") or {}).get("url"), \
                f"{name}: 缺 page.url（深链接是这个体系稳定的第一道保险）"
            tasks = data.get("tasks")
            assert isinstance(tasks, list) and tasks, f"{name}: 缺 tasks 列表"

            for ti, task in enumerate(tasks, 1):
                assert isinstance(task, dict), f"{name}: tasks[{ti}] 不是映射"
                assert task.get("name"), f"{name}: tasks[{ti}] 缺 name（报告里要靠它定位）"
                flow = task.get("flow")
                assert isinstance(flow, list) and flow, f"{name}: tasks[{ti}] 缺 flow 步骤"
                for si, item in enumerate(flow, 1):
                    cmds = [k for k in item if k not in META_KEYS]
                    assert len(cmds) == 1, (
                        f"{name}: tasks[{ti}].flow[{si}] 必须恰有一个指令键，"
                        f"实际={cmds or '空'}（多写/拼错键名都会让 run-yaml 报 "
                        f"'这一步没有可识别的指令'）"
                    )
