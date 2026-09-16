// 最小化连通性检测：只验证 .env 里的模型配置 + key 是否可用
// 用法：node check_model.mjs
// 不碰浏览器，3 秒出结果。key 有问题会立刻报 401，模型名有问题会报模型不存在。

import 'dotenv/config';

const baseUrl = (process.env.MIDSCENE_MODEL_BASE_URL || process.env.OPENAI_BASE_URL || '').replace(/\/+$/, '');
const apiKey = process.env.MIDSCENE_MODEL_API_KEY || process.env.OPENAI_API_KEY || '';
const model = process.env.MIDSCENE_MODEL_NAME || '';
const family = process.env.MIDSCENE_MODEL_FAMILY || '(未设置)';

console.log('=== 当前配置 ===');
console.log('BASE_URL :', baseUrl || '(空!)');
console.log('MODEL    :', model || '(空!)');
console.log('FAMILY   :', family);
console.log('API_KEY  :', apiKey
  ? `${apiKey.slice(0, 8)}...${apiKey.slice(-6)}  (长度 ${apiKey.length})`
  : '(空!)');

if (!baseUrl || !apiKey || !model) {
  console.error('\n❌ 配置不完整，请先补全 .env');
  process.exit(1);
}
if (apiKey.includes('PASTE_YOUR') || apiKey.includes('__')) {
  console.error('\n❌ API_KEY 还是占位符，没有替换成真实 key！这是 401 的直接原因。');
  console.error('   去 https://open.bigmodel.cn/ → API Keys 复制真 key,替换 .env 第 10 行。');
  process.exit(1);
}

// 用一张 64x64 的蓝色图片做视觉输入，验证多模态接口。
// （曾用 1x1，被 qwen3.8-max 以「边长须 >10px」拒绝——1x1 对部分模型是非法参数，
//   64x64 在各模型限制之内；真实用例发送的是整页截图，远大于此，不受影响。）
const tinyPng =
  'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAeElEQVR4nO3PUQkAIBTAwJfEzDbWEH4cwmABbrP2+brhgga0oAEtaEALGtCCBrSgAS1oQAsa0IIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAsa0IIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAsa0IIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAseuwhu0YdVjn6RAAAAAElFTkSuQmCC';

console.log('\n=== 发起一次最小视觉请求 ===');
try {
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: '这张图是什么颜色？只回答颜色词语。' },
            { type: 'image_url', image_url: { url: `data:image/png;base64,${tinyPng}` } },
          ],
        },
      ],
      max_tokens: 20,
    }),
  });

  const body = await res.text();
  console.log('HTTP', res.status);
  if (res.ok) {
    console.log('✅ 模型与 key 均可用！响应片段：', body.slice(0, 200));
  } else {
    console.error('❌ 调用失败：', body.slice(0, 400));
    if (body.includes('401') || body.includes('invalid_api_key') || body.includes('令牌')) {
      console.error('\n👉 结论：key 无效/过期/协议入口不对。核对 key 与 BASE_URL 是否同一平台。');
    } else if (body.includes('invalid_parameter_error') && /image|宽度|长度|length and width/i.test(body)) {
      console.error('\n👉 结论：模型与 key 已连通（能收到模型级参数校验说明鉴权已过），只是探针图片不满足该模型的尺寸限制 —— 请换更大的测试图。');
    } else if (body.includes('不存在') || /model.*(not found|does not exist)/i.test(body)) {
      console.error('\n👉 结论：模型名 `' + model + '` 在该平台不存在，核对模型列表里的拼写。');
    }
  }
} catch (e) {
  console.error('❌ 网络层错误：', e.message);
  console.error('   检查网络能否访问', baseUrl);
}
