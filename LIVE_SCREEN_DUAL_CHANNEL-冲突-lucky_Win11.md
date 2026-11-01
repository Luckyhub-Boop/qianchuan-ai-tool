# 直播大屏双通道

## 数据分工

| 指标 | 主来源 | 兜底与校验 |
| --- | --- | --- |
| 消耗、成交金额、成交单量、成交订单成本、ROI | 千川大屏页面退款前口径，每 10 秒抓取 | 大屏字段缺失时，MCP `qianchuan_report_uni_promotion_get_v1` 仅作兜底和交叉校验 |
| 累计观看、商品点击、峰值在线、GPM | 千川大屏页面，每 10 秒抓取 | 不从交易指标反算 |

交易 KPI 默认直接采用大屏当前显示值。`GET /api/live` 使用
`transactionSource=qianchuan_live_screen` 和 `tradeRefundPolicy=before_refund`
表示主交易字段来自退款前的大屏页面；大屏字段不完整时，
`transactionSource=qianchuan_mcp` 明确标记为 MCP 兜底，不能冒充大屏原值。
两通道独立更新，失败字段保留上一次有效值并标记延迟，不从其他指标反算。

## 新版 EBP 地址格式

新版直播分析列表：

```text
https://business.oceanengine.com/ebp/data-analysis/live-analysis/list?ebpid=<EBP_ID>
```

单场直播详情：

```text
https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?ebpid=<EBP_ID>&roomId=<LIVE_ROOM_ID>
```

`uuid` 由 EBP 页面动态生成，不是固定业务参数。旧版 `qianchuan.jinritemai.com/board-next?live_room_id=...` 不再作为采集入口。

## 当前直播场次识别

采集器按以下顺序选择场次：

1. 在新版 EBP 直播列表的 `tr` 行中查找包含“直播中”和 `ID:` 的行；优先使用第一个“直播中”场次，并读取该行第二个 `ID:` 作为抖音号 ID。
2. EBP 列表尚未收录当前全域直播时，调用本地 `/api/live/discover`，通过千川今日直播间 Open API 查询 `room_status=LIVING` 的场次。
3. 识别到直播中 `room_id` 后，通过新版 EBP SSO 跳转 `board-next` 直播大屏。

不会把“已结束”行当成当前直播，也不会再取列表第一条作为兜底。

大屏不返回历史原生峰值时，`peakOnline` 标记为 `observed_since_capture`，表示采集器启动后观测到的最高“实时在线人数”；该值不会冒充千川原生历史峰值。

## 首次安装

1. 安装 Node.js 20+。
2. 在项目目录执行 `npm install`。
3. 双击 `login-live-screen.bat`。
4. 登录脚本会打开新版 EBP 地址 `https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1`，完成登录后进入直播大屏。
5. 地址出现 `live_room_id` / `roomId`，或页面出现累计观看/商品点击/峰值在线/GPM 后，脚本会写入 `data/live-screen.json` 并结束。

登录态保存在 `data/chrome-profile`。Cookie 有效时，无头 Chrome 后续运行不会再要求扫码。
登录脚本会先写入 `data/live-screen-pause`，让看门狗暂时停掉无头采集器，避免同一 profile 被占用；登录结束后自动移除标记并恢复采集。

## 开机自启

首次部署完成后，双击一次 `install-autostart.bat`。安装器会创建当前 Windows 用户的登录自启计划任务：

- Windows 登录后等待 15 秒自动启动，不打开浏览器窗口。
- `start-autostart-loop.ps1` 负责守护 `start-background.ps1`，脚本异常退出后 30 秒重新拉起。
- `start-background.ps1` 负责从 PATH、项目目录、项目 `runtime/` 和本机 Codex 运行时查找 Node.js/Python，然后启动 `live_watchdog.py`。
- `live_watchdog.py` 持续守护 `server.py` 和 `live-screen-agent.js`；采集器退出或心跳超时后自动重启。
- 采集器首次启动有 60 秒加载宽限，避免千川页面首次加载超过 20 秒时被误判为卡死。
- 计划任务自身异常退出时，Windows 每分钟尝试重新启动，最多 999 次。
- 如果 Windows 安全策略禁止创建计划任务，安装器会退回到当前用户的 Startup 文件夹，不依赖管理员权限。

查看自启及重启链路：

- `data/live-autostart.log`：计划任务、启动循环、运行时缺失和每轮重启记录。
- `data/live-watchdog.log`：服务与采集器拉起、崩溃、心跳超时和暂停记录。
- `GET /api/health`：服务与 `liveScreenCapture` 健康状态。
- `GET /api/live/screen`：行为通道完整心跳和最近一次抓取结果。

卸载自启但保留程序文件，双击 `uninstall-autostart.bat`。

注意：采集器使用当前 Windows 用户的 `data/chrome-profile` 登录态，因此自启发生在用户登录后，不是在尚未登录的 Session 0 中。首次部署仍需要 Node.js 20+、Python 3.10+ 和 `npm install`。

## 日常启动

双击 `start.bat`。启动脚本会运行 `live_watchdog.py`：

- 每次启动前强制结束本机所有 `python / pythonw / py` 进程。
- 清理本项目遗留的 `live-screen-agent.js` 和 `data/chrome-profile` 无头 Edge 进程。
- 清理占用服务端口的旧进程，确保每次 `start.bat` 都创建新的服务进程。
- 主服务异常退出时自动重启。
- 无头采集器退出时自动重启。
- 采集器心跳超过约 45 秒时强制重启。

注意：该启动策略会结束本机其他 Python 程序。

安装开机自启后，日常开机不需要再双击 `start.bat`。如果需要打开网页看板，再双击 `start.bat` 即可。

健康检查：

- `GET /api/health`：`liveScreenCapture` 为行为通道心跳。
- `GET /api/live/screen`：查看无头 Chrome 当前状态、抓取时间和错误。
- `GET /api/live?account=fashion`：查看交易与行为两通道合并结果。

## 页面标签校准

默认按标签文本识别累计观看、商品点击、峰值在线、GPM、消耗、成交金额、
成交单量、成交订单成本和 ROI。若千川页面改版，复制
`live-screen.example.json` 为 `data/live-screen.json`，调整对应
`metrics.*.labels`，也可为单个指标设置 CSS `selector`。

交易字段的默认标签：

- 消耗：`整体消耗`、`广告消耗`、`实时消耗`、`消耗`
- 成交金额：`整体成交金额`、`累计成交金额`、`直播间成交金额`、`成交金额`
- 成交单量：`整体成交订单数`、`整体成单数`、`成交订单数`、`成交订单`、`成交单量`
- 成交订单成本：`整体成交订单成本`、`成交订单成本`、`订单成本`、`转化成本`
- ROI：`整体支付ROI`、`整体ROI`、`支付ROI`、`ROI`

成交金额会排除包含 `GPM` / `千次观看` 的文本，成交单量会排除包含
`成本` / `率` 的文本，避免把 GPM 或成交订单成本误识别为成交和单量。

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
- `login_required`：Cookie 失效，关闭占用 profile 的采集器后重新登录。
- `no_metrics`：页面已打开，但标签未匹配；检查页面语言、DOM 文案和 `labels` / `selector`。
- 采集器反复重启：检查 `data/live-screen-agent.log` 和 `data/live-watchdog.log`。

`data/live-screen.json`、`data/chrome-profile`、`data/live-screen-metrics.json` 均含本机登录信息或经营数据，不能提交到公开仓库。
