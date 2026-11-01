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
LOCK_PATH = DATA_DIR / "live-watchdog.lock"
PID_PATH = DATA_DIR / "live-watchdog.pid"
AGENT_LOCK_PATH = DATA_DIR / "live-screen-agent.lock"
WATCHDOG_LOG_PATH = DATA_DIR / "live-watchdog.log"
SERVER_LOG_PATH = DATA_DIR / "live-server.log"
AGENT_LOG_PATH = DATA_DIR / "live-screen-agent.log"
RESTART_DELAY_SECONDS = 5
AGENT_STARTUP_GRACE_SECONDS = 180
SCREEN_PAUSE_TTL_SECONDS = 35 * 60


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_log(path: Path, message: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_iso()}] {message}\n")

def open_append_log(path: Path) -> Any:
    try:
        return path.open("a", encoding="utf-8")
    except PermissionError:
        fallback = path.with_name(f"{path.stem}.active{path.suffix}")
        return fallback.open("a", encoding="utf-8")


def watchdog_log(message: str) -> None:
    print(f"[{now_iso()}] {message}", flush=True)
    append_log(WATCHDOG_LOG_PATH, message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def acquire_instance_lock() -> Any | None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open("a+", encoding="utf-8")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write("\0")
            handle.flush()
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def release_instance_lock(handle: Any | None) -> None:
    if handle is None:
        return
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


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
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def resolve_python() -> str:
    return os.getenv("QIANCHUAN_PYTHON", "").strip() or sys.executable


def resolve_node() -> str:
    configured = os.getenv("QIANCHUAN_NODE", "").strip()
    candidates = [
        configured,
        str(ROOT / "runtime" / "node" / "node.exe"),
        shutil.which("node") or "",
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        r"C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe",
        str(
            Path(os.getenv("USERPROFILE", ""))
            / ".cache"
            / "codex-runtimes"
            / "codex-primary-runtime"
            / "dependencies"
            / "node"
            / "node.exe"
        ),
    ]
    return next((item for item in candidates if item and Path(item).is_file()), "")


def process_alive(process: subprocess.Popen[Any] | None) -> bool:
    return bool(process and process.poll() is None)


def pid_is_running(pid: int | None) -> bool:
    if not pid or int(pid) <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, int(pid))
        if not handle:
            return ctypes.get_last_error() == 5
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == 258
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def running_agent_pid() -> int | None:
    payload = read_json(AGENT_LOCK_PATH)
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return None
    return pid if pid_is_running(pid) else None


def stop_pid(pid: int | None) -> None:
    if not pid_is_running(pid):
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(int(pid), 15)
    except OSError:
        pass


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
    log_handle = open_append_log(SERVER_LOG_PATH)
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
    log_handle = open_append_log(AGENT_LOG_PATH)
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


def ensure_agent_started(
    node_path: str,
) -> tuple[subprocess.Popen[Any] | None, int | None]:
    existing_pid = running_agent_pid()
    if existing_pid:
        watchdog_log(f"检测到既有采集器 PID={existing_pid}，不重复拉起")
        return None, existing_pid
    return start_agent(node_path), None


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
    puppeteer_ready = (ROOT / "node_modules" / "puppeteer-core" / "package.json").is_file()
    agent_supported = bool(node_path and puppeteer_ready)
    if not node_path:
        watchdog_log("未找到 Node.js，直播大屏采集器无法启动")
    elif not puppeteer_ready:
        watchdog_log("缺少 puppeteer-core，请先在项目目录执行 npm install")
    if not agent_supported:
        watchdog_log("后端服务将继续运行，直播大屏采集器保持停止")

    server_process: subprocess.Popen[Any] | None = None
    agent_process: subprocess.Popen[Any] | None = None
    if not server_healthy():
        server_process = start_server()
    else:
        watchdog_log("检测到既有服务，继续复用")
    external_agent_pid: int | None = None
    if agent_supported:
        agent_process, external_agent_pid = ensure_agent_started(node_path)
    agent_started_at = time.monotonic()
    agent_label = node_path if agent_supported else "disabled"
    watchdog_log(f"看门狗启动完成 server={server_url()} agent={agent_label}")

    try:
        while True:
            try:
                if not process_alive(server_process):
                    if server_healthy():
                        if server_process is not None:
                            watchdog_log("服务由外部进程提供，看门狗继续监控")
                        server_process = None
                    else:
                        server_process = start_server()

                if not agent_supported:
                    time.sleep(5)
                    continue

                if screen_pause_active():
                    if process_alive(agent_process):
                        watchdog_log("检测到登录暂停标记，停止无头采集器")
                        stop_process(agent_process)
                        agent_process = None
                    if pid_is_running(external_agent_pid):
                        watchdog_log(f"检测到登录暂停标记，停止既有采集器 PID={external_agent_pid}")
                        stop_pid(external_agent_pid)
                    external_agent_pid = None
                    time.sleep(2)
                    continue

                age = state_age_seconds()
                agent_running = process_alive(agent_process) or pid_is_running(external_agent_pid)
                agent_healthy = agent_running and (
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
                        if agent_running and age is not None
                        else "进程退出或尚未写入心跳"
                    )
                    watchdog_log(f"直播大屏采集器异常（{reason}），准备重启")
                    stop_process(agent_process)
                    stop_pid(external_agent_pid)
                    time.sleep(RESTART_DELAY_SECONDS)
                    agent_process = None
                    external_agent_pid = running_agent_pid()
                    if external_agent_pid:
                        watchdog_log(f"重启等待期间检测到采集器 PID={external_agent_pid}，继续复用")
                    else:
                        agent_process, external_agent_pid = ensure_agent_started(node_path)
                    agent_started_at = time.monotonic()
            except Exception as exc:
                watchdog_log(f"看门狗巡检异常：{exc}")
            time.sleep(5)
    finally:
        stop_process(agent_process)
        stop_pid(external_agent_pid)
        stop_process(server_process)


if __name__ == "__main__":
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        watchdog_log("检测到看门狗已在运行，本次启动退出")
        raise SystemExit(0)
    try:
        PID_PATH.write_text(str(os.getpid()), encoding="ascii")
        main()
    except KeyboardInterrupt:
        pass
    finally:
        release_instance_lock(instance_lock)
