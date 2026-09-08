# HSC 接口文档沉淀

## 环境信息

- 测试环境地址：`https://192.168.124.55:26400`（55 开发环境）
- 接口根路径：`/hsc-system-api`
- 认证方式：Header 中携带 `Authorization` 和 `X-Access-Token`
- HTTPS 证书：测试环境为自签名证书，调用时需关闭证书验证（`verify=False`）

## 通用请求头

```http
Authorization: <Token>
X-Access-Token: <Token>
Content-Type: application/json
```

> Token 从浏览器登录后获取：F12 → Application → LocalStorage → 查找 token 字段

## 1. 登录接口

### 基本信息

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/user/login` |
| 描述 | 用户登录获取 Token |

### 请求体

```json
{
  "username": "chenyh",
  "password": "加密后的密码",
  "code": "图片验证码",
  "uuid": "验证码绑定标识"
}
```

### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": "<Token 字符串>",
  "timestamp": 1784777334167
}
```

> 注：当前自动化采用手工抓包 Token 方式，未实现验证码自动处理。

## 2. 资产探测任务创建

### 基本信息

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/asset/probe` |
| 描述 | 创建资产探测扫描任务 |

### 请求体

```json
{
  "taskName": "接口自动化-001",
  "scanTarget": "192.168.124.123",
  "scheduleType": "IMMEDIATE",
  "taskStatus": "ENABLED",
  "syncToAsset": true,
  "speed": 2,
  "maxRetries": 2,
  "maxSendRate": 10000,
  "versionIntensity": 4,
  "hostTimeout": 30,
  "portTimeout": 10000,
  "skipHostDiscover": false,
  "osDetectEnabled": true,
  "hostDetectTemplate": 1,
  "serviceDetectEnabled": true,
  "udpScanEnabled": false,
  "ports": "1-65535",
  "udpPorts": "137",
  "excludePorts": "137",
  "tcpScanMethod": 1,
  "icmpEchoPing": true,
  "icmpTimestampPing": true,
  "icmpMacPing": true,
  "tcpAckPing": true,
  "tcpAckPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
  "tcpSynPing": true,
  "tcpSynPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
  "udpPing": true,
  "udpPingPorts": "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100",
  "arpPing": true
}
```

### 字段说明

| 字段 | 含义 | 前端限制/备注 |
|------|------|--------------|
| taskName | 任务名称 | 必填 |
| scanTarget | 扫描目标 | 必填，IP 或网段 |
| scheduleType | 执行方式 | `IMMEDIATE` 为立即执行；传非法值仍可创建成功 |
| taskStatus | 启用状态 | `ENABLED` 启用；`DISABLED` 禁用 |
| syncToAsset | 是否同步到资产 | true/false |
| speed | 扫描速度 | 页面上不直接对应此字段，通过下拉框映射其他参数 |
| maxRetries | 最大重试次数 | 页面范围 0-9；接口可传负数 |
| maxSendRate | 单主机最大发包速率 | 页面范围 10-20000 |
| versionIntensity | 版本探测强度 | 页面范围 1-9；接口传 999 会被静默处理为 9 |
| hostTimeout | 主机扫描超时时间 | 单位分钟；传 0 会导致任务 5 秒内完成且无数据 |
| portTimeout | 端口扫描超时时间 | 单位毫秒 |
| skipHostDiscover | 跳过主机发现 | true/false |
| osDetectEnabled | 启用操作系统识别 | true/false |
| hostDetectTemplate | 主机探测模板 | 枚举值 |
| serviceDetectEnabled | 启用服务识别 | true/false |
| udpScanEnabled | 启用 UDP 扫描 | true/false |
| ports | TCP 扫描端口 | 支持格式如 `1-65535`、`80,443` |
| udpPorts | UDP 扫描端口 | 支持格式同 ports |
| excludePorts | 排除端口 | 支持格式同 ports |
| tcpScanMethod | TCP 扫描策略 | 1=CONNECT 等；页面下拉框有固定选项；接口传非法值可创建成功 |

### 响应示例

#### 成功

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": "2080129425067892738",
  "timestamp": 1784777334167
}
```

#### 无 Token

```json
{
  "status": 401,
  "error": "未授权"
}
```

#### 业务错误（如空任务名）

```json
{
  "status": 400,
  "message": "任务名称不能为空",
  "error": "Bad Request",
  "data": null
}
```

> 注意：HSC 接口 HTTP 层通常返回 200，业务状态在 JSON 的 `code`/`success`/`status` 字段中体现。

## 3. 资产探测任务删除

### 基本信息

| 项目 | 内容 |
|------|------|
| URL | `DELETE /hsc-system-api/asset/probe/{id}` |
| 描述 | 删除指定 ID 的资产探测任务 |

### 路径参数

| 参数 | 含义 |
|------|------|
| id | 任务 ID（创建接口返回的 `result`） |

### 响应示例

#### 成功

```json
{
  "success": true,
  "code": 200,
  "message": "删除成功"
}
```

#### 删除不存在任务

```json
{
  "success": false,
  "code": 404,
  "message": "任务不存在"
}
```

#### 无 Token

```json
{
  "status": 401,
  "error": "未授权"
}
```

#### 非法 ID 格式

```json
{
  "success": false,
  "code": 400,
  "message": "任务ID格式错误"
}
```

#### 重复删除（幂等）

```json
{
  "success": true,
  "code": 200,
  "message": "删除成功"
}
```

> 注意：HSC 删除接口是**幂等**的，同一个 ID 删除两次都返回成功。

## 4. 资产探测任务查询（列表）

### 基本信息

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/asset/probe/list` |
| 描述 | 分页查询资产探测任务列表 |

### 请求头

除通用请求头外，还需额外携带：

```http
x-tenant-id: 0
x-timestamp: <当前毫秒时间戳>
x-version: v3
x-sign: <签名，从 F12 复制>
```

> ⚠️ `x-sign` 目前采用从 F12 硬编码复制的方式，后续可能需要研究 JS 签名生成逻辑。

### 请求体

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "orderBy": "create_time desc",
  "keyword": "测试",
  "keywordFields": ["taskNo", "taskName", "createBy"]
}
```

### 字段说明

| 字段 | 含义 | 备注 |
|------|------|------|
| pageNum | 当前页码 | 从 1 开始 |
| pageSize | 每页条数 | 如 10、50、100 |
| orderBy | 排序方式 | `create_time desc` 按创建时间倒序 |
| keyword | 搜索关键字 | 空字符串返回全部 |
| keywordFields | 搜索字段范围 | 数组，可选 `taskNo`、`taskName`、`createBy` |

### 响应示例

#### 成功

```json
{
  "success": true,
  "code": 200,
  "result": {
    "list": [
      {
        "id": "2080129425067892738",
        "taskNo": "NO20260723217",
        "taskName": "测试-非法扫描速度",
        "createBy": "chenyh",
        "createTime": "2026-07-23 15:30:00",
        "status": "ENABLED"
      }
    ],
    "total": 105,
    "pages": 11,
    "pageSize": 10,
    "pageNum": 1
  }
}
```

#### 无 Token

```json
{
  "status": 401,
  "error": "未授权"
}
```

#### 无 x-sign / x-sign 过期

```json
{
  "status": 401,
  "error": "签名验证失败"
}
```

### 响应字段路径

| 数据 | 路径 |
|------|------|
| 任务列表 | `result.list` |
| 总条数 | `result.total` |
| 总页数 | `result.pages` |
| 当前页大小 | `result.pageSize` |
| 当前页码 | `result.pageNum` |

## 5. 资产探测任务获取详情

### 基本信息

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/asset/probe/{id}?_t=时间戳` |
| 描述 | 获取指定任务的完整详情，用于编辑表单回填 |

### 路径参数

| 参数 | 含义 |
|------|------|
| id | 任务 ID |

### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": {
    "taskNo": "NO20260723222",
    "taskName": "测试-非法版本探测强度",
    "taskType": "ASSET_PROBE",
    "taskStatus": "ENABLED",
    "createBy": "chenyh",
    "scanTarget": "192.168.124.123",
    "scheduleType": "IMMEDIATE",
    "scheduleConfig": null,
    "portScanType": "TOP1000",
    "ports": "1-65535",
    "udpPorts": "137",
    "osDetectEnabled": true,
    "serviceDetectEnabled": true,
    "syncToAsset": true,
    "speed": 2,
    "maxRetries": 2,
    "maxSendRate": 10000,
    "versionIntensity": 9,
    "hostTimeout": 30,
    "portTimeout": 10000,
    "icmpEchoPing": true,
    "icmpTimestampPing": true,
    "icmpMacPing": true,
    "tcpAckPing": true,
    "tcpAckPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
    "tcpSynPing": true,
    "tcpSynPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
    "udpPing": true,
    "udpPingPorts": "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100",
    "arpPing": true,
    "skipHostDiscover": false,
    "hostDetectTemplate": 1,
    "udpScanEnabled": false,
    "tcpScanMethod": 1,
    "portStrategyId": null,
    "excludePorts": "137",
    "excludeTargets": null,
    "reportDefaultService": null
  },
  "timestamp": "1784862703311"
}
```

> 注：获取详情是修改任务的前置步骤，编辑页面打开时首先调用此接口获取完整数据。

## 6. 资产探测任务修改

### 基本信息

| 项目 | 内容 |
|------|------|
| URL | `PUT /hsc-system-api/asset/probe/{id}` |
| 描述 | 修改指定任务的全部字段 |

### 编辑页面交互流程

> ⚠️ **重要**：编辑是 **3 步向导**（基本信息 → 高级参数 → 端口参数），但**每一步都不调接口**，只在最后点"确定"时才发 1 个 PUT 请求。向导中填的字段保存在前端，最后一次性提交完整数据。

| 步骤 | 页面内容 | 是否调接口 |
|------|---------|-----------|
| 第 1 步 | 基本信息（任务名、检测目标、执行方式等） | ❌ 不调 |
| 第 2 步 | 高级参数（扫描速度、重试次数、超时等） | ❌ 不调 |
| 第 3 步 | 端口参数（TCP/UDP 端口、扫描策略等） | ❌ 不调 |
| 点击"确定" | 提交完整数据 | ✅ 调接口 |

### 请求体

> ⚠️ **注意**：修改接口需要传**全部字段**（不只是要改的字段），未传的字段会被清空。推荐做法：先调用获取详情接口，再用新值覆盖需要修改的字段，其余字段保持原样。

```json
{
  "taskName": "测试-修改名称",
  "scanTarget": "192.168.124.123",
  "scheduleType": "IMMEDIATE",
  "taskStatus": "ENABLED",
  "syncToAsset": true,
  "speed": 1,
  "maxRetries": 3,
  "maxSendRate": 5000,
  "versionIntensity": 5,
  "hostTimeout": 30,
  "portTimeout": 10000,
  "skipHostDiscover": false,
  "osDetectEnabled": true,
  "hostDetectTemplate": 1,
  "serviceDetectEnabled": true,
  "udpScanEnabled": false,
  "ports": "1-65535",
  "udpPorts": "137",
  "excludePorts": "137",
  "tcpScanMethod": 1,
  "icmpEchoPing": true,
  "icmpTimestampPing": true,
  "icmpMacPing": true,
  "tcpAckPing": true,
  "tcpAckPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
  "tcpSynPing": true,
  "tcpSynPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
  "udpPing": true,
  "udpPingPorts": "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100",
  "arpPing": true
}
```

### 响应示例

#### 成功

```json
{
  "success": true,
  "message": "",
  "code": 200
}
```

#### 无 Token

```json
{
  "status": 401,
  "error": "未授权"
}
```

## 7. 已发现的接口缺陷汇总

### 创建接口缺陷

| 缺陷 | 触发参数 | 当前状态 |
|------|---------|---------|
| 未校验 `speed` 参数 | `speed=999` | 已提 bug |
| 未校验 `tcpScanMethod` 枚举值 | `tcpScanMethod=999` | 已提 bug |
| 未校验 `maxRetries` 下限 | `maxRetries=-1` | 已提 bug |
| 未校验 `hostTimeout` 最小值 | `hostTimeout=0` | 已提 bug |
| 未校验 `versionIntensity` 范围 | `versionIntensity=999` | 已提 bug |
| 未校验 `ports` 格式 | `ports="abc"` | 已提 bug |
| 未校验 `udpPorts` 格式 | `udpPorts="abc"` | 已提 bug |
| 未校验 `scheduleType` 枚举值 | `scheduleType="INVALID_TYPE"` | 已提 bug |
| 任务名特殊字符/XSS/SQL 注入可创建 | 特殊字符串 | 已提 bug |

### 安全相关发现

| 发现 | 说明 | 风险等级 |
|------|------|---------|
| `x-sign` 硬编码可用 | 即使时间戳不一致仍能使用，说明签名校验容忍度较高 | 中 |
| 查询接口签名机制 | `x-sign` 生成逻辑与时间戳绑定不严格 | 待确认 |

## 8. 测试脚本

### 文件结构

```
~/hsc_auto/
├── config.py                    # 公共配置（BASE_URL, TOKEN, HEADERS）
├── utils.py                     # 公共函数（create_task, delete_task, cleanup_task, get_task_detail, update_task）
├── test_probe_task.py           # 资产探测任务全量测试（115 个用例）
├── test_unauthorized.py         # 未授权访问测试
├── test_demo.py                 # 入门示例
├── apis.md                      # 本文档
└── batch_clean.py               # 批量清理测试数据
```

### 运行命令

```bash
cd ~/hsc_auto
source venv/bin/activate

# 运行资产探测全量测试
pytest test_probe_task.py -v --html=report_probe.html

# 运行未授权测试
pytest test_unauthorized.py -v --html=report_unauthorized.html

# 运行全部测试
pytest -v --html=report_all.html
```

### 测试覆盖统计

| 模块 | 用例数 | 覆盖场景 |
|------|--------|---------|
| 资产探测（全量） | 115 | 创建 27 + 删除 15 + 修改 22 + 查询 19 + 边界批量 12 + 生命周期闭环 20 |
| **合计** | **115** | |

## 10. 网站测绘任务接口

> 服务地址：`https://192.168.124.55:26400/hsc-system-api`（与资产探测同一服务器）

### 10.1 创建任务

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/asset/web-map` |
| 描述 | 创建网站测绘任务 |

#### 请求体

```json
{
  "taskName": "网站测绘测试002",
  "scanTarget": "https://192.168.124.123",
  "scheduleType": "IMMEDIATE",
  "taskStatus": "ENABLED",
  "syncToAsset": true,
  "scanRange": 3,
  "scanDepth": 5,
  "crawlStrategy": "BFS",
  "maxCrawlDuration": 10,
  "concurrency": 20,
  "rateLimit": 300,
  "userAgent": "",
  "customHeaders": "[]",
  "connectTimeout": 15,
  "maxResponseSizeMb": 1024,
  "retries": 2,
  "enableJs": true,
  "enableJsluice": false,
  "excludeExtensions": "jpg,jpeg,gif,png,bmp,ico,ani,zip,gz,tar,rar,doc,docx,xls,xlsx,ppt,pptx,vsd,asf,avi,wm,wmp,wmv,ram,rm,rmvb,rp,rpm,rt,smil,scm,dat,m1v,m2v,m2p,m2ts,mp2v,mpe,mpeg,mpeg1,mpeg2,mpg,mpv2,pss,pva,tp,tpr,ts,m4b,m4r,m4p,m4v,mp4,mpeg4,3g2,3gp,3gp2,3gpp,mov,qt,flv,f4v,swf,hlv,ifo,vob,amv,csf,divx,evo,mkv,mod,pmp,vp6,bik,mts,xlmv,ogm,ogv,ogx,dvd,aac,ac3,acc,aiff,amr,ape,au,cda,dts,flac,m1a,m2a,m4a,mka,mp2,mp3,mpa,mpc,ra,tta,wav,wma,wv,mid,midi,ogg,oga",
  "excludeFilename": "del,delete,sigoff,sigout,logout,logoff,exit",
  "includePaths": "",
  "excludePaths": "",
  "ignoreQueryParams": true,
  "filterSimilarUrls": true,
  "statusCodeFilterMode": "404,410,409,412,414,500,502,503,504,505,506,507,509,510",
  "enableFormFilling": false,
  "formFillValues": "[]",
  "scanLevel": 0,
  "enableAuthScan": false
}
```

#### 字段说明

| 字段 | 含义 | 备注 |
|------|------|------|
| taskName | 任务名称 | 必填 |
| scanTarget | 检测目标 | 必填，URL |
| scheduleType | 执行方式 | `IMMEDIATE` 立即；`ONCE` 一次；`PERIODIC` 周期 |
| scheduleConfig | 定时/周期配置 | `scheduleType` 非 IMMEDIATE 时必填，JSON 字符串 |
| taskStatus | 启用状态 | `ENABLED` / `DISABLED` |
| syncToAsset | 同步到资产 | true/false |
| scanRange | 扫描范围 | 3=当前域（截图值） |
| scanDepth | 爬行深度 | 整数 |
| crawlStrategy | 爬行策略 | `BFS` 广度优先，`DFS` 深度优先 |
| scanLevel | 扫描级别 | 0=未选择/自定义（抓包创建值）；编辑时标准模式可能为 2 |
| maxCrawlDuration | 最大爬取时间 | 分钟 |
| concurrency | 并发数 | 整数 |
| rateLimit | 速率限制 | 整数 |
| enableJs | 执行 JavaScript | true/false |
| enableJsluice | 启用 Jsluice | true/false |
| excludeExtensions | 排除文件扩展名 | 逗号分隔 |
| excludeFilename | 排除文件名 | 逗号分隔 |
| includePaths | 包含路径 | 逗号分隔 |
| excludePaths | 排除路径 | 逗号分隔 |
| ignoreQueryParams | 忽略查询参数 | true/false |
| filterSimilarUrls | 过滤相似 URL | true/false |
| statusCodeFilterMode | 状态码过滤 | 逗号分隔 |
| enableFormFilling | 自动表单填充 | true/false |
| formFillValues | 表单填充值 | JSON 字符串 |
| enableAuthScan | 启用认证扫描 | true/false |

#### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": "2080688473840316417",
  "timestamp": 1784881228726
}
```

### 10.2 查询列表

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/asset/web-map/list` |
| 描述 | 分页查询网站测绘任务 |

#### 请求头

```http
x-tenant-id: 0
x-timestamp: <毫秒时间戳>
x-version: v3
x-sign: <从 F12 复制>
```

#### 请求体

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "orderBy": "create_time desc",
  "keyword": "测试",
  "keywordFields": ["taskNo", "taskName", "createBy"]
}
```

### 10.3 修改任务

| 项目 | 内容 |
|------|------|
| URL | `PUT /hsc-system-api/asset/web-map/{id}` |
| 描述 | 修改网站测绘任务 |

> 注意：修改需传完整字段，建议先 GET 详情再覆盖要改的值。

### 10.4 删除任务

| 项目 | 内容 |
|------|------|
| URL | `DELETE /hsc-system-api/asset/web-map/{id}` |
| 描述 | 删除网站测绘任务 |

### 10.5 获取任务详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/asset/web-map/{id}` |
| 描述 | 获取任务配置详情（任务名称、状态、扫描目标、扫描范围/深度等） |

#### 请求头

```http
x-tenant-id: 0
x-timestamp: <毫秒时间戳>
x-version: v3
x-sign: E19D6243CB1945AB4F7202A1B00F77D5
```

#### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": {
    "taskNo": "NO20260724307",
    "taskName": "测试-详情端点探测",
    "taskType": "WEB_MAP",
    "taskStatus": "ENABLED",
    "createBy": "chenyh",
    "scanTarget": "https://192.168.1.1",
    "scheduleType": "IMMEDIATE",
    "scheduleConfig": null,
    "scanRange": 3,
    "scanDepth": 5,
    "crawlStrategy": "BFS",
    "maxCrawlDuration": 10,
    "concurrency": 20,
    "rateLimit": 300,
    ...
  }
}
```

> 注意：`GET /asset/web-map/result/{id}` 是结果页接口，返回的是测绘结果（域名/IP/URL 列表），不包含任务属性；任务不存在时可能返回 `"结果不存在"`。

---

## 11. 脆弱性扫描接口

### 11.1 主机漏洞扫描任务

#### 11.1.1 创建任务

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/host-scan` |
| 描述 | 创建主机漏洞扫描任务 |

##### 请求体

```json
{
  "taskName": "主机漏洞-默认模板",
  "scanTarget": "192.168.124.123",
  "scheduleType": "IMMEDIATE",
  "taskStatus": "ENABLED",
  "syncToAsset": true,
  "templateId": "29",
  "speed": 2,
  "maxRetries": 2,
  "maxSendRate": 10000,
  "versionIntensity": 4,
  "hostTimeout": 30,
  "portTimeout": 10000,
  "skipHostDiscover": false,
  "osDetectEnabled": true,
  "hostDetectTemplate": 1,
  "serviceDetectEnabled": true,
  "udpScanEnabled": false,
  "ports": "1-65535",
  "udpPorts": "137",
  "excludePorts": "137",
  "tcpScanMethod": 1,
  "pocEnabled": true,
  "icmpEchoPing": true,
  "icmpTimestampPing": true,
  "icmpMacPing": true,
  "tcpAckPing": true,
  "tcpAckPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
  "tcpSynPing": true,
  "tcpSynPorts": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017",
  "udpPing": true,
  "udpPingPorts": "53,67,68,69,111,123,137,138,161,162,500,514,1900,4500,5060,16100",
  "arpPing": true
}
```

##### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": "2080129425067892738",
  "timestamp": 1784777334167
}
```

#### 11.1.2 删除任务

| 项目 | 内容 |
|------|------|
| URL | `DELETE /hsc-system-api/vuln/host-scan/{id}` |
| 描述 | 删除主机漏洞扫描任务 |

#### 11.1.3 批量删除任务

| 项目 | 内容 |
|------|------|
| URL | `DELETE /hsc-system-api/vuln/host-scan/batch` |
| 描述 | 批量删除主机漏洞扫描任务 |

##### 请求体

```json
{
  "taskIds": ["id1", "id2"]
}
```

#### 11.1.4 修改任务

| 项目 | 内容 |
|------|------|
| URL | `PUT /hsc-system-api/vuln/host-scan/{id}` |
| 描述 | 修改主机漏洞扫描任务 |

#### 11.1.5 查询任务列表

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/host-scan/list` |
| 描述 | 分页查询主机漏洞扫描任务列表 |

##### 请求体

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "orderBy": "create_time desc",
  "condition": {},
  "keyword": "",
  "keywordFields": []
}
```

#### 11.1.6 任务配置详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/vuln/host-scan/{id}?_t={timestamp}` |
| 描述 | 查询任务配置详情，用于编辑回填 |

#### 11.1.7 任务执行详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/vuln/host-scan/{id}/execution?_t={timestamp}` |
| 描述 | 查询任务执行详情 |

#### 11.1.8 任务操作

| 操作 | 方法 | URL |
|------|------|------|
| 启动/重新开始 | POST | `/vuln/host-scan/{id}/start` |
| 终止 | POST | `/vuln/host-scan/{id}/stop` |
| 暂停 | POST | `/vuln/host-scan/{id}/pause` |
| 恢复 | POST | `/vuln/host-scan/{id}/resume` |
| 重试 | POST | `/vuln/host-scan/{id}/retry` |
| 复制 | POST | `/vuln/host-scan/{id}/copy` |

#### 11.1.9 批量导出

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/host-scan/export-zip` |
| 描述 | 批量导出主机漏洞扫描任务 |

##### 请求体

```json
{
  "taskIds": ["id1", "id2"],
  "format": "docx"
}
```

##### 已知缺陷

| 缺陷 | 触发参数 | 当前状态 |
|------|---------|---------|
| 缺少 `templateId` 可创建 | payload 不含 templateId | 已提 bug |
| 非法 `templateId` 可创建 | templateId=999999 | 已提 bug |
| 非法 `taskStatus` 可创建 | taskStatus="INVALID" | 已提 bug |
| 非法 `speed` 可创建 | speed=999 | 已提 bug |
| 负数 `maxRetries` 可创建 | maxRetries=-1 | 已提 bug |
| `maxSendRate=0` 可创建 | maxSendRate=0 | 已提 bug |
| 非法 `versionIntensity` 可创建 | versionIntensity=10 | 已提 bug |
| `hostTimeout=0` 可创建 | hostTimeout=0 | 已提 bug |
| 非法 `ports` 格式可创建 | ports="abc" | 已提 bug |
| 任务名特殊字符/XSS/SQL 注入可创建 | 特殊字符串 | 已提 bug |

### 11.2 Web 漏洞扫描任务

#### 11.2.1 创建任务

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/web-scan` |
| 描述 | 创建 Web 漏洞扫描任务 |

##### 请求体

```json
{
  "taskName": "测试",
  "scanTarget": "https://192.168.112.123",
  "scheduleType": "IMMEDIATE",
  "taskStatus": "ENABLED",
  "syncToAsset": true,
  "scanRange": 3,
  "scanDepth": 5,
  "crawlStrategy": "BFS",
  "maxCrawlDuration": 10,
  "concurrency": 20,
  "rateLimit": 300,
  "userAgent": "",
  "customHeaders": "[]",
  "connectTimeout": 15,
  "maxResponseSizeMb": 1024,
  "retries": 2,
  "enableJs": true,
  "enableJsluice": false,
  "excludeExtensions": "jpg,jpeg,gif,png,bmp,ico,ani,zip,gz,tar,rar,doc,docx,xls,xlsx,ppt,pptx,vsd,asf,avi,wm,wmp,wmv,ram,rm,rmvb,rp,rpm,rt,smil,scm,dat,m1v,m2v,m2p,m2ts,mp2v,mpe,mpeg,mpeg1,mpeg2,mpg,mpv2,pss,pva,tp,tpr,ts,m4b,m4r,m4p,m4v,mp4,mpeg4,3g2,3gp,3gp2,3gpp,mov,qt,flv,f4v,swf,hlv,ifo,vob,amv,csf,divx,evo,mkv,mod,pmp,vp6,bik,mts,xlmv,ogm,ogv,ogx,dvd,aac,ac3,acc,aiff,amr,ape,au,cda,dts,flac,m1a,m2a,m4a,mka,mp2,mp3,mpa,mpc,ra,tta,wav,wma,wv,mid,midi,ogg,oga",
  "excludeFilename": "del,delete,sigoff,sigout,logout,logoff,exit",
  "includePaths": "",
  "excludePaths": "",
  "ignoreQueryParams": true,
  "filterSimilarUrls": true,
  "statusCodeFilterMode": "404,410,409,412,414,500,502,503,504,505,506,507,509,510",
  "enableFormFilling": false,
  "formFillValues": "[]",
  "scanLevel": 2,
  "enableAuthScan": false,
  "templateId": 36,
  "templateConcurrency": 25,
  "bulkSize": 50,
  "detectionRateLimit": 200,
  "detectionTimeout": 10,
  "detectionRetries": 1
}
```

##### 字段说明

| 字段 | 含义 | 备注 |
|------|------|------|
| taskName | 任务名称 | 必填 |
| scanTarget | 检测目标 | 必填，URL |
| scheduleType | 执行方式 | `IMMEDIATE` 立即执行 |
| taskStatus | 启用状态 | `ENABLED` / `DISABLED` |
| syncToAsset | 同步到资产 | true/false |
| scanRange | 扫描范围 | 3=当前域 |
| scanDepth | 爬行深度 | 整数 |
| crawlStrategy | 爬行策略 | `BFS` 广度优先，`DFS` 深度优先 |
| scanLevel | 扫描级别 | 0=自定义，1=快速，2=标准，3=全面 |
| maxCrawlDuration | 最大爬取时间 | 分钟 |
| concurrency | 爬行并发数 | 整数 |
| rateLimit | 爬行每秒最大请求数 | 整数 |
| enableJs | 是否执行 JavaScript | true/false |
| enableJsluice | 是否深度 JS 解析 | true/false |
| excludeExtensions | 排除文件扩展名 | 逗号分隔 |
| excludeFilename | 排除文件名 | 逗号分隔 |
| includePaths | 包含路径 | 逗号分隔 |
| excludePaths | 排除路径 | 逗号分隔 |
| ignoreQueryParams | 忽略查询参数 | true/false |
| filterSimilarUrls | 过滤相似 URL | true/false |
| statusCodeFilterMode | 状态码过滤 | 逗号分隔 |
| enableFormFilling | 自动表单填充 | true/false |
| formFillValues | 表单填充值 | JSON 字符串 |
| enableAuthScan | 启用认证扫描 | true/false |
| templateId | 漏洞模板 ID | 默认 36 |
| templateConcurrency | Web 检测模板并发数 | 默认 25 |
| bulkSize | Web 检测批量目标数 | 默认 50 |
| detectionRateLimit | Web 检测每秒最大请求数 | 默认 200 |
| detectionTimeout | Web 检测超时时间 | 默认 10 秒 |
| detectionRetries | Web 检测失败重试次数 | 默认 1 |

##### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": "2082003273803522050",
  "timestamp": "1785223236896"
}
```

#### 11.2.2 删除与批量删除

| 操作 | 方法 | URL |
|------|------|------|
| 删除 | DELETE | `/vuln/web-scan/{id}` |
| 批量删除 | DELETE | `/vuln/web-scan/batch` |

#### 11.2.3 修改任务

| 项目 | 内容 |
|------|------|
| URL | `PUT /hsc-system-api/vuln/web-scan/{id}` |
| 描述 | 修改 Web 漏洞扫描任务 |

> ⚠️ **已知缺陷**：PUT /vuln/web-scan/{id} 对任何字段修改均返回 500，`{"status":500,"message":null,"error":"抱歉，服务器开小差了","data":null}`。

#### 11.2.4 查询任务列表

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/web-scan/list` |
| 描述 | 分页查询 Web 漏洞扫描任务列表 |

##### 请求体

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "orderBy": "create_time desc",
  "condition": {},
  "keyword": "测试",
  "keywordFields": ["taskNo", "taskName", "createBy"]
}
```

##### 响应字段

| 字段 | 说明 |
|------|------|
| id | 任务 ID |
| taskNo | 任务编号 |
| taskName | 任务名称 |
| scanTarget | 扫描目标 |
| scheduleType | 执行方式 |
| taskStatus | 任务状态 |
| createBy | 创建人 |
| createTime | 创建时间 |
| latestExecStatus | 最新执行状态 |
| latestExecProgress | 最新执行进度 |
| latestTriggerType | 最新触发方式 |
| latestExecStartTime | 最新执行开始时间 |
| latestExecEndTime | 最新执行结束时间 |

#### 11.2.5 任务配置详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/vuln/web-scan/{id}?_t={timestamp}` |
| 描述 | 查询任务配置详情 |

#### 11.2.6 任务执行详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/vuln/web-scan/{id}/execution?_t={timestamp}` |
| 描述 | 查询任务执行详情 |

#### 11.2.7 任务操作

| 操作 | 方法 | URL |
|------|------|------|
| 启动/重新开始 | POST | `/vuln/web-scan/{id}/start` |
| 终止 | POST | `/vuln/web-scan/{id}/stop` |
| 暂停 | POST | `/vuln/web-scan/{id}/pause` |
| 恢复 | POST | `/vuln/web-scan/{id}/resume` |
| 重试 | POST | `/vuln/web-scan/{id}/retry` |
| 复制 | POST | `/vuln/web-scan/{id}/copy` |

##### 已知缺陷

| 缺陷 | 说明 | 当前状态 |
|------|------|---------|
| 终止后状态未更新 | 点击终止成功后，任务状态仍为「待执行」，操作列仍为「终止」，导致任务无法删除 | 已提 bug |
| xlsx 导出不支持 | 导出格式传 xlsx 时后端返回错误 | 待确认 |

#### 11.2.8 批量导出

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/web-scan/export-zip` |
| 描述 | 批量导出 Web 漏洞扫描任务 |

##### 请求体

```json
{
  "taskIds": ["id1", "id2"],
  "format": "docx"
}
```

### 11.3 基线核查任务

#### 11.3.1 创建任务

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/baseline-scan` |
| 描述 | 创建在线基线核查任务 |

##### 请求体

```json
{
  "taskName": "cehsi1",
  "scanTarget": "192.168.124.55",
  "scheduleType": "IMMEDIATE",
  "taskStatus": "ENABLED",
  "checkType": 2,
  "targetsConfig": "[{\"ip\":\"192.168.124.55\",\"protocol\":\"ssh\",\"port\":22,\"username\":\"root\",\"password\":\"XingDing@2024\",\"templates\":[{\"templateId\":\"332358588846572071\",\"templateName\":\"DB2_配置规范_(Linux).zip\",\"parameters\":{}}]}]"
}
```

##### 字段说明

| 字段 | 含义 | 备注 |
|------|------|------|
| taskName | 任务名称 | 必填 |
| scanTarget | 扫描目标 | 必填，IP |
| scheduleType | 执行方式 | `IMMEDIATE` 立即执行 |
| taskStatus | 启用状态 | `ENABLED` / `DISABLED` |
| checkType | 检查类型 | 2=在线基线核查 |
| targetsConfig | 目标配置 | JSON 字符串，包含 IP、协议、端口、用户名、密码、模板列表 |

##### 响应示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": "2082027343655886849",
  "timestamp": "1785228975593"
}
```

#### 11.3.2 删除与批量删除

| 操作 | 方法 | URL | 备注 |
|------|------|------|------|
| 删除 | DELETE | `/vuln/baseline-scan/{id}` | |
| 批量删除 | DELETE | `/vuln/baseline-scan/batch` | `taskIds` 为逗号分隔字符串，如 `"id1,id2"` |

#### 11.3.3 修改任务

| 项目 | 内容 |
|------|------|
| URL | `PUT /hsc-system-api/vuln/baseline-scan/{id}` |
| 描述 | 修改基线核查任务 |

#### 11.3.4 查询任务列表

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/baseline-scan/list` |
| 描述 | 分页查询基线核查任务列表 |

##### 请求体

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "orderBy": "create_time desc",
  "condition": {},
  "keyword": "",
  "keywordFields": ["taskNo", "taskName", "createBy"]
}
```

#### 11.3.5 任务配置详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/vuln/baseline-scan/{id}?_t={timestamp}` |
| 描述 | 查询任务配置详情 |

#### 11.3.6 任务执行详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/vuln/baseline-scan/{id}/execution?_t={timestamp}` |
| 描述 | 查询任务执行详情 |

#### 11.3.7 任务操作

| 操作 | 方法 | URL |
|------|------|------|
| 启动/重新开始 | POST | `/vuln/baseline-scan/{id}/start` |
| 终止 | POST | `/vuln/baseline-scan/{id}/stop` |
| 暂停 | POST | `/vuln/baseline-scan/{id}/pause` |
| 恢复 | POST | `/vuln/baseline-scan/{id}/resume` |
| 重试 | POST | `/vuln/baseline-scan/{id}/retry` |
| 复制 | POST | `/vuln/baseline-scan/{id}/copy` |

#### 11.3.8 批量导出

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/vuln/baseline-scan/export-zip` |
| 描述 | 批量导出基线核查任务 |

### 11.4 脆弱性概览

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 高风险主机列表 | POST | `/vuln/host/assetList` | 按 totalRiskCount 排序 |
| 高风险网站列表 | POST | `/vuln/web/assetList` | 按 totalRiskCount 排序 |
| 弱口令统计 | GET | `/vuln/weakpass/statistics?_t={timestamp}` | 统计卡片 |
| 基线统计 | GET | `/vuln/baseline/statistics?_t={timestamp}` | 统计卡片 |
| 核心指标 | GET | `/risk/overview/metrics?timeRange={week\|month\|quarter\|year}&_t={timestamp}` | 趋势指标 |

---

## 12. 脚本文件说明

| 文件 | 说明 |
|------|------|
| `vuln_management/test_vuln_scan_host.py` | 主机漏洞扫描任务测试（89+ 用例） |
| `vuln_management/utils_vuln_scan_host.py` | 主机漏洞扫描任务工具函数 |
| `vuln_management/test_vuln_scan_web.py` | Web 漏洞扫描任务测试（89+ 用例） |
| `vuln_management/utils_vuln_scan_web.py` | Web 漏洞扫描任务工具函数 |
| `vuln_management/test_baseline_scan.py` | 基线核查任务测试（73+ 用例） |
| `vuln_management/utils_baseline_scan.py` | 基线核查任务工具函数 |
| `vuln_management/test_vuln_overview.py` | 脆弱性概览测试 |
| `vuln_management/utils_vuln.py` | 脆弱性概览工具函数 |

### 10.6 获取任务结果页

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/asset/web-map/result/{id}?_t={timestamp}` |
| 描述 | 查看任务测绘结果（域名、IP、URL 列表等） |

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/asset/web-map/{id}/execution?_t={timestamp}` |
| 描述 | 查看任务执行状态/进度 |

#### 请求头

```http
x-tenant-id: 0
x-timestamp: <毫秒时间戳>
x-version: v3
x-sign: E19D6243CB1945AB4F7202A1B00F77D5
```

### 10.7 相关文件

- `utils_web_map.py`：网站测绘公共函数
- `test_web_map_task.py`：网站测绘测试用例

### 10.8 与 PRD 需求映射

网站测绘对应 PRD 中 **F-006 扫描任务调度** 的任务类型 1（网站检测）。当前 `test_web_map_task.py` 已扩至 116 条用例，按增删改查 + 边界批量 + 生命周期闭环组织。

| 需求点 | 测试文件对应用例 |
|--------|------------------|
| 任务类型：网站检测 | 所有 `TestCreate` 用例默认创建网站测绘任务 |
| 执行方式：立即 / 定时 / 周期 | `TestCreate.test_create_web_map_task_once_schedule`、`TestCreate.test_create_web_map_task_periodic_schedule`、`TestLifecycle.test_create_scheduled_task`、`TestLifecycle.test_create_periodic_task`、`TestLifecycle.test_modify_schedule_from_immediate_to_periodic` |
| 任务状态：启用 / 禁用 | `TestUpdate.test_update_task_status`、`TestLifecycle.test_create_disable_then_enable` |
| 支持暂停、恢复、停止、重试、复制 | `TestLifecycle.test_pause_task` / `test_resume_task` / `test_stop_task` / `test_retry_task` / `test_copy_task`（接口存在性探测，失败不阻塞） |
| 扫描目标冲突避免并发扫描 | `TestBoundaryBatch.test_concurrent_query` |
| 任务超时自动停止 | 待补充长时任务测试 |
| 参数校验 / 边界 | `TestCreate` 中非法目标、非法协议、负数深度、超长名称、特殊字符、空名称、空目标；`TestBoundaryBatch` 中非法分页、批量 10/50、翻页一致性 |
| 安全：未授权 / XSS / SQL 注入 | `TestCreate` / `TestDelete` / `TestUpdate` / `TestQuery` 中 `*_no_token`、`*_sql_injection*`、`*_xss*` 用例 |
| 幂等删除 | `TestDelete.test_delete_web_map_task_already_deleted` |
| 查询响应时间 / 性能 | `TestQuery.test_query_response_time`、`TestBoundaryBatch.test_response_time_*` |
| 数据一致性 / 闭环 | `TestLifecycle` 中创建 → 详情 → 列表 → 修改 → 删除 → 验证已删除 |

### 10.9 测试用例清单

详见 `test_web_map_task.py`，共 **116 条用例**，按模块组织：

- **TestCreate（27 个）**：正常创建、无 Token、空名称、超长名称、缺少目标、非法目标/协议、特殊字符、XSS、SQL 注入、空/HTTP/HTTPS/域名目标、只传任务名/只传目标、非法 scheduleType、负数深度、非法扫描范围/爬行策略/扫描级别、禁用状态、一次性定时、周期执行
- **TestDelete（15 个）**：正常删除、删除不存在、无 Token、非法 ID、幂等删除、SQL 注入 ID、批量删除、错误 HTTP 方法、删除运行中、批量部分不存在、批量全不存在、超长/负数/0/空 ID 删除
- **TestUpdate（22 个）**：修改名称、目标、执行方式、状态、高级参数、扫描范围/深度、JS 开关、过滤设置、超时/重试、无 Token、修改不存在、空名、非法 scheduleType、非法扫描深度、缺少必填字段、SQL 注入、XSS、超长名、多字段同时修改、基于详情修改、部分字段修改
- **TestQuery（19 个）**：列表、按名称、模糊、空关键字、无结果、分页、页大小 10/50/100、按创建人、排序、特殊字符、SQL 注入、超长关键字、无 Token、分页边界、total 一致性、指定字段搜索、XSS、响应时间、缺少必填字段
- **TestBoundaryBatch（12 个）**：pageSize 10000、pageNum 0/-1/9999、pageSize=1、响应时间、大页响应时间、并发查询、翻页一致性、批量创建 10、批量创建 50、批量修改
- **TestLifecycle（20 个）**：创建后详情一致性、创建后列表一致性、修改后查询一致性、全流程串联、创建-执行-删除、状态检查、状态轮询、一次性定时、周期任务、暂停/恢复/停止/重试/复制、禁用再启用、改执行方式、立即执行等待、重复名生命周期、详情不存在、执行状态、执行状态无 Token

### 10.10 运行命令

```bash
cd ~/hsc_auto
source venv/bin/activate

# 全量运行
pytest test_web_map_task.py -v --html=report_web_map.html

# 按类运行
pytest test_web_map_task.py::TestCreate -v -s
pytest test_web_map_task.py::TestLifecycle -v -s

# 清理测试数据
python batch_clean_web_map.py
```

---

## 13. 合规运营接口

> 覆盖 13 个子模块（top3_review 为空目录）。其中 11 个业务类型复用同一套
> `/compliance/task` 通用接口，仅 `typeCode` 与创建 payload 不同；合规总览、
> 管理系统、个人信息保护 PIA 多步骤为独立接口。
> 对应 55 自动化：`compliance_operations/`（3 utils + 4 test + 2 yaml）。

### 13.0 typeCode 全集

| typeCode | 中文名 | 来源子模块 |
|----------|--------|-----------|
| `COMPLIANCE_NS` | 网络安全任务书 | gdpr |
| `COMPLIANCE_PI` | 个人信息保护 | personal_info |
| `COMPLIANCE_DJPC` | 等保测评 | cybersecurity_maturity |
| `COMPLIANCE_SM` | 国密合规 | cryptographic_compliance |
| `COMPLIANCE_HR` | 三甲评审 | cybersecurity_task |
| `COMPLIANCE_DS` | 数据安全 | data_security |
| `COMPLIANCE_EMR` | 电子病历评级 | emr_rating |
| `COMPLIANCE_MATURITY` | 网络安全成熟度 | evaluation |
| `COMPLIANCE_SH` | 智慧医院评级 | hospital_rating |
| `COMPLIANCE_CONN` | 互联互通 | interconnect |
| `COMPLIANCE_IM` | 互联网诊疗 | internet_medicine |

### 13.1 任务列表查询

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/compliance/task/list` |
| 描述 | 查询合规任务列表（分页、关键字、状态/standard/year/targetLevel 筛选） |

请求体：

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "condition": {
    "typeCode": "COMPLIANCE_NS",
    "latestStatus": "PENDING",
    "standard": "detection",
    "year": 2026,
    "targetLevel": "3",
    "taskName": "任务名"
  },
  "keyword": "",
  "keywordFields": ["taskName"]
}
```

> `condition` 必填字段仅 `typeCode`；其余为可选筛选。`standard` 仅 PI 使用
> （detection/pia/audit）；`year`/`targetLevel` 仅评级类（DJPC/SM/EMR/SH/CONN）使用。

响应 `result`：

```json
{
  "list": [{"id": "2095...", "taskName": "任务名", "typeCode": "COMPLIANCE_NS",
            "typeName": "网络安全任务书", "latestStatus": "PENDING",
            "latestExecProgress": 0, "createTime": "2026-09-03 16:00:00"}],
  "total": "1", "pageNum": "1", "pageSize": "10", "pages": "1"
}
```

### 13.2 创建任务

| 项目 | 内容 |
|------|------|
| URL | `POST /hsc-system-api/compliance/task` |
| 描述 | 创建合规任务，`result` 返回任务 id 字符串 |

> **55 实测关键结论**：除 `COMPLIANCE_PI` 外，其余 10 个 typeCode 仅
> `taskName + typeCode` 即可创建成功，后端对 `formData`/`selectedCheckRoots`
> 等硬编码字段完全容错。`COMPLIANCE_PI` 强校验 `fileIds` 与 `formData.standard`，
> 缺任一返回 400。

通用最小请求体：

```json
{
  "taskName": "合规任务名",
  "typeCode": "COMPLIANCE_NS",
  "fileIds": [1]
}
```

各 typeCode 创建 payload 差异（`build_task_payload` 默认值）：

| typeCode | 额外字段 |
|----------|---------|
| NS | `fileIds: [1]` |
| PI | `fileIds: [3054]` + `formData{standard:"detection", dimensions:[...]}` |
| DJPC | `templateId:"1"`, `targetLevel:"等保二级"`, `year:2026`, `systemIds:[]`, `fileIds:[]` |
| SM | `templateId:"5"`, `targetLevel:"3"`, `year:2026`, `systemIds:[]`, `fileIds:[1]` |
| HR | `year:2026`, `currentLevel:"乙等"`, `targetLevel:"甲等"` |
| DS | `typeId:3`, `systemIds:[]`, `fileIds:[1]` |
| EMR | `targetLevel:"4"`, `systemIds:[]` |
| MATURITY | `targetLevel:"4"` |
| SH | `targetLevel:"3"`, `systemIds:[]` |
| CONN | `targetLevel:"4b"` |
| IM | `systemIds:[]`, `fileIds:[1]` |

### 13.3 删除任务

| 项目 | 内容 |
|------|------|
| URL | `DELETE /hsc-system-api/compliance/task/{taskId}` |
| 描述 | 删除合规任务 |

> **55 实测**：统一用 `DELETE /compliance/task/{taskId}`；123 旧框架部分子模块
> 使用的 `DELETE /compliance/task/batch?taskIds={id}` 在 55 返回 500（已废弃）。

### 13.4 报告详情

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/compliance/task/{taskId}/report?_t={毫秒时间戳}` |
| 描述 | 查询任务报告详情 |

响应 `result`：

```json
{
  "taskId": "2095...",
  "typeCode": "COMPLIANCE_NS",
  "taskName": "任务名",
  "status": "PENDING",
  "systemNames": [],
  "systems": [],
  "overview": {"score": 0, "conclusion": "", "scoreLabel": "", "resultSummary": ""},
  "tabs": [{"tabKey": "", "tabType": "", "tabLabel": "", "tree": []}]
}
```

### 13.5 合规总览

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/compliance/overview/recent-tasks?status=ALL&pageNum=1&pageSize=10&_t={ts}` |
| 描述 | 查询最近任务列表（合规总览页） |

响应 `result`：`{items: [{taskId, taskName, typeName, status, statusName, progress, checkTime}], total, pageNum, pageSize}`

### 13.6 等保结果分布

| 项目 | 内容 |
|------|------|
| URL | `GET /hsc-system-api/compliance/classified-protection/result-distribution?_t={ts}` |
| 描述 | 查询等保检测结果分布统计（可选 `systemId` 参数） |

响应 `result`：`{conformant, partialConformant, nonConformant, notApplicable, undetermined, total, conformantRate, highRisk, systems[]}`

### 13.7 管理系统

| 项目 | 内容 |
|------|------|
| 新增 | `POST /hsc-system-api/compliance/system`（multipart） |
| 查询列表 | `POST /hsc-system-api/compliance/system/list`（JSON） |
| 编辑 | `PUT /hsc-system-api/compliance/system/{id}`（multipart） |
| 删除 | `DELETE /hsc-system-api/compliance/system/{id}` |

> **55 实测关键结论**：新增/编辑系统**必须用 multipart/form-data**（JSON 放在名为
> `request`、文件名为 `blob` 的 form 字段中），用普通 `application/json` 会返回 500。
> 查询列表、删除走普通 JSON/GET。

multipart 请求体（request 字段内容）：

```json
{
  "systemType": "自动测试系统-xxx",
  "networkSegment": "10.0.0.0/24",
  "deployLocation": "检验楼机房",
  "websiteUrl": "",
  "description": "自动化测试系统",
  "filingDate": "",
  "filingNumber": "",
  "assessmentOrg": "",
  "assessmentDate": "",
  "assetIds": []
}
```

关联资产接口：

| 项目 | 内容 |
|------|------|
| 下拉选项 | `GET /hsc-system-api/asset/options?_t={ts}` → `result: [{id, assetName, ip, assetType}]` |
| 按 ID 查详情 | `GET /hsc-system-api/asset/list-by-ids?ids=id1,id2&_t={ts}` |

### 13.8 个人信息保护 PIA 多步骤

| 项目 | 内容 |
|------|------|
| 保存风险评估（步骤 3） | `POST /hsc-system-api/personal-info-protection/pia/{taskId}/step/3` |
| 保存风险处置（步骤 5） | `POST /hsc-system-api/personal-info-protection/pia/{taskId}/step/5` |
| 人工修改判定结果 | `PUT /hsc-system-api/compliance/result/{resultId}` |

步骤 3 请求体：

```json
{
  "riskSources": [{"sourceType": "INTERNAL", "riskDesc": "风险源", "threatType": "网络攻击"}],
  "rightsImpacts": [{"dimension": "autonomy", "impactDesc": "影响自主选择", "impactLevel": 2}],
  "riskMatrix": [{"riskSourceId": 0, "riskDesc": "风险", "likelihood": 1, "impactLevel": 1, "riskScore": 1, "riskLevel": "low"}]
}
```

> **已知限制**：step/3、step/5 仅支持 UI 工作流创建的任务，API 创建的任务调用
> 会返回 500（自动化已兼容 skip）。

人工修改判定请求体：

```json
{"result": "符合", "remark": "人工判定为符合"}
```

`result` 取值：`符合` / `部分符合` / `不符合` / `不适用`。

---

## 14. 合规运营测试脚本

对应 55 框架 `compliance_operations/`：

```
compliance_operations/
├── __init__.py
├── utils_compliance.py      # 通用 /compliance/task + 11 typeCode + 只读接口
├── utils_system.py          # 管理系统 CRUD + 资产接口
├── utils_pia.py             # PIA 多步骤 + 判定结果
├── test_task_common.py      # 通用任务 CRUD + 生命周期 + 安全 + noAuth + 只读接口
├── test_type_codes.py       # 11 typeCode 参数化 + targetLevel 越界校验
├── test_system.py           # 管理系统 CRUD
└── test_pia.py              # PI 多 standard + 多步骤 + 判定
data/
├── compliance_task.yaml
└── compliance_type_codes.yaml
```

运行：

```bash
cd ~/hsc_auto_dev55
./venv/bin/pytest compliance_operations/ -q
```

### 14.1 测试覆盖统计

| 模块 | 用例数 | 说明 |
|------|--------|------|
| 通用任务 CRUD | 19 | 创建/查询/删除数据驱动 + 生命周期 + 安全 + noAuth + 只读接口 |
| 11 typeCode | 18 | 11 个正常创建 + 7 个 targetLevel 越界校验（xfail） |
| 管理系统 | 5 | CRUD 闭环 + 资产接口 + noAuth |
| 个人信息保护 | 7 | 3 standard 创建 + 必填校验 + 多步骤 + 判定 |

全量结果：**49 用例 = 39 passed + 3 skipped + 7 xfailed**。

### 14.2 已发现缺陷（55 环境）

| 缺陷 | 表现 | 标注 |
|------|------|------|
| targetLevel 越界未校验 | DJPC/SM/HR/EMR/MATURITY/SH/CONN 的 targetLevel 越界值被静默放行返回 200 | 7 个 xfail |
| 空/缺 taskName 未校验 | 返回 500「服务器开小差了」而非参数校验错误 | 用例走 assert_business_fail |

### 14.3 迁移要点（123 → 55）

1. **删除格式修正**：123 的 gdpr/internet_medicine 用 `batch?taskIds=`，55 统一改
   `DELETE /task/{id}`（batch 在 55 返回 500）。
2. **文件 ID 失效**：123 硬编码的 fileIds（如 8827）在 55 返回「无效文件ID」，
   已改用 55 实测有效的 `[3054]`/`[3058]`。
3. **去重合并**：13 个 utils + 13 个 test（26 文件）合并为 3 utils + 4 test（7 文件），
   10 个子模块复用 `/compliance/task` 通用接口仅 typeCode 不同。
4. **打印式用例清理**：123 大量「只 print 不真断言」的边界用例已提炼为有真实断言的
   数据驱动用例。
