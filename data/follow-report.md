# 直播跟播监控记录

## 2026-11-18 10:40 开播前基线

- 千川采集器：not_live，ok=true，4 个账号均未开播，心跳正常（约 2 秒）
- 百应采集器：crashed 循环中。
  - 诱因：10:35 我误判"占用 buyin-chrome-profile 的 11 个 msedge 进程"是登录窗口残留，终止了它们。实际那是百应采集器自己启动的无头浏览器，终止后 puppeteer 的页面句柄失效，持续报 Attempted to use detached Frame。
  - 现状：看门狗已拉起新进程（PID 37328），浏览器已重建（主进程 31624，共 11 个子进程），但采集器在"直播中控台 → 直播大屏专业版"跳转时反复失败，约每 40 秒重试一次。
- 录制器：waiting_stream，ok=true，主录制 healthy，目录可写
- 转写：idle，modelReady=false（懒加载设计，实测加载 model.bin 成功，耗时 10.1 秒）
- 录制守护：active，primary.healthy=true，backup.healthy=false（旧状态残留，主录制不受影响）
- 处置决定：不再终止任何挂 buyin-chrome-profile 的 msedge 进程；观察 12:00 开播后百应是否自愈
- 需人工：否（当前）
## 2026-11-18 12:34 定时跟播（12:34 实测）

- 千川：ok，live，房间 7709356711446252351（赵镭精讲），心跳 4s
- 百应：ok，live，缺失指标由 6 项降至 3 项（spend、roi、watchCount 仍未抓到），连续抓取正常
- 录制：recording，第 8 段，最后落段 12:34:15；12:22 曾有重启但自动恢复同一 session（2026-11-18_..._120505），未丢录像
- 录制守护：active，主 healthy，备 unhealthy（旧状态，按规则只记录）
- 转写：processing，已处理 0，待处理 1，part_000001 自 12:10 起 24 分钟无产出
- 看门狗：12:26-12:29 百应因 EBUSY（buyin-live-metrics.json 被坚果云同步占用）连续重启 5 次，12:28:41 后稳定
- tmp 残留：0（writeJsonAtomic 修复生效）
- 处理：本次将重启 ASR 让 cpu_threads 由 4 提升到 10 生效
- 需人工：否

### 2026-11-18 13:00 转写链路故障定位与修复（重要）

**根因**：faster-whisper 1.2.1 的解码函数调用 av.open(..., metadata_errors="ignore")，而本机 PyAV 19.0.2 的 av.open 已移除该参数，抛 TypeError: open() got an unexpected keyword argument 'metadata_errors'。转写在解码第一步就失败，因此**从部署以来从未真正产出过话术**（昨天 18:03-18:17 同一段重复 13 次失败即为同一原因）。

**为什么之前看起来像"卡住"**：状态文件停在 processing、已处理恒为 0、日志只有"转写 xxx audio=300s"没有后续，实际是解码异常被吞在重试逻辑里。

**修复方式**：不改依赖版本（降级 PyAV 会影响正在抓直播流的 audio_capture.py），改为在 live_asr.py 启动时给 av.open 包一层兼容壳，自动丢弃 metadata_errors 后透传。已随模块导入生效（自检 patched=True）。

**实测验证**：单独跑 part_000001（300 秒音频）
- 模型加载 9.2 秒
- 转写成功 239 段 / 1674 字
- 转写耗时 411 秒，RTF=1.37
- 抽样文本："比较薄弱像成猛进呢忽上忽下忽高忽低小宝呢学不会听不懂跟不上的这个时候呢把一号链接带回到家来..."（内容为真实直播口播）

**其他调整**：cpu_threads 由 min(4,核数) 提升到 min(10,核数)（本机 12 逻辑核）；beam_size 由 5 降为 1。

**遗留问题（需决策）**：large-v3 在纯 CPU 上 RTF=1.37，即 5 分钟音频要 411 秒处理，稳定落后约 37%。全天 8 小时约 96 段，需要约 11 小时才能转完，当天无法完全追平。可选：换 medium 模型（约 1.5GB，RTF 预计 0.6-0.7，可跟上）或接受延后转写。

**同期状态**：千川 ok/live；百应 ok/缺 3 项（spend、roi、watchCount）；录制 recording 第 12 段。

## 2026-11-18 16:23 跟播轮次（定时任务触发）

- 环境：公司机 WINDOWS-MT4H69T；进程齐全（watchdog 32552、server 20276、千川 node 9536、百应 node 17748、录制 14548、audio_capture 30792、ASR 27720、录制守护 32580）
- 健康接口：顶层 status=partial
- 千川：ok，live=true，账号「赵镭精讲小数基本功」房间 7709356711446252351；spend 11707.7 / GMV 5376 / 订单 34 / ROI 0.46 / 观看 2995 / GPM 1561.51；心跳 age 1.76s
- 百应：ok，age 4.13s，missingMetrics=3（spend / roi / watchCount），error 为空
- 录制：status=recording，segmentCount=25，lastSegmentAt 16:22:56，session 2026-11-18_7709356711446252351_140818
- 录制守护：status=active，primary.healthy=true，backup.healthy=false（主正常、备异常，按规则只记录不处理）
- 转写：status=processing，modelReady=true，processed=9，pending=1，当前 part_000010（16:16:13 开始），ageSeconds=407.64
- tmp 残留：0

### 问题与动作

1. 15:36:41–15:37:37 百应采集器连续报 `The browser is already running for D:\AI投放产品\buyin-chrome-profile`，其间拉起 PID 8264、17748 两次；15:37:37 后稳定，之后每 10s 正常「百应抓取 ok 指标=10 渠道=8 补充=22」。本轮已自愈，未做干预。
2. 15:38:02 录制器进程退出，watchdog 自动重启 PID 14548，恢复同一场次 `_140818`，未丢录像；当前 25 段持续录制正常。
3. ASR ageSeconds=407.64 超过 90s 阈值，但 live-asr.log 显示 16:16:13 已开始 part_000010 且 processed 从 7 推进到 9，属长任务推进中而非卡死，因此未重启（重启会丢弃当前进度且不解决吞吐）。
4. 转写吞吐异常：part_000008 开始 15:22:39、part_000009 15:49:44、part_000010 16:16:13，约 26 分钟/5分钟音频，RTF≈5.3，远慢于早先单测的 1.37，转写将持续落后于录制。

### 需人工

- 转写吞吐（问题 4）：是否改用 medium 模型或接受延后转写。
- 备用录制 backup.healthy=false 长期未恢复（不影响当前主录制）。
- 百应仍缺 spend / roi / watchCount 三项；千川大屏已提供同名字段，需确认复盘口径以哪个为准。