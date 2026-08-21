"""
验证码识别工具（ddddocr）

- ddddocr 是本地离线 OCR，无需联网、无需调第三方 API，适合测试环境验证码自动识别。
- 若未安装 ddddocr，recognize_captcha 会抛出清晰提示，引导用户本地安装。
"""
try:
    import ddddocr
except ImportError:
    ddddocr = None


def recognize_captcha(image_bytes: bytes) -> str:
    """
    识别验证码图片字节（PNG/JPG），返回识别出的字符串。

    :param image_bytes: 图片二进制，如 Playwright element.screenshot() 的返回值
    :return: 识别出的验证码文本（已 strip）
    """
    if ddddocr is None:
        raise RuntimeError(
            "未安装 ddddocr，无法自动识别验证码。\n"
            "请在本机项目 venv 中执行：\n"
            "    ./venv/bin/pip install ddddocr\n"
            "（仅 UI 登录用例依赖，接口自动化不需要）"
        )
    ocr = ddddocr.DdddOcr(show_ad=False)
    return ocr.classification(image_bytes).strip()
