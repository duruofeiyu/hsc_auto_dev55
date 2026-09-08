"""
55 开发环境 - 资产管理 - 网站测绘任务工具层
API 模块：/asset/web-map
来源：hsc_auto_dev123/asset_management/discovery/utils_web_map.py + apis.md 第 10 节

说明：
- 复用 55 的 base.request_wrapper（自动注入 x-sign 签名，不再硬编码）
- 修改接口需传全部字段，推荐先 get_web_map_detail 再覆盖
- scheduleType 非 IMMEDIATE 时需传 scheduleConfig（JSON 字符串）
"""
import sys
import os
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

WEB_MAP_BASE = f"{BASE_URL}/asset/web-map"


def build_web_map_payload(
    task_name="网站测绘-自动化模板",
    scan_target="https://192.168.124.55",
    schedule_type="IMMEDIATE",
    task_status="ENABLED",
    sync_to_asset=True,
    scan_range=3,
    scan_depth=5,
    crawl_strategy="BFS",
    scan_level=0,
    max_crawl_duration=10,
    concurrency=20,
    rate_limit=300,
    connect_timeout=15,
    retries=2,
    max_response_size_mb=1024,
    enable_js=True,
    enable_jsluice=False,
    enable_form_filling=False,
    form_fill_values="[]",
    user_agent="",
    custom_headers="[]",
    enable_auth_scan=False,
    schedule_config=None,
):
    """构建网站测绘任务 payload（字段与 apis.md 第 10.1 节对齐）"""
    payload = {
        "taskName": task_name,
        "scanTarget": scan_target,
        "scheduleType": schedule_type,
        "taskStatus": task_status,
        "syncToAsset": sync_to_asset,
        "scanRange": scan_range,
        "scanDepth": scan_depth,
        "crawlStrategy": crawl_strategy,
        "scanLevel": scan_level,
        "ignoreQueryParams": True,
        "filterSimilarUrls": True,
        "maxCrawlDuration": max_crawl_duration,
        "concurrency": concurrency,
        "rateLimit": rate_limit,
        "connectTimeout": connect_timeout,
        "retries": retries,
        "maxResponseSizeMb": max_response_size_mb,
        "enableJs": enable_js,
        "enableJsluice": enable_jsluice,
        "enableFormFilling": enable_form_filling,
        "formFillValues": form_fill_values,
        "userAgent": user_agent,
        "customHeaders": custom_headers,
        "enableAuthScan": enable_auth_scan,
        "excludeExtensions": (
            "jpg,jpeg,gif,png,bmp,ico,ani,zip,gz,tar,rar,doc,docx,xls,xlsx,"
            "ppt,pptx,vsd,asf,avi,wm,wmp,wmv,ram,rm,rmvb,rp,rpm,rt,smil,scm,"
            "dat,m1v,m2v,m2p,m2ts,mp2v,mpe,mpeg,mpeg1,mpeg2,mpg,mpv2,pss,pva,"
            "tp,tpr,ts,m4b,m4r,m4p,m4v,mp4,mpeg4,3g2,3gp,3gp2,3gpp,mov,qt,"
            "flv,f4v,swf,hlv,ifo,vob,amv,csf,divx,evo,mkv,mod,pmp,vp6,bik,"
            "mts,xlmv,ogm,ogv,ogx,dvd,aac,ac3,acc,aiff,amr,ape,au,cda,dts,"
            "flac,m1a,m2a,m4a,mka,mp2,mp3,mpa,mpc,ra,tta,wav,wma,wv,mid,midi,"
            "ogg,oga"
        ),
        "excludeFilename": "del,delete,sigoff,sigout,logout,logoff,exit",
        "includePaths": "",
        "excludePaths": "",
        "statusCodeFilterMode": "404,410,409,412,414,500,502,503,504,505,506,507,509,510",
    }
    if schedule_config is not None:
        payload["scheduleConfig"] = schedule_config
    return payload


def query_web_map_tasks(payload=None):
    """查询网站测绘任务列表：POST /asset/web-map/list"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
            "keyword": "", "keywordFields": ["taskNo", "taskName", "createBy"],
        }
    return request_wrapper("post", f"{WEB_MAP_BASE}/list", msg="查询网站测绘任务列表",
                           json=payload, headers=get_headers())


def create_web_map_task(payload):
    """创建网站测绘任务：POST /asset/web-map"""
    return request_wrapper("post", WEB_MAP_BASE, msg="创建网站测绘任务",
                           json=payload, headers=get_headers())


def update_web_map_task(task_id, payload):
    """修改网站测绘任务：PUT /asset/web-map/{task_id}（需传完整 payload）"""
    return request_wrapper("put", f"{WEB_MAP_BASE}/{task_id}", msg="修改网站测绘任务",
                           json=payload, headers=get_headers())


def delete_web_map_task(task_id):
    """删除网站测绘任务：DELETE /asset/web-map/{task_id}"""
    return request_wrapper("delete", f"{WEB_MAP_BASE}/{task_id}", msg="删除网站测绘任务",
                           headers=get_headers())


def get_web_map_detail(task_id):
    """获取网站测绘任务详情：GET /asset/web-map/{task_id}?_t={ts}"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEB_MAP_BASE}/{task_id}", msg="获取网站测绘任务详情",
                           params=params, headers=get_headers())


def get_web_map_execution(task_id):
    """获取网站测绘任务执行状态：GET /asset/web-map/{task_id}/execution?_t={ts}"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEB_MAP_BASE}/{task_id}/execution", msg="获取网站测绘执行状态",
                           params=params, headers=get_headers())


def get_web_map_result(task_id):
    """获取网站测绘结果页：GET /asset/web-map/result/{task_id}?_t={ts}"""
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEB_MAP_BASE}/result/{task_id}", msg="获取网站测绘结果",
                           params=params, headers=get_headers())


def build_web_map_payload_from_detail(detail):
    """从详情反构造完整修改 payload"""
    if not isinstance(detail, dict):
        return build_web_map_payload()
    payload = build_web_map_payload()
    for k in payload.keys():
        if k in detail:
            payload[k] = detail[k]
    return payload


def get_web_map_list_from_response(resp):
    """从查询响应中提取任务列表（容错）"""
    try:
        data = resp.json()
        if data.get("success"):
            return data.get("result", {}).get("list", [])
    except Exception:
        pass
    return []


def build_schedule_config_once(start_time=None):
    """构造一次性定时任务的 scheduleConfig（JSON 字符串）"""
    if start_time is None:
        start_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    return json.dumps({"startTime": start_time}, ensure_ascii=False)


def build_schedule_config_periodic(frequency="WEEKLY", day_of_week=1, day_of_month=1, hour=10, minute=52):
    """构造周期任务的 scheduleConfig（JSON 字符串）"""
    return json.dumps({
        "frequency": frequency,
        "dayOfWeek": day_of_week,
        "dayOfMonth": day_of_month,
        "hour": hour,
        "minute": minute,
    }, ensure_ascii=False)
