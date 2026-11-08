# 开机自启

首次安装运行（正常桌面用户）：

```powershell
.\install-autostart.ps1
```

也可以在资源管理器中双击 `install-autostart.bat`。

如果新电脑还没有本地 Whisper，先在项目目录运行 `install-whisper.bat`。它会安装
`faster-whisper`/OpenCC，并把免费 `faster-whisper-tiny` 模型下载到 `models/whisper-tiny/`。

安装器优先注册当前用户的“登录时”计划任务；如果计划任务权限不可用，则在当前用户的 Windows Startup 目录创建 `QianchuanLiveScreenAutostart.lnk` 作为回退。Windows 登录后，脚本会：

1. 启动 `live_watchdog.py`。
2. 由看门狗启动并守护 `server.py`。
3. 由看门狗启动并守护 `live-screen-agent.js`。
4. 由看门狗启动并守护 `buyin-live-agent.js`。
5. 由看门狗启动并守护 `live_recorder.py`。
6. 由看门狗启动并守护 `live_asr.py`，使用项目本地 `models/whisper-tiny` 转写直播音频。
7. 自动打开 `http://127.0.0.1:8765/#review`。
8. 千川采集器恢复 `data/chrome-profile`，百应采集器恢复 `data/buyin-chrome-profile`，自动进入各自已保存的直播大屏并持续抓取。
9. 千川签名直播流可用后，录像器自动写入坚果云目录之外的 `D:\DAI投放产品录屏备份\`；每场 5 分钟分段，结束尝试合并 MP4，并只保留最近 10 个自然日。
10. ASR 从已录制直播分段提取音频，完成本地 Whisper 转写，并写入各自场次的 `asr/` 子目录。

看门狗、服务端、千川/百应采集器和录像器都有单实例保护。`start-autostart-loop.ps1` 负责在看门狗异常退出后重新拉起；看门狗再分别重启 `server.py`、千川采集器、百应采集器和录像器。因此不要为任何子进程单独创建第二个自启项。

登录 Windows 后验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Get-Content .\data\live-watchdog.pid
Get-Process node | Where-Object { $_.Path -like '*\runtime\node\node.exe' }
```

预期：`ok=true`，`liveScreenCapture.status=ok`，`buyinLiveCapture.status=ok` 且 `available=true`；看门狗 PID 对应一个存活的 `python.exe`；项目 Node 采集器有千川、百应各 1 个。若本机禁止写入计划任务或 Startup 目录，安装器会明确报错，需要用当前 Windows 用户身份重新运行 `install-autostart.bat`。

移除开机自启：

```powershell
.\uninstall-autostart.ps1
```

首次分别运行一次 `login-live-screen.bat` 和 `login-buyin.bat`。登录状态保存后，后续开机不需要再次扫码；只有平台明确提示登录态过期时，才重新运行对应登录脚本。
