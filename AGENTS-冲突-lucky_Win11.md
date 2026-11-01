# AGENTS.md

本文件面向在本仓库工作的 AI 助手，说明项目背景、技术选型与必须遵守的约定。

最近更新：2026-10-23

## 0. 换电脑交接（先读）

### 0.1 当前可运行结论

- 产品是一个单页 Web 看板，入口为 `index.html`，本地数据服务为 `server.py`，默认访问地址是 `http://127.0.0.1:8765/`。
- Python 服务端仍只使用标准库；直播大屏行为通道新增 Node.js + `puppeteer-core`，只影响大屏观看/点击/峰值/GPM 采集，不影响 Python 主服务和历史素材快照。
- 数据页、素材页和今日直播间已接通真实链路；数据页直播大屏优先读取千川大屏页面上的退款前交易指标（消耗、成交金额、成交单量、成交订单成本、ROI）和观看/点击/峰值/GPM，MCP 仅在交易字段缺失时兜底并明确标记。
- 当前唯一真实广告主为 `1744479430946824`，当前授权主体为企业 BP 账户 `1855365007750474`。其他广告主没有授权时不能凭账户 ID 伪造接入。
- 交接时最近一次可核实快照为 revision 984、同步时间 `2026-10-21T10:34:04+08:00`：5 条计划、5 个抖音号、2,226 条素材、1,316 条非零跑量；视频与直播间画面素材合计消耗 63,892.25、成交 42,671.46、254 单。数值会随同步变化，以 `/api/health` 和快照为准。

### 0.2 换电脑必须复制的文件

建议复制整个 `AI投放工具` 目录，但排除本机浏览器缓存和临时目录：

- 必须：`server.py`、`index.html`、`start.ps1`、`start.bat`、`start-background.ps1`、`start-autostart-loop.ps1`、`install-autostart.ps1`、`install-autostart.bat`、`uninstall-autostart.ps1`、`uninstall-autostart.bat`、`runtime/`、`vendor/`、`test_server.py`、`test_live_watchdog.py`、`qianchuan.config.example.json`、`AGENTS.md`、`PRD.md`、`package.json`、`package-lock.json`、`live-screen-agent.js`、`live-screen-agent.test.js`、`live_watchdog.py`、`login-live-screen.bat`、`live-screen.example.json`、`LIVE_SCREEN_DUAL_CHANNEL.md`。
- 需要继续同步千川时必须：`data/qianchuan-token.json`。该文件包含访问令牌，只能通过安全方式迁移，不能提交到公开仓库或发送到群聊。
- 需要使用千川 MCP 直播大屏数据时必须：`data/qianchuan-mcp.json`。该文件包含 MCP API Key URL，只能通过安全方式迁移。
- 需要保留无头 Chrome 登录态时必须安全迁移 `data/live-screen.json` 和 `data/chrome-profile/`；两者包含直播大屏地址/Cookie，不能提交或外发。若不迁移，在新电脑执行一次 `login-live-screen.bat` 即可。
- 需要离线查看已同步数据时：`data/qianchuan-snapshot.json`。该文件包含真实经营数据，也应按敏感业务数据管理。
- 需要自动采集直播大屏画面时：`live-capture-extension/`，并在新电脑浏览器中重新“加载解压缩扩展”。
- 不要迁移：`.edge-profile*`、`.tmp-*`、`__pycache__/`、`data/hls/` 等本机缓存或临时产物。截图文件可用于验收，但不是运行依赖。

### 0.3 新电脑启动步骤

1. 安装 Python 3.10+ 和 Node.js 20+，确保 `python`、`node`、`npm` 命令可用；也可在 `start.ps1` 中加入本机 Python 路径，用 `QIANCHUAN_NODE` 指定 Node。
2. 将整个项目放到固定目录，不要依赖旧电脑的 `D:\ai投放产品\我的坚果云` 绝对路径。
3. 确认新电脑可以访问 `https://api.oceanengine.com`，并从安全存储中恢复 `data/qianchuan-token.json`；也可通过环境变量 `QIANCHUAN_ACCESS_TOKEN` 注入令牌。
4. 需要自定义接口、分页或账户配置时，复制 `qianchuan.config.example.json` 为 `qianchuan.config.json` 后修改。当前这台电脑没有正式配置文件，默认配置由 `server.py` 提供。
5. 首次安装执行 `npm install`，再双击 `login-live-screen.bat`。脚本打开新版 EBP 入口 `https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1`；登录并进入直播大屏后，检测到 `live_room_id` 或大屏指标标签即自动保存地址和 Cookie。旧版 `qianchuan.jinritemai.com` 地址会被拒绝。
6. 首次部署双击一次 `install-autostart.bat`，创建 Windows 登录自启；正常开机登录后无需再手动启动采集器。需要打开网页看板时双击 `start.bat`，或执行 `.\start.ps1`。
7. 打开 `http://127.0.0.1:8765/api/health` 检查 `ok`、`liveScreenCapture`、MCP 和凭证状态；`GET /api/live/screen` 可单独查看行为通道心跳，`data/live-autostart.log` 可查看自启链路。
8. 验证回归：执行 `python -m unittest -v test_server.py`（预期 33 个用例）、`python -m unittest -v test_live_watchdog.py`（预期 7 个用例）和 `npm run test:live-screen`。
9. `live-capture-extension` 仍可作为传统浏览器画面采集备用方案；双通道行为指标默认由无头 Chrome 采集，不需要常驻可见大屏。

启动策略：`start.ps1` 在每次启动前会强制结束本机所有 `python.exe`、`pythonw.exe`、`py.exe`，清理本项目遗留的 `live-screen-agent.js` 与 `data/chrome-profile` Edge 进程，并释放服务端口，确保每次双击 `start.bat` 都创建全新进程。该策略会影响本机其他 Python 程序。

可用环境变量：

| 环境变量 | 用途 | 是否必需 |
| --- | --- | --- |
| `QIANCHUAN_ACCESS_TOKEN` | 直接注入千川 Open API 令牌 | 与 token 文件二选一 |
| `QIANCHUAN_MCP_URL` | 覆盖 `data/qianchuan-mcp.json` 中的远程 MCP 地址 | 否 |
| `QIANCHUAN_TOKEN_FILE` | 指定非默认 token 文件路径 | 否 |
| `QIANCHUAN_ADVERTISER_IDS` | 逗号分隔的广告主 ID，覆盖默认账户列表 | 否 |
| `QIANCHUAN_PORT` | 本地服务端口，默认 `8765` | 否 |
| `QIANCHUAN_SYNC_INTERVAL_SECONDS` | 服务端同步间隔 | 否 |
| `QIANCHUAN_FFMPEG` | ffmpeg 可执行文件路径 | 使用 RTMP/FLV 转码时需要 |
| `QIANCHUAN_NODE` | Node.js 可执行文件路径 | 看门狗找不到 `node` 时需要 |
| `QIANCHUAN_BROWSER_PATH` | Chrome / Edge 可执行文件路径 | 自动探测失败时需要 |

### 0.4 新电脑常见阻塞

- 千川接口返回鉴权错误：确认 token 未过期，且新电脑使用的是有该广告主权限的同一开发者和授权主体。
- 页面没有数据但服务健康：先检查是否选中了零跑量抖音号；切到“总览”或“赵镭图解/赵镭精讲”账号。
- `WinError 10013`：通常是运行环境禁止本地套接字或外部网络。用正常 PowerShell 启动 `start.ps1`，不要在受限沙箱内运行同步。
- 直播画面不出现：先检查扩展是否加载、千川直播大屏是否登录并打开、`/api/live` 是否返回 `captured:true`。
- 双通道行为指标为空：运行 `login-live-screen.bat` 重新进入直播大屏，再检查 `GET /api/live/screen`；`config_required` 表示未保存地址，`login_required` 表示独立 profile 登录态失效。
- 采集器反复重启：检查 `data/live-screen-agent.log`、`data/live-watchdog.log`，确认 `node_modules/puppeteer-core` 存在且没有其他进程占用 `data/chrome-profile`。
- 开机后采集器未启动：运行 `Get-ScheduledTask -TaskName QianchuanLiveScreenAutostart` 检查任务状态，并查看 `data/live-autostart.log`；若提示 Node.js/Python 缺失，先完成运行时安装。计划任务被安全策略禁用时，重新运行 `install-autostart.bat` 会退回到当前用户 Startup 文件夹。
- RTMP/FLV 无法转码：新电脑安装 ffmpeg 或设置 `QIANCHUAN_FFMPEG`，脚本和 `server.py` 会自动探测常见路径。

### 0.5 模块进度总览

| 模块 | 当前状态 | 真实数据 | 主要未完成项 |
| --- | --- | --- | --- |
| 数据 | 部分可用 | 全域推广报表 + 大屏退款前交易/行为指标；MCP 兜底校验 | 首次登录、页面标签校准、180 天历史未回填 |
| 素材 | 可用 | 视频与直播间画面跑量、完播率、平均停留 | 素材人群画像 |
| 诊断 | 部分可用 | 今日直播间指标、直播画面、流量/用户/商品 | ASR、主播状态识别、曝光人数 |
| 话术 | 部分可用 | 本地词库上传 | 真实 ASR、逐句归因、优质/低效话术统计 |
| 投放诊断 | 部分可用 | 直播流量渠道和人群画像 | 知识库解析、真实操作 API、AI 建议 |
| 复盘 | 演示为主 | 直播流可看 | 录像存储、回放切片、人脸与视频理解 |
| AI 模型 | 未接入 | 无 | DeepSeek 诊断与建议生成 |

## 1. 项目定位

千川 AI 投放诊断工具。

核心目标是让投手从**操作者**变成**盯盘者**：把日常盯盘、异常发现、原因诊断这类重复劳动交给 AI，投手只做决策和关键操作。

## 2. 技术栈

- 界面：网页（Web）
- 模型：DeepSeek
- 数据源：千川 API

具体框架与依赖以实际代码为准。尚未确定的选型不要擅自引入新框架或新依赖。

## 3. 数据口径

所有指标与千川后台逐字段对齐。数据页顶部“全域推广报表数据”使用 `total_pay_order_gmv_for_roi2`（用户实际支付金额），属于退款后口径，必须标为“用户实付 · 退款后”，不能与直播大屏退款前成交混用。

- 指标的名称、定义、单位、统计周期、归因规则，一律以千川后台展示为准。
- 与后台字段一对一映射，不合并、不改名、不做二次加工口径。
- 计算出的数值与千川后台不一致时，以千川后台为准，并记录到「踩坑记录」。
- 新增指标前，先确认千川后台存在对应字段，并在本节登记口径。
- 千川账户与抖音开播账号一一绑定；切换账号后，页面数据必须跟随当前抖音号。
- 总看板总账户使用千川广告主账户/全域计划账户口径，不能把抖音号作者维度归因简单相加后冒充后台总账户；抖音号列表只用于归因拆分，归因差额单独展示。
- 数据页直播大屏以千川大屏页面为交易主口径：消耗、成交金额、成交单量、成交订单成本、ROI 直接取页面实际展示的退款前值；累计观看、商品点击、峰值在线、GPM 取同一无头 Chrome 抓取的页面值。交易字段缺失时才使用 MCP `qianchuan_report_uni_promotion_get_v1` 兜底，并返回 `transactionSource=qianchuan_mcp` 明确标记，不能把 MCP 值冒充大屏原值。
- MCP 兜底优先使用 `total_pay_order_gmv_include_coupon_for_roi2`（整体成交金额），ROI 按整体成交金额 ÷ 消耗计算；`total_pay_order_gmv_for_roi2`（用户实际支付金额）只作为旧接口兼容回退。`total_cost_per_pay_order_for_roi2` 对应成交订单成本。
- 大屏行为指标只接受页面实际显示并可匹配到标签的值；四个核心标签（累计观看、商品点击、峰值在线、GPM）任一缺失时标记部分字段，不按其他指标反推。页面结构变化时通过 `data/live-screen.json` 的 `metrics.*.labels` 或 `selector` 校准。
- 直播间五维四率（诊断页）：五维取千川今日直播间接口的场次累计值——进入 = 累计观看人数 `total_live_watch_cnt`，停留 = 观看满 1 分钟人数 `live_watch_one_minute_count`，互动 = 累计评论次数 `total_live_comment_cnt`，成交 = 成交订单数；曝光人数接口未返回，曝光层与「曝光→进入率」标记为待接入，不补造。
- 四率口径：进入→停留 = 1 分钟观看 ÷ 累计观看；停留→互动 = 评论次数 ÷ 1 分钟观看（评论是次数不是人数，只作趋势参考）；观看→成交 = 成交订单 ÷ 累计观看，与 PRD 转化率一致。
- 诊断页实时建议阈值属于运营经验值，不是千川后台口径：进入→停留 30%、停留→互动 10%、观看→成交 2%、ROI 1、付费流量占比 70%；页面需明确标注参考线。后续预测按本场当前节奏线性外推到 4 小时场次，只作参考，不写成承诺值。
- 素材页统计窗口为含当天的近 7 个自然日。视频和直播间画面分别调用千川素材维度报表，逐日数据按素材 ID 汇总；消耗、成交、订单、展示、点击、完播率和平均停留取千川返回值，点击率与 ROI 由汇总分子/分母重新计算。
- 素材综合分分项先归一，再按展示 30%、转化（成交订单）30%、点击 30%、其他（ROI）10% 加权；适合放量取综合分 TOP 5，适合追投优先取消耗不高于样本中位数且已有成交的素材，不足 5 条时用其余有跑量素材补齐。
- 素材报表是素材维度归因，素材合计不强行拼接到计划总消耗。标题、其他创意等归因会和视频/直播间画面形成口径差异，不能用差额反推或补造素材。

## 4. 已完成

- PRD v2 已落库。
- 纯前端数据看板首版：核心指标、趋势图、日期范围。
- 顶部功能导航：数据、素材、诊断、话术、投放诊断、复盘。
- 账号切换入口、账号隔离与总看板汇总校验骨架。
- 素材页：TOP 10 综合分、追投/放量清单、全量素材数据表与人群画像；综合分按展示 30%、转化（订单）30%、点击 30%、其他（ROI）10% 加权，适合追投与适合放量各展示 TOP 5；素材报表使用独立近 7 天窗口并每 2 分钟刷新；千川计划名日期统一压缩为 `2026.6.30` 格式。
- 素材跑量报表已切换到千川官方 `/open_api/v1.0/qianchuan/report/uni_promotion/data/get/`：视频主题按抖音号、投放方式、下单平台过滤并分页拉取逐日数据，再按素材 ID 汇总消耗、成交、订单、展示、点击、完播率和平均停留；直播间画面使用独立主题和字段集。
- 复盘页：只保留录制状态、录像回放、时间轴问题/优势标注、主播画像与赛后整体结论；直播中的实时监控已并入诊断页。
- 回放折线图：话术、流量、成交影响复盘，支持 1/5/30 分钟颗粒度与人群画像悬停。
- 主播画像：个人信息、风格/状态评估、历史录屏上传学习、时段与话术匹配。
- 主播库联动：样貌匹配主播、历史出单节奏叠加到回放折线图，并生成综合复盘。
- 诊断页（直播间实时诊断）：实时监控看板（9 项实时 KPI、直播大屏、累计消耗/成交曲线、人货场状态、五维四率漏斗、实时建议、后续预测、实时事件），页内提供「实时数据」「在投素材」「五维四率」三个专属页签，不再跳转到账号级数据/素材页。直播大屏与曲线上下相邻、共用同一时钟。
- 直播大屏播放链路：支持 m3u8（Edge 原生 / hls.js）、flv（flv.js）、mp4/webm（原生）；RTMP / HTTP-FLV 可由后端 `StreamTranscoder` 调 ffmpeg 转成本地 HLS（`/hls/<key>/index.m3u8`）。千川直播大屏的签名 HTTP-FLV 由本机 `live-capture-extension` 从真实媒体请求自动采集，按 roomId 仅在服务端内存保留 30 分钟；诊断页优先走 `/api/live/stream.flv?room=...` 本机代理，失败时回退浏览器直连 FLV。指标接口暂时失败但已捕获画面时，页面显示 `STREAM` 并明确标注指标暂不可用，不伪造直播指标。仍支持 `live.streamUrl`、页面本地地址与 `?stream=<url>` 调试。
- 话术页：违禁词大全（本地 TXT/CSV 上传、批量粘贴、分类筛选与版本记录）、主播优质话术集选与参考合集、持续低效话术清单。
- 实时话术看板：逐句展示 ASR 语句，4 秒延迟归因评论、停留和成交影响，含实时评论与逐句影响曲线。
- 投放诊断页：实时流量渠道与人群画像、下一手建议、投放知识库文档上传、千川四类操作台与操作后流量影响、流量异常时段看板。
- 千川 MCP：已加载 `qianchuan` HTTP MCP，首个真实广告账户已接入数据页。
- 数据页真实数据：`TT-申坤-赵镭老师(店播)-小学数学-自运营`（`1744479430946824`），口径为千川全域推广，当前快照已写入 2026-10-12 至 2026-10-20 的消耗、用户实付成交金额与成交订单；10-12 至 10-17 为 0。
- 数据页已接本地服务：启动时读取 `/api/dashboard`，点击刷新调用 `/api/sync`，页面每 10 秒读取服务端快照；服务端每 10 秒执行轻量实时同步，历史完整同步每 180 秒执行，素材元数据/归因分页独立按 900 秒缓存；服务不可用时回退内置快照并明确标注。
- 总看板今日实时链路：账户维度官方日报当天数据优先；账户接口失败时回退官方全域计划接口当天汇总；抖音号使用作者维度官方报表当天数据，并同步覆盖计划当天行。页面显示今日累计更新时间、官方账户/计划回退来源和失败状态。
- 刷新接口最多同步等待 0.75 秒，未完成立即返回 202 和当前快照，后台任务继续执行；页面每秒跟进，直到 revision 更新，避免被完整素材任务阻塞。
- 数据趋势图支持消耗、成交、订单、ROI、转化成本五条折线多选叠加，默认消耗+成交；按钮高亮控制显隐，各线使用独立量级、不同颜色和清晰图例，悬停展示全部五项指标真实值。
- `live-screen-agent.js` 使用 `puppeteer-core`、无头 Edge/Chrome 和独立 `data/chrome-profile`，每 10 秒从大屏页面抓取消耗、成交金额、成交单量、成交订单成本、ROI、累计观看、商品点击、峰值在线和 GPM。`live_watchdog.py` 每 5 秒巡检，进程退出或心跳超过约 45 秒时自动重启。
- `/api/live` 返回 `source=qianchuan_live_dual_channel`；大屏交易字段完整时，顶层返回 `transactionSource=qianchuan_live_screen`、`tradeRefundPolicy=before_refund`，并通过 `metricSources` 标注每个指标来源。`channels.trade` 保留 MCP 兜底/校验结果，`channels.behavior` 保存页面抓取结果；单通道失败时独立降级。
- 千川 MCP 通过 `data/qianchuan-mcp.json` 配置，服务端会执行 `initialize`、`tools/list` 和 `tools/call`；`GET /api/mcp/tools` 查看工具列表，`GET /api/mcp/field-descriptions?tool=<tool_name>` 返回官方字段说明。`qianchuan_report_live_get_v1` 和 `/api/mcp/raw/live` 保留为原始响应诊断，不参与大屏退款前 KPI 合成。
- MCP 交易兜底字段 schema 已确认：广告主 ID 为整数；起止时间使用 `YYYY-MM-DD HH:mm:ss`；`fields` 必填；`marketing_goal=ALL`、`order_platform=ALL`。优先取 `total_pay_order_gmv_include_coupon_for_roi2`、`total_pay_order_count_for_roi2`、`total_cost_per_pay_order_for_roi2`，金额已是元、订单已是单量，不再除以 100000。
- 同步与限流：账户报表、抖音号日报各缓存 120 秒，素材缓存 6 小时；千川请求之间强制至少 0.35 秒间隔，命中 40100 / 429 自动重试，持续限流按 60 / 120 / 300 秒退避，`syncBackoffSeconds` 同时写入快照和 `/api/health`。
- `start.bat` / `start.ps1` 已改为启动 `live_watchdog.py` 并打开页面；看门狗负责拉起/重启 `server.py` 和 `live-screen-agent.js`，脚本仍会自动查找 `py`、`python` 或 Codex 自带 Python。
- 开机自启已补齐：`install-autostart.bat` 创建当前用户登录计划任务，任务运行 `start-autostart-loop.ps1`；启动循环守护 `start-background.ps1`，后者查找 Node/Python 并运行 `live_watchdog.py`。计划任务被安全策略阻止时自动退回 Startup 文件夹。卸载入口为 `uninstall-autostart.bat`。
- 计划维度已落地：快照 `accounts[].plans[]` 保存每条计划的日报与素材，数据、素材、诊断三块共用同一个账号 + 计划选择状态。
- 数据页账号视角展示计划拆分列表，标记投放中、已暂停、未使用；点击计划进入单计划 KPI、趋势、素材和诊断。
- 诊断页在计划视角下展示计划独立的区间指标、诊断分、问题与建议，不再复用账户级人货场示例。
- 后端 `campaigns` 配置支持计划列表、计划日报、计划素材三个接口，字段名、状态映射、分页和过滤键均可配置。
- 已接入真实千川 Open API：全域计划列表 `/qianchuan/uni_promotion/list/`、计划素材 `/qianchuan/uni_promotion/ad/material/get/`、今日直播间 `/qianchuan/today_live/room/get/` 及流量、用户、商品接口。
- 数据页已写入 5 条真实全域计划（2 条历史有消耗、3 条本周期无消耗）；计划素材按分页完整拉取，再用官方素材维度报表补真实跑量。
- 多抖音号对比：当前广告主下 5 个抖音号以 `accounts[].awemes[]` 挂在同一广告主下，前端展开为 5 个可切换账号；启动默认进入赵镭图解账号，顺序固定为图解、精讲、拆解、通解，其余账号排后。
- 自动化测试：`test_server.py` 的日期范围、10 秒周期与账号顺序、MCP JSON-RPC/SSE、工具发现接口、固定工具调用、原始响应零改写、MCP 直播优先链路、双数据源看板契约、退款前直播指标、账户/抖音号对账、快速刷新、多指标图表契约、今日累计覆盖与零值保护、账户实时回退、素材分页、直播流、HTTP 接口共 27 个用例全部通过。
- 2026-10-21 素材板块更新：官方素材报表替代全零的 `stats_info` 作为跑量来源；补视频与直播间画面当天累计；TOP5 两栏、全量素材合并、标题/直播素材去重、计划日期统一为 `2026.6.30` 风格、缓存兜底均已验证。验收截图见 `material-report-final.png`。

## 5. 下一步

- 优先补齐历史数据：账户报表 `50000` 时使用计划日报回退，但计划回退受 `campaigns.historyDays` 限制（默认 7）。当前 `HISTORY_DAYS=182`，快照实际只有 2026-10-12 至 2026-10-20 共 9 天，且 10-12 至 10-17 为 0。先备份快照，再把 `campaigns.historyDays` 调到 180 做全量回填，并验证 30 / 90 / 180 天范围。
- Open API 凭证已配置并验证计划、素材、直播间接口；继续观察账户报表 `50000` 是否恢复，恢复后可去掉“计划日报汇总”回退。
- 计划素材已接入，下一步补充素材级人群画像接口；当前素材画像仍显示“—”。
- 实时直播画面链路已打通；下一步接入直播录像存储，替换复盘页的回放示例数据。
- 自动画面采集需要在 Chrome / Edge 中一次性加载 `live-capture-extension`，并保持千川直播大屏页面打开；不安装时仍可手工粘贴短时拉流地址。
- 接入人脸识别、视频理解与主播风格模型，替换录屏上传后的模拟分析结果。
- 接入实时指标、ASR 和违禁词库，替换实时诊断中仍为示例的话术与主播状态数据。
- 接入 ASR、逐句归因和话术效果模型，替换实时话术看板的示例语句与归因结果。
- 接入词库同步渠道（团队表格、千川词库、开放 API），替换本地上传与示例版本记录。
- 接入千川操作 API，替换投放操作台的示例执行，并按操作时间回读流量影响。
- 接入文档解析与检索，替换投放知识库的本地模拟学习结果。
- 接入 DeepSeek，替换本地规则诊断与投放建议生成。
- 逐模块补齐素材、投放诊断和复盘的真实数据能力。

## 6. 踩坑记录

- `TT-申坤-赵镭老师(店播)-小学数学-自运营` 近 30 天标准推广报表为空，实际消耗来自全域推广；取数使用 `qianchuan_report_uni_promotion_get_v1`。
- 全域推广接口不返回观看人数和转化率；`qianchuan_report_live_get_v1` 查询历史日期 2026-10-17 返回空，不能据此补造这两项指标。
- 当前 `qianchuan` MCP 仅开放账户级和全域聚合报表；素材报表、直播间详情/流量/用户洞察接口存在于千川开放平台文档，但未暴露为 MCP 工具，需接入官方 Open API OAuth 凭证后直接调用。
- 话术逐句归因与复盘回放不属于千川报表能力，需要额外接入直播评论流、ASR、录像存储和话术效果分析服务。
- 当前 MCP 授权主体为企业 BP 账户 `1855365007750474`，可直接查询的广告主仍只有 `1744479430946824`；其余广告主暂无权限，不能凭空补账户。
- 当前 MCP 不提供计划列表、计划报表和计划素材接口；计划层数据只能通过千川 Open API 获取。默认路径按标准推广计划接口配置，全域推广账户若返回 404/字段不符，需在 `qianchuan.config.json` 调整路径与 `fieldMap`。
- 未取得计划接口数据时，前端只展示“账户汇总（未拆分计划）”，不会伪造计划名称或把账户数据摊到多条计划。
- 当前账户的账户维度报表接口会返回 `50000`，已自动回退为“计划日报汇总”；计划日报金额字段单位为千分之一分，需除以 `100000`。
- 千川官方接口不返回直播推流/拉流地址；直播大屏媒体请求包含带签名的 HTTP-FLV 地址。本机扩展负责从该请求采集地址，后端只做短时内存缓存和同源代理，不写日志、不写快照。
- 今日直播间接口不返回曝光人数，五维漏斗的“曝光”层与“曝光→进入率”只能标记待接入；互动接口只给评论次数，不能当作互动人数。
- 今日直播间接口会触发“系统请求频率超限”，此时 `/api/live` 返回 `live:false` 并带 `errors`，不能当成未开播处理，页面保留上一次快照展示。
- 千川官方 Open API 不返回直播间推流/拉流地址：诊断页可通过本机采集扩展自动获取直播大屏签名 FLV，或使用手工粘贴地址；没有地址时只能显示封面和待接入状态。
- 网页版抖音直播链接（`live.douyin.com/...`）是页面不是媒体流，不能直接作为播放源；iframe 嵌入通常被拒绝且依赖登录态和风控参数。实际可播放源是网页播放器 Network 中的带签名 `.flv` / `.m3u8` 请求，地址会过期。
- 当前开发机 Edge 155 实测原生 HLS 可解析并进入 playing（640×360），headless 截图里 HLS 画面可能全黑，但元数据与播放事件正常；换电脑后浏览器版本可能不同，仍以 `hls.js` 作为兼容兜底。
- hls.js / flv.js 已落盘到 `vendor/hls.min.js`、`vendor/flv.min.js`，Chromium 可离线播放。旧诊断页曾因请求被注入 `Access-Token` 头触发 CDN CORS 失败；当前播放器和本机代理均不发送该头，已验证 1080×1920 FLV 进入 `readyState=4` 且 `playing`。
- 当前开发机的 ffmpeg 位于 `C:\Program Files (x86)\damai\resources\app\node_modules\ffmpeg-static-electron\bin\win\x64\ffmpeg.exe`，该路径不保证在其他电脑存在。换机后安装 ffmpeg 或设置 `QIANCHUAN_FFMPEG`；后端还会探测常见路径和 PATH。
- 180 天回填仍未完成：`HISTORY_DAYS=182`，但 `campaigns.historyDays` 仍是 7，计划日报实际只保留 2026-10-12 至 2026-10-20 共 9 天，其中 10-12 至 10-17 被写成 0；回填窗口与计划日报取数不匹配，修复前需先保护已有快照再重跑。
- 当前开发机 PATH 中没有 `python` / `py`，Python 服务回退到 Codex 自带运行时；换电脑时应确保 `python` 可用，不能依赖这条 Codex 专用路径。PowerShell 5.1 执行含中文的 `.ps1` 时需要 UTF-8 BOM。
- `qianchuan.config.json` 和 `data/qianchuan-token.json` 已在 `.gitignore` 中排除。不要为了“方便复制”把真实 token 写进 README、AGENTS.md、截图或提交历史。
- 素材页最初无数据的根因有两处：误把账户 182 天窗口传给素材接口，以及每个计划只取第 1 页 100 条；素材必须使用独立近 7 天窗口，并按 `page_info.total_page` 拉完全部分页。
- `VIDEO` 与 `LIVE_ROOM` 必须使用各自字段集：直播间画面使用 `live_show_count_exclude_video_for_roi2`、`live_watch_count_exclude_video_for_roi2` 等字段；把视频的 `*_v2` 展示/观看字段传给直播间画面会返回 `40000 参数错误`。
- 当前计划 `1866854933192299` 返回 1348 条视频 + 1 条直播间画面；计划 `1869402008695177` 返回 865 条视频 + 1 条直播间画面。后者的素材接口统计仍全部为 0，即使计划日报有消耗，也不能据此补造素材跑量。
- `/qianchuan/uni_promotion/ad/material/get/` 适合获取计划素材库和封面，但其 `stats_info` 在本账户会返回全零；真实跑量必须使用 `/qianchuan/report/uni_promotion/data/get/`。该接口的 `anchor_id` 过滤值应传抖音号 ID（`aweme_id`），不是 `room_info.anchor_id`。
- 素材维度报表的 `anchor_id`、`aggregate_smart_bid_type`、`ecp_app_id` 是必填过滤项，单次过滤只传一个枚举码；视频主题使用 `SITE_PROMOTION_POST_DATA_VIDEO`，直播间画面主题使用 `SITE_PROMOTION_POST_DATA_LIVE`，且直播间画面的维度列表也必须显式包含 `anchor_id`。

## 7. 进度快照（2026-10-22）

### 7.1 可运行状态

- `server.py` 提供 `/api/dashboard`、`/api/sync`、`/api/live`、`/api/live/screen`、`/api/health`；`index.html` 为单页前端；`start.ps1` / `start.bat` 可启动双通道看门狗并打开 `http://127.0.0.1:8765/`。
- 交接时最新快照 `data/qianchuan-snapshot.json` revision 984，已回填近 7 天真实素材；具体 revision 与同步时间以 `/api/health` 为准。受 Codex 受限沙箱重启时服务可能因本机网络权限 `WinError 10013` 进入 `cache/failed`，但真实素材快照不会丢失；正常通过 `start.bat` / `start.ps1` 启动时恢复千川实时同步。
- 同步节奏：服务端每 10 秒执行当天轻量实时同步，每 180 秒执行完整历史同步，素材元数据与归因分页按 900 秒周期执行；已完成自然日的历史账户报表与抖音号日报各缓存 120 秒，当天累计值每个实时周期重新拉取；千川请求之间强制 0.35 秒间隔，命中 40000 / 40100 / 429 自动重试，持续限流时按 60 / 120 / 300 秒自动退避，并把 `syncBackoffSeconds` 写进快照和 `/api/health`。
- `test_server.py` 33 个用例全部通过，覆盖日期范围、10 秒周期与账号顺序、MCP 协议链、`qianchuan_report_uni_promotion_get_v1` 精确调用、大屏退款前交易覆盖 MCP、交易字段不完整时不混算、登录过期状态、当前直播场次发现与 19 位 room_id 精度、双通道独立降级、行为指标合并、今日累计覆盖与零值保护、轻量同步跳过历史/素材、账户/抖音号对账、刷新 3 秒响应、多指标图表、素材分页、直播流和 HTTP 接口。`npm run test:live-screen` 覆盖中文单位、交易字段标签解析、误匹配排除、单实例锁、残留锁清理、EBP roomId 和 FLV 地址提取。
- 直播大屏：支持 m3u8、HTTP-FLV、mp4/webm，以及 RTMP 经 ffmpeg 转本地 HLS；`live-capture-extension` 可从千川直播大屏自动采集签名 FLV，诊断页经本机代理或直连播放。真实播放验证截图见 `diag-real-stream-success.png`。
- 开机自启：Windows 用户登录 15 秒后由计划任务后台启动 `start-autostart-loop.ps1`，不弹出浏览器；启动循环、背景启动器、看门狗形成三层守护。看门狗使用单实例锁同时拉起并监控 `server.py` 与 `live-screen-agent.js`，后端进程退出后 5 秒巡检周期内自动重启。`start.ps1` 和开机任务统一复用同一套启动逻辑，优先使用项目内置 `runtime/python` 与 `runtime/node`，不依赖 Codex 运行时。自启日志为 `data/live-autostart.log`。计划任务被策略拒绝时安装器回退到 Startup 文件夹。

### 7.2 已接入的真实数据

- 广告主 `1744479430946824`，当前快照有 9 个日期（2026-10-12 至 2026-10-20），其中 10-12 至 10-17 为 0；10-18 消耗 9,448.20 / 成交 6,888 / 41 单，10-19 消耗 5,926.74 / 成交 4,200 / 25 单，10-20 消耗 60,333.70 / 成交 40,822.46 / 243 单；合计消耗 75,708.64、成交 51,910.46、309 单。
- 代码已接入今日累计实时层：当天账户行优先使用官方账户报表，失败时回退官方计划汇总；计划行与作者维度行同步覆盖当天日期；快照新增 `realtime`、`syncKind`、`syncRequest` 与 `reconciliation`，`/api/health` 同步暴露。
- 真实环境验证：19:22 今日消耗 4,703.12，19:26 更新为 4,740.41，证明数据随时间同步变化；旧版一次完整刷新耗时 150.933 秒，新版轻量刷新实测 2.982 秒返回、后台实时同步约 3 秒完成，10 秒后 revision 继续递增。
- 对账验证：旧版在 19:26 出现总账户消耗 4,740.41 与抖音号归因和 4,749.07 相差 8.66；根因是总账户与抖音号使用不同归因口径且并非同一刷新时点。新版总看板固定使用账户序列，抖音号求和只作拆分展示并单独标记归因差。
- 5 条真实全域计划已拉取，当前全部为暂停 / 系统暂停状态；历史有消耗的 2 条计划为 `1866854933192299` 和 `1869402008695177`，其余 3 条本周期无消耗。计划日报只有 9 天，长周期仍未回填。
- 两计划已按近 7 天窗口拉完整素材分页，并合并官方素材维度日报：窗口 `2026-10-15` 至 `2026-10-21`，当前 2,226 条素材、1,316 条非零跑量；视频与直播间画面消耗合计 63,892.25、成交 42,671.46、254 单，2 条直播间画面均有真实跑量。素材报表是素材维度归因，不应强行与计划总消耗差额补造；标题等其他创意同时存在时会形成归因差异。
- 5 个抖音号当前均显示“已暂停”：赵镭图解累计消耗 60,333.70 / 成交 40,822.46，赵镭精讲累计消耗 15,374.94 / 成交 11,088，其余 3 个为 0；前端已按抖音号拆分展示并支持汇总/单账号切换。
- 诊断页实时监控已接通今日直播间、封面、开播时间、直播状态、消耗、成交、ROI、在投计划，以及流量、用户、商品接口；无直播时明确返回 `live: false`。
- 诊断页已重构：实时监控看板 + 实时数据 + 在投素材 + 五维四率四个页签；页内曲线按页面轮询快照记录，不再使用分钟级示例曲线；实时建议与后续预测基于真实场次累计值计算。
- 复盘页已移除实时监控页签，只保留录制状态、录像回放、问题/优势标注、主播画像和赛后整体结论。
- 2026-10-22 15:39 端到端验证 `/api/live`：MCP 交易通道返回今日消耗 2,580.03、用户实际支付 1,176.00、7 单、ROI 0.46；行为通道当时因首次 profile 尚未登录，独立返回 `config_required`，未影响交易通道。
- 2026-10-22 17:51 双通道完整验证：正确识别当前直播场次 `7699337106561846035`，MCP 返回消耗 3,475.64、成交 1,344.00、8 单、ROI 0.39；大屏抓取直播间整体观看人数 1,149、商品点击 233、GPM 986.78、实时在线 5、观测峰值 6，直播流同时捕获成功。

### 7.3 仍为示例或未接入

- 数据页：交易通道已接真实 MCP；观看/点击/GPM 已通过当前真实直播验证。千川大屏不返回原生历史峰值，目前 `peakOnline` 是采集器启动后的观测最高在线；AI 诊断仍为本地规则，DeepSeek 尚未配置。
- 素材页：人群画像仍为空；完播率、平均停留已由素材维度报表接入，综合分基于当前已有字段计算。
- 诊断页：主播语速/能量/情绪、话术 ASR 合规仍待接入；曝光人数接口未返回，曝光→进入率待接入；实时曲线只在页面打开期间按 30 秒轮询打点，刷新页面会重新累计。
- 直播大屏：指标行为通道已改由无头 Chrome 每 10 秒抓取，画面流仍可由无头 Chrome 响应或传统 `live-capture-extension` 采集。录像存储、回放切片和 ASR 仍未接入。
- 话术页：违禁词本地 TXT/CSV 上传可用；ASR 逐句归因、优质话术摘取、持续低效话术统计仍为示例。
- 投放诊断：直播中的流量渠道和人群画像可读真实接口；下一手建议、知识库、操作台及操作后影响为规则或示例，未写入千川后台。
- 复盘：录像回放、时间轴标注、主播画像、主播库仍为示例；直播流、录像存储、ASR、人脸识别和视频理解尚未接入。
- 取数：`HISTORY_DAYS=182` 已设置，但 `campaigns.historyDays` 仍是 7，账户/计划日报实际只有 2026-10-12 至 2026-10-20 共 9 天，且 10-12 至 10-17 为 0。修复前不要用当前快照做 30 / 90 / 180 天长周期结论。

### 7.4 当前优先级

1. 用开机自启和 `start.bat` 各做一次长时间看盘验证：确认登录后自动拉起、每次手动启动都创建新的 Python/服务/采集器进程、旧进程无残留，且 10 秒心跳持续正常。
2. 验证换场、下播、重新开播、断流和签名过期；确认 EBP 列表出现“直播中”后优先直接取该行，列表延迟时继续使用 `/api/live/discover`。
3. 修复 180 天计划日报回填：备份现有快照，把 `campaigns.historyDays` 调到 180，重跑并验证 30 / 90 / 180 天范围。
4. 继续确认千川是否提供原生历史峰值在线字段；若没有，保持当前“观测峰值”口径并在 UI 明确标注，不得改写成后台原值。
5. 确认素材级人群画像对应的千川接口与字段，补入 `fieldMap`；跑量指标、完播率和平均停留已接入。
6. 接入 DeepSeek，替换本地规则诊断与建议生成。
7. 接入千川操作 API、ASR、录像存储与回放切片；在此之前操作台保持演示执行，不自动修改预算。

### 7.5 MCP 直播报表接入状态（2026-10-21）

- 本节保留为历史排查记录；2026-10-22 起双通道交易指标已改用 `qianchuan_report_uni_promotion_get_v1`，不再等待 `qianchuan_report_live_get_v1` 原始字段核验。
- 用户明确要求：必须先打印 `qianchuan_report_live_get_v1` 原始返回，确认实际字段名；不得先猜字段再写解析。
- 金额口径：千川 API 常见金额为“十万分之一元”，除以 `100000` 才是真实金额；需根据原始字段和单位确认后应用。
- 时间参数：查询日期传 `2026-10-21` 对应完整起止时间 `2026-10-21 00:00:00` 至 `2026-10-21 23:59:59`。
- 首个验证账号固定为广告主 `1744479430946824`、抖音号 `7637818476896437305`（赵镭图解小数基本功）。
- 当前广告主下共 5 个抖音号，单账号验证成功后才扩展；每个抖音号必须分别调用，不能复用首个账号结果。
- `flows`、`users`、`products` 当前为空，是否属于接口不返回、响应层级不同或解析路径错误尚未确认；必须先看原始 JSON。
- 已实现 `/api/mcp/raw/live` 零解析接口，返回 `toolSchema`、实际 `arguments` 和完整 `rawJsonRpcResponse`，不做任何指标映射。
- `data/qianchuan-mcp.json` 当前 `rawVerified=false`，MCP 直播解析处于关闭状态，以免未经核验的数据进入看板。
- 当前阻塞：Codex 命令沙箱访问远程 MCP 被 `WinError 10013` 阻断；`8765` 正在运行的进程启动时间早于原始诊断接口加入时间，访问 `/api/mcp/raw/live` 返回 404。需要用户关闭旧服务并重新启动 `start.bat` / `start.ps1`。

### 7.6 2026-10-22 当日总结

#### 今天做了什么

- 完成直播大屏双通道：交易指标走 MCP `qianchuan_report_uni_promotion_get_v1`；观看、商品点击、GPM、实时在线和观测峰值走 `puppeteer-core` 无头 Edge。
- 完成新版 EBP 登录与跳转链路：登录入口切换到 `business.oceanengine.com`，通过 EBP 列表、今日直播间 Open API 和新版 EBP SSO 最终打开 `board-next` 当前直播大屏。
- 修正当前场次选择：只优先选择 EBP 表格里同时包含“直播中”和 `ID:` 的行；已结束场次不再作为当前直播兜底；EBP 尚未收录时使用 `/api/live/discover` 的 `room_status=LIVING`。
- 修复 19 位 `room_id` 精度问题：服务端额外返回字符串 `roomId`，避免 JavaScript Number 导致末位失真。
- 完成真实直播验证：当前场次 `7699337106561846035` 抓取到观看 1,149、商品点击 233、GPM 986.78、实时在线 5、观测峰值 6；MCP 同步返回消耗 3,475.64、成交 1,344.00、8 单、ROI 0.39。
- 接通直播流自动采集，当前场次成功捕获签名 FLV，并接入现有本机代理播放链路。
- 新增看门狗和登录暂停机制；`start.ps1` 改为强制重启：每次启动前结束所有 Python 进程、旧采集器和 profile Edge 进程，再启动新服务。
- 新增 `/api/live/discover`、`/api/live/screen`、`liveScreenCapture` 健康字段、双通道 UI、`LIVE_SCREEN_DUAL_CHANNEL.md` 和自动化测试。
- 验证结果：29 个 Python 用例、Node 采集解析测试、PowerShell 语法和 Python 编译均通过。

#### 还有什么没做

- EBP 直播分析列表当前仍可能只返回历史“已结束”记录，正在直播的全域场次存在收录延迟，因此目前必须保留 Open API 兜底。
- 新版 EBP 大屏只返回“实时在线人数”，没有确认存在原生历史峰值在线字段；当前峰值是采集器启动后观测到的最大值，不是整场后台原值。
- 尚未完成整场长时间运行验证，包括连续切换场次、下播重开、断流恢复、签名过期刷新和跨小时稳定性。
- 180 天历史计划日报仍未回填：`campaigns.historyDays` 实际仍偏短，当前快照不能用于 30 / 90 / 180 天长期结论。
- 素材人群画像、DeepSeek 诊断、真实 ASR、话术逐句归因、录像存储、回放切片和千川真实操作 API 仍未接入。
- `start.ps1` 按要求会结束本机所有 Python 程序，属于强制策略；尚未增加“仅清理本项目进程”的可选模式。

#### 下一步要做什么

1. 每次启动通过 `start.bat` 验证硬重启：检查旧 Python、采集器、profile Edge 和端口占用均为 0，再确认新 PID、`/api/health` 和 `/api/live/screen` 正常。
2. 在当前直播持续运行至少一个完整场次，核对每次 10 秒心跳、观看/点击/GPM 增量、直播流、换场和下播后的状态。
3. 观察 EBP 列表是否出现当前“直播中”行；出现后验证采集器优先走 EBP 行，而不是 Open API 兜底。
4. 查找千川是否开放原生峰值在线字段；若没有，在 UI 统一显示“观测峰值（采集开始后）”，并保留首次观测时间。
5. 备份快照后修复 180 天历史回填，验证 30 / 90 / 180 天范围。
6. 继续接入素材人群画像、DeepSeek、ASR、录像与回放、千川操作 API。

## 8. 更新记录

### 2026-10-24：修复采集器多实例、残留锁和登录状态误判

- `live-screen-agent.js` 新增 `data/live-screen-agent.lock` PID 锁；第二个采集器在锁 owner 仍存活时直接退出，崩溃遗留的锁会通过 PID 检查自动清理。
- 看门狗启动前读取同一采集器锁，已有存活采集器时只接管心跳监控，不再重复拉起；登录暂停时会同时停止内部和外部采集器 PID。
- 无头浏览器启动前会清理专用 profile 的 `SingletonLock`、`SingletonCookie`、`SingletonSocket`、`DevToolsActivePort*` 和 `lockfile`，并只终止命令行包含该专用 profile 路径的 orphan Edge/Chrome。
- 登录地址保存条件收紧为：URL/正文存在 8 位以上 `roomId`，或页面明确是“直播大屏/直播间详情”且至少出现 3 个大屏指标；“直播分析”列表仅在同时存在“直播中”和 `ID:` 时允许保存。普通 `/ebp/home` 会被清除为 `pageUrl=""` 并等待重新登录。
- `/api/live` 新增顶层 `captureStatus` 与 `loginRequired`；`login_required` 时交易和行为错误均明确返回“登录已过期”，诊断页、曲线、漏斗、四率、实时数据和复盘状态统一显示“登录已过期”，不再落成“未开播”。
- 实测第二采集器被 PID 锁拒绝；看门狗重启后复用既有采集器 PID；误存的 `/ebp/home` 已从配置清除；UI 实测显示“需要重新登录大屏 / 登录已过期”。后端强杀后 5.3 秒恢复，采集器 PID 保持不变。

### 2026-10-24：修复无头 Edge 启动崩溃并补齐订单成本

- 实时抓取失败的首个根因是 Edge 155 的无头 GPU 子进程在当前 Windows 环境反复崩溃，日志出现 `GPU process isn't usable. Goodbye.`，最终表现为 Puppeteer 固定 30 秒启动超时。`live-screen-agent.js` 增加 `--no-sandbox --disable-gpu --disable-gpu-sandbox` 启动参数，实测同一 Edge 可在约 0.7 秒内建立 DevTools 连接。
- 进一步检查发现 `data/chrome-profile/Default/Network/Cookies` 中没有 `oceanengine.com` 或 `jinritemai.com` Cookie，说明独立采集 profile 的登录态也同时失效；修复浏览器启动后仍需执行一次 `login-live-screen.bat` 重新扫码登录。
- `login-live-screen.bat` 改为优先使用项目内置 `runtime/node/node.exe`，不再依赖系统 PATH。
- 交易字段新增 `orderCost`，匹配“整体成交订单成本 / 成交订单成本 / 支付订单成本 / 订单成本”，并从采集器透传到 `/api/live` 和数据页卡片；测试样本覆盖整体消耗 2901、订单 15、订单成本 194.78、净成交 ROI 0.81、观看 745。
- EBP 详情页保存的是固定 `roomId`，采集器现每 120 秒通过 `/api/live/discover` 检查当前开播场次；发现新 `roomId` 后替换 URL 并切换，避免登录恢复后仍一直读取昨天或上一场的数据。

### 2026-10-24：修复开机后后端未自启动

- 现场检查确认本机没有 `QianchuanLiveScreenAutostart` 计划任务，当前用户 Startup 目录也没有本项目快捷方式；同时旧 `start.ps1` 未优先使用项目内置 Python，开机早期可能只找系统 Python 或 Codex 运行时，导致服务无法启动。
- `start.ps1` 改为调用统一后台启动器，优先使用 `runtime/python/python.exe` 和 `runtime/node/node.exe`；检测到尚未配置自启时会先尝试一次性安装，启动后最多等待 60 秒确认 `/api/health`，后端健康后才打开页面，浏览器打开失败不再误报服务启动失败。
- `live_watchdog.py` 现在即使 Node 或直播采集器不可用也会继续守护后端，并新增进程级单实例锁，避免开机任务和手动 `start.bat` 重复拉起多个看门狗。
- `install-autostart.ps1` 恢复为登录计划任务安装器，任务运行 `start-autostart-loop.ps1`；计划任务被安全策略拒绝时回退到 Startup 快捷方式。`start-hidden.vbs` 改为启动自动恢复循环。
- 安装器现在会把实际执行账户、任务注册结果和 Startup 回退结果写入 `data/live-autostart.log`。Codex 命令会话使用 `CodexSandboxOffline` 账户，无法写真实 Windows 用户的 Startup 或注册计划任务，因此最终注册必须在桌面用户环境双击一次 `start.bat` 或 `install-autostart.bat`。
- 实测终止监听 `8765` 的后端进程后，约 5 秒内看门狗拉起新的 `server.py`，`/api/health` 恢复为 `ok:true`；`test_server.py` 32 个用例和 `test_live_watchdog.py` 4 个用例通过，PowerShell 脚本语法检查通过。

### 2026-10-23：直播大屏交易指标切换为退款前口径

- 用户确认千川直播大屏展示的是退款前数据，MCP 原有 `total_pay_order_gmv_for_roi2` / `total_pay_order_count_for_roi2` 组合不再作为大屏主交易口径。
- `live-screen-agent.js` 新增从大屏 DOM 直接抓取 `spend`、`gmv`、`orders`、`orderCost`、`roi`，与累计观看、商品点击、峰值在线、GPM 使用同一 10 秒采集周期。
- `/api/live` 在大屏交易字段完整时返回 `transactionSource=qianchuan_live_screen`、`tradeRefundPolicy=before_refund`，顶层交易 KPI 用大屏值覆盖 MCP；新增 `metricSources` 标明每个指标的来源和退款口径。
- MCP 兜底改用“整体成交金额” `total_pay_order_gmv_include_coupon_for_roi2`、成交单量、成交订单成本和“整体成交金额 ÷ 消耗”计算 ROI；仅在大屏交易字段缺失时使用，并标记 `transactionSource=qianchuan_mcp`。
- 数据页交易 KPI 改为消耗、成交金额、成交单量、成交订单成本、ROI 五项，再展示四项大屏行为指标；诊断页同步增加成交订单成本。
- 新增 `GET /api/mcp/field-descriptions?tool=<tool_name>`，通过 MCP `get_tool_response_field_desc` 返回官方字段说明，不暴露 MCP URL 或凭证。
- Node 解析测试增加交易字段和“成交订单成本不得误识别为成交单量、GPM 不得误识别为成交金额”的测试；`test_server.py` 增加大屏交易覆盖 MCP、交易字段不完整时不混算的用例，合计 31 个 Python 用例通过。

### 2026-10-23：直播大屏采集器开机自启与双层守护

- 新增 `install-autostart.ps1` / `install-autostart.bat`：为当前 Windows 用户注册登录触发的计划任务，登录后等待 15 秒在后台启动采集器，不打开浏览器。
- 新增 `start-autostart-loop.ps1`：持续守护 `start-background.ps1`，启动脚本异常退出后 30 秒重试；计划任务再负责守护该循环，任务异常时每分钟重启。
- 新增 `start-background.ps1`：独立查找 Node.js、Python 和项目内 `node_modules/puppeteer-core`，设置 `QIANCHUAN_NODE` / `QIANCHUAN_PYTHON` 后启动现有 `live_watchdog.py`，不执行会关闭其他 Python 的强制清理逻辑。
- 项目已内置 Windows 便携运行时：`runtime/node/node.exe`（Node.js 24.21.0）和精简版 `runtime/python`（CPython 3.12.14 标准库，不含第三方 site-packages），并保留上游许可证。`start-background.ps1` 优先支持项目运行时，同时兼容 PATH、标准安装目录及本机 Codex 运行时。
- 计划任务被 Windows 安全策略禁止时，安装器自动回退到当前用户 Startup 文件夹；新增 `uninstall-autostart.bat` 清理自启任务、回退入口、启动循环、看门狗和采集器。
- 修复 `live_watchdog.py` 的 `state_age_seconds()` 缩进错误。此前心跳解析代码实际位于 `screen_pause_active()` 的不可达分支，导致看门狗拿不到心跳年龄，采集器启动约 20 秒后可能被误判并反复重启。
- 采集器首次启动宽限从 20 秒提高到 60 秒，覆盖千川页面最长 30 秒的首次导航等待，避免开机初始化时被看门狗误杀。
- 新增 `test_live_watchdog.py` 四个心跳与启动宽限用例；原有 29 个 Python 用例全部通过，PowerShell 语法检查和 Python 编译通过。

### 2026-10-22：直播大屏双通道与持久化无头采集

- 交易通道切换为 MCP `qianchuan_report_uni_promotion_get_v1`：今日 00:00 至当前时间查询账户 `stat_cost`、用户实际支付、订单和整体支付 ROI；金额字段直接按元使用。
- 行为通道新增 `live-screen-agent.js`：`puppeteer-core` 调用本机 Edge/Chrome，使用独立 `data/chrome-profile`，每 10 秒抓取累计观看、商品点击、峰值在线、GPM，并输出 `data/live-screen-metrics.json` 心跳与匹配证据。
- 首次登录通过 `login-live-screen.bat` 完成；脚本先写 `data/live-screen-pause` 让看门狗释放 profile，检测到地址含 `live_room_id` 后自动写入 `data/live-screen.json`，登录结束移除暂停标记，后续 Cookie 有效时无头运行，不重复扫码。
- 2026-10-22 登录入口已切换到新版 `business.oceanengine.com` EBP 地址；登录模式不再复用旧 `pageUrl`，并拒绝 `qianchuan.jinritemai.com` 历史地址。新版页面只要出现 `live_room_id` 或两个以上大屏指标标签即可自动识别并保存完整业务查询参数。
- 新版 EBP 直播分析列表固定为 `/ebp/data-analysis/live-analysis/list?ebpid=<EBP_ID>`；单场详情固定为 `/ebp/data-analysis/live-analysis/detail?ebpid=<EBP_ID>&roomId=<LIVE_ROOM_ID>`。`uuid` 是页面动态参数，不能写死。采集器已识别 `roomId`，并合并“直播数据 / 流量表现 / 直播间投放”三个页签。
- EBP 列表的直播状态从表格 `tr` 行识别：只有同时包含“直播中”和 `ID:` 的行才可作为当前场次；`已结束` 行不能兜底当前直播。全域直播尚未出现在 EBP 列表时，调用 `/api/live/discover` 通过今日直播间 Open API 的 `room_status=LIVING` 获取精确 `roomId`。
- 当前直播场次通过新版 EBP SSO 打开 `qianchuan.jinritemai.com/board-next`。大屏返回直播间整体观看人数、商品点击次数、GPM、实时在线人数；历史原生峰值未返回时，`peakOnline` 只能记录 `observed_since_capture` 的观测最高在线值。
- 新增 `live_watchdog.py`：守护主服务和采集器，进程退出或心跳超时自动拉起；`start.ps1` / `start.bat` 改为启动看门狗。
- `/api/live` 返回 `qianchuan_live_dual_channel` 与两通道状态；任一通道失败时只降级该通道。数据页更新为 4 项交易 KPI + 4 项大屏行为 KPI，并展示双通道运行状态。
- 新增 `GET /api/live/screen`、`liveScreenCapture` 健康信息、`live-screen.example.json`、Node 解析测试和 Python 双通道测试。
- 修正当前直播场次选择：新版 EBP 表格中只接受同时包含“直播中”和 `ID:` 的行；全域直播尚未进入 EBP 列表时，通过 `GET /api/live/discover` 调用今日直播间 Open API 获取 `room_status=LIVING`，再将 `roomId` 作为字符串传给 EBP SSO 的 `board-next`。
- 实际验证当前直播 `room_id=7699337106561846035`：大屏页面标题“直播大屏”、状态“直播中”，抓取直播间整体观看人数 1,149、商品点击次数 233、GPM 986.78、实时在线人数 5；`peakOnline=6` 明确标记为 `observed_since_capture`。
- `start.ps1` 改为强制重启：每次先结束本机所有 Python 进程、本项目旧采集器和 profile Edge 进程，并释放端口，再启动新的看门狗/服务/采集器。
- 验证：29 个 Python 用例和 Node 采集解析用例通过；无头 Edge 持久化 profile 冒烟通过；实测 MCP 交易通道返回今日 2,580.03 消耗、1,176.00 支付、7 单、ROI 0.46；页面验收截图 `dashboard-dual-channel.png`。

### 2026-10-21：接入千川远程 MCP 直播大屏数据

- 新增远程 MCP API Key 配置 `data/qianchuan-mcp.json`，并加入 `.gitignore`；另提供无密钥的 `qianchuan-mcp.example.json`。
- 服务端实现标准 MCP JSON-RPC 客户端，支持 Streamable HTTP、SSE 响应和旧版 SSE endpoint 回退，完成 `initialize`、`tools/list`、`tools/call`。
- 直播板块固定调用 `qianchuan_report_live_get_v1`，传入广告主 ID、抖音号 ID、当天日期及 `stat_cost` / `pay_order_amount` / `pay_order_count` 字段，标准化为现有退款前直播 payload。
- 直播大屏数据优先走 MCP，MCP 不可用时继续走现有千川 Open API；`/api/live` 返回 `source=qianchuan_mcp_live_screen`、命中的 MCP 工具名与退款前字段。
- 新增 `GET /api/mcp/tools` 诊断入口，便于查看实际开放的工具及参数 schema；不会返回 API Key。
- 新增 `GET /api/mcp/raw/live` 零解析接口，默认请求今日、广告主 `1744479430946824` 和图解抖音号 `7637818476896437305`，原样返回 JSON-RPC 响应；`rawVerified=false` 时不会使用未经核验的字段解析。
- 已确认 `qianchuan_report_live_get_v1` schema：广告主和抖音号使用整数 ID，`start_time` / `end_time` 使用当天完整秒级时间，`fields` 为必填数组，`stats_authority` 默认 `CURRENT`。
- 当前数据解析暂时不上线：`rawVerified=false`，必须先通过原始 JSON 核对字段、金额单位、列表层级与 `flows/users/products` 的实际返回，再更新解析和开启开关。
- 验证结果：27 个自动化测试全部通过；原始诊断接口、固定工具调用和响应零改写均有测试覆盖。
- 当前阻塞：运行中的 `8765` 服务早于原始诊断接口代码，`/api/mcp/raw/live` 返回 404；必须在正常桌面环境重启服务后才能完成真实原始返回打印。

### 2026-10-21：数据页拆分全域推广报表与直播大屏双看板

- 数据页顶部新增“全域推广报表数据”板块标识，明确成交金额为报表口径、未剔除退款。
- 新增“千川直播大屏数据”独立板块，成交金额与订单明确标注退款前口径，不与全域推广报表混算。
- 直播大屏板块包含消耗、退款前成交、退款前订单、ROI、累计观看、观看满 1 分钟 6 项 KPI，以及累计趋势图和实时流量结构图。
- `/api/live` 新增 `source=qianchuan_live_screen`、`refundPolicy=before_refund` 及 `gmvBeforeRefund`、`ordersBeforeRefund` 字段；直播缓存从 20 秒缩短到 5 秒，数据页每 10 秒刷新。
- 验证结果：23 个自动化测试全部通过；Python、配置 JSON、页面 JavaScript 语法检查通过；真实 `/api/live` 当前场次接口正常返回。

### 2026-10-21：数据总看板 10 秒刷新、多指标趋势与口径修正

- 实时轻量同步从 30 秒缩短到 10 秒；完整历史与素材同步独立为 180 秒低频任务，不再阻塞看板刷新。
- `/api/sync` 改为后台任务 + 最多 0.75 秒等待，未完成返回 202，实测点击刷新 2.982 秒响应。
- 总看板改为广告主账户序列，抖音号作者报表只用于账号拆分，新增 `reconciliation` 对账数据，避免把归因求和冒充总账户。
- 金额、订单、ROI、转化成本统一显示完整真实数字并保留两位小数，不再压缩为“万”。
- 趋势图支持消耗、成交、订单、ROI、转化成本多选叠加，默认消耗+成交，支持高亮、隐藏、图例和悬停查看全部指标真实值。
- 启动默认进入赵镭图解账号，账号顺序固定为图解、精讲、拆解、通解，其余账号排后。
- 验证结果：22 个自动化测试通过；Python、配置 JSON、页面 JavaScript 语法检查通过。

### 2026-10-21：总看板今日实时累计同步

- 将“已完成自然日历史同步”和“今日累计实时同步”拆成两层，避免账户/计划日报截止日固定为昨天。
- 账户维度当天行优先调用 `/open_api/v1.0/qianchuan/report/uni_promotion/get/`；接口失败时使用官方全域计划接口当天汇总，不伪造账户数据。
- 计划维度每轮同步调用全域计划接口覆盖当天行；作者维度使用官方数据报表为每个抖音号补齐当天累计。
- 新增 `sync.realtimeCacheSeconds=25` 与 `sync.includeToday=true` 配置；页面每 30 秒读取最新快照并显示“今日实时已更新”、更新时间及数据来源。
- 当天累计值采用同日 upsert；接口瞬时返回全零时保留上次有效值，避免看板回跳。
- 验证结果：`test_server.py` 18 个用例全部通过；Python 编译、配置 JSON 与页面内联 JavaScript 语法检查通过。

### 2026-10-21：素材板块真实跑量与交付整理

- 将素材跑量来源从计划素材接口的 `stats_info` 切换到官方素材维度报表 `/open_api/v1.0/qianchuan/report/uni_promotion/data/get/`。
- 视频使用 `SITE_PROMOTION_POST_DATA_VIDEO`，直播间画面使用 `SITE_PROMOTION_POST_DATA_LIVE`；按抖音号、投放方式、下单平台过滤，逐页拉取逐日数据后按素材 ID 汇总。
- 修正 `anchor_id` 口径：过滤值传抖音号 ID（`aweme_id`）；直播间画面报表的维度列表也要显式包含 `anchor_id`。
- 接入素材消耗、成交、订单、展示、点击、完播率和平均停留；点击率、转化成本和 ROI 使用汇总后的分子/分母计算。
- 素材窗口改为含当天的近 7 天，保留当天累计值；当前账户今天暂无新增消耗时显示 0，不用 0 覆盖前一日有效数据。
- 将官方报表跑量与计划素材元数据合并；素材元数据接口临时超时或返回全零时，保留已有有效跑量并标记缓存。
- 修复直播间画面与计划元数据重复问题，并对账号/总览素材按 `accountId + materialId` 去重。
- 两栏 TOP5 已按综合分规则补齐：适合放量取综合分前 5；适合追投优先取中位消耗以下的成交素材，不足时用其他有跑量素材补齐。
- 计划日期统一压缩为 `2026.6.2`、`2026.6.30` 风格，完整计划 ID 继续保留用于取数和排障。
- 更新 `qianchuan.config.example.json` 的素材报表配置；`server.py`、`index.html`、`test_server.py`、`PRD.md` 已同步更新。
- 验证结果：16 个自动化测试通过；页面截图 `material-report-final.png`；当前快照素材页有 1,316 条非零跑量素材。

### 2026-10-20：真实计划、直播画面与数据页基线

- 接入真实全域计划、计划日报、计划素材、今日直播间、流量、用户和商品接口。
- 完成账号切换、5 个抖音号拆分、计划列表和计划诊断。
- 打通千川直播大屏签名 FLV 的本机采集、短时缓存与同源代理。
- 完成素材页首版、诊断/复盘/话术/投放诊断的页面结构与基础交互。

### 后续更新约定

- 每次完成可运行功能后，在本节新增日期条目，并在“模块进度总览”和“进度快照”同步更新状态。
- 迁移电脑前，不把 `.tmp-*`、浏览器 profile、`__pycache__` 当成产品文件；真实 token 只通过安全渠道恢复。
- 如果没有更新 `data/qianchuan-snapshot.json`，新电脑首次启动会自动同步；同步失败也不要手工填入示例值冒充真实数据。
