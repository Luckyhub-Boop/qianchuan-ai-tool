from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
AGENT_PATH = ROOT / "live-screen-agent.js"
SCREEN_STATE_PATH = DATA_DIR / "live-screen-metrics.json"
SCREEN_PAUSE_PATH = DATA_DIR / "live-screen-pause"
WATCHDOG_LOG_PATH = DATA_DIR / "live-watchdog.log"
SERVER_LOG_PATH = DATA_DIR / "live-server.log"
AGENT_LOG_PATH = DATA_DIR / "live-screen-agent.log"
RESTART_DELAY_SECONDS = 5
AGENT_STARTUP_GRACE_SECONDS = 60
SCREEN_PAUSE_TTL_SECONDS = 35 * 60


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_log(path: Path, message: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_iso()}] {message}\n")


def watchdog_log(message: str) -> None:
    print(f"[{now_iso()}] {message}", flush=True)
    append_log(WATCHDOG_LOG_PATH, message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def server_url() -> str:
    port = os.getenv("QIANCHUAN_PORT", "8765").strip() or "8765"
    return f"http://127.0.0.1:{port}"


def server_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{server_url()}/api/health", timeout=2) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return isinstance(payload, dict) and "liveScreenCapture" in payload
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def resolve_python() -> str:
    return os.getenv("QIANCHUAN_PYTHON", "").strip() or sys.executable


def resolve_node() -> str:
    configured = os.getenv("QIANCHUAN_NODE", "").strip()
    return configured or shutil.which("node") or ""


def process_alive(process: subprocess.Popen[Any] | None) -> bool:
    return bool(process and process.poll() is None)


def stop_process(process: subprocess.Popen[Any] | None) -> None:
    if not process or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
            process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def start_server() -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = SERVER_LOG_PATH.open("a", encoding="utf-8")
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [resolve_python(), str(ROOT / "server.py")],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"服务进程已拉起 PID={process.pid}")
    return process


def start_agent(node_path: str) -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = AGENT_LOG_PATH.open("a", encoding="utf-8")
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [node_path, str(AGENT_PATH)],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"直播大屏采集器已拉起 PID={process.pid}")
    return process


def state_age_seconds() -> float | None:
    state = read_json(SCREEN_STATE_PATH)
    heartbeat = str(state.get("heartbeatAt") or "").strip()
    if not heartbeat:
        return None
    try:
        parsed = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(parsed.tzinfo) - parsed).total_seconds())
    except (TypeError, ValueError):
        return None


def screen_pause_active() -> bool:
    if not SCREEN_PAUSE_PATH.is_file():
        return False
    try:
        if time.time() - SCREEN_PAUSE_PATH.stat().st_mtime <= SCREEN_PAUSE_TTL_SECONDS:
            return True
        SCREEN_PAUSE_PATH.unlink(missing_ok=True)
        watchdog_log("登录暂停标记已过期，自动恢复采集")
    except OSError as exc:
        watchdog_log(f"读取登录暂停标记失败：{exc}")
    return False


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    node_path = resolve_node()
    if not node_path:
        watchdog_log("未找到 Node.js，直播大屏双通道采集器无法启动")
        raise SystemExit(2)
    if not (ROOT / "node_modules" / "puppeteer-core" / "package.json").is_file():
        watchdog_log("缺少 puppeteer-core，请先在项目目录执行 npm install")
        raise SystemExit(3)

    server_process: subprocess.Popen[Any] | None = None
    agent_process: subprocess.Popen[Any] | None = None
    if not server_healthy():
        server_process = start_server()
    else:
        watchdog_log("检测到既有服务，继续复用")
    agent_process = start_agent(node_path)
    agent_started_at = time.monotonic()
    watchdog_log(f"看门狗启动完成 server={server_url()} agent={node_path}")

    try:
        while True:
            try:
                if not process_alive(server_process):
                    if server_healthy():
                        watchdog_log("服务由外部进程提供，看门狗继续监控")
                    else:
                        server_process = start_server()

                if screen_pause_active():
                    if process_alive(agent_process):
                        watchdog_log("检测到登录暂停标记，停止无头采集器")
                        stop_process(agent_process)
                        agent_process = None
                    time.sleep(2)
                    continue

                age = state_age_seconds()
                agent_healthy = process_alive(agent_process) and (
                    time.monotonic() - agent_started_at <= AGENT_STARTUP_GRACE_SECONDS
                    or (
                        age is not None
                        and age
                        <= max(
                            45,
                            (read_json(SCREEN_STATE_PATH).get("intervalSeconds") or 10)
                            * 4,
                        )
                    )
                )
                if not agent_healthy:
                    reason = (
                        f"心跳超时 {age:.0f}s"
                        if process_alive(agent_process) and age is not None
                        else "进程退出或尚未写入心跳"
                    )
                    watchdog_log(f"直播大屏采集器异常（{reason}），准备重启")
                    stop_process(agent_process)
                    time.sleep(RESTART_DELAY_SECONDS)
                    agent_process = start_agent(node_path)
                    agent_started_at = time.monotonic()
            except Exception as exc:
                watchdog_log(f"看门狗巡检异常：{exc}")
            time.sleep(5)
    finally:
        stop_process(agent_process)
        stop_process(server_process)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
