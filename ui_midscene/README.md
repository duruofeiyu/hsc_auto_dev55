# HSC UI 自动化 PoC —— midscene.js

用**视觉驱动**的自然语言写 UI 自动化，免维护 CSS 选择器。和现有
`pytest` 接口/UI 框架**并存互补**，不互相替代：pytest 守关键路径硬断言，
midscene 用来快速铺广度、对付"其它交互逻辑"。

## 为什么要用它（解决你的痛点）
原来手写 Page Object，每个按钮都要猜 `.el-xxx` 选择器，猜错就要
"你跑→我改"往返。midscene 直接看截图、用中文指令操作：

```js
await ai('在处置面板中选择「派单」方式，填写必要信息后点击提交');
await aiAssert('页面提示处置/派单成功，且没有报错');
```

新增一个交互 = 加一句中文，**不需要任何选择器**。

## 快速开始
```bash
cd ui_midscene
npm install
cp .env.example .env          # 填 API key，或切本地模型（见下方合规说明）
npx playwright install chromium   # 首次需要，拉浏览器内核
npm test                     # 有头跑，你能看到 AI 操作
```

前置：确保 pytest 框架的登录态已生成（跑过 pytest UI 用例就会在
`../ui_tests/.auth/` 下产出 `state_55_common_admin.json` 等文件）。本 PoC
直接复用它，**无需重新登录**。切换 123 环境时设 `HSC_ENV=123` 即可自动
改用 `state_123_common_admin.json`。

## 合规说明（重要）
HSC 是**医院安全驾驶舱**，你正在做 **CCRC 年审**。把界面截图传公有云
LLM = 敏感数据出境，在审计里是实锤风险。因此：

- **demo 阶段**可用方式一（阿里云 Qwen-VL）快速验证效果；
- **正式用于 HSC**请切方式二：本地起一个 Qwen-VL（vLLM / ollama），
  `OPENAI_BASE_URL` 指向 `localhost`，数据零出境。

## 文件说明
- `playwright.config.js`：复用 pytest 的 storage_state 登录态
- `tests/disposal.spec.js`：处置面板派单 / 处理结论提交复核 两条样例
- `.env.example`：云模型 / 本地模型两种配置
