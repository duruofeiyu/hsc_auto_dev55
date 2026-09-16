"""
验证码识别工具（2026-09-15 升级：视觉大模型优先，ddddocr 兜底）

背景（123 环境实测）：ddddocr 对弧排+扭曲+干扰线的验证码不稳定——
真值 URXH 它能认成 uRXH（字形对、大小写错），另一张直接认成 GNGP（完全错），
导致登录 12 连败。视觉大模型（qwen3.8-max，公司 token-plan 网关，
配置复用 ui/midscene/.env）读这种图 + 保大小写，准确率完全不同档次。

策略：LLM 优先；LLM 不可用/输出不合法 → 回退 ddddocr（55 环境老链路仍可用）。
识别函数每次登录刷新才调用（几秒一次），token 成本可忽略。
"""
import base64
import os
import re

try:
    import ddddocr
except ImportError:
    ddddocr = None

CAPTCHA_PATTERN = re.compile(r"^[A-Za-z0-9]{4,5}$")

# ui/midscene/.env：模型四件套（与 Midscene 同一配置源，改一处两边生效）
_MIDSCENE_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "midscene", ".env"
)


def _load_midscene_env():
    cfg = {}
    try:
        with open(_MIDSCENE_ENV, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip().strip("\"'")
    except OSError:
        pass
    # 环境变量优先于文件
    for k in ("MIDSCENE_MODEL_BASE_URL", "MIDSCENE_MODEL_API_KEY", "MIDSCENE_MODEL_NAME"):
        if os.getenv(k):
            cfg[k] = os.environ[k]
    return cfg


def recognize_captcha_llm(image_bytes: bytes, timeout: int = 30) -> str:
    """用视觉大模型识别验证码，保留原始大小写。失败/不可用返回 ''。"""
    cfg = _load_midscene_env()
    base, key, model = (
        cfg.get("MIDSCENE_MODEL_BASE_URL"),
        cfg.get("MIDSCENE_MODEL_API_KEY"),
        cfg.get("MIDSCENE_MODEL_NAME"),
    )
    if not (base and key and model):
        return ""
    try:
        import requests

        resp = requests.post(
            f"{base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "max_tokens": 64,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": (
                            "这是登录验证码图片，包含 4-5 位字母数字。"
                            "只输出图片中的字符本身，严格保留大小写（大写就输出大写），"
                            "不要标点、空格、解释。若某字符大小写难辨，优先按字形高度判断。"
                        )},
                        {"type": "image_url", "image_url": {"url": (
                            "data:image/jpeg;base64,"
                            + base64.b64encode(image_bytes).decode()
                        )}},
                    ],
                }],
            },
            timeout=timeout,
            verify=False,  # 内网网关自签场景兜底；公网证书同样可过
        )
        data = resp.json()
        text = (data["choices"][0]["message"]["content"] or "").strip()
        m = re.search(r"[A-Za-z0-9]{4,5}", text)
        return m.group(0) if m else ""
    except Exception:
        return ""


def recognize_captcha(image_bytes: bytes) -> str:
    """
    识别验证码图片字节（PNG/JPG 均可），返回识别出的字符串。
    优先视觉大模型（保大小写、抗扭曲），不可用时回退 ddddocr。
    """
    llm = recognize_captcha_llm(image_bytes)
    if llm and CAPTCHA_PATTERN.fullmatch(llm):
        return llm

    if ddddocr is None:
        if not llm:
            raise RuntimeError(
                "验证码识别双通道均不可用：LLM 无结果且未安装 ddddocr。\n"
                "    ./venv/bin/pip install ddddocr"
            )
        return llm
    ocr = ddddocr.DdddOcr(show_ad=False)
    return ocr.classification(image_bytes).strip()
