# 开机自启

首次安装运行（正常桌面用户）：

```powershell
.\install-autostart.ps1
```

也可以在资源管理器中双击 `install-autostart.bat`。

安装器优先注册当前用户的“登录时”计划任务；如果计划任务权限不可用，则在当前用户的 Windows Startup 目录创建 `QianchuanLiveScreenAutostart.lnk` 作为回退。Windows 登录后，脚本会：

1. 启动 `live_watchdog.py`。
2. 由看门狗启动并守护 `server.py`。
3. 由看门狗启动并守护 `live-screen-agent.js`。
4. 自动打开 `http://127.0.0.1:8765/#diagnosis`。
5. 直播大屏采集器恢复已保存的 chrome-profile 登录态，自动进入当前直播大屏并按 5 分钟归档数据。

看门狗和服务端都有单实例保护。`start-autostart-loop.ps1` 负责在看门狗异常退出后重新拉起；看门狗再负责重启 `server.py` 和采集器。因此不要为 `server.py` 单独创建第二个自启项。

登录 Windows 后验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Get-Content .\data\live-watchdog.pid
Get-Process node | Where-Object { $_.Path -like '*\runtime\node\node.exe' }
```

预期：`ok=true`；看门狗 PID 对应一个存活的 `python.exe`；项目 Node 采集器只有 1 个。若本机禁止写入计划任务或 Startup 目录，安装器会明确报错，需要用当前 Windows 用户身份重新运行 `install-autostart.bat`。

移除开机自启：

```powershell
.\uninstall-autostart.ps1
```

如果独立 chrome-profile 登录态过期，需要重新运行一次 `login-live-screen.bat`。登录状态恢复后，后续开机不再需要扫码。
