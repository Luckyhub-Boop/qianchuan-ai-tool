# AGENTS.md

本文件面向在本仓库工作的 AI 助手，说明项目背景、技术选型与必须遵守的约定。

最近更新：2026-11-08

## 0. 换电脑交接（先读）

### 0.1 当前可运行结论

- 产品是一个单页 Web 看板，入口为 `index.html`，本地数据服务为 `server.py`，默认访问地址是 `http://127.0.0.1:8765/`。
- Python 服务端仍只使用标准库；直播大屏行为通道新增 Node.js + `puppeteer-core`，只影响大屏观看/点击/峰值/GPM 采集，不影响 Python 主服务和历史素材快照。
- 数据页、素材页和今日直播间已接通真实链路；直播大屏相关卡片位于诊断页“实时监控曲线”，交易与行为指标均由独立 `chrome-profile` 的无头 Chrome 直接抓取，失败时明确显示失败，不使用 MCP 补值。
- 已增加独立“知识库”页，支持上传 TXT / MD / CSV / JSON、DOC/DOCX、XLS/XLSX、PPT/PPTX 与可提取文本的 PDF。后台上传后自动抽取文本、切分片段并写入本地 `data/learning-index.json`；知识库对话、AI 问题定位和投放诊断建议按“大模型通用知识为主、用户经验做底线校验”的方式使用检索片段，并标注来源与冲突。页面展示整体学习进度、单文档学习进度和学习成果解说，明确提取字数、片段数、失败资料及应用位置。扫描版 PDF 和旧版 DOC/XLS/PPT 不可提取时会明确标记失败，不能把“已入库”表述成“已学习”。
- 当前唯一真实广告主为 `1744479430946824`，当前授权主体为企业 BP 账户 `1855365007750474`。其他广告主没有授权时不能凭账户 ID 伪造接入。
- 2026-11-08 已清理外部目录全部历史录像。新的复盘策略为：直播中按 5 分钟临时采集音频，场次结束且全部转写完成后，后台生成会话/每日 `review.json` 与 `review.md`，归档校验成功后再立即删除临时音频；不保留视频回放，失败时保留临时文件供重试。当前临时采集模式为 `audio_only_pyav`，不再依赖旧版 ffmpeg 解码 HEVC 视频。
- 巨量百应直播中控台通道已完成独立登录、采集、接口、前端补充展示和开机守护恢复。当前 `buyinLiveCapture.status=ok`、`available=true`，保存了独立 `buyin-chrome-profile`、Cookie 和页面地址；强制结束百应采集器后，看门狗已实测自动拉起新 PID，并凭持久化登录态恢复采集，无需再次登录。
- 2026-11-07 最近核验快照为 revision 23549、同步时间 `2026-11-07T20:14:22+08:00`：`/api/health` 为 `success`，千川直播大屏 `ok`，百应采集 `ok`，录像器 `recording`，本地 ASR `idle`。录像根目录已迁移到坚果云目录之外的 `D:\DAI投放产品录屏备份`，当前场次已生成 5 个 5 分钟分段。DeepSeek 产品模型固定为 `deepseek-flash`，但 `DEEPSEEK_API_KEY` 尚未配置，当前模式为 `local_fallback`。MCP 直播报表仍返回空 `data`，直播相关实时字段继续按既有规则使用大屏采集器。
- 2026-10-25 运行态核验：`start.bat` 在无项目进程、8765 端口空闲时冷启动通过，看门狗、后端、单个采集器各 1 个进程；采集器状态为 `ok`，当前直播间 `7700373751996746532` 持续返回真实大屏指标。OAuth 应用参数尚未配置，因此当前只有已有 Access Token，没有 Refresh Token，不能宣称 OAuth 授权已完成。
- 2026-11-05 运行态核验：看门狗、后端、单个采集器各 1 个进程；当前直播间 `7704532779547085622`，大屏心跳 `ok`、`streamCaptureOnline=true`，交易/行为字段均有真实值。今日直播间 Open API 当前仍为 `zero_pending`，五维四率保持 `partial`，不能用官方 0 覆盖大屏。OAuth 仍未配置。

### 0.2 换电脑必须复制的文件

建议复制整个 `AI投放工具` 目录，但排除本机浏览器缓存和临时目录：

- 必须：`server.py`、`index.html`、`start.ps1`、`start.bat`、`start-background.ps1`、`start-autostart-loop.ps1`、`start-hidden.vbs`、`vendor/`、`test_server.py`、`test_live_watchdog.py`、`qianchuan.config.example.json`、`AGENTS.md`、`PRD.md`、`AUTOSTART.md`、`install-autostart.ps1`、`install-autostart.bat`、`uninstall-autostart.ps1`、`package.json`、`package-lock.json`、`live-screen-agent.js`、`live-screen-agent.test.js`、`buyin-live-agent.js`、`buyin-live-agent.test.js`、`live_watchdog.py`、`login-live-screen.bat`、`login-buyin.bat`、`live-screen.example.json`、`buyin-live.example.json`、`LIVE_SCREEN_DUAL_CHANNEL.md`、`OAUTH_OPENAPI.md`、`oauth_login.py`、`oauth-login.ps1`、`oauth-login.bat`、`data/qianchuan-oauth.example.json`。
- 必须补充 `recording_store.py`、`review_finalizer.py`、`live_recorder.py`、`audio_capture.py`、`live_asr.py`、`test_recording_store.py`、`test_review_finalizer.py`、`test_audio_capture.py`、`test_live_asr.py`、`requirements-whisper.txt`、`install-whisper.ps1`、`install-whisper.bat`。临时音频固定保存在坚果云目录之外的 `D:\DAI投放产品录屏备份`，不得迁入项目或由坚果云同步，并在分析归档成功后立即删除；本地 Whisper 模型仍属于本机运行依赖。迁移录像/音频时必须按敏感经营数据安全传输。
- 需要继续同步千川时必须：`data/qianchuan-token.json`。该文件包含访问令牌，只能通过安全方式迁移，不能提交到公开仓库或发送到群聊。
- 需要自动刷新 OAuth Token 时必须：`data/qianchuan-oauth.json`。该文件包含 App Secret、Refresh Token 所需的 App ID 和已登记回调地址，只能本机安全保存，不能提交或外发。
- 需要使用千川 MCP 直播大屏数据时必须：`data/qianchuan-mcp.json`。该文件包含 MCP API Key URL，只能通过安全方式迁移。
- 需要保留无头 Chrome 登录态时必须安全迁移 `data/live-screen.json`、`data/live-screen-session.json` 和 `data/chrome-profile/`；它们包含直播大屏地址/Cookie，不能提交或外发。`live-screen-session.json` 只用于重启后的自动登录恢复。
- 需要保留巨量百应直播中控台登录态时必须安全迁移 `data/buyin-live.json`、`data/buyin-live-session.json`、`data/buyin-live-metrics.json` 和 `data/buyin-chrome-profile/`；它们包含百应页面地址、Cookie 和经营数据，不能提交或外发。
- 需要离线查看已同步数据或保留 5 分钟整场归档时：`data/qianchuan-snapshot.json`、`data/live-screen-history.json`。这些文件包含真实经营数据，也应按敏感业务数据管理。
- 需要保留已上传的产品学习资料时：`data/learning-documents/`、`data/learning-documents.json` 和 `data/learning-index.json`。其中可能包含内部 SOP、经营数据与复盘，只能通过安全方式迁移，不能提交到公开仓库。
- 需要自动采集直播大屏画面时：`live-capture-extension/`，并在新电脑浏览器中重新“加载解压缩扩展”。
- 不要迁移：`.edge-profile*`、`.tmp-*`、`__pycache__/`、`data/hls/` 等本机缓存或临时产物。截图文件可用于验收，但不是运行依赖。

### 0.3 新电脑启动步骤

1. 安装 Python 3.10+ 和 Node.js 20+，确保 `python`、`node`、`npm` 命令可用；也可在 `start.ps1` 中加入本机 Python 路径，用 `QIANCHUAN_NODE` 指定 Node。
2. 将整个项目放到固定目录，不要依赖旧电脑的 `D:\ai投放产品\我的坚果云` 绝对路径。
3. 确认新电脑可以访问 `https://api.oceanengine.com`，并从安全存储中恢复 `data/qianchuan-token.json`；也可通过环境变量 `QIANCHUAN_ACCESS_TOKEN` 注入令牌。
4. 需要自定义接口、分页或账户配置时，先备份现有 `qianchuan.config.json`，再按 `qianchuan.config.example.json` 调整。当前电脑已有正式配置文件，`campaigns.historyDays` 为 30。
5. 首次安装执行 `npm install`，再运行 `install-whisper.bat` 安装开源 ASR 依赖并把 `faster-whisper-tiny` 下载到 `models/whisper-tiny/`；然后双击 `login-live-screen.bat`。脚本固定使用项目 `runtime\node\node.exe`，打开新版 EBP 入口；只有检测到 roomId 或至少 2 个指定大屏指标才自动保存地址和 Cookie。旧版 `qianchuan.jinritemai.com/uni-prom`、无 roomId 的旧 board 和 EBP 首页都会被拒绝。
6. 双击 `login-buyin.bat`，以 1440×900 正常窗口打开 `https://buyin.jinritemai.com/mpa/account/login?log_out=1&type=24`，助手会自动切到“抖音手机号登录”；登录巨量百应后选择对应账号角色并进入当前场次的直播中控台。巨量百应不是抖店，不能使用 `fxg.jinritemai.com/login`。只有抓到可核验数值后才保存独立百应 profile、页面地址和会话。
7. 双击 `start.bat`，或在 PowerShell 中执行 `.\start.ps1`。脚本会启动看门狗，由看门狗分别守护主服务、千川大屏采集器和百应直播中控台采集器。
8. 打开 `http://127.0.0.1:8765/api/health` 检查 `ok`、`liveScreenCapture`、`buyinLiveCapture`、MCP 和凭证状态；`GET /api/live/screen`、`GET /api/live/buyin` 可分别查看两个采集器心跳。
9. 验证回归：执行 `python -m unittest -v test_server.py`、`python -m unittest -v test_live_watchdog.py`、`npm run test:live-screen` 和 `npm run test:buyin-live`。
10. `live-capture-extension` 仍可作为传统浏览器画面采集备用方案；直播大屏指标与交易字段默认由无头 Chrome 直接抓取，不需要常驻可见大屏。

启动策略：当前 `start.ps1` 会请求后台监督进程拉起缺失的看门狗；如果原看门狗和主服务仍健康，则复用现有进程。冷启动已验证通过，但“双击 `start.bat` 强制重启现有服务”尚未实现。更新 Python 代码后若需要确保加载新版本，应先只结束本项目的 `server.py` 与 `live_watchdog.py`，再执行 `start.bat`；不要结束本机其他 Python 程序。

可用环境变量：

| 环境变量 | 用途 | 是否必需 |
| --- | --- | --- |
| `QIANCHUAN_ACCESS_TOKEN` | 直接注入千川 Open API 令牌 | 与 token 文件二选一 |
| `QIANCHUAN_APP_ID` | 巨量开放平台应用 App ID | OAuth 时可选，覆盖本地配置 |
| `QIANCHUAN_APP_SECRET` | 巨量开放平台应用 App Secret | OAuth 时可选，覆盖本地配置 |
| `QIANCHUAN_REDIRECT_URI` | OAuth 应用后台登记的回调地址 | OAuth 时可选，覆盖本地配置 |
| `QIANCHUAN_MCP_URL` | 覆盖 `data/qianchuan-mcp.json` 中的远程 MCP 地址 | 否 |
| `QIANCHUAN_TOKEN_FILE` | 指定非默认 token 文件路径 | 否 |
| `QIANCHUAN_ADVERTISER_IDS` | 逗号分隔的广告主 ID，覆盖默认账户列表 | 否 |
| `QIANCHUAN_PORT` | 本地服务端口，默认 `8765` | 否 |
| `QIANCHUAN_SYNC_INTERVAL_SECONDS` | 服务端同步间隔 | 否 |
| `QIANCHUAN_FFMPEG` | ffmpeg 可执行文件路径 | 使用 RTMP/FLV 转码时需要 |
| `QIANCHUAN_RECORDINGS_DIR` | 录屏根目录，覆盖默认 `D:\DAI投放产品录屏备份` | 否 |
| `QIANCHUAN_NODE` | Node.js 可执行文件路径 | 看门狗找不到 `node` 时需要 |
| `QIANCHUAN_BROWSER_PATH` | Chrome / Edge 可执行文件路径 | 自动探测失败时需要 |
| `BUYIN_BROWSER_PATH` | 百应采集专用 Chrome / Edge 可执行文件路径 | 自动探测失败时需要 |

### 0.4 新电脑常见阻塞

- 千川接口返回鉴权错误：确认 token 未过期，且新电脑使用的是有该广告主权限的同一开发者和授权主体。
- OAuth 无法生成授权链接：先执行 `oauth-login.bat`，填写开放平台应用的 App ID、App Secret 和已登记回调地址；MCP API Key 不能代替 App ID/Secret。
- 页面没有数据但服务健康：先检查是否选中了零跑量抖音号；切到“总览”或“赵镭图解/赵镭精讲”账号。
- `WinError 10013`：通常是运行环境禁止本地套接字或外部网络。用正常 PowerShell 启动 `start.ps1`，不要在受限沙箱内运行同步。
- 直播画面不出现：先检查扩展是否加载、千川直播大屏是否登录并打开、`/api/live` 是否返回 `captured:true`。
- 大屏采集指标为空：运行 `login-live-screen.bat` 重新进入直播大屏，再检查 `GET /api/live/screen`；`config_required` 表示未保存地址，`login_required` 表示独立 profile 登录态失效。
- 百应渠道或千次观看成交为空：运行 `login-buyin.bat`，人工进入当前场次的巨量百应直播中控台，再检查 `GET /api/live/buyin`；`login_required` 不能被当成“未开播”。
- 百应采集与千川采集同时异常：分别检查 `data/buyin-live-agent.log`、`data/live-screen-agent.log`，两套 profile 不能同时被登录窗口占用。
- 采集器反复重启：检查 `data/live-screen-agent.log`、`data/live-watchdog.log`，确认 `node_modules/puppeteer-core` 存在且没有其他进程占用 `data/chrome-profile`。
- RTMP/FLV 无法转码：新电脑安装 ffmpeg 或设置 `QIANCHUAN_FFMPEG`，脚本和 `server.py` 会自动探测常见路径。

### 0.5 模块进度总览

| 模块 | 当前状态 | 真实数据 | 主要未完成项 |
| --- | --- | --- | --- |
| 数据 | 部分可用 | 全域推广报表；账户序列覆盖 33 个日期；直播指标由大屏单源采集；冷启动与日志锁问题已修复 | 180 天历史未回填；账户实时接口偶发 500 时仍回退计划汇总；OAuth 自动续期未配置 |
| 知识库 | 可用 | 本地文档上传、解析、分块、检索、删除、重建索引、学习进度、成果解说、带来源标注问答，以及 DeepSeek flash 通用知识为主、经验底线校验的生成入口与本地回退 | `DEEPSEEK_API_KEY` 未配置，外部生成尚未实测 |
| 素材 | 可用 | 116 天素材库与跑量报表、删除同步、完整数审计、官方上传时间、等级筛选和真实 Excel 导出；当前去重 1,885 条素材 | 51 条已离库历史视频和 5 条直播间画面无上传时间；素材人群画像 |
| 诊断 | 部分可用 | 大屏直抓交易/行为、5 分钟整场归档、五维四率即时大屏返回与 MCP/官方直播字段补充、代理 FLV 稳定播放、百应渠道/画像补充 | MCP 直播报表空数据、官方直播累计字段当前为零、百应画像当前不可用、主播状态识别 |
| 话术 | 可用 | 本地词库、PyAV 16k 单声道 WAV 临时音频、faster-whisper、长句合并、出单/掉人窗口归因、TOP 5；临时录像与永久归档转写统一查询，支持历史场次切换 | 更强中文模型可选升级；历史场次下拉仍需持续回归 |
| 投放诊断 | 部分可用 | 字段缺失说明、近 30 天操作推演、百应渠道/千次观看成交补充、5 分钟异常推断、本地文档底线校验、DeepSeek flash 配置状态 | MCP 直播报表当前返回空 data、`DEEPSEEK_API_KEY` 未配置、真实操作 API |
| 复盘 | 可用 | 外部目录临时音频、5 分钟交易/流量回溯、Whisper 长句归因、结构化话术结论、15 分钟分析、JSON/Markdown 永久复盘归档、分析成功后立即删除临时音频 | 人脸、多模态主播状态识别、百应真实画像持续可用性 |
| AI 模型 | 已配置、待密钥 | 开发模型 `deepseek-v4-pro`；产品模型 `deepseek-flash`；统一客户端、状态接口、知识库生成（经验底线校验）与本地回退已接入 | `DEEPSEEK_API_KEY` 未配置；AI 诊断、建议、问题定位尚未全部切换为模型生成 |

### 0.6 今日进度（2026-11-08）

#### 1. 今天做了什么

- 停止旧录像流程并永久删除 `D:\DAI投放产品录屏备份` 下 6 个历史场次，共约 56.44 GB；`data/review-archive/` 中的历史转写、指标、复盘 JSON 和 Markdown 均保留。
- 新增 `review_finalizer.py`：场次结束后必须同时满足“录像状态完成、所有临时分段完成转写、会话 `review.json/review.md`、每日 JSON/Markdown、基础 manifest 与 transcript 已落盘”，验证通过后才删除临时媒体目录；任一条件失败则保留并重试。
- 复盘不再合并 `session.mp4`，避免重复占用空间；会话级和每日级复盘均同时保存结构化 JSON 与可读 Markdown。
- 当前千川流的视频编码为 HEVC，旧版 ffmpeg 3.0.1 反复报 `Video codec (c) is not implemented`，无法生成 TS。新增 `audio_capture.py`，使用 PyAV 从签名 FLV 中只解码 AAC 音频，重采样为 16k 单声道 WAV，并每 5 分钟切段；`live_recorder.py` 的当前模式为 `captureMode=audio_only_pyav`。
- 已实测 PyAV 能识别当前流 `audio=aac`、`video=hevc`，并在当前场次 `2026-11-08_7705568418515766067_190202` 生成首个临时音频分段。音频 WAV 头会在写入过程中持续回写，进程异常退出后已写内容仍可读取。
- 修复“话术板块有归档文件但显示无数据”：根因是 `/api/script/analysis` 原先只查询 `RECORDINGS_DIR` 临时录像目录；原始视频删除后，不会扫描 `data/review-archive/sessions/`。
- 新增临时录像与永久归档统一数据源 `recording_store.script_session_sources()`：当前临时目录有有效转写时优先使用；否则使用永久归档；两者都没有转写时才显示“尚未生成”。
- 话术接口新增 `session` 参数并返回 `selectedSessionId`、`availableSessions`、`sessionSource`。前端场次下拉从“只选日期”升级为列出每个有转写的历史场次，并标注“历史归档/本次临时录制”。
- 读归档 manifest 时统一把历史 `recording` 状态规范为 `archived_analysis`，并从 transcript 的最后一句补偿缺失的 `endedAt`，避免已删除视频的历史场次被误判为仍在录制。
- 12:34 场次 `2026-11-08_7705568418515766067_123419` 已确认读取正常：归档 transcript 共 2,232 段原始转录，合并为 97 条完整长句，接口返回 5 类优质话术和 12 类低效话术。
- 当前话术默认不再被无转写的 19:02 新场次遮挡；默认选中 12:34 历史归档，同时场次选择器可访问 11/6、11/7、11/8 共 11 个历史场次。
- 今日回归共 101 项 Python 测试通过，新增覆盖：归档转写回退、历史场次选择、归档 manifest 状态规范化、音频采集 WAV 可恢复写入、转写不完整时不删除媒体、完整归档后删除媒体。

#### 2. 还有什么没做

- 需要等待当前场次首个完整 5 分钟 WAV 被 ASR 处理后，再验证新音频采集的实时转写和场次结束后的自动归档删除闭环。
- PyAV 首次打开千川签名 FLV 在本机约需 40–50 秒，页面不能把这段连接时间误判成转写服务异常。
- 话术页每次加载会读取较大的归档 transcript，后续可增加服务端缓存，但当前 11 个场次的接口响应已可正常返回。
- 现有历史归档中部分旧 manifest 仍写有“HLS/MP4”旧口径，读取时已规范化；文件本身不要求批量改写。

#### 3. 下一步要做什么

1. 观察当前场次生成第二个 5 分钟音频分段后，确认 ASR 自动处理第一段且话术页可切换显示“本次临时录制”。
2. 观察场次结束后的完整归档、临时目录删除、服务重启和失败重试。
3. 持续验证话术场次下拉在 11/6、11/7、11/8 各场次间切换，不串场、不把旧转写挂到新场次。
4. 视接口耗时增加归档 transcript 的服务端缓存，避免重复解析大 JSON。

### 0.7 今日进度（2026-11-07）

#### 2. 今天做了什么

- 复盘页完成布局和加载优化：侧栏改为两列且按内容高度排列，避免空白拉伸；`/api/review/sessions` 支持 `date=YYYY-MM-DD`，仅返回选中日期，同时返回 `availableDates`，避免一次加载全部历史。
- 所有仍存在视频的复盘日期统一使用 `/api/review/daily-playlist?account=...&date=...` 全天播放列表；只有外部录像目录确有 TS/MP4 时才返回播放地址。视频过期但分析仍存在的日期标记为“录像已过期 · 分析保留”，不再返回无效播放地址。
- 复盘新增 15 分钟数据分析、全天长句话术明细和出单长句 TOP 5。话术按完整长句、时间和对应效果逐条展示，不再把长段结论混在一起；修复全天聚合把毫秒时间戳误当秒导致时长异常的问题。
- 复盘新增“先分析、后删除”后台流程：所有分段转写完成、会话 JSON/Markdown、每日 JSON/Markdown 和基础归档均落盘成功后，才删除原始录像目录。任一归档步骤失败会保留录像重试。
- 完成会话级永久分析归档：`manifest.json`、Whisper transcript、指标、`review.json` 和 `review.md` 写入 `data/review-archive/sessions/`；每日聚合文档同步保存 `data/review-archive/<account>_<date>.json/.md`。归档校验成功后原始录像立即删除，话术和分析结果永久可读。
- 百应采集器会读取千川当前 `roomId` 并自动切换直播大屏，已实测从旧房间 `7704903843406039850` 切到当前房间 `7705197544334166826`，避免跨直播间串数据。
- 百应新增近 1 分钟看播、近 5 分钟购买、全场看播、全场购买四类画像提取，支持性别、年龄、地域 TOP 和分布，写入 `data/buyin-live-audience-history.json`，原始快照保留 14 天。当前百应页面显示“无法查看用户画像”时如实记录不可用，不补造。
- 复盘曲线按 `roomId` 和时间戳匹配最近的百应画像快照，最大匹配窗口 10 分钟；看播人群优先近 1 分钟画像，出单人群优先近 5 分钟购买画像，并展示画像来源、采集时间和失败原因。
- 核实 MCP 时间序列能力：`qianchuan_report_advertiser_get_v1` 原生只支持日/小时；`qianchuan_report_live_get_v1` 和 `qianchuan_report_uni_promotion_get_v1` 没有时间粒度或时间序列返回字段。两个 15 分钟 MCP 窗口实测均返回空 `data`，因此 15 分钟数据由千川大屏高频历史聚合，并明确标注 MCP 不支持原因。
- 修复录像代理 502：根因是抖音 CDN 重定向主机与其证书域名不匹配。代理优先使用签名原始流，并只对通过 CDN 白名单校验的媒体流关闭证书主机名校验；普通千川 API、OAuth 和其他 HTTPS 请求仍保持正常 TLS 校验。修复后本机代理返回 `200 OK`，录像器恢复 `recording`。
- 录像 TS、FLAC、Whisper 均按 5 分钟粒度运行；当前外部录像目录已验证 5 个片段，播放列表分段时长约 300 秒。
- 录屏根目录迁移到 `D:\DAI投放产品录屏备份`。项目原 `recordings/` 目录已整体移出并删除，迁移约 15.2 GB 历史录像；坚果云项目目录不再保存录屏视频，只同步代码和数据/分析文件。
- 新增 DeepSeek 双模型机制：开发模型固定 `deepseek-v4-pro`，产品模型固定 `deepseek-flash`；产品统一通过 `deepseek_client.py` 读取模型，新增 `/api/ai/config`、健康状态和 `aiConfig` 返回。知识库命中片段时使用 flash 生成，通用知识为主、经验仅作底线校验；未配置或失败会自动回退本地通用规则 + 检索。

#### 3. 还有什么没做

- `DEEPSEEK_API_KEY` 尚未配置，因此 DeepSeek 外部调用尚未真实跑通；当前知识库仍走本地通用规则 + 检索回退，AI 诊断报告、投放建议和问题定位仍主要由本地规则/检索生成，经验仅作底线校验，尚未全部切换为 `deepseek-flash` 生成。
- 当前 Codex 会话模型由客户端控制，仓库只能强制后续开发会话按 `deepseek-v4-pro` 选择，无法在业务代码中热切换当前会话模型。
- 百应画像当前被页面提示“无法查看用户画像”，采集器和匹配逻辑已完成，但真实分布的持续采集与曲线展示仍取决于百应页面何时放量展示画像。
- MCP 直播报表仍返回空 `data`，没有原生 15 分钟时间序列；当前 15 分钟数据依赖千川大屏采集器聚合。待 MCP 恢复后，仍需验证其字段一致性和来源优先级。
- 原始录像默认不再保留 10 天；`retentionDays=1` 仅作为分析失败时的磁盘保护上限。持续观察失败重试、归档成功删除和重启恢复即可。
- 仍存在长期模块缺口：OAuth Refresh Token 自动续期未配置、90/180 天历史未回填、素材人群画像未接入、人脸/视频理解与主播状态识别未接入、千川真实操作 API 未接入。

#### 4. 下一步要做什么

1. 配置 `DEEPSEEK_API_KEY`，先验证 `deepseek-flash` 的“通用知识为主、经验底线校验”回答，再把 AI 诊断报告、投放建议和问题定位全部接到同一产品客户端；调用失败必须继续回退本地结果并显示来源。
2. 观察外部临时录屏目录，验证场次结束后完整转写、JSON/Markdown 归档、原始录像立即删除、失败重试和重启恢复。
3. 当百应页面重新展示真实画像时，验证四类画像的实际提取和复盘曲线时间匹配；若仍不可用，保持明确失败态。
4. 持续探测 MCP 直播报表恢复情况；若恢复并出现可用时间序列，先完成 MCP 优先、采集器回退的来源切换验证。
5. 按长期路线继续推进 OAuth 自动续期、90/180 天历史回填、素材人群画像、人脸/多模态分析、主播状态识别和真实操作 API。

## 1. 项目定位

千川 AI 投放诊断工具。

核心目标是让投手从**操作者**变成**盯盘者**：把日常盯盘、异常发现、原因诊断这类重复劳动交给 AI，投手只做决策和关键操作。

## 2. 技术栈

- 界面：网页（Web）
- 模型：DeepSeek
- 数据源：千川 API

具体框架与依赖以实际代码为准。尚未确定的选型不要擅自引入新框架或新依赖。

## 3. 数据口径

### 3.0 DeepSeek 模型分工（强制）

- 使用 Codex、AI 助手或子代理进行代码开发、功能修改、调试和产品设计时，开发模型必须使用 `deepseek-v4-pro`。仓库内的开发模型策略配置在 `deepseek.config.example.json` 和本地 `data/deepseek.json` 的 `models.development`，任何开发协作不得使用 `deepseek-flash` 代替。
- 产品运行时面向用户的 DeepSeek 功能，包括 AI 诊断报告、投放建议、问题定位、知识库自然语言回答及其他生成式能力，必须统一使用 `deepseek-flash`。产品功能不得自行硬编码其他模型，必须通过服务端统一 DeepSeek 客户端读取 `models.product`。
- 当前可用会话模型由 Codex 客户端决定，仓库配置用于约束后续开发会话和子代理模型选择；不能通过修改业务代码切换当前正在运行的 Codex 会话模型。
- DeepSeek API Key 只允许通过 `DEEPSEEK_API_KEY` 环境变量或已被 `.gitignore` 排除的本地配置文件提供，不得写入代码、测试、日志、快照或提交历史。
- 未配置密钥、调用失败或被限流时，产品必须回退现有本地规则/本地检索结果并明确标注回退原因，不得伪造 DeepSeek 输出。

所有指标与千川后台逐字段对齐。

- 指标的名称、定义、单位、统计周期、归因规则，一律以千川后台展示为准。
- 与后台字段一对一映射，不合并、不改名、不做二次加工口径。
- 计算出的数值与千川后台不一致时，以千川后台为准，并记录到「踩坑记录」。
- 新增指标前，先确认千川后台存在对应字段，并在本节登记口径。
- 千川账户与抖音开播账号一一绑定；切换账号后，页面数据必须跟随当前抖音号。
- 总看板总账户使用千川广告主账户/全域计划账户口径，不能把抖音号作者维度归因简单相加后冒充后台总账户；抖音号列表只用于归因拆分，归因差额单独展示。
- 数据源之间必须隔离：MCP 是报表、分析和建议的主数据源；MCP 有有效值时，不得用大屏值覆盖全局报表、投放诊断或建议。大屏只用于“全域推广报表数据”的授权回退，以及五维四率、指标走势、直播间实时诊断等大屏专属板块。
- 大屏专属板块使用页面当前展示口径；素材维度报表继续使用其官方净成交字段，但必须标注“千川 Open API · 素材维度报表”来源，不能冒充 MCP。MCP 暂不可用时，才允许大屏临时回退，并在来源中明确显示“大屏直抓（MCP暂不可用）”。
- 诊断页“实时监控曲线”固定为直播大屏直抓口径：消耗、成交、订单、ROI、累计观看、商品点击、峰值在线、GPM、实时在线和可识别的流量渠道均取千川大屏页面当前展示值；抓取失败字段留空并显示“抓取失败”，不可用 MCP 或其他指标补差。五维四率例外：先立即返回大屏数据，MCP 在后台补充；MCP 报错、超时、空数据或线程启动失败都不能阻塞 `/api/live`。
- 大屏行为指标只接受页面实际显示并可匹配到标签的值；四个核心标签（累计观看、商品点击、峰值在线、GPM）任一缺失时标记部分字段，不按其他指标反推。页面结构变化时通过 `data/live-screen.json` 的 `metrics.*.labels` 或 `selector` 校准。
- 直播间五维四率（诊断页）：五维取千川今日直播间接口的场次累计值——进入 = 累计观看人数 `total_live_watch_cnt`，停留 = 观看满 1 分钟人数 `live_watch_one_minute_count`，互动 = 累计评论次数 `total_live_comment_cnt`，成交 = 净成交订单数；曝光人数接口未返回，曝光层与「曝光→进入率」标记为待接入，不补造。
- 四率口径：进入→停留 = 1 分钟观看 ÷ 累计观看；停留→互动 = 评论次数 ÷ 1 分钟观看（评论是次数不是人数，只作趋势参考）；观看→成交 = 净成交订单 ÷ 累计观看，与 PRD 转化率一致。
- 诊断页实时建议阈值属于运营经验值，不是千川后台口径：进入→停留 30%、停留→互动 10%、观看→成交 2%、ROI 1、付费流量占比 70%；页面需明确标注参考线。后续预测按本场当前节奏线性外推到 4 小时场次，只作参考，不写成承诺值。
- 素材页统计窗口固定从 `2026-07-01` 起，结束到最近一个完整自然日（次日自动顺延）。视频和直播间画面分别调用千川素材维度报表，按素材 ID 汇总；消耗、净成交、净成交订单、曝光、点击、完播率和平均停留取千川返回值，点击率与净成交ROI 由汇总分子/分母重新计算。
- 素材综合分分项先归一，再按展示 30%、转化（净成交订单）30%、点击 30%、其他（净成交ROI）10% 加权；适合放量取综合分 TOP 5，适合追投优先取消耗不高于样本中位数且已有净成交的素材，不足 5 条时用其余有跑量素材补齐。
- 素材报表是素材维度归因，素材合计不强行拼接到计划总消耗。标题、其他创意等归因会和视频/直播间画面形成口径差异，不能用差额反推或补造素材。

## 4. 已完成

- PRD v2 已落库。
- 纯前端数据看板首版：核心指标、趋势图、日期范围。
- 顶部功能导航：数据、素材、诊断、话术、投放诊断、复盘。
- 账号切换入口、账号隔离与总看板汇总校验骨架。
- 素材页：TOP 10 综合分、追投/放量清单、全量素材数据表与人群画像；综合分按曝光 30%、转化（订单）30%、点击 30%、其他（ROI）10% 加权，适合追投与适合放量各展示 TOP 5；全量表按曝光量降序，使用 `2026-07-01` 至最近完整自然日窗口，每 3 分钟刷新并每 3 小时完整对账；千川计划名日期统一压缩为 `2026.6.30` 格式。
- 素材跑量报表已切换到千川官方 `/open_api/v1.0/qianchuan/report/uni_promotion/data/get/`：视频主题按抖音号、投放方式、下单平台过滤并按整个区间分页拉取，再按素材 ID 汇总消耗、成交、订单、曝光、点击、完播率和平均停留；直播间画面使用独立主题和字段集。
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
- 数据页真实数据：`TT-申坤-赵镭老师(店播)-小学数学-自运营`（`1744479430946824`），口径为千川全域推广净成交；账户与抖音号历史序列、今日计划/作者报表、素材报表及直播大屏统一使用净成交金额、净成交订单和净成交ROI。
- 数据页已接本地服务：启动时读取 `/api/dashboard`，点击刷新调用 `/api/sync`，页面每 10 秒读取服务端快照；服务端每 10 秒执行轻量实时同步，历史完整同步每 180 秒执行，素材库按独立 3 分钟周期强制刷新；服务不可用时回退内置快照并明确标注。
- 知识库页：`GET/POST /api/learning/documents` 负责清单和原始文件上传，`GET /api/learning/search?q=...` 检索片段，`POST /api/assistant/chat` 先基于通用投放知识结合当前数据给出建议，再用已学片段做底线校验并标注来源/冲突（未配置 DeepSeek 时回退本地通用规则 + 检索），`POST /api/learning/reindex` 重建全部索引，`GET /api/learning/documents/download?id=...` 下载，`DELETE /api/learning/documents?id=...` 删除；单文件限制 25 MB，上传文件名经过路径清理，原始文件使用随机 ID 存储，清单和索引通过原子写入维护。
- 总看板今日实时链路：账户维度官方日报当天数据优先；账户接口失败时回退官方全域计划接口当天汇总；抖音号使用作者维度官方报表当天数据，并同步覆盖计划当天行。页面显示今日累计更新时间、官方账户/计划回退来源和失败状态。
- 刷新接口最多同步等待 0.75 秒，未完成立即返回 202 和当前快照，后台任务继续执行；页面每秒跟进，直到 revision 更新，避免被完整素材任务阻塞。
- 数据趋势图支持消耗、成交、订单、ROI、转化成本五条折线多选叠加，默认消耗+成交；按钮高亮控制显隐，各线使用独立量级、不同颜色和清晰图例，悬停展示全部五项指标真实值。
- 直播大屏已切换为大屏单源：`live-screen-agent.js` 使用 `puppeteer-core`、无头 Edge/Chrome 和独立 `data/chrome-profile`，每 10 秒抓取交易、累计观看、商品点击、曝光、GPM 和实时在线；`live_watchdog.py` 每 5 秒巡检，进程退出或心跳超时自动重启。
- `/api/live` 返回 `source=qianchuan_live_screen_direct`，采集器有新鲜数据时即使状态为 `stale` 也照常返回并带 `staleWarning`；交易与行为字段失败时分别展示真实失败态，不用 MCP 或其他指标补差。MCP 五维查询只允许后台执行，失败后冷却 30 秒；历史曲线在 `/api/live` 中只读内存缓存，避免 7–8 MB 历史 JSON 阻塞主接口。`/api/health` 暴露 `liveScreenCapture`，`/api/live/screen` 返回完整心跳，5 分钟历史写入 `data/live-screen-history.json`。
- 千川 MCP 通过 `data/qianchuan-mcp.json` 配置，服务端会执行 `initialize`、`tools/list` 和 `tools/call`；投放诊断 `/api/campaign/diagnostics` 使用 MCP `qianchuan_report_live_get_v1` 获取实时投放字段，`GET /api/mcp/tools` 可查看当前工具列表。MCP 未返回字段或返回空 `data` 时，投放诊断显示缺失原因和解决方案，不使用演示值。
- 巨量百应直播中控台已作为独立通道接入：`login-buyin.bat` 使用可见浏览器人工登录并保存独立 profile；`buyin-live-agent.js` 用无头 Chrome 每 10 秒抓取 DOM 表格和 JSON 网络响应，输出渠道流量占比、成交金额占比、渠道千次观看成交及页面可核验的补充字段。`GET /api/live/buyin` 查看状态，`POST /api/live/buyin/refresh` 立即刷新；投放诊断的优先级固定为 MCP 主源 > 百应字段补充/临时回退 > 千川大屏临时回退，响应通过 `fieldSources` 标明每个字段来源。
- 当前开机 Startup 快捷方式指向本项目 `start-hidden.vbs`，登录 Windows 后由 `start-autostart-loop.ps1` 拉起看门狗；看门狗同时守护千川和百应采集器。百应登录完成后只保存会话，不保留可见浏览器；后台以无头模式自动打开已保存的直播中控台地址。登录暂停标记已绑定登录进程 PID，登录窗口异常退出时下一次巡检会自动清除，不会让开机后的采集永久停摆。
- 百应只有页面明确给出净成交金额、净成交订单和净成交ROI 时，才允许临时顶替 MCP 的核心交易指标；普通成交/支付金额标记为 `gmvScope=buyin_reported`，只能作为补充字段，不能驱动净成交判断。
- 百应“直播大屏专业版 · 流量分析”已接入原生渠道三列：流量占比、成交金额占比、渠道千次观看成交。接口在百应原生值可用时返回 `flowValueKind=native`，来源为 `buyin_compass_live_screen_dom`；千川 `statQuery` 只作为兜底，由渠道流量人数和成交金额计算，返回 `flowValueKind=calculated`，不能宣称为千川页面直接展示字段。
- 投放诊断的流量渠道和画像改为横向自适应网格：渠道卡片按可用宽度自动排列为多列，长渠道名自动换行，渠道表列间距不少于 7–12 px；性别、年龄、地域和实时看播画像使用横向分区卡片。2026-11-06 用 1440 宽页面和长渠道名样本验收，重叠元素数为 0。
- 复盘已接入 `live_recorder.py`：看门狗常驻启动，直播中从千川大屏签名 FLV 的本机代理临时采集到 `D:\DAI投放产品录屏备份\<日期>_<roomId>_<时间>/`。当前由 `audio_capture.py` 使用 PyAV 只解码音频，每 5 分钟生成一个 16k 单声道 WAV；保留对旧 TS/M3U8 文件的历史兼容。场次结束后不再合并 MP4；后台在全部 Whisper 转写和复盘归档成功后立即删除临时音频。项目所在的坚果云目录只同步代码、复盘文档和 `data/` 数据，不同步录屏视频。
- `GET /api/review/sessions` 扫描本地录像清单，并按 roomId、日期合并千川直播大屏 5 分钟历史，返回真实消耗、净成交、订单、ROI、流量节点、来源和分析步骤。复盘页保持原版位和播放器控件，仅把视频源换成本地 HLS/MP4、曲线换成真实 5 分钟序列；ASR 未接入时话术线留空并明确显示，不生成逐句话术或主播风格分数。
- 2026-11-06 实跑已验证：录像、音频和 Whisper 转写均按 5 分钟分段；`/api/review/sessions` 返回真实累计消耗、净成交、订单、ROI、问题/优势标注和来源；“录像回放”可实际播放画面并拖动进度，`/recordings/*` 返回 HTTP 206 Range。
- 直播话术 ASR 已接入 `live_asr.py`：从每场直播的 TS 分段抽取 16k 单声道 FLAC，使用项目本地 `models/whisper-tiny` 的 `faster-whisper` CPU INT8 模型转写，再用 OpenCC 统一简体中文。不调用第三方付费 API，不用麦克风。
- Whisper 结果写入场次 `asr/transcript.json`，同时约每 5 秒记录在线、消耗、成交、订单到 `asr/metrics.json`；复盘接口按每句话起止时间对齐指标，输出“对应窗口出单 / 掉人 / 留人 / 无明显变化”，并明确这是时间窗口关联，不是因果证明。
- MCP 直播报表字段 schema 以 `qianchuan_report_live_get_v1` 实际 schema 为准；当前请求会同时索要交易、观看、曝光、评论、关注、GPM、在线等字段。金额换算按 `live.moneyDivisor` 处理，并在响应中暴露换算口径。
- 同步与限流：账户报表、抖音号日报各缓存 120 秒，素材缓存 6 小时；千川请求之间强制至少 0.35 秒间隔，命中 40100 / 429 自动重试，持续限流按 60 / 120 / 300 秒退避，`syncBackoffSeconds` 同时写入快照和 `/api/health`。
- `start.bat` / `start.ps1` 已改为启动 `live_watchdog.py` 并打开页面；看门狗负责拉起/重启 `server.py`、`live-screen-agent.js` 和 `buyin-live-agent.js`，脚本仍会自动查找 `py`、`python` 或 Codex 自带 Python。
- 计划维度已落地：快照 `accounts[].plans[]` 保存每条计划的日报与素材，数据、素材、诊断三块共用同一个账号 + 计划选择状态。
- 数据页账号视角展示计划拆分列表，标记投放中、已暂停、未使用；点击计划进入单计划 KPI、趋势、素材和诊断。
- 诊断页在计划视角下展示计划独立的区间指标、诊断分、问题与建议，不再复用账户级人货场示例。
- 后端 `campaigns` 配置支持计划列表、计划日报、计划素材三个接口，字段名、状态映射、分页和过滤键均可配置。
- 已接入真实千川 Open API：全域计划列表 `/qianchuan/uni_promotion/list/`、计划素材 `/qianchuan/uni_promotion/ad/material/get/`、今日直播间 `/qianchuan/today_live/room/get/` 及流量、用户、商品接口。
- 数据页已写入 5 条真实全域计划（2 条历史有消耗、3 条本周期无消耗）；计划素材按分页完整拉取，再用官方素材维度报表补真实跑量。
- 多抖音号对比：当前广告主下 5 个抖音号以 `accounts[].awemes[]` 挂在同一广告主下，前端展开为 5 个可切换账号；启动默认进入赵镭图解账号，顺序固定为图解、精讲、拆解、通解，其余账号排后。
- 直播场次自动发现：采集器启动前及每轮抓取前逐个查询 `qianchuan.config.json` 中的抖音号，当前覆盖图解、精讲、拆解、通解；发现 `LIVING` 后使用实时 roomId 动态打开大屏，换场时清空旧指标和旧直播流。四个账号全部成功且均无直播时写 `not_live` 并显示“未开播”，查询失败则写 `discovery_error`/`discovery_incomplete`，不回退旧场次。
- 官方直播字段对照通道：直播场次发现接口在 `officialLive` 中返回今日直播间 Open API 的直接字段映射。该接口可给出 roomId、账号、开播时间和部分累计投放字段，但不返回实时在线、峰值、GPM、订单成本和曝光人数；2026-11-04 实测当前场次累计值仍返回 0，而大屏同场次已有非零值，所以只作独立对照，不覆盖大屏 KPI。2026-11-05 已将该通道的 `watchCount`、`watchOneMinute`、`comments`、`orders` 接入五维四率和 5 分钟历史：状态为 `ok` 时在 MCP 缺失字段后补充；状态为 `zero_pending` 时整组忽略，仍使用大屏真实值。`qianchuan/report/live/get/` 当前今日及历史查询均返回空 `data`，暂不接入。
- 自动化测试：`test_server.py` 当前 62 个用例通过，覆盖 MCP 原始口径优先于大屏、MCP 暂不可用时带标签的大屏回退、净成交与总成交审计隔离、四账号直播巡检、确认未开播状态、MCP 挂起或未分类异常时 `/api/live` 仍快速返回采集器数据、新鲜 `stale` 大屏值可用、官方直播字段零值保护与五维补充、知识来源章节标注、手动刷新请求 ID、产品学习资料、素材分页、直播流和 HTTP 接口等链路。
- 2026-10-21 素材板块更新：官方素材报表替代全零的 `stats_info` 作为跑量来源；补视频与直播间画面当天累计；TOP5 两栏、全量素材合并、标题/直播素材去重、计划日期统一为 `2026.6.30` 风格、缓存兜底均已验证。验收截图见 `material-report-final.png`。

## 5. 下一步

- 产品学习资料已完成本地抽取、分块、检索、知识库对话和策略建议来源标注；下一步可选接入 DeepSeek，由大模型基于通用投放知识先行作答，再把检索到的片段作为底线校验标注来源与冲突。无论是否接入模型，“已上传”都不等于“模型已经学会”，经验只做底线参考，不是唯一答案。
- 继续补齐历史数据：账户报表 `50000` 时使用计划日报回退，计划回退受 `campaigns.historyDays` 限制。`campaigns.historyDays` 已从 7 调到 30，快照当前覆盖 `2026-09-23` 至 `2026-10-23` 共 31 个日期、18 个有效日；下一步备份快照后验证 90 / 180 天回填。
- Open API 凭证已配置并验证计划、素材、直播间接口；继续观察账户报表 `50000` 是否恢复，恢复后可去掉“计划日报汇总”回退。
- 计划素材已接入，下一步补充素材级人群画像接口；当前素材画像仍显示“—”。
- 实时直播画面链路已打通；下一步接入直播录像存储，替换复盘页的回放示例数据。
- 自动画面采集需要在 Chrome / Edge 中一次性加载 `live-capture-extension`，并保持千川直播大屏页面打开；不安装时仍可手工粘贴短时拉流地址。
- 接入人脸识别、视频理解与主播风格模型，替换录屏上传后的模拟分析结果。
- 接入实时指标、ASR 和违禁词库，替换实时诊断中仍为示例的话术与主播状态数据。
- 接入 ASR、逐句归因和话术效果模型，替换实时话术看板的示例语句与归因结果。
- 接入词库同步渠道（团队表格、千川词库、开放 API），替换本地上传与示例版本记录。
- 接入千川操作 API，替换投放操作台的示例执行，并按操作时间回读流量影响。
- 文档解析、本地检索与知识库对话已接入产品学习资料，投放诊断页已复用同一资料清单和命中片段作为底线校验；下一步评估 DeepSeek 以通用知识为主、经验底线校验的方式生成建议。
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
- 180 天回填仍未完成：`campaigns.historyDays` 已从 7 调到 30 并完成 30 天窗口回填，但 90 / 180 天范围尚未验证；继续扩大前需先保护现有快照，避免旧有效值被 0 覆盖。
- 当前开发机 PATH 中没有 `python` / `py`，Python 服务回退到 Codex 自带运行时；换电脑时应确保 `python` 可用，不能依赖这条 Codex 专用路径。PowerShell 5.1 执行含中文的 `.ps1` 时需要 UTF-8 BOM。
- `qianchuan.config.json` 和 `data/qianchuan-token.json` 已在 `.gitignore` 中排除。不要为了“方便复制”把真实 token 写进 README、AGENTS.md、截图或提交历史。
- 素材页最初无数据的根因有两处：误把账户 182 天窗口传给素材接口，以及每个计划只取第 1 页 100 条；素材必须使用独立 `materialStartDate` 窗口，并按 `page_info.total_page` 拉完全部分页，再用 `total_number` 核对唯一素材数。
- `VIDEO` 与 `LIVE_ROOM` 必须使用各自字段集：直播间画面使用 `live_show_count_exclude_video_for_roi2`、`live_watch_count_exclude_video_for_roi2` 等字段；把视频的 `*_v2` 展示/观看字段传给直播间画面会返回 `40000 参数错误`。
- 当前计划 `1866854933192299` 返回 1348 条视频 + 1 条直播间画面；计划 `1869402008695177` 返回 865 条视频 + 1 条直播间画面。后者的素材接口统计仍全部为 0，即使计划日报有消耗，也不能据此补造素材跑量。
- `/qianchuan/uni_promotion/ad/material/get/` 适合获取计划素材库和封面，但其 `stats_info` 在本账户会返回全零；真实跑量必须使用 `/qianchuan/report/uni_promotion/data/get/`。该接口的 `anchor_id` 过滤值应传抖音号 ID（`aweme_id`），不是 `room_info.anchor_id`。
- 素材维度报表的 `anchor_id`、`aggregate_smart_bid_type`、`ecp_app_id` 是必填过滤项，单次过滤只传一个枚举码；视频主题使用 `SITE_PROMOTION_POST_DATA_VIDEO`，直播间画面主题使用 `SITE_PROMOTION_POST_DATA_LIVE`，且直播间画面的维度列表也必须显式包含 `anchor_id`。
- 2026-10-25 冷启动排查发现 `data/live-server.log` 被云同步标记为只读，`live_watchdog.py` 启动 `server.py` 时打开该日志抛出 `PermissionError`，导致看门狗 code 1 退出、`start.bat` 一直等待。现已改为主日志不可写时自动写入 `data/live-server.active.log`，并通过 UTF-8 模式启动看门狗。
- 登录助手关闭可见浏览器属于保存后的后台交接动作，但旧代码只看 URL 就关闭，随后又把带 roomId 的 `qianchuan.jinritemai.com/board-next` 当旧地址清空。现在新版 EBP 登录后 SSO 到的 `board-next?roomId=...` 被识别为现行直播大屏；登录助手必须实际解析到页面指标后才倒计时关闭，因此不会在列表页或指标未加载时闪退。

## 7. 进度快照（2026-10-23）

### 7.1 可运行状态

- `server.py` 提供 `/api/dashboard`、`/api/sync`、`/api/live`、`/api/live/screen`、`/api/live/discover`、`/api/campaign/diagnostics` 和 `/api/health`；`index.html` 为单页前端；`start.ps1` / `start.bat` 会启动看门狗、主服务和直播大屏采集器，并打开 `http://127.0.0.1:8765/`。
- 截至 2026-10-23 21:55，最新快照 `data/qianchuan-snapshot.json` revision 3552：账户序列 31 个日期（`2026-09-23` 至 `2026-10-23`），18 个有效消耗/成交日，日均消耗 24,612.16、日均成交 13,955.88、日均订单 83.11；近 7 天素材 3,037 条，其中 1,339 条非零跑量。
- 同步节奏：服务端每 10 秒执行当天轻量实时同步，每 180 秒执行完整历史同步，素材元数据与归因分页按 900 秒周期执行；已完成自然日的历史账户报表与抖音号日报各缓存 120 秒，当天累计值每个实时周期重新拉取；千川请求之间强制 0.35 秒间隔，命中 40000 / 40100 / 429 自动重试，持续限流时按 60 / 120 / 300 秒自动退避，并把 `syncBackoffSeconds` 写进快照和 `/api/health`。
- `test_server.py` 32 个用例通过，覆盖日期范围、10 秒周期与账号顺序、MCP 协议链、当前直播场次发现与 19 位 room_id 精度、大屏直抓交易、5 分钟历史归档、五维四率 MCP 优先/大屏回退、投放诊断 30 天基线与空数据说明、今日累计覆盖与零值保护、轻量同步跳过历史/素材、账户/抖音号对账、刷新 3 秒响应、多指标图表、素材分页、直播流和 HTTP 接口。`npm run test:live-screen` 覆盖中文单位、交易/曝光/渠道标签解析、EBP roomId 和 FLV 地址提取。
- 2026-10-23 21:55 运行态核验存在缺口：主服务健康且实时同步正常；大屏最后有效心跳为 `2026-10-23T13:52:04.824Z`（北京时间 21:52:04），此后心跳过期，`streamCaptureOnline=false`，本机未检出看门狗和采集器进程。`/api/live` 已按真实失败态返回，并继续展示 5 分钟持久化历史中最后一次有效节点。
- 直播大屏：支持 m3u8、HTTP-FLV、mp4/webm，以及 RTMP 经 ffmpeg 转本地 HLS；`live-capture-extension` 可从千川直播大屏自动采集签名 FLV，诊断页经本机代理或直连播放。真实播放验证截图见 `diag-real-stream-success.png`。

### 7.2 已接入的真实数据

- 广告主 `1744479430946824` 的账户序列已覆盖 31 个日期（`2026-09-23` 至 `2026-10-23`），其中 18 天有有效消耗/成交；当前 30 天窗口合计消耗 443,018.87、成交 251,205.79、1,496 单。`2026-10-22` 消耗 173,446.77、成交 100,751.14、600 单；`2026-10-23` 为实时累计值，会继续变化。
- 代码已接入今日累计实时层：当天账户行优先使用官方账户报表，失败时回退官方计划汇总；计划行与作者维度行同步覆盖当天日期；快照新增 `realtime`、`syncKind`、`syncRequest` 与 `reconciliation`，`/api/health` 同步暴露。
- 5 条真实全域计划已拉取，其中 `1866854933192299` 当前为“投放中”，`1869402008695177` 等其余计划为暂停或系统暂停。
- 近 7 天素材窗口已更新为 `2026-10-17` 至 `2026-10-23`：当前 3,037 条素材，其中视频 3,034 条、直播间画面 3 条；1,339 条有真实跑量，素材维度合计消耗 70,627.34、成交 44,183.60、263 单。素材报表是素材维度归因，不应强行与计划总消耗差额补造。
- 诊断页实时监控已接通今日直播间、封面、开播时间、直播状态、消耗、成交、ROI、在投计划，以及流量、用户、商品接口；无直播时明确返回 `live: false`。
- 诊断页已改为大屏单源并新增 5 分钟整场归档：实时监控看板、大屏数据卡片、持久化历史曲线、实时数据、在投素材和五维四率共用同一场次；页面刷新或采集短时失败后仍可显示已成功归档节点，不用 MCP 补写交易缺口。
- 五维四率先返回直播大屏值，MCP `qianchuan_report_live_get_v1` 只在后台补充；当前 MCP 报错不会阻塞交易主接口。`/api/live` 首次与缓存过期后的实测响应均在 0.5 秒级。
- 2026-10-23 21:52 最后一次有效大屏抓取：消耗 6,817.68、成交 4,200.00、29 单、ROI 0.62、累计观看 1,857、商品点击 499、曝光 73,846、GPM 2,093.68、实时在线 5、观测峰值 7；流量渠道为短视频及图文引流 51.72%、搜索 20.69%、直播推荐 10.34%、其他 10.34%、头条西瓜 6.90%。该节点已写入 5 分钟历史，但之后心跳已过期，不能视为当前实时值。
- 复盘页已移除实时监控页签，只保留录制状态、录像回放、问题/优势标注、主播画像和赛后整体结论。
- 投放诊断 `/api/campaign/diagnostics` 已接入近 30 天真实基线，当前窗口 30 天、观测到 30 个日期、18 个有效日，日均消耗 24,610.71、日均成交 13,955.88、日均订单 83.11、平均客单 167.92、平均 ROI 0.5671；MCP 返回空数据时会明确展示字段级缺失原因，并暂停给出放量/控量操作。

### 7.3 仍为示例或未接入

- 数据页：近 30 天账户序列已回填，180 天仍未完成；长周期结论在补齐前不可用。AI 诊断仍为本地规则，DeepSeek 尚未配置。
- 素材页：人群画像仍为空；跑量、完播率、平均停留已由素材维度报表接入，综合分基于当前已有字段计算。
- 诊断页：直播大屏采集进程当前未运行，最后心跳已过期；需要恢复看门狗和采集器并完成整场稳定性验证。主播语速/能量/情绪、话术 ASR 合规仍待接入；1 分钟观看和评论字段当前未返回。
- 直播大屏：累计观看、商品点击、GPM、实时在线、曝光及交易字段已能真实抓取；历史原生峰值在线未确认存在，`peakOnline` 仍是采集器启动后的观测最高值。录像存储、回放切片和 ASR 仍未接入。
- 话术页：违禁词本地 TXT/CSV 上传可用；ASR 逐句归因、优质话术摘取、持续低效话术统计仍为示例。
- 投放诊断：MCP 直播报表当前返回空 `data`，实时字段、流量渠道和用户画像均处于失败态；操作台已用近 30 天快照做推演，但不执行、不写入千川后台。本地学习资料已接入建议的底线校验，DeepSeek 生成和真实操作 API 尚未接入。
- 复盘：录像回放、时间轴标注、主播画像、主播库仍为示例；直播流、录像存储、ASR、人脸识别和视频理解尚未接入。
- 取数：`campaigns.historyDays` 已从 7 调整为 30 并完成回填，但 `HISTORY_DAYS=182` 对应的 90 / 180 天仍未验证；当前快照只能用于近 30 天窗口。
- 自动启动：`install-autostart.ps1` 和 `start-hidden.vbs` 已实现，但尚未完成“重启 Windows 后自动恢复服务与采集器”的实机验收。

### 7.4 当前优先级

1. 通过 `start.bat` 重新拉起看门狗、主服务和采集器，确认 `/api/live/screen` 心跳恢复；排查 21:52 后采集器退出及日志中的 `live-screen-metrics.json` 原子写入 `EPERM`。
2. 在当前直播持续观察至少一个完整场次，覆盖 10 秒心跳、换场、下播重开、断流、签名过期、跨小时运行和页面刷新恢复。
3. 打印并核对 `qianchuan_report_live_get_v1` 原始返回，确认当前空 `data` 是权限、参数、场次还是接口能力问题；修复前继续保持失败态，不用大屏补 MCP 字段口径。
4. 备份现有快照后验证 90 / 180 天计划日报回填，至少检查 30 / 90 / 180 天范围和零值保护。
5. 完成开机自启实机验收，记录 Windows 重启后看门狗、服务、采集器 PID 和诊断页恢复时间。
6. 在 UI 统一标明“观测峰值（采集开始后）”，并保留首次观测时间；继续确认千川是否有原生历史峰值在线字段。
7. 继续接入素材人群画像、DeepSeek、真实 ASR、录像存储与回放切片、千川真实操作 API。

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

### 7.7 2026-10-23 当日总结

以下状态以 2026-10-23 21:55 的 `/api/health`、`/api/live`、快照和进程检查为准；实时数字与运行状态会继续变化，交接时以接口返回为准。

#### 2 - 今天做了什么

- 完成诊断页直播数据“大屏单源”：交易、累计观看、商品点击、曝光、GPM、实时在线和可识别流量渠道直接读取千川直播大屏；抓取失败时保留失败态，不再通过 MCP 或其他字段补造。
- 新增 5 分钟整场归档 `data/live-screen-history.json`，页面刷新、服务重启和短时抓取失败后仍可展示已成功落盘的历史节点；历史曲线与实时卡片已合并到诊断页。
- 完成五维四率的 MCP 优先、大屏逐字段回退逻辑；MCP 缺失的停留、评论等字段显示“未返回”，不用 0 或反推值填充。
- 新增 `/api/campaign/diagnostics`，接入近 30 天快照真实基线、字段级缺失说明、5 分钟异常推断和操作台推演。当前基线为 30 天窗口、18 个有效日，日均消耗 24,610.71、日均成交 13,955.88、日均订单 83.11、平均 ROI 0.5671。
- 将 `campaigns.historyDays` 从 7 调整为 30 并完成回填；账户快照当前覆盖 `2026-09-23` 至 `2026-10-23` 共 31 个日期，其中 18 天有有效消耗/成交。
- 素材窗口同步更新为 `2026-10-17` 至 `2026-10-23`，当前 3,037 条素材、1,339 条非零跑量，视频 3,034 条、直播间画面 3 条。
- 修复 `live_watchdog.py` 心跳函数提前返回造成的误判重启，并新增 `install-autostart.ps1`、`install-autostart.bat`、`uninstall-autostart.ps1`、`start-hidden.vbs` 和 `AUTOSTART.md`，支持当前 Windows 用户登录后自动启动诊断工具。
- 完成真实大屏抓取验证：最后一次有效节点为 21:52:04，消耗 6,817.68、成交 4,200.00、29 单、ROI 0.62、累计观看 1,857、商品点击 499、曝光 73,846、GPM 2,093.68、实时在线 5、观测峰值 7。
- 验证结果：32 个 Python 用例、Node 采集解析用例、Python 编译、内联 JavaScript 语法检查和无头浏览器控制台检查通过；更新验收截图 `diagnosis-real-monitor-final.png`、`campaign-real-data-failure-final.png`。

#### 3 - 还有什么没做

- 大屏运行稳定性尚未闭环。21:55 核验时最后心跳已过期，`streamCaptureOnline=false`，本机未检出 `live_watchdog.py` 和 `live-screen-agent.js` 进程；日志中还出现过 `live-screen-metrics.json` 原子写入 `EPERM`。持久化历史可保留旧节点，但当前实时值不可用。
- 尚未完成整场稳定性验收，包括换场、下播重开、断流恢复、签名过期、跨小时运行、页面刷新和采集器自动重启。
- MCP `qianchuan_report_live_get_v1` 当前仍返回空 `data`；投放诊断的实时指标、流量渠道和用户画像处于失败态。没有核实前不能猜测字段或用大屏值冒充 MCP 返回。
- 大屏没有确认存在原生历史峰值在线字段，当前峰值只是采集器启动后的观测最高值；1 分钟观看、评论、关注等字段仍未返回。
- 30 天历史已回填，但 90 / 180 天历史未完成、未验证，当前快照不能用于 90 / 180 天结论。
- 开机自启代码已完成，但尚未做 Windows 重启后的实机验收，也尚未验证断网、登录态失效和采集器异常退出后的自动恢复。
- 素材人群画像、DeepSeek 诊断、真实 ASR、逐句话术归因、录像存储、回放切片、人脸/视频理解和千川真实操作 API 均未接入。
- `start.ps1` 启动前会结束本机所有 Python 进程，不影响功能验证，但会波及其他 Python 程序；尚未增加“仅清理本项目进程”的可选模式。

#### 4 - 下一步要做什么

1. 通过正常桌面环境运行 `start.bat`，恢复看门狗、主服务和采集器；确认新 PID、`/api/health`、`/api/live/screen` 与 10 秒心跳恢复，并定位 21:52 后进程缺失及 `EPERM` 写入问题。
2. 在当前直播持续观察至少一个完整场次，逐项验证换场、下播、重新开播、断流、签名过期和跨小时运行；失败时确认页面展示真实失败态且历史归档不丢。
3. 打印并核对 `qianchuan_report_live_get_v1` 原始 JSON-RPC 返回，确认空 `data` 的具体原因；随后修正参数、权限或字段映射，再恢复投放诊断和五维四率。
4. 备份现有快照后验证 90 / 180 天计划日报回填，检查 30 / 90 / 180 天范围、零值保护和旧有效值不被 0 覆盖。
5. 完成开机自启实机验收：重启 Windows 后检查看门狗、服务、采集器 PID、诊断页恢复时间和断网后的重试行为。
6. 在诊断页统一标注“观测峰值（采集开始后）”及首次观测时间，并继续确认千川是否提供原生历史峰值在线字段。
7. 按业务价值继续接入素材人群画像、DeepSeek 诊断、真实 ASR、话术逐句归因、录像与回放切片、千川真实操作 API。

### 7.8 2026-10-24 当日总结

以下状态以 2026-10-24 本次收尾时的代码、自动化测试和本机接口检查为准；登录时间和实时数据会继续变化，交接时以 `/api/health`、`/api/live/screen` 和现场页面为准。

#### 1 - 今天做了什么

- 完成新版 EBP 直播大屏地址治理：配置只接受 `business.oceanengine.com` 的 EBP 直播分析大屏或带 `live_room_id` / `roomId` 的地址；旧版 `qianchuan.jinritemai.com/uni-prom` 和无 roomId 的旧 `/board-next` 不再接受。采集器遇到旧地址会立即清空 `pageUrl`，不再打开旧页面空转。
- 重写登录启动链路：`login-live-screen.bat` 固定使用项目 `runtime\node\node.exe`，不再回退系统 PATH；缺少 runtime Node 或 `puppeteer-core` 时直接给出明确错误。登录模式会等待后台采集器释放单实例锁，再打开可见浏览器。
- 收紧登录保存条件：只有识别到 roomId，或页面出现累计观看、商品点击、峰值、GPM、消耗、成交中的至少 2 项时，才写入 `data/live-screen.json`；EBP 首页和旧版页面不会覆盖正确地址。
- 完成采集器单实例与锁恢复：使用 `data/live-screen-agent.lock` 阻止重复采集器；看门狗拉起前先检查既有 PID；启动时清理 `SingletonLock`、`DevToolsActivePort`、`DevToolsActivePort-*`、`lockfile` 及 `Default` 子目录残留；退出时关闭浏览器并释放锁。
- 修复长加载误杀：采集器每 5 秒刷新心跳，覆盖浏览器启动、EBP 页面加载和三个页签抓取过程；看门狗首次启动宽限从 60 秒提高到 180 秒。实测 EBP 页面加载超过 60 秒时，同一采集器 PID 不再被错误重启。
- 统一登录失效展示：后端顶层错误、交易通道、行为通道和前端实时监控、五维四率、数据流均显示“登录已过期，请重新登录”，不再降级成“未开播”或普通“未返回”；历史归档只作为历史节点展示。
- 确认自启和守护链路：Startup 快捷方式指向 `start-hidden.vbs`，自启循环拉起看门狗，看门狗同时守护 `server.py` 和采集器。分别强制结束采集器、后端和看门狗后，均成功拉起新 PID，`/api/health` 恢复 `ok=true`。
- 验证结果：`test_server.py` 33 项、`test_live_watchdog.py` 9 项、Node 采集测试、Python 编译、内联 JavaScript 语法检查和 PowerShell 脚本解析全部通过。运行态最终为：看门狗、后端、采集器各 1 个进程，`/api/health` 正常，采集器心跳新鲜，`/api/live` 正确返回 `login_required`。
- 实际打开过带 roomId 的新版 EBP 详情页并观察到采集器持续心跳；随后独立 `chrome-profile` 的登录态失效，页面跳转到 EBP 登录页，接口按真实失败态显示“登录已过期，请重新登录”。

#### 2 - 还有什么没做

- 当前 `chrome-profile` 的 EBP 登录态已过期，尚未完成一次人工登录后的真实指标恢复验收；因此当前页面显示 `login_required`，不能视为实时抓取已恢复。
- 登录态恢复后，尚未完成至少一个完整直播场次的稳定性验收，包括换场、下播重开、断流恢复、签名过期、跨小时运行、页面刷新和采集器自动重启。
- 新版 EBP 页面在登录态有效时曾成功打开详情页，但尚未核实全部交易和行为指标标签均已稳定映射；若页面字段改版，仍需校准 `data/live-screen.json` 的 `metrics.*.labels` 或 `selector`。
- Windows 重启后的开机自启尚未做实机验收；当前已验证 Startup 快捷方式存在、自启循环可拉起看门狗、看门狗可重启后端和采集器，但没有实际重启 Windows。
- 复盘录像实跑使用当前内置 ffmpeg 3.0.1：不支持新版 HLS `append_list` 和 `rw_timeout`，因此采用 MPEG-TS segment muxer + 程序生成 `.m3u8`；MP4 合并需要 `-bsf:a aac_adtstoasc`。不要改回旧版不支持的参数。
- 当前 `faster-whisper 1.2.1` 与已安装 PyAV 的路径解码接口不兼容；`live_asr.py` 已改为先用 PyAV 解码成 16k float32 NumPy 波形再送入 Whisper，不要直接改回 `model.transcribe(path)`。
- 当前沙箱身份无权重写 Administrator 的 Startup 快捷方式，重新执行安装器会报“拒绝访问”；需要在正常桌面用户下执行 `install-autostart.bat` 才能刷新或重建快捷方式。
- MCP `qianchuan_report_live_get_v1` 仍返回空 `data`；投放诊断的 MCP 实时指标、流量渠道和用户画像仍处于失败态。没有核实前不能用大屏值冒充 MCP 返回。
- 90 / 180 天历史回填、素材人群画像、DeepSeek 诊断、真实 ASR、逐句话术归因、录像存储、回放切片、人脸与视频理解、千川真实操作 API 仍未完成。

#### 3 - 下一步要做什么

1. 在正常桌面环境双击 `login-live-screen.bat`，按脚本提示进入 `business.oceanengine.com` 新版 EBP 直播大屏；确认地址保存为 EBP 大屏或带 roomId 的地址。
2. 登录后依次检查 `/api/live/screen`、`/api/live` 和诊断页，确认状态从 `login_required` 切换到 `ok` 或 `partial`，并核对消耗、成交、订单、ROI、累计观看、商品点击、GPM、实时在线和流量渠道。
3. 若 `partial` 持续存在，检查 EBP“直播数据 / 流量表现 / 直播间投放”三个页签的实际 DOM 文案，必要时校准 `data/live-screen.json` 的标签或 selector，不使用其他接口补造。
4. 在当前直播持续观察至少一个完整场次，验证换场、下播重开、断流、跨小时、页面刷新、浏览器崩溃和采集器重启后的自动恢复。
5. 在正常桌面用户下重新执行 `install-autostart.bat`，然后实际重启 Windows，检查登录 Windows 后是否直接可用 `http://127.0.0.1:8765/`，并确认看门狗、后端和采集器各只有一个实例。
6. 完成登录态恢复和整场稳定性验收后，再继续处理 MCP 直播报表空数据、90 / 180 天历史回填及素材人群画像等后续模块。

### 7.9 2026-10-25 当日总结

#### 2 - 今天做了什么

1. 修复 `start.bat` 冷启动失败：解决 `data/live-server.log` 只读导致看门狗启动 `server.py` 时抛 `PermissionError`、启动器一直等待的问题。后端日志不可写时自动回退到 `data/live-server.active.log`。
2. 同步修复启动器日志锁：`data/live-autostart.log` 被云同步或其他进程短暂占用时，`start.ps1`、`start-background.ps1`、`start-autostart-loop.ps1` 和安装器自动改写 `data/live-autostart.active.log`，日志失败不再阻断启动。
3. 完成冷启动实测：停止本项目看门狗、后端和采集器后执行 `start.bat`，约 9 秒内恢复页面，看门狗、后端、采集器各 1 个进程，`/api/health` 正常且采集器心跳恢复。
4. 修复直播大屏登录链路：`login-live-screen.bat` 不再长时间等待旧采集器 PID，接管请求可在秒级释放单实例锁并打开登录页；只有实际解析到 roomId 或大屏指标后才保存地址、倒计时并交接，不再把保存后的正常关闭误判为闪退。
5. 确认新版 EBP 与旧版地址边界：`business.oceanengine.com` 为登录入口，SSO 后带 roomId 的 `qianchuan.jinritemai.com/board-next` 是现行大屏；只有无 roomId 的旧 board 和旧 `/uni-prom` 才拒绝，解决新旧千川地址误判。
6. 完成开机自动恢复与后台采集：持久化 `data/live-screen-session.json` 的 Cookie、localStorage 和 sessionStorage；正常开机由看门狗、后端和采集器自动恢复，关闭项目页面不影响后台采集和 5 分钟历史归档。
7. 修复直播画面突然黑屏、短暂卡顿和后端重启后无画面：固定使用本机 `/api/live/stream.flv?room=...` 代理，启用 384KB 初始缓冲，代理快速重试，增加 `Accept-Encoding: identity`，并按 20 秒周期重新登记仍在播放的签名 FLV 地址。
8. 扩大直播 CDN 白名单，加入实际重定向域名 `*.bytefcdnrd.com`；后端重启后即使旧长连接不再触发网络事件，也能在约 20 秒内恢复画面地址。
9. 修复 `data/live-screen-history.json` 末尾多余 `}` 导致 `/api/live` 整体失败的问题；新增 `.bak.json` 原子备份、主文件损坏隔离和空历史降级，历史读取故障不再阻断当前大屏指标与画面。
10. 定位实时在线与累计成交在 17:15 后重叠的原因：项目页面关闭期间历史节点仍持续写入，实际是无头大屏长连接读取值冻结。采集器新增指标签名检测，连续 5 分钟完全不变时自动刷新大屏并重新绑定当前直播流；前端把实时在线放入独立底部刻度带。
11. 查清 MCP 权限上限：当前 API Key 只绑定 MCP 网关，开放 11 个工具，没有素材管理或素材维度工具；`qianchuan_report_live_get_v1` 对当前全域推广账户返回空 `data`，`qianchuan_report_uni_promotion_get_v1` 还会出现 40100/50000，不能把空值或错误写成业务 0。
12. 新增 OAuth2 授权助手：`oauth-login.bat` / `oauth_login.py` 可填写 App ID、App Secret 和已登记回调地址，生成带随机 state 的授权链接，接收本机回调或粘贴远程回调 URL，换取并安全保存 Access Token、Refresh Token、到期时间和 scope。
13. 新增 OAuth 状态与自动刷新骨架：`GET /api/oauth/status`、`/api/health.oauth` 只暴露配置状态和到期信息；Access Token 到期前 5 分钟自动使用 Refresh Token。当前尚未执行真实新授权，因为本机没有开放平台应用的 App ID/Secret/回调配置。
14. 新增 Open API 网络中断重试：把 `http.client.IncompleteRead` 纳入千川请求重试，解决全量同步在响应中途断开后直接失败的问题；重试后完整同步已成功结束。
15. 新增直播数据源对比接口 `GET /api/live/compare?account=fashion`。实测今日直播间 Open API 正确识别 `roomId=7700373751996746532`、状态 `LIVING`，但当前账号消耗、成交、订单、观看、点击等全部返回 0；同一时刻无头大屏返回真实非零值，因此 Open API 不能替代大屏实时经营指标。
16. 素材统计窗口统一为 `2026-07-01` 至最近完整自然日，当前覆盖 `2026-07-01—2026-10-24` 共 116 天；素材库每 3 分钟刷新，每 3 小时执行完整对账。
17. 完成素材完整数与删除同步：5/5 计划完整，计划源总数 4,448，账户去重 1,885，接口缺失 0；后台已删除素材会从项目全量表同步移除，历史报表中存在但当前素材库不存在的素材只保留审计计数。
18. 找到并接入真实素材上传时间：官方 `/open_api/v1.0/qianchuan/video/get/` 的 `create_time` 即上传时间。视频库 1,854 条全部返回上传时间；与 1,885 条去重素材合并后，1,829 条匹配成功。
19. 明确 56 条无上传时间素材：51 条历史视频已不在当前视频库，5 条为直播间画面；按 `material_ids` 回查仍无结果时继续显示“未获取”，不能用素材 ID、视频 ID、名称日期或其他字段推算。
20. 落实素材清理规则：曝光 `< 60` 且订单 `< 2` 且上传 `> 40` 天标红“建议删除”；上传时间确实未获取时标黄“待核对上传时间”。本次快照按该规则识别 1,097 条红色、45 条黄色，规则会随着下一次真实同步变化。
21. 素材页新增等级筛选：优质、观察、待优化、无数据、建议删除、待核对上传时间；筛选口径与页面综合判断和清理提示保持一致。
22. 素材页新增选择导出：开启后逐行显示复选框，支持逐条勾选、全选当前筛选、清空和仅导出已选素材；搜索、类型、等级筛选变化时保留勾选，切换账号或计划时清空，避免跨范围误导出。
23. 完成真实 `.xlsx` 导出：浏览器端生成标准 OOXML 工作簿，包含 29 列、素材与计划信息、全部经营指标、综合判断、投放策略、清理提示、素材/审核状态、人群画像、统计窗口和数据来源；红/黄风险行带底色，首行冻结并启用自动筛选。
24. Excel 导出实测通过：无头 Edge 筛选并全选 1,029 条待优化素材，下载约 2 MB 文件，共 1,030 行（含表头）、29 列；Office Excel COM 和 `openpyxl` 均成功打开，表头、数据、冻结窗格、自动筛选和颜色格式正常。
25. 回归验证：`test_server.py` 41 项、`test_live_watchdog.py` 10 项、Node 采集器测试、Python 编译、页面内联 JavaScript 语法和 PowerShell 脚本解析全部通过；当前服务健康、采集器状态 `ok`。

#### 3 - 还有什么没做

1. 真实 OAuth 授权尚未完成：本机没有 `data/qianchuan-oauth.json`，未知 App ID、App Secret 和已登记回调地址；当前 `oauthConfigured=false`、`refreshTokenConfigured=false`，现有 Token 过期后仍需人工处理。
2. 今日直播间 Open API 对当前全域推广账户只返回直播间身份和零值经营数据，直播大屏仍是实时交易与行为指标的唯一真实来源；尚未找到能替代大屏的官方实时经营接口。
3. 51 条已离库历史视频和 5 条直播间画面尚无真实上传时间；没有证据时继续保持“未获取”，尚未确认是否存在其他官方资产接口可补齐。
4. 当前只完成短时连续采集和冷启动验证，尚未覆盖一个完整直播场次的换场、下播重开、断流、签名过期、跨小时运行、浏览器崩溃及自动恢复。
5. Windows 实际重启后的开机自启尚未验收；目前验证了冷启动和无页面运行，但没有真正重启 Windows 检查登录后自动恢复时间与进程唯一性。
6. 素材每 3 分钟刷新、每 3 小时完整对账的长时间连续运行尚未跨多个周期观察；两次强制全量同步中曾出现 `IncompleteRead`，已加重试并成功，但仍需观察后续稳定性。
7. 账户维度实时报表偶发 500，当前自动回退官方计划汇总；回退值可用，但页面和 `/api/health` 会显示 `partial`，尚未恢复为账户维度原始来源。
8. MCP 直播报表仍为空，投放诊断的 MCP 实时指标、流量渠道和人群画像仍处于失败态；不能拿大屏或 MCP 其他聚合值冒充缺失字段。
9. 素材人群画像仍未接入；DeepSeek、真实 ASR、逐句话术归因、录像存储、回放切片、人脸/视频理解和千川真实操作 API 均未完成。
10. 素材 Excel 导出已自动验证，但尚未经过用户手工选择、下载、Office 打开和业务字段确认；需要用户完成最后一轮人工验收。
11. `start.bat` 已能冷启动，但当前不会强制重启仍健康运行的旧后端；更新 Python 代码后需要先手动结束本项目的后端与看门狗，尚未提供只重启本项目进程的一键入口。

#### 4 - 下一步要做什么

1. 在巨量开放平台登记回调地址，推荐 `http://127.0.0.1:8767/oauth/callback`；双击 `oauth-login.bat` 填写 App ID、App Secret 和回调地址，完成一次真实授权。
2. 授权后确认 `/api/oauth/status` 显示 `oauthConfigured=true`、`refreshTokenConfigured=true` 和有效到期时间；再用新 Token 重新跑 `GET /api/live/compare`、今日直播间、素材库视频和 `/api/health`。
3. 用户手工进入素材页测试：按优质/待优化筛选、逐条勾选、全选、清空、导出 Excel，并核对下载文件名、29 列字段、综合判断、清理提示和颜色格式。
4. 跟踪一次完整直播场次，重点验证 10 秒心跳、5 分钟归档、换场、下播重开、断流、签名刷新、跨小时、关闭项目页面和采集器自动重启；如有字段冻结，校准标签或 selector，不使用其他接口补值。
5. 在正常桌面用户下运行 `install-autostart.bat` 后实际重启 Windows，记录从登录桌面到 `http://127.0.0.1:8765/` 可用的时间，并确认看门狗、后端、采集器各只有一个实例。
6. 连续观察素材 3 分钟刷新与 3 小时对账，核对新增、删除、缺失数、上传时间和红黄标规则；如出现接口断包，检查自动重试日志并继续保留上次完整值。
7. 继续调查 51 条历史视频和直播间画面是否存在可用的官方上传时间接口；没有真实返回值时保持“未获取”，禁止推算。
8. 观察账户实时报表 500 与 MCP 空数据是否恢复；恢复前继续保持回退来源和失败态标注，再推进素材人群画像、DeepSeek、ASR、录像回放和真实操作 API。
9. 为 `start.bat` 增加“重启本项目”安全模式：只结束本项目 `server.py`、`live_watchdog.py` 和采集器，不误杀本机其他 Python 进程；同时保留当前已验证通过的冷启动模式。

### 7.10 2026-11-02 当日总结

以下状态以 2026-11-02 22:05 的 `/api/health`、`/api/learning/documents`、页面验收和自动化测试为准；实时经营数据与运行状态会继续变化，交接时以接口现场返回为准。

#### 2 - 今天做了什么

1. 新增独立“知识库”页面，支持批量上传 TXT、MD、CSV、JSON、PDF、DOC/DOCX、XLS/XLSX、PPT/PPTX，单文件限制 25 MB；上传后自动抽取文本、重叠切分、写入本地 `data/learning-index.json`，并支持下载、删除和重建索引。
2. 新增知识库问答接口 `POST /api/assistant/chat` 和前端对话区。回答先基于通用投放知识结合当前数据给出建议，再用本地检索命中的 1–3 个片段做底线校验，展示文档名、片段序号、相关度和原文出处，并标注与过往习惯的一致或冲突；未命中或没有资料时明确说明并继续按通用知识回答，不编造内部规则。
3. 知识库已接入三个实际应用位置：专属助手对话、数据页“AI 问题定位”、投放诊断“下一手建议”。投放诊断会把命中资料作为底线校验，标注与过往习惯的一致或冲突，不再据此上调置信度。
4. 新增整体学习进度条和单文档学习进度。整体进度按“成功进入检索索引的文档数 ÷ 已上传文档数”计算；可检索文档显示 100%，已保存但文本提取失败的文档显示 35% 并标注失败原因。
5. 新增“学习进度与成果解说”板块，动态展示提取字数、可检索片段数、文件格式、待处理/失败文档，以及知识当前应用到哪些产品功能；页面明确说明这里展示的是本地知识覆盖度，不代表模型参数被重新训练。
6. 完成真实页面验收：临时构造 1 份可学习文档和 1 份旧格式失败文档时，整体进度正确显示 75%，单文档分别显示 100% 和 35%；验收后临时文档已删除。
7. 当前知识库真实状态为 2 份文档、68 个可检索片段、49,657 个提取字符，整体学习进度 100%；文档为 `操作记录.xlsx` 和 `千川投放skill-v1.md`。
8. 回归验证：`test_server.py` 51 项全部通过，页面内联 JavaScript 语法检查通过；桌面和移动端页面验收截图已生成。知识库相关 PRD、AGENTS 说明和前端契约测试已同步更新。

#### 3 - 还有什么没做

1. DeepSeek 尚未接入。当前知识库对话是本地检索式原文抽取，不是大模型自然语言生成；不能把“命中文档并回答”表述成已经完成模型训练或 DeepSeek 学习。
2. 尚未记录每个文档在真实对话、问题定位和投放建议中的实际引用次数与最近引用时间。当前页面能说明“接入了哪些功能”，但还不能回答“某份文档具体被用过多少次、最近一次用在哪里”。
3. 对话记录只保存在当前页面内存，刷新页面后清空；尚未实现本地持久化、收藏问题或历史会话管理。
4. 检索仍是本地 TF-IDF + 中英文 n-gram，不是语义向量检索。资料规模扩大后可能出现同义表达召回不足；当前不能宣称具备语义理解。
5. 扫描版 PDF 和旧版 DOC/XLS/PPT 不支持 OCR/格式转换，仍会明确标记文本提取失败；扫描件、老 Office 文件还不能直接进入知识库。
6. 文档模型尚未增加目录/标签/版本管理、重复文档检测、批量文件夹导入和文档级启用/停用。当前只能按单文件上传、查看和删除。
7. 截至 22:05，服务进程与知识库接口正常，但当日经营数据实时同步状态仍为 `failed`，`realtime.updatedAt` 仍停留在 `2026-10-26T21:03:38+08:00`；MCP 最近错误为 SSE HTTP 400 `app信息有误`。这与知识库功能无关，但仍是当前产品整体运行缺口。
8. OAuth 目前只有 Access Token，没有 Refresh Token；`oauthConfigured=false`、`refreshTokenConfigured=false`，现有 Token 到期后仍需人工处理。

#### 4 - 下一步要做什么

1. 配置 DeepSeek 后，由大模型基于通用投放知识结合当前数据先作答，再用 `/api/learning/search` 或 `/api/assistant/chat` 命中的片段做底线校验，冲突处标注“这和过往的投放习惯不符”；经验是刹车不是方向盘，不把知识库当唯一答案。
2. 增加知识引用审计：按文档记录命中次数、最近命中时间、最近应用模块（助手对话 / 问题定位 / 投放建议）和最近引用片段，在“学习成果解说”中展示真实使用情况。
3. 将问答历史持久化到本地，支持历史会话、问题收藏和按文档筛选相关问答；敏感知识仍只保存在本机。
4. 在文档规模明显增长后引入语义向量检索或混合检索，并保留当前 TF-IDF 结果作为兜底和可解释命中依据。
5. 增加扫描 PDF OCR、旧版 Office 转换和批量文件夹导入；无法转换的文件继续明确失败，不把“已上传”标记成“已学习”。
6. 增加文档标签、版本、启用/停用和重复检测，方便区分投放 SOP、场次复盘、字段口径和经营数据。
7. 继续修复当日经营数据实时同步和 MCP `app信息有误` 问题，并补齐 OAuth 自动续期；知识库能力与本机经营数据链路应分别验收，不能相互冒充成功。

### 7.11 2026-11-05 当日总结

以下状态以 2026-11-05 13:32 的本机运行态、`/api/health`、`/api/live/discover` 和自动化测试为准；直播场次、指标和进程状态会继续变化。

#### 1 - 今天做了什么

1. 复核 2026-11-04 的官方直播字段对照工作，确认真实账号 `1744479430946824` 当前场次 `7704532779547085622` 可以由今日直播间 Open API 正确发现，四个抖音号查询完整，当前官方累计值仍为 `0`，大屏同场次有真实非零值。
2. 补齐官方直播字段和五维四率之间的断点：`officialLive.status=ok` 时，`watchCount`、`watchOneMinute`、`comments`、`orders` 在 MCP 未返回后补充，最后才回退大屏；`zero_pending` 时整组忽略，不使用 0 覆盖大屏。
3. 5 分钟历史节点同步补齐大屏未直接返回的 1 分钟观看和评论字段；大屏已有值始终优先，只有缺失字段才从五维来源补充。
4. 诊断页曝光层说明同步改为“MCP、官方直播字段与大屏均未返回”，避免页面仍只写 MCP/大屏两路。
5. 新增自动化用例同时覆盖两条边界：官方直播字段非零时正确进入漏斗和历史；官方 `zero_pending` 时不得覆盖大屏值。
6. 修复直播发现瞬时超时误清空画面地址：只有四个账号明确确认未开播或换场时才重置流；`discovery_error` / `discovery_incomplete` 保留当前场次的短时流 URL，让 20 秒周期登记在服务恢复后继续工作。
7. 完成故障注入验证：仅重启本项目后端后，采集器进入短暂 `discovery_error`，但 `streamCaptureOnline` 保持 `true`；下一次巡检恢复 `status=ok`、`live=true`，`/api/live` 继续返回当前 roomId 和大屏交易指标。
8. 为知识库命中的经验增加统一来源标注：Markdown 文档按命中词定位最近的 `## 第X节` 标题，输出“文件名 第X节 标题”；Excel 等无章节文档只输出文件名。AI 问题定位、投放诊断“下一手建议”、知识库对话和经验底线校验列表统一使用该标注，并以浅灰小字放在结论或动作附近。
9. 顶部“刷新”改为真正的按需拉取：前端同时触发当日报表实时同步和 `/api/live/refresh`，采集器通过请求文件提前结束等待并抓取一次大屏，后端等到同一请求 ID 的最新状态后直接返回。按钮加载期间显示“正在拉取最新数据...”，完成后立即把该份 `/api/live` 快照应用到页面。
10. 真实页面验收：点击刷新后约 4.5 秒完成大屏抓取，加载状态、成功提示、9 项 KPI 和知识依据小字均正常渲染；状态文件与 `/api/live` 的消耗、净成交、净成交订单逐项一致。当前实测值会继续变化，以现场为准。
11. 修正数据源优先级：看板今日数据先读取 60 秒内有效的 MCP 缓存，MCP 有交易指标时使用 MCP 原始口径并标注“千川 MCP · 主数据源”；只有 MCP 无有效值时，才使用大屏并标注“大屏直抓（MCP暂不可用）”。
12. 投放诊断新增独立的大屏回退边界：MCP 有值时完全保持 MCP 口径；MCP 报错、空 data 或没有交易指标时，才临时读取大屏，响应增加 `fallbackFromMCP=true`、`mcpAvailable=false` 和明确来源标签。
13. 数据页面恢复 MCP 优先和来源隔离展示：主报表指标不再统一改名成净成交，也不再跨源覆盖；大屏专属 KPI、五维四率和实时诊断继续使用大屏自己的净成交数字。
14. 回归验证：`test_server.py` 62 项、`test_live_watchdog.py` 10 项、Node 采集器测试、Python 编译和页面内联 JavaScript 语法检查全部通过。
15. “指标走势”增加大屏历史回退：MCP/报表无可用序列时，直接使用 `/api/live?account=fashion` 返回的当前直播 5 分钟历史节点绘制消耗、成交、订单、净成交ROI 和净成交成本，并在图表元信息标注“大屏直抓（MCP暂不可用）”和实际直播抖音号。
16. 大屏采集器新增渠道明细网络解析：从直播大屏 `statQuery` 的 `combined_first_compass_entrance_code` 行中直接读取 `total_live_watch_cnt_for_roi2` 和 `total_live_pay_amt_for_roi2`，计算每个渠道的流量占比、成交金额占比和渠道千次观看成交，不使用页面文字猜测。
17. 投放诊断的“流量渠道与用户画像”在 MCP 回退时展示 8 个渠道的流量占比、成交金额占比和千次观看成交；页面明确显示“大屏直抓（MCP暂不可用）”，人口属性缺失时说明大屏渠道明细不提供性别、年龄、地域画像。
18. 真实页面验收：“指标走势”已绘制大屏历史折线并显示实际直播号；渠道表已显示短视频及图文引流、搜索、直播推荐、头条西瓜、抖音商城推荐、关注、个人主页&店铺&橱窗等渠道数据。

#### 2 - 还有什么没做

1. 今日直播间 Open API 的累计值仍为 0，因此本次仅完成“将来非零时可用”的代码闭环，不能宣称当前官方的 1 分钟观看、评论和成交已经恢复。
2. 当前本机使用已有 Access Token，仍没有 Refresh Token；`oauthConfigured=false`、`refreshTokenConfigured=false`。
3. MCP `qianchuan_report_live_get_v1` 对全域推广账户仍返回空 `data`，投放诊断的 MCP 实时指标、流量渠道和用户画像继续保持失败态。
4. 90 / 180 天历史、素材人群画像、DeepSeek、ASR、录像回放、人脸/视频理解和千川真实操作 API 仍未完成。

#### 3 - 下一步要做什么

1. 继续观察今日直播间 Open API 的累计非零样例；出现非零值后核对五维来源标记、四率计算和 5 分钟历史节点，不把 0 当成真实经营结果。
2. 完成 OAuth App ID / App Secret / 回调地址配置和一次真实授权，验证 Refresh Token 自动续期。
3. 继续等待或排查 MCP 直播报表空 `data`，保持失败态，不用大屏或官方字段冒充 MCP 返回。
4. 在真实直播场次中继续验收换场、下播重开、断流、签名过期、跨小时运行和采集器自动恢复。

## 8. 更新记录

### 2026-10-25：开机自动恢复、登录接管与直播画面稳定化

- 新增千川 OAuth2 一键授权链路：`oauth-login.bat` 会读取/提示填写本机 `data/qianchuan-oauth.json` 中的 App ID、App Secret 和已登记回调地址，生成带随机 `state` 的 `open.oceanengine.com/audit/oauth.html` 授权链接；本机回调会自动用 `auth_code` 换取 Access Token/Refresh Token，远程回调可粘贴完整回调 URL。Token 写入 `data/qianchuan-token.json`，到期前 5 分钟自动使用 Refresh Token 刷新。`GET /api/oauth/status` 和 `/api/health.oauth` 只暴露配置/到期状态，不返回任何密钥。
- 重要区分：`data/qianchuan-mcp.json` 中的 API Key 只用于 11 个 MCP 工具，不能生成 OAuth 授权链接；OAuth 必须使用巨量开放平台开发者应用的 App ID/App Secret，并确保应用后台已申请千川接口权限。
- 新增直播数据源逐项对比 `GET /api/live/compare?account=fashion`。2026-10-25 实测今日直播间 Open API 能返回精确 `roomId=7700373751996746532`、`LIVING`，但当前全域推广账户的消耗、成交、订单、累计观看、商品点击等字段均为 0；同一时刻无头大屏返回消耗 16,833.01、成交 8,232、56 单、累计观看 2,974、商品点击 957。因此 Open API 可用于直播间发现与辅助字段核对，不能替代大屏实时经营指标。
- 素材上传时间接入官方 `/open_api/v1.0/qianchuan/video/get/`：响应 `create_time` 即上传时间。实测素材库 1,854 条视频全部有上传时间；合并到 5 个计划、1,885 条去重素材后，1,829 条能匹配真实上传时间，56 条无法匹配（51 条历史视频已不在当前素材库、5 条直播间画面），这 56 条保持“未获取”，不推算。
- 素材页新增选择导出与真实 `.xlsx` 导出：开启选择模式后逐行复选框、全选当前筛选、清空和仅导出已选素材；新增等级筛选（优质、观察、待优化、无数据、建议删除、待核对上传时间）。导出的单工作表包含 29 列，保留综合判断和独立清理提示，红/黄风险行底色、冻结首行、自动筛选。已用无头 Edge 实测筛选并全选 1,029 条待优化素材，下载文件约 2 MB；Office Excel COM 与 openpyxl 均成功打开，读取 1,030 行（含表头）、29 列。
- 启动器日志在 `data/live-autostart.log` 被云同步或其他进程短暂占用时，`start.ps1`、`start-background.ps1`、`start-autostart-loop.ps1` 和安装器会自动改写到 `data/live-autostart.active.log`，不再因日志写锁阻断启动。
- Open API Key 实际绑定 `https://open.oceanengine.com/qianchuan/mcp?API_KEY=...`，是 MCP 网关凭证。实测 `tools/list` 仅开放 11 个工具：账户基础/授权查询、代理商与工作台账户查询、抖音号授权、标准推广账户报表、今日直播报表、全域推广账户报表、店铺广告主列表和字段说明；没有素材管理或素材维度工具。
- `qianchuan_report_live_get_v1` 对当前全域账户 `1744479430946824`、抖音号 `7637818476896437305` 调用成功（code 0）但返回空 `data`，原因是该工具属于标准推广直播报表；当前账户实际使用全域推广。`qianchuan_report_uni_promotion_get_v1` 曾触发 40100 系统限流或 50000 服务错误，需按退避重试，不能把空响应或错误写成真实 0。
- 当前 OAuth 直连 Open API 已用于 `/qianchuan/today_live/room/get/`、流量/用户/商品接口、计划/素材库和素材维度报表。素材上传时间改由官方 `/open_api/v1.0/qianchuan/video/get/` 获取，响应 `create_time` 的官方定义就是素材上传时间；当前账户实测 1,854 条视频全部返回该字段。计划素材库中的直播间画面及 51 条已不在当前视频库的历史视频无法从该接口取得上传时间，页面必须继续显示“未获取”，不能按素材 ID、视频 ID 或名称日期推算。
- 实时曲线 17:15 后“在线与成交重叠”经历史节点核对排除了项目页面关闭：17:15—20:15 每 5 分钟节点持续写入，但无头大屏页读到的消耗、成交、订单、观看和在线值全部冻结。重启采集器后数值立即更新，确认是独立大屏页长连接假死，不是项目页面或后台停止。
- `live-screen-agent.js` 现在检测核心指标签名；连续 5 分钟完全不变时自动刷新大屏页面并重新绑定当前直播流，避免页面 DOM 长时间停留在旧值。看门狗、后端、采集器不依赖项目页面，关闭项目页面仍持续归档。
- 实时监控图把“实时在线”放入独立的底部刻度带和浅色背景，不再与累计消耗、累计成交共用主图区域，避免量纲不同且同时持平时产生视觉重叠。
- 素材统计窗口改为 `2026-07-01` 至最近完整自然日；本次真实刷新覆盖 `2026-07-01—2026-10-24`，共 116 天。素材库每 3 分钟刷新，每 3 小时执行一次完整对账标记。
- 素材库以千川计划素材库接口为准：本次 5/5 计划完整，源总数 4,448 条，账户去重 1,885 条，缺失 0 条；同步删除 43 条已不在后台的素材、新增 2 条。历史报表中有 41 条素材已不在当前素材库，现只保留审计计数，不再重新加入全量表。
- MCP `tools/list` 当前没有素材维度工具，因此素材数据来源统一标注为“千川 Open API · 计划素材库 + 素材维度报表”，不拿 MCP 账户聚合值冒充素材明细。
- 计划素材接口和素材维度报表本身不返回上传时间；上传时间必须从独立的 `/open_api/v1.0/qianchuan/video/get/` 素材库视频接口取得，并按 `material_id` 合并。不能把“计划素材列表没有时间”误判为千川整体没有该字段。
- `/open_api/v1.0/qianchuan/video/get/` 的 `create_time` 官方定义为素材上传时间；对已不在当前素材库的历史视频，按 `material_ids` 回查仍可能为空，此时必须显示“未获取”，不能用素材 ID、视频 ID 或名称日期推算。
- 全量素材按曝光量降序展示；素材报表维度不再按“素材×每日”拉取，改为 116 天区间直接聚合，避免行数超过接口分页上限。部分报表查询失败时保留上次同窗口指标并标记不完整，不将失败写成 0。
- 2026-10-25 再次出现“有指标但无画面”：后端重启会清空 `LiveStreamRegistry` 的内存地址，而采集器只在网页产生新的 FLV 网络响应时登记，旧长连接不再触发上报。采集器现按 20 秒周期强制重新登记最近一条流地址，后端重启后最多约 20 秒自动恢复画面。
- 实际媒体重定向域名为 `*.bytefcdnrd.com`，旧白名单只允许 `douyincdn.com` / `byteimg.com`，周期登记会返回 HTTP 400。现已将 `bytefcdnrd.com` 加入受信字节 CDN 白名单；实测后端重启后先无流地址，周期登记后自动恢复，浏览器 `readyState=4` 且画面持续前进。
- `data/live-screen-history.json` 末尾曾多出 `}`，旧版后端在历史归档读取时抛 JSON 解析异常，导致 `/api/live` 整条链路返回 `live=false`。现已修复现网文件；新代码会同时维护 `data/live-screen-history.bak.json`，主文件损坏时先备份为 `live-screen-history.corrupt-<时间>.json`，再从备份恢复，无法恢复时使用空历史继续运行。
- 历史读取故障已与实时数据隔离：即使历史恢复流程出现异常，也只返回历史曲线错误，不再阻断当前大屏指标、画面和 `/api/live`。
- `login-live-screen.bat` 不再等待旧采集器 PID 最长 90 秒。登录模式会写入接管请求，常驻采集器在 500ms 检查周期内保存会话、关闭浏览器并释放单实例锁；5 秒内未释放时才执行进程树兜底结束，因此点击后可立即进入当前直播场次的登录页。
- 新增 `data/live-screen-session.json` 会话快照，成功后保存 EBP/千川 Cookie、localStorage 和 sessionStorage，并在每次启动时恢复；该文件包含敏感登录凭据，已加入 `.gitignore`，只能本机安全保管。
- 正常使用不再需要双击 `login-live-screen.bat`。开机由计划任务/Startup 启动看门狗、后端和采集器；采集器使用当前直播场次和持久化登录态自动恢复，每次从 Open API 发现最新 roomId。仅当平台明确要求重新扫码或短信验证时，登录脚本才作为应急入口。
- 直播播放改为固定使用本机代理 `/api/live/stream.flv?room=...`，不再把每 30 秒可能变化的签名直链作为播放器主地址，避免每次 URL 更新都销毁并重建播放器。
- FLV 播放器启用 384KB 初始缓冲、关闭音频轨道要求；代理断流时先对同一本机地址快速重试两次，再回退直链。上游代理请求增加 `Accept-Encoding: identity` 和 `no-cache`，减少压缩/缓存造成的短暂断流。
- 自动化回归保持通过：`test_server.py` 33 项、`test_live_watchdog.py` 10 项、Node 采集测试、Python 编译和 PowerShell 语法检查。

### 2026-10-25：冷启动修复与新版 EBP 直播大屏交接修复

- 复现冷启动卡“等待中”：完全停止计划任务、看门狗、后端和采集器后，`start.bat` 启动的 `live_watchdog.py` 因 `data/live-server.log` 被标记为只读，在打开日志时触发 `PermissionError` 并以 code 1 退出，后端没有启动。
- 看门狗日志改为可回退打开：主日志不可写时自动写入 `data/live-server.active.log`；后台启动统一使用 `python -X utf8` 和 `PYTHONUTF8=1`，避免隐藏 PowerShell 进程中的编码问题。`start.ps1` 等待时间调整为 120 秒，并优先通过 Edge/Chrome 显式打开诊断页。
- 冷启动实测：8765 端口空闲、无项目进程时执行 `start.bat`，约 4 秒内 `/api/health` 恢复、看门狗/后端/采集器各 1 个进程，日志确认 `Opened dashboard with Edge`。
- 修正直播大屏地址判定：新版登录入口仍是 `business.oceanengine.com` EBP，点击直播大屏后通过 SSO 打开 `qianchuan.jinritemai.com/board-next?live_room_id=...`。该地址是现行大屏，不再因域名被判旧地址；只有无 roomId 的旧千川页面才清空。
- 登录助手不再只凭 URL 关闭浏览器：在真实大屏页保存地址后，必须成功解析到页面指标才显示 10 秒倒计时并交接给后台无头采集器；EBP 列表页不会被误判为登录完成，指标未加载时浏览器保持打开。
- 修复后的真实采集验证：roomId `7700373751996746532` 成功抓到消耗 8,649.04、成交 4,032.00、28 单、ROI 0.47、累计观看 1,493、商品点击 497、曝光 66,933、GPM 2,471.89、在线 5 和 5 个成交渠道，`/api/live` 返回 `captureStatus=ok`。
- 登录过期后，采集器会尝试通过 EBP 单点恢复；若 EBP 会话本身失效，页面明确显示 `login_required`，不再误报为“未开播”或“无指标”。
- 回归结果：`test_server.py` 33 项、`test_live_watchdog.py` 10 项、Node 采集测试、Python 编译、PowerShell 脚本解析和内联 JavaScript 语法检查全部通过。

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

### 2026-10-23：大屏单源、整场归档、投放诊断与开机自启

- 直播交易指标改为千川大屏页面直接抓取，`/api/live` 返回 `source=qianchuan_live_screen_direct`；任何交易字段抓取失败时显示“抓取失败”，不再调用 MCP 交易接口补值。
- 新增 `data/live-screen-history.json`，服务端按 5 分钟桶归档整场真实大屏数据，页面刷新、服务重启和短时抓取失败后仍可展示已成功归档的历史节点。
- “直播大屏双通道”从数据页移到诊断页，与实时监控曲线合并；数据卡片位于曲线上方，节点悬停展示进房率、进人渠道、消耗、成交、订单、ROI、在线与 GPM。
- 五维四率改为 MCP `qianchuan_report_live_get_v1` 优先，缺失字段逐项回退大屏；曝光、1 分钟观看、评论等未返回字段显示“未返回”，不按 0 或反推值填充。
- 新增 `/api/campaign/diagnostics`：消耗、成交、ROI、GPM、在线、流量渠道、用户画像从 MCP 实时读取；MCP 返回空数据时给出字段级缺失原因和权限/字段解决方案，不使用大屏或演示值补造。
- 投放诊断下一手建议使用目标成交成本 300、商品价格 168、ROI 参考线 0.56 与真实数据做规则推断；流量异常由大屏 5 分钟历史增量推断，并明确标注为推断。
- 千川操作台的滑块推演改为读取近 30 天快照真实日均消耗、成交、订单、客单价与 ROI，输出推演 ROI、消耗、点击、成交、订单和成本；点击数为空时保持空值。操作不执行、不写入千川，统一标注“仅供参考”。`campaigns.historyDays` 已从 7 调到 30，并完成一次完整回填：当前 30 天窗口有 30 个日期、18 个有效消耗/成交日，日均消耗 24,602.72、日均成交 13,927.88、日均订单 82.94、平均客单 167.92、平均 ROI 0.5661。
- 修复 `live_watchdog.py` 心跳函数提前返回导致采集器被误判并反复重启的问题；新增 `install-autostart.ps1` / `start-hidden.vbs`，当前用户登录后自动启动看门狗、后端、大屏采集器并打开诊断页。
- 验证：32 个 Python 用例、Node 采集解析用例、Python 编译、内联 JavaScript 语法检查和无头浏览器控制台检查全部通过；真实大屏抓到消耗 6,687.96、成交 3,696、26 单、ROI 0.55、观看 1,820、点击 474、曝光 72,538、GPM 1,921.69；当前 MCP 直播报表返回空 `data`，投放诊断按失败态展示。验收截图：`diagnosis-real-monitor-final.png`、`campaign-real-data-failure-final.png`。

### 2026-10-24：新版 EBP 登录与采集稳定性修复

- 配置地址收紧为 `business.oceanengine.com` EBP 直播分析地址或带 `live_room_id` / `roomId` 的地址；旧版 `qianchuan.jinritemai.com/uni-prom` 和无 roomId 的旧 `/board-next` 不再接受。采集器检测到旧版 `pageUrl` 后立即清空配置并进入 `login_required`，不再打开旧页面空转。
- `login-live-screen.bat` 固定使用项目 `runtime\node\node.exe`，不再回退系统 PATH；缺少 runtime Node 或 `puppeteer-core` 时直接失败。登录模式等待采集器释放单实例锁后打开可见浏览器，只有识别到 roomId 或累计观看、商品点击、峰值、GPM、消耗、成交中的至少 2 项才保存地址。
- 采集器使用 `data/live-screen-agent.lock` 单实例锁；看门狗启动和重启前都检查既有采集器 PID。新增退出关闭浏览器、SIGINT / SIGTERM 清理、过期 agent 锁替换，以及 `SingletonLock`、`DevToolsActivePort`、`DevToolsActivePort-*`、`lockfile` 和 `Default` 子目录残留清理。
- 采集器新增 5 秒心跳保活，长页面加载和三个 EBP 页签抓取期间不会被 45 秒心跳阈值误杀；看门狗首次启动宽限提高到 180 秒。
- `login_required` 在后端顶层错误、交易通道、行为通道和页面状态中统一显示“登录已过期，请重新登录”，不再降级为“未开播”；有历史节点时明确只展示历史归档。
- 自启链路为 Windows 登录时计划任务，权限不足时回退到当前用户 Startup 快捷方式；`start-autostart-loop.ps1` 拉起看门狗，看门狗同时守护 `server.py` 和采集器。已实测强制结束采集器、服务端和看门狗自身后均拉起新 PID，`/api/health` 恢复 `ok=true`。
- 回归结果：`test_server.py` 33 个用例、`test_live_watchdog.py` 9 个用例、Node 采集测试、Python 编译和内联 JavaScript 语法检查全部通过。
- 当前运行态：主服务健康，旧版地址已清空；独立 `chrome-profile` 的 EBP 登录态在实测重开后退回登录页，`/api/live` 正确返回 `login_required`。需要双击 `login-live-screen.bat` 完成一次新版 EBP 登录后才能恢复真实大屏指标；代码层面不会再误判为未开播或使用旧接口补值。

### 后续更新约定

- 每次完成可运行功能后，在本节新增日期条目，并在“模块进度总览”和“进度快照”同步更新状态。
- 迁移电脑前，不把 `.tmp-*`、浏览器 profile、`__pycache__` 当成产品文件；真实 token 只通过安全渠道恢复。
- 如果没有更新 `data/qianchuan-snapshot.json`，新电脑首次启动会自动同步；同步失败也不要手工填入示例值冒充真实数据。
