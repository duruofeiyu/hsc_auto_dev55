// ============================================================================
// 参数化用例模板：一条流程 × N 种测试情况
// ============================================================================
// 这是 templates/ 下的参考模板，不参与 npm test（playwright.config.js 的
// testDir 只扫 ./tests）。看懂后 cp 到 tests/ 下、按实际页面核对 TODO，
// 就会被 npm test 跑到。
//
// 【它解决什么问题】
//   Recorder 录出来的 = 一条固定路径 = 只覆盖 1 种情况。
//   但一个「测试点」（例如：新建任务）通常带 4~6 种「测试情况」
//   （正常 / 必填留空 / 仅空格 / 超长 / 重复 / 特殊字符）。
//   靠录 6 次去覆盖是维护灾难 —— 正确做法：录 1 次拿路径，然后参数化展开。
//
// 【midscene 到底省了什么、没省什么】
//   省了「选择器」：以前写 page.click('#app .el-table__row:nth-child(1) .btn')，
//   现在写 await aiTap('第一条记录操作列里的「处置」按钮')。页面改版不烂。
//   没省「用例设计」：前置条件、测试数据、预期结果、参数化、断言 —— 还是你写。
//   所以「UI 自动化还是要写用例」这个判断是对的，只是写的东西变了。
//
// 【最大的坑：假绿】
//   aiTap / ai 这类动作「执行完」就返回，不等结果、不校验效果，报告照样打勾。
//   每条用例必须有硬断言，且断言要落在能持久化的东西上（刷新后还在、DOM 里
//   读得到），不能只信一句 toast。下面的正向用例演示了「刷新后回查」。
//
// 【数据准备建议】
//   能用 pytest 接口框架造的前置数据，就别用 UI 摆。
//   接口造数（秒级、可清理）+ UI 只验交互（薄薄一层）是最省时的组合。
//   用完的测试数据记得清理，否则污染环境、影响后面用例。
// ============================================================================

import { test, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';

const aiTest = test.extend(PlaywrightAiFixture());

// TODO: 换成你实际的「资产发现」深链接（深链接直达可以跳过菜单点击这个最不稳的环节）
const PAGE_URL = process.env.HSC_ASSET_URL || '/assetDiscovery';

// 稳定的唯一后缀：跑多少次都不会和上一次撞名
const STAMP = Date.now();

// ---------------------------------------------------------------------------
// 数据表 = 这个「测试点」的所有「测试情况」
// 每行 = 一条用例，只有 input / expect 不同，流程完全相同
// ---------------------------------------------------------------------------
const CASES = [
  {
    id: 'TC-ASSET-001',
    title: '新建任务-正常新增（正向）',
    input: { name: `AUTO_任务_${STAMP}` },
    expect: { kind: 'success' },
  },
  {
    id: 'TC-ASSET-002',
    title: '新建任务-任务名称为空（必填校验）',
    input: { name: '' },
    expect: { kind: 'validation', hint: '请输入' },
  },
  {
    id: 'TC-ASSET-003',
    title: '新建任务-名称仅输入空格（边界）',
    input: { name: '   ' },
    expect: { kind: 'validation', hint: '请输入' },
  },
  {
    id: 'TC-ASSET-004',
    title: '新建任务-名称超长（边界）',
    input: { name: 'A'.repeat(100) },
    // 超长是「截断」还是「报错」取决于实现，先记录不硬判，观察一轮再定预期
    expect: { kind: 'observe' },
  },
  {
    id: 'TC-ASSET-005',
    title: '新建任务-名称含特殊字符（异常）',
    input: { name: `<script>x</script>_${STAMP}` },
    expect: { kind: 'observe' },
  },
];

// ---------------------------------------------------------------------------
// 公共流程：Recorder 录出来的部分在这里，只把「会变的值」抽成参数
// ---------------------------------------------------------------------------
async function openNewTaskDialog(page, ai) {
  await page.goto(PAGE_URL);
  await ai('等待资产发现的任务列表加载完成');
  await aiTap('页面上的「新建任务」按钮');
  await aiWaitFor('新建任务的对话框已经弹出');
}

// ---------------------------------------------------------------------------
// 展开成 N 条用例
// ---------------------------------------------------------------------------
for (const c of CASES) {
  aiTest(`${c.id} ${c.title}`, async ({ page, ai, aiTap, aiInput, aiAssert, aiQuery }) => {
    // ---- 前置 ----
    await openNewTaskDialog(page, ai);

    // ---- 步骤：值从参数来，不写死进提示词（避免模型自己编数据）----
    if (c.input.name) {
      await aiInput('对话框中的「任务名称」输入框', { value: c.input.name });
    }
    await aiTap('对话框底部的「确定」按钮');

    // ---- 断言：Recorder 不会给你写这段，必须自己补 ----
    if (c.expect.kind === 'success') {
      // 第一层：UI 即时反馈
      await aiAssert('页面出现了保存成功的提示，且新建对话框已经关闭');

      // 第二层（防假绿）：刷新后回列表复核，不轻信 toast
      await page.reload();
      await ai('等待资产发现的任务列表加载完成');
      const r = await aiQuery(
        `任务列表中是否存在名称为「${c.input.name}」的记录，只返回 {"found": true} 或 {"found": false}`
      );
      expect(r.found, `刷新后列表里应当能找到「${c.input.name}」`).toBe(true);

      // TODO: 清理测试数据（接口删或 UI 删），避免污染环境
    } else if (c.expect.kind === 'validation') {
      // 负向用例：既要有校验提示，也要确认「没真的创建成功」
      await aiAssert(`对话框内出现了必填校验提示，例如包含「${c.expect.hint}」字样`);
      await aiAssert('新建任务对话框仍然停留在页面上，没有被关闭');
    } else {
      // observe：先只记录现象，不判通过与否，人工看报告后再补准确预期
      await aiAssert('页面给出了某种明确反馈（成功提示或错误提示均可），没有卡死无响应');
    }
  });
}

// ---------------------------------------------------------------------------
// 想加测试点？照着复制一段，改数据表即可。
// 想加模块？换掉 PAGE_URL 和两三条中文指令即可，无需维护任何选择器。
//
// 什么时候用 YAML（Recorder 直接产物）、什么时候用这种 JS：
//   · 一条固定路径、不需要参数化、给非开发同学看  -> YAML 够用
//   · 一个测试点要覆盖多种情况、要写断言/清理/取数 -> 用 JS（本文件）
// ---------------------------------------------------------------------------
