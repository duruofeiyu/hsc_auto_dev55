"""资产管理 → 资产发现页（/assetDiscover）—— Python 侧 UI 用例。

对应手工用例：TC-HSC55-SCAN-002 / 003 / 004
流程步骤在 flows/asset_discover.yaml（YAML 描述"点哪几下"），
本文件负责：数据驱动、断言、Allure 装饰 —— 全部 Python。

跑法：
    cd ~/hsc_auto
    ./venv/bin/pytest ui/py/test_asset_discover.py -v
    HSC_ENV=55 ./venv/bin/pytest ui/py -v        # 切环境
"""
import re

import allure
import pytest

from ui.py.ai_flow import run_flow

# 本页「专有」卡片名 —— 断言钉死在正确页面，落到资产概览等别页立刻红（防假绿）
REQUIRED_CARDS = ["探测任务总数", "任务执行概览", "扫描活跃度"]


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("资产管理-资产发现")
class TestAssetDiscoverCards:
    """TC-HSC55-SCAN-002：统计卡片数据显示"""

    @allure.title("统计卡片三张齐全且数值为非负数字")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_cards_present_and_numeric(self):
        result = run_flow("asset_discover")

        cards_task = result.task("统计卡片")
        assert not cards_task["failed"], f"卡片校验任务失败：{cards_task['steps']}"

        # YAML 里 javascript 步骤把三张卡片文本提取进 results.cards_text
        cards_text = cards_task["results"].get("cards_text")
        assert cards_text, f"没提取到卡片文本，results={cards_task['results']}"
        if isinstance(cards_text, str):
            import json as _json
            cards_text = _json.loads(cards_text)

        for name in REQUIRED_CARDS:
            text = cards_text.get(name, "")
            assert text, f"缺少「{name}」卡片（当前页可能不是资产发现页）"
            nums = re.findall(r"-?\d+(?:\.\d+)?", text)
            assert nums, f"「{name}」读不到数字：{text}"
            # 2026-09-16 实测修正：卡片含"较昨日 -12"这类环比值，带负号是合法业务数据
            # （原"所有数字≥0"断言过粗，数据下降日会误报）。规则改为：
            # ① 至少要有一个非负数值（计数本体）；② 百分比不得超过 100%。
            positives = [n for n in nums if not n.startswith("-")]
            assert positives, f"「{name}」没有任何非负数值：{text}"
            for n in positives:
                if f"{n}%" in text:
                    assert float(n) <= 100, f"「{name}」百分比越界：{n}%"

    @allure.title("探测任务总数：UI 卡片 == 接口基线（跨层一致性）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_probe_total_matches_api(self):
        """2026-09-16 优化：不再钉死魔数（两天漂两次 21→22），改为与接口基线交叉验证。

        口径：卡片值 = /asset/probe/list 的 total + /asset/web-map/list 的 total
        （实测 14+8=22，页面把探测与网站测绘两类任务合计展示）。
        好处：数据怎么涨都不误报；不一致本身就是信号（统计口径变了 / 前后端不同步）。
        """
        import json as _json
        import re as _re

        from ui.py.api_baseline import asset_discover_task_total

        result = run_flow("asset_discover")
        cards = result.task("统计卡片")["results"]["cards_text"]
        cards = _json.loads(cards) if isinstance(cards, str) else cards
        m = _re.search(r"(\d+)", cards.get("探测任务总数", ""))
        assert m, f"卡片读不到数字：{cards.get('探测任务总数')!r}"
        ui_total = int(m.group(1))

        api_total = asset_discover_task_total()
        assert ui_total == api_total, (
            f"UI 卡片({ui_total}) 与接口基线({api_total}) 不一致："
            "要么页面统计口径变了，要么前后端数据不同步（都是值得查的信号）"
        )


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("资产管理-资产发现")
class TestAssetDiscoverAI:
    """AI 旁证层：同一页面用 AI 读一遍，和 DOM 读数交叉验证"""

    @allure.title("AI 版卡片完整性（旁证，非唯一依据）")
    @allure.severity(allure.severity_level.MINOR)
    def test_ai_cross_check(self):
        result = run_flow("asset_discover")
        ai_task = result.task("AI 版")
        # AI 断言允许偶发波动：这里失败只记录不阻断（与 JS 侧"降级观察"策略一致）
        if ai_task["failed"]:
            pytest.skip(f"AI 旁证波动（已知不稳定，非阻塞）：{ai_task['steps']}")
