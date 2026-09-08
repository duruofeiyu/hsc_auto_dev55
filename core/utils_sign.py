"""
55 开发环境 - 系统管理 - x-sign 签名工具
复刻 HSC 前端 axios 拦截器中的签名算法（index-*.js / requestInterceptors）：

    X-Sign = MD5( JSON.stringify( sortAsc(merge(query, params, data)) 剔除 _t ) + SALT ).toUpperCase()

其中：
  - query / params / data 合并后按 key 升序排序
  - 数字/布尔值会先规范化为字符串（复刻前端 mergeObject 的 myIsNaN/boolean 处理）
  - _t（时间戳防重放参数）不计入签名
  - SALT 为前端写死的固定盐值

注意：签名计算用的对象会做规范化（数字->字符串等），但实际发送的请求体不受影响（保持原始类型）。
该算法于 2026-08-27 通过真实抓包样本验证：MD5("{}"+SALT).upper() == 样本 x-sign。
"""
import hashlib
import json

# 前端写死的签名盐值（index-*.js 中 lI 常量）
SIGN_SALT = "dd05f1c54d63749eda95f9fa6d49v442a"


def _is_real_number(v):
    # 复刻 JS: typeof t === "number" && !isNaN(t)
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _norm_value(v):
    if _is_real_number(v):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def _parse_query_string(url):
    """复刻 parseQueryString：解析 url 上的 query 参数 + path-variable"""
    result = {}
    q_index = url.find("?")
    path_part = url[:q_index] if q_index != -1 else url
    if "/" in path_part:
        tail = path_part[path_part.rfind("/") + 1:]
        if "," in tail:
            # 复刻：含逗号的最后一段视为 path variable
            result["x-path-variable"] = tail
    if q_index != -1:
        query = url[q_index + 1:]
        for pair in query.split("&"):
            if not pair:
                continue
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k] = v
            else:
                result[pair] = ""
    return result


def _merge(base, extra):
    """复刻 mergeObject：把 extra 合并进 base，嵌套 dict 保序、number/bool 规范化为字符串"""
    if not isinstance(extra, dict):
        return base
    for k, v in extra.items():
        if _is_real_number(v):
            v = str(v)
        elif isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items()}  # 保序浅拷贝
        base[k] = v
    return base


def compute_sign(url, params=None, data=None):
    """
    计算 HSC 接口 x-sign 签名
    :param url: 请求 URL（可含 query）
    :param params: GET query 参数 dict（axios params）
    :param data: 请求体 dict（axios data / json）
    :return: 32 位大写 hex 字符串
    """
    obj = _parse_query_string(url)
    obj = _merge(obj, params)
    if data:
        obj = _merge(obj, data)
    # sortAsc：按 key 升序重建
    sorted_obj = {k: obj[k] for k in sorted(obj.keys())}
    # 剔除 _t（时间戳防重放参数不计入签名）
    sorted_obj.pop("_t", None)
    raw = json.dumps(sorted_obj, ensure_ascii=False, separators=(",", ":"))
    return hashlib.md5((raw + SIGN_SALT).encode("utf-8")).hexdigest().upper()
