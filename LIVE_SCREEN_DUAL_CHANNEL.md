# 直播大屏直抓与 5 分钟归档

## 数据分工

| 指标 | 来源 | 说明 |
| --- | --- | --- |
| 消耗、成交、订单、ROI | 千川直播大屏页面 | 直接抓取当前展示值，不使用 MCP 兜底 |
| 累计观看、商品点击、峰值在线、GPM、实时在线、曝光、流量渠道 | 千川直播大屏页面 | 无头 Chrome 每 10 秒抓取，字段相同则写入 5 分钟历史 |

任何字段抓取失败时直接标记失败并留空，不使用 MCP、其他通道或历史值冒充当前值。历史归档用于展示已成功抓取的整场 5 分钟节点。

五维四率单独按“MCP 优先、缺失字段回退大屏”处理；这不影响交易指标的大屏单源约束。

## 新版 EBP 地址格式

新版直播分析列表：

```text
https://business.oceanengine.com/ebp/data-analysis/live-analysis/list?ebpid=<EBP_ID>
```

单场直播详情：

```text
https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?ebpid=<EBP_ID>&roomId=<LIVE_ROOM_ID>
```

`uuid` 由 EBP 页面动态生成，不是固定业务参数。配置地址只接受两类：`business.oceanengine.com` 的 EBP 直播分析大屏，或任何带 `live_room_id` / `roomId` 的地址。旧版 `qianchuan.jinritemai.com/uni-prom` 和没有 roomId 的旧 `/board-next` 会被拒绝；检测到旧版 `pageUrl` 时会立即清空并提示重新登录。

## 当前直播场次识别

采集器按以下顺序选择场次：

1. 在新版 EBP 直播列表的 `tr` 行中查找包含“直播中”和 `ID:` 的行；优先使用第一个“直播中”场次，并读取该行第二个 `ID:` 作为抖音号 ID。
2. EBP 列表尚未收录当前全域直播时，调用本地 `/api/live/discover`，通过千川今日直播间 Open API 查询 `room_status=LIVING` 的场次。
3. 识别到直播中 `room_id` 后，通过新版 EBP SSO 跳转 `board-next` 直播大屏。

不会把“已结束”行当成当前直播，也不会再取列表第一条作为兜底。

大屏不返回历史原生峰值时，`peakOnline` 标记为 `observed_since_capture`，表示采集器启动后观测到的最高“实时在线人数”；该值不会冒充千川原生历史峰值。

## 首次安装

1. 项目内必须保留 `runtime\node\node.exe` 和已安装的 `node_modules\puppeteer-core`。
2. 双击 `login-live-screen.bat`；脚本固定使用项目 runtime Node，不依赖系统 PATH。
3. 登录脚本会打开新版 EBP 地址 `https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1`，完成登录后进入直播大屏。
4. 只有地址出现 `live_room_id` / `roomId`，或页面至少出现累计观看、商品点击、峰值、GPM、消耗、成交中的 2 项时，脚本才写入 `data/live-screen.json`。首页和旧版页面不会覆盖已有地址。

登录态保存在 `data/chrome-profile`。Cookie 有效时，无头 Chrome 后续运行不会再要求扫码。
登录脚本会先写入 `data/live-screen-pause`，让看门狗暂时停掉无头采集器；登录模式会等待单实例锁释放后再打开可见浏览器，避免同一 profile 被占用。登录结束后自动移除标记并恢复采集。

采集器使用 `data/live-screen-agent.lock` 保证单实例；看门狗拉起前先检查锁和 PID。启动时会清理 `SingletonLock`、`DevToolsActivePort`、`DevToolsActivePort-*`、`lockfile` 等崩溃残留；正常退出、SIGINT / SIGTERM 和异常退出都会关闭浏览器并释放锁。

采集器每 5 秒刷新一次心跳，即使 EBP 页面加载或三个页签抓取超过 45 秒，也不会被看门狗误判为卡死。看门狗另有 180 秒启动宽限，覆盖首次浏览器启动和页面加载。

## 日常启动

双击 `start.bat`。启动脚本会运行 `live_watchdog.py`：

- 每次启动前强制结束本机所有 `python / pythonw / py` 进程。
- 清理本项目遗留的 `live-screen-agent.js` 和 `data/chrome-profile` 无头 Edge 进程。
- 清理占用服务端口的旧进程，确保每次 `start.bat` 都创建新的服务进程。
- 主服务异常退出时自动重启。
- 无头采集器退出时自动重启。
- 采集器心跳超过约 45 秒时强制重启。

注意：该启动策略会结束本机其他 Python 程序。

健康检查：

- `GET /api/health`：`liveScreenCapture` 为行为通道心跳。
- `GET /api/live/screen`：查看无头 Chrome 当前状态、抓取时间和错误。
- `GET /api/live?account=fashion`：查看大屏直抓、五维四率来源与 5 分钟历史归档。

## 页面标签校准

默认按标签文本识别四个指标。若千川页面改版，复制 `live-screen.example.json` 为 `data/live-screen.json`，调整对应 `metrics.*.labels`，也可为单个指标设置 CSS `selector`。

```json
{
  "metrics": {
    "watchCount": {
      "labels": ["累计观看人数", "累计观看", "观看人数"],
      "selector": ""
    }
  }
}
```

`data/live-screen-metrics.json` 中会记录每个指标的匹配文本和置信度，便于定位误识别或缺失。

## 排障

- `config_required`：尚未完成首次登录，运行 `login-live-screen.bat`。
- `login_required`：Cookie 失效。页面和接口统一显示“登录已过期，请重新登录”，不会降级成“未开播”或“未返回”；运行 `login-live-screen.bat` 重新登录。
- `no_metrics`：页面已打开，但标签未匹配；检查页面语言、DOM 文案和 `labels` / `selector`。
- 采集器反复重启：检查 `data/live-screen-agent.log` 和 `data/live-watchdog.log`；若出现 `The browser is already running`，确认只有一个项目 Node 进程且启动前残留锁已清理。

`data/live-screen.json`、`data/chrome-profile`、`data/live-screen-metrics.json` 均含本机登录信息或经营数据，不能提交到公开仓库。
