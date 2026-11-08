# 千川大屏、巨量百应补充与 5 分钟归档

## 数据分工

| 指标 | 来源 | 说明 |
| --- | --- | --- |
| 消耗、净成交金额、净成交订单、净成交ROI | 千川直播大屏页面 | 直接抓取当前展示值，不使用 MCP 兜底 |
| 累计观看、商品点击、峰值在线、GPM、实时在线、曝光、流量渠道 | 千川直播大屏页面 | 无头 Chrome 每 10 秒抓取，字段相同则写入 5 分钟历史 |

任何字段抓取失败时直接标记失败并留空，不使用 MCP、其他通道或历史值冒充当前值。历史归档用于展示已成功抓取的整场 5 分钟节点。

五维四率单独按“MCP 优先、缺失字段回退大屏”处理；这不影响交易指标的大屏单源约束。

## 三方数据源优先级

1. 千川 MCP 是报表、分析和建议的主数据源。MCP 有值时，百应和千川大屏都不能覆盖。
2. MCP 缺渠道、人群画像或其他扩展指标时，优先使用巨量百应直播中控台的页面真实值，
   并在 `fieldSources` 中标记为 `buyin_live_screen`。
3. MCP 完全没有当前场核心交易指标时，百应核心指标可临时顶上；百应也不可用时才回退
   千川直播大屏。接口会同时返回 `buyinUsed`、`buyinSupplemented`、
   `qianchuanScreenUsed` 和 `fieldSources`，前端不会把回退值显示成 MCP。

百应只有明确返回“净成交金额 / 净成交订单 / 净成交ROI”时才允许顶替 MCP 的净成交
核心指标。若页面只返回普通“成交金额”或“支付金额”，采集器标记
`gmvScope=buyin_reported`，该值只能进入补充字段，不能作为净成交驱动投放诊断。

百应和千川使用不同的 Chrome profile、锁、状态文件和采集进程，两个页面的数字不会互相
覆盖。百应登录失效只显示 `login_required`，不会显示成“未开播”。

## 巨量百应直播中控台采集

首次登录：

1. 双击 `login-buyin.bat`。
2. 脚本以 1440×900 正常窗口、100% 页面比例打开巨量百应达人工作台官方登录页 `https://buyin.jinritemai.com/mpa/account/login?log_out=1&type=24`；`log_out=1` 只用于清掉旧的百应登录态。
3. 登录助手会自动点击右上角“切换为手机登录”，直接显示“手机号码 / 验证码 / 登录”。巨量百应与抖店是两个不同后台，不使用 `fxg.jinritemai.com/login`。
4. 登录后人工进入当前直播场次的“直播中控台”或“直播大屏”。推荐入口为
   `https://buyin.jinritemai.com/dashboard/live/control`。
5. 页面出现流量占比、成交金额占比、千次观看成交或其他可核验直播数值后，脚本会保存
   地址、Cookie、localStorage、sessionStorage，并交给后台无头采集器。

采集器文件：

- 配置：`data/buyin-live.json`
- 登录态：`data/buyin-chrome-profile/`、`data/buyin-live-session.json`
- 状态：`data/buyin-live-metrics.json`
- 锁与日志：`data/buyin-live-agent.lock`、`data/buyin-live-agent.log`
- 手动刷新请求：`data/buyin-live-refresh.request.json`

百应采集同时读取页面 DOM 表格和 JSON 网络响应。必需补充分组包括：

- 渠道：流量人数、流量占比、成交金额、成交金额占比、订单、渠道千次观看成交。
- 其他页面指标：商品点击率、成交转化率、平均停留、退款率/金额、互动率、曝光、
  评论、关注等；只保存页面实际出现且可以解析为数值的字段。
- 页面出现但尚未映射为固定名称的数值字段，写入 `extras`，保留原始标签、值、单位和
  来源；不会推测单位或补造数值。

健康检查：

- `GET /api/live/buyin`：百应采集器心跳、页面地址、指标、渠道和补充字段。
- `POST /api/live/buyin/refresh`：立即请求百应采集器抓取一轮，并等待同一
  `captureRequestId` 回传。

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

采集器在启动前以及每一轮抓取前都会调用本地 `/api/live/discover`。服务端从
`qianchuan.config.json` 读取当前广告账户配置的抖音号列表，逐个查询千川今日直播间
Open API，并查找 `room_status=LIVING` 的场次。默认覆盖图解、精讲、拆解、通解四个
账号。

识别到直播中 `room_id` 后，采集器使用实时返回的 `room_id`、广告主 ID 和可用主播 ID
动态生成新版 `board-next` 大屏地址。`data/live-screen.json` 中的 `pageUrl` 只保存最近
一次解析结果和登录恢复目标，不是直播间来源；切换账号或停播时不会继续使用其中的旧
roomId。

- 四个账号都成功查询且没有 `LIVING` 场次：`status=not_live`，页面明确显示“未开播”，
  清空当前指标、峰值和旧直播流。
- 任一账号查询失败：状态为 `discovery_error` 或 `discovery_incomplete`，页面显示
  “直播状态读取失败/不完整”，不能误报成“未开播”，也不会回退抓取旧场次。
- 发现接口瞬时失败不等于直播流已失效：状态仍按失败展示，但采集器不会清空当前场次
  已登记的短时流地址；20 秒周期续登记在服务或接口恢复后继续工作。只有确认未开播或
  明确换场时才重置旧场次和旧流。
- 多个账号同时开播：按配置顺序选择第一个 `LIVING` 场次，并在 `checkedAccounts` 中
  返回每个账号的检测结果，便于追踪。

### 官方 Open API 直出边界

`/api/live/discover` 会同时返回 `officialLive`，来自千川今日直播间 Open API 的直接
字段，不计算、不补差。当前已验证可返回：

- 场次和账号：`room_id`、`room_status`、`aweme_id`、`aweme_name`、`start_time`。
- 累计投放字段：`stat_cost`、净成交金额、净成交订单、净成交ROI、累计观看、观看满 1 分钟、
  商品点击、评论、关注和 `room_delivery`。
- 实时在线、峰值在线、GPM、成交订单成本、曝光人数：当前接口未返回，仍只能取直播
  大屏页面实际展示值。

2026-11-04 实测当前场次时，今日直播间接口返回的累计消耗、成交、订单和观看均为
`0`，而同一 roomId 的大屏已有非零真实值。因此 `officialLive.status=zero_pending`
时只作为官方对照通道，不覆盖大屏 KPI。`qianchuan/report/live/get/` 当前对今日和
历史日期均返回空 `data`，在拿到官方非空样例前不接入解析。

2026-11-05 起，`officialLive.status=ok` 时，累计观看、观看满 1 分钟、评论次数和成交
订单会在 MCP 未返回后补充五维四率，并写入 5 分钟历史中原本缺失的字段；大屏已有值
始终优先。`zero_pending` 时整组官方累计值被忽略，避免用 0 覆盖大屏真实值。实时在线、
峰值在线、GPM、订单成本和曝光人数仍只取大屏实际展示值。

大屏交易口径固定为“净成交”：净成交金额、净成交订单、净成交ROI 和净成交订单成本。
开放接口对应字段分别为 `total_order_settle_amount_for_roi2_1h`、
`total_order_settle_count_for_roi2_1h`、`total_prepay_and_pay_settle_roi2_1h`、
`total_cost_per_pay_order_settle_for_roi2_1h`。总成交只保留为审计字段，不与净成交混算。

渠道明细直接读取大屏 `statQuery` 的 `combined_first_compass_entrance_code` 行：
`total_live_watch_cnt_for_roi2` 作为渠道流量人数，
`total_live_pay_amt_for_roi2` 作为渠道成交金额；流量占比、成交金额占比按渠道合计计算，
渠道千次观看成交 = 渠道成交金额 ÷ 渠道流量人数 × 1000。该明细仅用于大屏范围，
MCP 有数据时仍以 MCP 为报表、分析和建议的主数据源。

百应专业版直播大屏可用时优先读取其“流量分析”原生列：
`渠道名称 / 流量占比 / 成交金额占比 / 渠道千次观看成交`。此时接口返回
`flowValueKind=native`，渠道行来源为 `buyin_compass_live_screen_dom`，不再二次计算
成交占比或 GPM。只有百应专业版不可用时，才回退到千川 `statQuery` 的原始流量人数和
成交金额计算，并返回 `flowValueKind=calculated`；前端来源说明明确写为
“千川大屏网络原始行计算（非页面直接展示）”。

大屏不返回历史原生峰值时，`peakOnline` 标记为 `observed_since_capture`，表示采集器启动后观测到的最高“实时在线人数”；该值不会冒充千川原生历史峰值。

手动刷新通过 `POST /api/live/refresh` 写入 `data/live-screen-refresh.request.json`。采集器在等待周期内检测到请求后会立即开始下一轮抓取，并在状态文件中回传同一 `captureRequestId`；后端只接受匹配的请求 ID，随后绕过 10 秒缓存生成新版 `/api/live` 快照。前端在加载期间显示“正在拉取最新数据...”，完成后直接应用该快照。

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
- 千川和百应两个无头采集器分别巡检、分别重启。
- 任一采集器心跳超过约 45 秒时强制重启对应进程。

注意：该启动策略会结束本机其他 Python 程序。

健康检查：

- `GET /api/health`：`liveScreenCapture` 为行为通道心跳。
- `GET /api/live/screen`：查看无头 Chrome 当前状态、抓取时间和错误。
- `GET /api/live/buyin`：查看巨量百应直播中控台采集状态和补充字段。
- `GET /api/live?account=fashion`：查看大屏直抓、五维四率来源与 5 分钟历史归档。

## 复盘整场录制

`live_watchdog.py` 同时守护 `live_recorder.py`。录像器读取
`GET /api/live/stream/status` 和 `/api/live/screen`，只在千川签名画面流可用且当前
场次直播时录制，不使用 MCP 或其他指标补造视频。

- 录像根目录：坚果云目录之外的 `D:\DAI投放产品录屏备份\`。
- 单场目录：`D:\DAI投放产品录屏备份\<YYYY-MM-DD>_<roomId>_<HHMMSS>\`。
- 视频格式：5 分钟一个 MPEG-TS 分段，程序维护 `index.m3u8`；场次结束后尝试通过
  ffmpeg concat 合并 `session.mp4`。
- 断流或服务重启：90 秒内等待同一 roomId 的画面流重新注册；恢复后继续使用原目录和
  后续分段号，避免把同一场拆成多个场次。
- 保留策略：最多保留最近 10 个自然日；录像器启动时和跨日运行后自动删除最早日期目录。
- `GET /recordings/.../session.mp4` 支持 HTTP Range，可拖动复盘播放器进度条。

复盘接口 `GET /api/review/sessions?account=...` 将本地录像清单与千川直播大屏 5 分钟
历史按日期、roomId 合并，返回真实消耗、净成交、订单、ROI、节点序列和本地规则标注。
返回内容同时包含 `dataSources`、`analysisSteps` 和 `sourceNote`，页面在原复盘版位内展示。
ASR 未接入时话术线留空，主播风格、情绪、人脸与样貌匹配显示“未接入”，不生成虚构结果。

## 本地 Whisper 话术分析

`live_asr.py` 由看门狗常驻守护，输入是 `D:\DAI投放产品录屏备份\` 中已经从直播流录制完成的 TS
分段，不读取电脑麦克风，也不调用第三方付费 ASR。

1. 每个 5 分钟直播分段完成后，ffmpeg 抽取对应的 16k 单声道 FLAC 到该场次 `asr/audio/`。
2. 使用项目本地 `models/whisper-tiny/` 的 `faster-whisper-tiny` CPU INT8 模型按 5 分钟粒度转写中文。
3. OpenCC 将繁体输出统一转成简体中文。
4. ASR 服务每约 5 秒记录在线人数、消耗、成交、订单到 `asr/metrics.json`。
5. `recording_store.analyze_speech()` 按每句话的绝对起止时间与指标采样对齐，标记：
   - `对应窗口出单`
   - `对应窗口掉人`
   - `对应窗口留人`
   - `无明显变化`

这些标签表示同一时间窗口的相关变化，不表示话术与成交存在确定因果关系。转写结果保存到
`asr/transcript.json`，并进入原有复盘问题/优势列表、话术曲线和结论区。

首次换机可运行 `install-whisper.bat` 安装开源依赖并从镜像下载 `tiny` 模型。模型只保存在
项目本机 `models/whisper-tiny/`，不调用付费 API。

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
- 百应 `config_required`：尚未完成百应登录，运行 `login-buyin.bat`。
- 百应 `login_required`：百应 Cookie 失效，重新运行 `login-buyin.bat`；这不是未开播。
- `login_required`：Cookie 失效。页面和接口统一显示“登录已过期，请重新登录”，不会降级成“未开播”或“未返回”；运行 `login-live-screen.bat` 重新登录。
- `not_live`：四个配置账号均查询成功，但没有正在直播的场次。
- `discovery_error` / `discovery_incomplete`：至少一个账号查询失败，不能据此判定未开播。
- `no_metrics`：页面已打开，但标签未匹配；检查页面语言、DOM 文案和 `labels` / `selector`。
- 采集器反复重启：检查 `data/live-screen-agent.log` 和 `data/live-watchdog.log`；若出现 `The browser is already running`，确认只有一个项目 Node 进程且启动前残留锁已清理。

`data/live-screen.json`、`data/chrome-profile`、`data/live-screen-metrics.json` 均含本机登录信息或经营数据，不能提交到公开仓库。
