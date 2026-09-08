"""
55 开发环境 - 脆弱性管理 - Web 漏洞扫描任务工具层
API 模块：/vuln/web-scan
来源：hsc_auto_dev123/vuln_management/web_vuln/utils_vuln_scan_web.py（字段对齐 apis.md §11.2）

说明：
- 复用 55 base.request_wrapper（自动注入 x-sign）
- 已知缺陷：PUT /vuln/web-scan/{id} 对任何字段修改均返回 500（apis.md §11.2.3），update 用例需 xfail
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from config import BASE_URL
from core.base import request_wrapper, assert_success, assert_business_fail, get_headers

WEB_SCAN_BASE = f"{BASE_URL}/vuln/web-scan"

KEYWORD_FIELDS = ["taskNo", "taskName", "createBy"]

_EXCLUDE_EXTENSIONS = ("jpg,jpeg,gif,png,bmp,ico,ani,zip,gz,tar,rar,doc,docx,xls,xlsx,ppt,pptx,vsd,"
                       "asf,avi,wm,wmp,wmv,ram,rm,rmvb,rp,rpm,rt,smil,scm,dat,m1v,m2v,m2p,m2ts,mp2v,"
                       "mpe,mpeg,mpeg1,mpeg2,mpg,mpv2,pss,pva,tp,tpr,ts,m4b,m4r,m4p,m4v,mp4,mpeg4,"
                       "3g2,3gp,3gp2,3gpp,mov,qt,flv,f4v,swf,hlv,ifo,vob,amv,csf,divx,evo,mkv,mod,"
                       "pmp,vp6,bik,mts,xlmv,ogm,ogv,ogx,dvd,aac,ac3,acc,aiff,amr,ape,au,cda,dts,"
                       "flac,m1a,m2a,m4a,mka,mp2,mp3,mpa,mpc,ra,tta,wav,wma,wv,mid,midi,ogg,oga")
_EXCLUDE_FILENAME = "del,delete,sigoff,sigout,logout,logoff,exit"
_STATUS_CODE_FILTER = "404,410,409,412,414,500,502,503,504,505,506,507,509,510"


def build_web_scan_payload(
    task_name="自动化Web漏洞扫描",
    scan_target="https://192.168.112.123",
    schedule_type="IMMEDIATE",
    task_status="ENABLED",
    sync_to_asset=True,
    scan_range=3,
    scan_depth=5,
    crawl_strategy="BFS",
    max_crawl_duration=10,
    concurrency=20,
    rate_limit=300,
    user_agent="",
    custom_headers="[]",
    connect_timeout=15,
    max_response_size_mb=1024,
    retries=2,
    enable_js=True,
    enable_jsluice=False,
    exclude_extensions=None,
    exclude_filename=None,
    include_paths="",
    exclude_paths="",
    ignore_query_params=True,
    filter_similar_urls=True,
    status_code_filter_mode=None,
    enable_form_filling=False,
    form_fill_values="[]",
    scan_level=2,
    enable_auth_scan=False,
    template_id=36,
    template_concurrency=25,
    bulk_size=50,
    detection_rate_limit=200,
    detection_timeout=10,
    detection_retries=1,
):
    """构建 Web 漏洞扫描任务 payload（字段对齐 apis.md §11.2.1）"""
    return {
        "taskName": task_name,
        "scanTarget": scan_target,
        "scheduleType": schedule_type,
        "taskStatus": task_status,
        "syncToAsset": sync_to_asset,
        "scanRange": scan_range,
        "scanDepth": scan_depth,
        "crawlStrategy": crawl_strategy,
        "maxCrawlDuration": max_crawl_duration,
        "concurrency": concurrency,
        "rateLimit": rate_limit,
        "userAgent": user_agent,
        "customHeaders": custom_headers,
        "connectTimeout": connect_timeout,
        "maxResponseSizeMb": max_response_size_mb,
        "retries": retries,
        "enableJs": enable_js,
        "enableJsluice": enable_jsluice,
        "excludeExtensions": _EXCLUDE_EXTENSIONS if exclude_extensions is None else exclude_extensions,
        "excludeFilename": _EXCLUDE_FILENAME if exclude_filename is None else exclude_filename,
        "includePaths": include_paths,
        "excludePaths": exclude_paths,
        "ignoreQueryParams": ignore_query_params,
        "filterSimilarUrls": filter_similar_urls,
        "statusCodeFilterMode": _STATUS_CODE_FILTER if status_code_filter_mode is None else status_code_filter_mode,
        "enableFormFilling": enable_form_filling,
        "formFillValues": form_fill_values,
        "scanLevel": scan_level,
        "enableAuthScan": enable_auth_scan,
        "templateId": template_id,
        "templateConcurrency": template_concurrency,
        "bulkSize": bulk_size,
        "detectionRateLimit": detection_rate_limit,
        "detectionTimeout": detection_timeout,
        "detectionRetries": detection_retries,
    }


def query_web_scan_tasks(payload=None):
    """查询 Web 漏洞扫描任务列表：POST /vuln/web-scan/list"""
    if payload is None:
        payload = {
            "pageNum": 1, "pageSize": 10, "orderBy": "create_time desc",
            "condition": {}, "keyword": "", "keywordFields": KEYWORD_FIELDS,
        }
    return request_wrapper("post", f"{WEB_SCAN_BASE}/list", msg="查询Web漏洞扫描任务列表",
                           json=payload, headers=get_headers())


def create_web_scan_task(payload):
    """创建：POST /vuln/web-scan"""
    return request_wrapper("post", WEB_SCAN_BASE, msg="创建Web漏洞扫描任务",
                           json=payload, headers=get_headers())


def update_web_scan_task(task_id, payload):
    """编辑：PUT /vuln/web-scan/{id}（已知缺陷：任何修改均返回 500）"""
    return request_wrapper("put", f"{WEB_SCAN_BASE}/{task_id}", msg="编辑Web漏洞扫描任务",
                           json=payload, headers=get_headers())


def delete_web_scan_task(task_id):
    """删除：DELETE /vuln/web-scan/{id}"""
    return request_wrapper("delete", f"{WEB_SCAN_BASE}/{task_id}", msg="删除Web漏洞扫描任务",
                           headers=get_headers())


def batch_delete_web_scan_tasks(task_ids):
    """批量删除：DELETE /vuln/web-scan/batch，body={"taskIds": [...]}"""
    if not isinstance(task_ids, list):
        task_ids = [task_ids]
    return request_wrapper("delete", f"{WEB_SCAN_BASE}/batch", msg="批量删除Web漏洞扫描任务",
                           json={"taskIds": task_ids}, headers=get_headers())


def start_web_scan_task(task_id):
    """启动：POST /vuln/web-scan/{id}/start"""
    return request_wrapper("post", f"{WEB_SCAN_BASE}/{task_id}/start", msg="启动Web漏洞扫描任务",
                           headers=get_headers())


def stop_web_scan_task(task_id):
    """终止：POST /vuln/web-scan/{id}/stop"""
    return request_wrapper("post", f"{WEB_SCAN_BASE}/{task_id}/stop", msg="终止Web漏洞扫描任务",
                           headers=get_headers())


def get_web_scan_detail(task_id):
    """任务配置详情：GET /vuln/web-scan/{id}?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEB_SCAN_BASE}/{task_id}", msg="查询Web漏洞扫描任务详情",
                           params=params, headers=get_headers())


def get_web_scan_execution(task_id):
    """任务执行详情：GET /vuln/web-scan/{id}/execution?_t=ts"""
    import time
    params = {"_t": int(time.time() * 1000)}
    return request_wrapper("get", f"{WEB_SCAN_BASE}/{task_id}/execution", msg="查询Web漏洞扫描执行详情",
                           params=params, headers=get_headers())


def export_web_scan_tasks(task_ids, export_format="docx"):
    """批量导出：POST /vuln/web-scan/export-zip"""
    return request_wrapper("post", f"{WEB_SCAN_BASE}/export-zip", msg="导出Web漏洞扫描任务",
                           json={"taskIds": task_ids, "format": export_format}, headers=get_headers())
