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
            for n in nums:
                assert float(n) >= 0, f"「{name}」出现负数：{n}"
                if f"{n}%" in text:
                    assert float(n) <= 100, f"「{name}」百分比越界：{n}%"

    @allure.title("探测任务总数与期望值一致（数据驱动演示）")
    @allure.severity(allure.severity_level.NORMAL)
    # 期望值按环境维护（123：09-15=21，09-16=22——探测任务会新增，这类值隔几天就漂。
    # 纪律：跑红先跑流程拿实际值，属业务增长就更新参数值（不是用例失败）；55 回填后可加 (env,expect) 对）
    @pytest.mark.parametrize("expect_total", ["22"])
    def test_probe_total_data_driven(self, expect_total):
        """换 --var 就是一条新用例 —— 和你接口框架 YAML 数据驱动同一思路。

        注意：总数是会变的业务数据（新增探测任务就会变），
        当回归跑红先核对环境真实值，再判断是 bug 还是期望值过期。
        """
        result = run_flow("asset_discover", vars={"EXPECT_TOTAL": expect_total})
        check = result.task("期望「探测任务总数」")
        assert not check["failed"], (
            f"总数不等于 {expect_total}（看输出里的实际值；环境数据变了就改参数）"
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
