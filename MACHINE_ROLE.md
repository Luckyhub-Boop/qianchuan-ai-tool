# 机器归属规则（采集主控 / 只读）

> 目的：项目代码与 `data/` 放在坚果云同步盘，多台机器同时启动会互相覆盖状态文件，
> 产生大量“冲突”副本（已发生 107 个，累计 572.7 MB）。
> 本规则让同一时间只有**一台**机器负责录制、采集、转写，其余机器只读。

## 角色

| 角色 | 判定 | 行为 |
| --- | --- | --- |
| `primary` 采集主控 | 本机指纹 = `data/primary-machine.json` 中的 `machineId` | 启动完整链路：录制器、本地转写、大屏采集、百应采集、录制守护 |
| `readonly` 只读 | 主控文件存在但指纹不同 | 只启动后端服务供查看，**不录制、不采集、不转写** |
| `unclaimed` 未认领 | 主控文件缺失且本机不是 `PRIMARY_HOSTNAME` | 同上，且**永不自我认领** |

指纹 = 计算机名 + 系统盘卷序列号，见 `machine_identity.py`。

## 文件

- `data/primary-machine.json`：当前采集主控登记。只由主控机写入，只读机永不改写。
- `machine_identity.py`：判定实现。`PRIMARY_HOSTNAME` 常量限定“谁允许自我认领”。

## 当前状态（2026-11-17）

- 采集主控：`WINDOWS-MT4H69T`，machineId `cfdba2e378d6ba53`，卷序列号 `F6C7E7EC`
- 家里那台（`lucky_Win11`）：读到此文件后自动进入只读，不再采集，也不再写 `data/`

## 如何切换主控

1. 在目标机器上查看自己的指纹：
   `python -c "import machine_identity as m; print(m.fingerprint(), m.machine_id())"`
2. 用目标机器的 `machineId` / `hostname` 改写 `data/primary-machine.json`
3. 重启目标机器的 `live_watchdog.py`

> 换主机名或重装系统会改变指纹；此时旧主控文件会失效，需要重新登记。

## 如何验证

看门狗启动日志（`data/live-watchdog.log`）会出现其中一行：

- `本机为采集主控（WINDOWS-MT4H69T），启动完整采集链路`
- `本机不是采集主控（主控=XXX），进入只读模式：只启动后端服务，不启动录制/采集/转写`

## 已知限制（待打包阶段解决）

只读机仍会启动后端服务，`server.py` 可能写入少量派生文件到同步盘 `data/`。
彻底消除需要把 `data/` 移出同步目录（打包基建第 1 项），本规则只是先止血。
