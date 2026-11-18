from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import machine_identity
import paths


ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = paths.EXTERNAL_ROOT
DATA_DIR = ROOT / "data"
AGENT_PATH = ROOT / "live-screen-agent.js"
SCREEN_STATE_PATH = DATA_DIR / "live-screen-metrics.json"
SCREEN_PAUSE_PATH = DATA_DIR / "live-screen-pause"
BUYIN_AGENT_PATH = ROOT / "buyin-live-agent.js"
BUYIN_SCREEN_STATE_PATH = DATA_DIR / "buyin-live-metrics.json"
BUYIN_SCREEN_PAUSE_PATH = DATA_DIR / "buyin-live-pause"
RECORDER_PATH = ROOT / "live_recorder.py"
RECORDER_STATE_PATH = DATA_DIR / "live-recorder-state.json"
RECORDER_LOCK_PATH = DATA_DIR / "live-recorder.lock"
GUARD_PATH = ROOT / "recording_guard.py"
GUARD_STATE_PATH = DATA_DIR / "live-recording-guard-state.json"
GUARD_LOCK_PATH = DATA_DIR / "live-recording-guard.lock"
ASR_PATH = ROOT / "live_asr.py"
ASR_STATE_PATH = DATA_DIR / "live-asr-state.json"
ASR_LOCK_PATH = DATA_DIR / "live-asr.lock"
LOCK_PATH = DATA_DIR / "live-watchdog.lock"
PID_PATH = DATA_DIR / "live-watchdog.pid"
AGENT_LOCK_PATH = DATA_DIR / "live-screen-agent.lock"
BUYIN_AGENT_LOCK_PATH = DATA_DIR / "buyin-live-agent.lock"
WATCHDOG_LOG_PATH = DATA_DIR / "live-watchdog.log"
SERVER_LOG_PATH = DATA_DIR / "live-server.log"
AGENT_LOG_PATH = DATA_DIR / "live-screen-agent.log"
BUYIN_AGENT_LOG_PATH = DATA_DIR / "buyin-live-agent.log"
RECORDER_LOG_PATH = DATA_DIR / "live-recorder.log"
GUARD_LOG_PATH = DATA_DIR / "live-recording-guard.log"
ASR_LOG_PATH = DATA_DIR / "live-asr.log"
RESTART_DELAY_SECONDS = 5
AGENT_STARTUP_GRACE_SECONDS = 180
SCREEN_PAUSE_TTL_SECONDS = 35 * 60
RECORDER_ERROR_RESTART_SECONDS = 45
ASR_ERROR_RESTART_SECONDS = 60
AGENT_CRASH_RESTART_SECONDS = 30
AGENT_PERSISTENT_RESTART_SECONDS = 120
RESTART_COOLDOWN_SECONDS = 30
STABLE_RUN_SECONDS = 60
MAX_RESTART_BACKOFF_SECONDS = 300


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


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def keep_awake_enabled() -> bool:
    """是否开启“保持系统唤醒”，默认开启，可用 QIANCHUAN_KEEP_AWAKE=0 关闭。"""
    return os.getenv("QIANCHUAN_KEEP_AWAKE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def set_thread_execution_state(flags: int) -> bool:
    """在 Windows 上保持系统唤醒，防止空闲进入睡眠而中断直播录制。"""
    if os.name != "nt":
        return False
    try:
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(flags)
        return True
    except Exception:
        return False


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


def server_port() -> int:
    raw_port = os.getenv("QIANCHUAN_PORT", "8765").strip() or "8765"
    try:
        return int(raw_port)
    except ValueError:
        return 8765


def server_url() -> str:
    return f"http://127.0.0.1:{server_port()}"


def server_port_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", server_port()), timeout=1):
            return True
    except OSError:
        return False


def server_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{server_url()}/api/health", timeout=3) as response:
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
        str(EXTERNAL_ROOT / "runtime" / "node" / "node.exe"),
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


def running_agent_pid(lock_path: Path | None = None) -> int | None:
    payload = read_json(lock_path or AGENT_LOCK_PATH)
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


def child_environment() -> dict[str, str]:
    """子进程统一继承的环境。

    显式把解析出来的外部根写进环境，而不是靠“父进程刚好设过、子进程刚好继承”。
    这样即使以后有人改成独立进程、换启动方式，子进程也不会退回各自的默认值。
    """
    env = dict(os.environ)
    env["QIANCHUAN_EXTERNAL_ROOT"] = str(EXTERNAL_ROOT)
    return env


def start_server() -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open_append_log(SERVER_LOG_PATH)
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [resolve_python(), str(ROOT / "server.py")],
        cwd=str(ROOT),
        env=child_environment(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"服务进程已拉起 PID={process.pid} 外部根={EXTERNAL_ROOT}")
    return process


def start_recorder() -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open_append_log(RECORDER_LOG_PATH)
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [resolve_python(), str(RECORDER_PATH)],
        cwd=str(ROOT),
        env=child_environment(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"直播录像器已拉起 PID={process.pid} 外部根={EXTERNAL_ROOT}")
    return process


def start_asr() -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open_append_log(ASR_LOG_PATH)
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [resolve_python(), str(ASR_PATH)],
        cwd=str(ROOT),
        env=child_environment(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"本地 Whisper ASR 已拉起 PID={process.pid} 外部根={EXTERNAL_ROOT}")
    return process


def start_guard() -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open_append_log(GUARD_LOG_PATH)
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [resolve_python(), str(GUARD_PATH)],
        cwd=str(ROOT),
        env=child_environment(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"录制守护已拉起 PID={process.pid} 外部根={EXTERNAL_ROOT}")
    return process


def start_agent(
    node_path: str,
    agent_path: Path = AGENT_PATH,
    log_path: Path = AGENT_LOG_PATH,
    label: str = "直播大屏采集器",
) -> subprocess.Popen[Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open_append_log(log_path)
    creation_flags = 0x08000000 if os.name == "nt" else 0
    process = subprocess.Popen(
        [node_path, str(agent_path)],
        cwd=str(ROOT),
        env=child_environment(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    watchdog_log(f"{label}已拉起 PID={process.pid} 外部根={EXTERNAL_ROOT}")
    return process


def ensure_agent_started(
    node_path: str,
) -> tuple[subprocess.Popen[Any] | None, int | None]:
    existing_pid = running_agent_pid()
    if existing_pid:
        watchdog_log(f"检测到既有采集器 PID={existing_pid}，不重复拉起")
        return None, existing_pid
    return start_agent(node_path), None


def ensure_buyin_agent_started(
    node_path: str,
) -> tuple[subprocess.Popen[Any] | None, int | None]:
    existing_pid = running_agent_pid(BUYIN_AGENT_LOCK_PATH)
    if existing_pid:
        watchdog_log(f"检测到既有百应采集器 PID={existing_pid}，不重复拉起")
        return None, existing_pid
    return (
        start_agent(
            node_path,
            BUYIN_AGENT_PATH,
            BUYIN_AGENT_LOG_PATH,
            "百应直播中控台采集器",
        ),
        None,
    )


def ensure_recorder_started() -> tuple[subprocess.Popen[Any] | None, int | None]:
    existing_pid = running_agent_pid(RECORDER_LOCK_PATH)
    if existing_pid:
        watchdog_log(f"检测到既有录像器 PID={existing_pid}，不重复拉起")
        return None, existing_pid
    return start_recorder(), None


def ensure_asr_started() -> tuple[subprocess.Popen[Any] | None, int | None]:
    existing_pid = running_agent_pid(ASR_LOCK_PATH)
    if existing_pid:
        watchdog_log(f"检测到既有 ASR 服务 PID={existing_pid}，不重复拉起")
        return None, existing_pid
    return start_asr(), None


def ensure_guard_started() -> tuple[subprocess.Popen[Any] | None, int | None]:
    existing_pid = running_agent_pid(GUARD_LOCK_PATH)
    if existing_pid:
        watchdog_log(f"检测到既有录制守护 PID={existing_pid}，不重复拉起")
        return None, existing_pid
    return start_guard(), None


def state_age_seconds(state_path: Path | None = None) -> float | None:
    state = read_json(state_path or SCREEN_STATE_PATH)
    heartbeat = str(state.get("heartbeatAt") or "").strip()
    if not heartbeat:
        return None
    try:
        parsed = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(parsed.tzinfo) - parsed).total_seconds())
    except (TypeError, ValueError):
        return None


def field_age_seconds(state: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        value = str(state.get(field) or "").strip()
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return max(0.0, (datetime.now(parsed.tzinfo) - parsed).total_seconds())
        except (TypeError, ValueError):
            continue
    return None


def persistent_bad_status(status: str) -> set[str]:
    return {
        "error",
        "crashed",
        "login_required",
        "no_metrics",
        "page_mismatch",
        "config_required",
        "permission_denied",
    }


def needs_manual_action_status(status: str) -> set[str]:
    """重启解决不了的坏状态：只上报，不自动重启。

    登录过期、账号权限不足、缺少配置都只能由人处理；
    反复重启只会不断新建浏览器，把配置目录占住。
    """
    return {"login_required", "permission_denied", "config_required"}


def auto_restart_status(status: str) -> set[str]:
    return persistent_bad_status(status) - needs_manual_action_status(status)


def crash_status(status: str) -> set[str]:
    return {"error", "crashed"}


def screen_pause_active(
    pause_path: Path | None = None,
    label: str = "登录暂停",
) -> bool:
    pause_path = pause_path or SCREEN_PAUSE_PATH
    if not pause_path.is_file():
        return False
    try:
        try:
            pause_data = json.loads(pause_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pause_data = {}
        owner_pid = (
            pause_data.get("pid")
            if isinstance(pause_data, dict)
            else None
        )
        if owner_pid is not None and not pid_is_running(owner_pid):
            pause_path.unlink(missing_ok=True)
            watchdog_log(f"{label}进程已退出，自动恢复采集")
            return False
        if time.time() - pause_path.stat().st_mtime <= SCREEN_PAUSE_TTL_SECONDS:
            return True
        pause_path.unlink(missing_ok=True)
        watchdog_log(f"{label}标记已过期，自动恢复采集")
    except OSError as exc:
        watchdog_log(f"读取{label}标记失败：{exc}")
    return False


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    watchdog_log("外部根解析：" + paths.describe())
    watchdog_log(
        "子进程将继承 QIANCHUAN_EXTERNAL_ROOT=" + str(EXTERNAL_ROOT)
    )
    keep_awake_active = keep_awake_enabled() and set_thread_execution_state(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    )
    if keep_awake_active:
        watchdog_log(
            "系统保持唤醒已开启：看门狗运行期间防止空闲睡眠中断直播录制"
            "（设置 QIANCHUAN_KEEP_AWAKE=0 可关闭）"
        )
    elif keep_awake_enabled():
        watchdog_log(
            "系统保持唤醒调用失败：请手动检查电源设置，避免睡眠中断直播录制"
        )
    try:
        import model_bootstrap

        bootstrap = model_bootstrap.ensure_models(EXTERNAL_ROOT, log=watchdog_log)
        if bootstrap.get("downloaded"):
            watchdog_log("模型自动下载完成：" + "、".join(bootstrap["downloaded"]))
        if bootstrap.get("errors"):
            watchdog_log("模型自动下载部分失败：" + "；".join(bootstrap["errors"]))
        watchdog_log(
            f"模型检查完成：现有 {len(bootstrap.get('present') or [])} 个，"
            f"已补齐 {len(bootstrap.get('downloaded') or [])} 个，"
            f"失败 {len(bootstrap.get('errors') or [])} 个"
        )
    except Exception as exc:
        watchdog_log(f"模型自动下载流程异常：{exc}")
    node_path = resolve_node()
    puppeteer_ready = (EXTERNAL_ROOT / "node_modules" / "puppeteer-core" / "package.json").is_file()
    agent_supported = bool(node_path and puppeteer_ready)
    if not node_path:
        watchdog_log("未找到 Node.js，直播大屏采集器无法启动")
    elif not puppeteer_ready:
        watchdog_log("缺少 puppeteer-core，请先在项目目录执行 npm install")
    if not agent_supported:
        watchdog_log("后端服务将继续运行，直播大屏采集器保持停止")

    server_process: subprocess.Popen[Any] | None = None
    agent_process: subprocess.Popen[Any] | None = None
    buyin_agent_process: subprocess.Popen[Any] | None = None
    recorder_process: subprocess.Popen[Any] | None = None
    asr_process: subprocess.Popen[Any] | None = None
    guard_process: subprocess.Popen[Any] | None = None
    bad_since: dict[str, float] = {}
    last_restart_at: dict[str, float] = {}
    restart_attempts: dict[str, int] = {}
    last_spawn_at: dict[str, float] = {}
    next_restart_at: dict[str, float] = {}

    def restart_gate(component: str) -> tuple[bool, float]:
        """限制同一组件被反复拉起，避免出现“退出就重启”的风暴。"""
        now = time.monotonic()
        blocked_until = next_restart_at.get(component, 0.0)
        if now < blocked_until:
            return False, blocked_until - now
        spawned = last_spawn_at.get(component, 0.0)
        if spawned and now - spawned < STABLE_RUN_SECONDS:
            restart_attempts[component] = restart_attempts.get(component, 0) + 1
        else:
            restart_attempts[component] = 0
        return True, 0.0

    def note_restart(component: str) -> None:
        now = time.monotonic()
        last_spawn_at[component] = now
        attempt = min(restart_attempts.get(component, 0), 6)
        delay = min(MAX_RESTART_BACKOFF_SECONDS, RESTART_DELAY_SECONDS * (2 ** attempt))
        next_restart_at[component] = now + delay
        if attempt > 0:
            watchdog_log(
                f"{component} 连续第 {attempt + 1} 次拉起，{delay:.0f}s 内不再重复重启"
            )

    manual_notice_at: dict[str, float] = {}

    def notice_manual(component: str, status: str, reason: str) -> None:
        """登录过期、权限不足等重启无效的状态，只提示，不重启。"""
        now = time.monotonic()
        if now - manual_notice_at.get(component, 0.0) < 600:
            return
        manual_notice_at[component] = now
        watchdog_log(
            f"{component} 状态 {status}，需要人工处理，不会自动重启；原因：{reason}"
        )

    def should_restart_bad(
        component: str,
        state: dict[str, Any],
        bad_statuses: set[str],
        threshold_seconds: float,
    ) -> tuple[bool, str, float]:
        status = str(state.get("status") or "unknown")
        if status not in bad_statuses:
            bad_since.pop(component, None)
            return False, "", 0.0
        bad_since.setdefault(component, time.monotonic())
        bad_age = time.monotonic() - bad_since[component]
        cooldown = time.monotonic() - last_restart_at.get(component, 0.0)
        reason = str(state.get("error") or state.get("sourceLabel") or status)
        return bad_age >= threshold_seconds and cooldown >= RESTART_COOLDOWN_SECONDS, reason, bad_age

    def mark_component_restarted(component: str) -> None:
        bad_since.pop(component, None)
        last_restart_at[component] = time.monotonic()
        note_restart(component)

    role, primary_owner = machine_identity.resolve_role(DATA_DIR)
    # 只有明确的 primary 才启动采集链路：unclaimed（无主控文件且本机不在认领清单）
    # 与 readonly 一样按受限处理，避免第二台机器悄悄变成主控。
    read_only_mode = role != machine_identity.ROLE_PRIMARY
    watchdog_log("机器身份：" + machine_identity.describe(role, primary_owner))
    watchdog_log("认领资格：" + machine_identity.claim_hint(DATA_DIR))
    if read_only_mode and role == machine_identity.ROLE_READONLY:
        watchdog_log(
            "本机不是采集主控（主控="
            + str(
                primary_owner.get("hostname")
                or primary_owner.get("machineId")
                or "未知"
            )
            + "），进入只读模式：只启动后端服务，不启动录制/采集/转写"
        )
    elif read_only_mode:
        watchdog_log(
            "本机未认领主控（无 primary-machine.json 且不在可认领清单），"
            "按只读处理：只启动后端服务，不启动录制/采集/转写"
        )
    else:
        watchdog_log(
            f"本机为采集主控（{machine_identity.hostname()}），启动完整采集链路"
        )

    if server_healthy():
        watchdog_log("检测到既有服务，继续复用")
    elif server_port_listening():
        watchdog_log("检测到既有服务端口，继续复用等待健康接口恢复")
    else:
        server_process = start_server()
    external_agent_pid: int | None = None
    external_buyin_agent_pid: int | None = None
    external_recorder_pid: int | None = None
    external_asr_pid: int | None = None
    external_guard_pid: int | None = None
    if agent_supported and not read_only_mode:
        agent_process, external_agent_pid = ensure_agent_started(node_path)
        buyin_agent_process, external_buyin_agent_pid = ensure_buyin_agent_started(
            node_path
        )
        recorder_process, external_recorder_pid = ensure_recorder_started()
        asr_process, external_asr_pid = ensure_asr_started()
        guard_process, external_guard_pid = ensure_guard_started()
    agent_started_at = time.monotonic()
    buyin_agent_started_at = time.monotonic()
    agent_label = node_path if agent_supported else "disabled"
    watchdog_log(f"看门狗启动完成 server={server_url()} agent={agent_label}")

    try:
        while True:
            try:
                if keep_awake_active:
                    set_thread_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
                if not process_alive(server_process):
                    if server_healthy() or server_port_listening():
                        if server_process is not None:
                            watchdog_log("服务由外部进程提供，看门狗继续监控")
                        server_process = None
                    else:
                        server_process = start_server()

                if not agent_supported or read_only_mode:
                    time.sleep(5)
                    continue

                recorder_running = (
                    process_alive(recorder_process)
                    or pid_is_running(external_recorder_pid)
                )
                if not recorder_running:
                    allowed, wait_left = restart_gate("recorder")
                    if not allowed:
                        watchdog_log(
                            f"直播录像器重启退避中，{wait_left:.0f}s 后再尝试"
                        )
                    else:
                        watchdog_log("直播录像器进程退出，准备重启")
                        stop_process(recorder_process)
                        stop_pid(external_recorder_pid)
                        recorder_process = None
                        external_recorder_pid = running_agent_pid(RECORDER_LOCK_PATH)
                        if external_recorder_pid:
                            watchdog_log(
                                f"重启等待期间检测到录像器 PID={external_recorder_pid}，继续复用"
                            )
                        else:
                            recorder_process, external_recorder_pid = ensure_recorder_started()
                        mark_component_restarted("recorder")
                else:
                    recorder_state = read_json(
                        RECORDER_LOCK_PATH.parent / "live-recorder-state.json"
                    )
                    recorder_bad, recorder_reason, recorder_bad_age = should_restart_bad(
                        "recorder",
                        recorder_state,
                        {"error"},
                        RECORDER_ERROR_RESTART_SECONDS,
                    )
                    if recorder_bad:
                        watchdog_log(
                            f"录制器持续错误 {recorder_bad_age:.0f}s，准备重启；原因：{recorder_reason}"
                        )
                        stop_process(recorder_process)
                        stop_pid(external_recorder_pid)
                        recorder_process = None
                        external_recorder_pid = None
                        mark_component_restarted("recorder")
                        recorder_process, external_recorder_pid = ensure_recorder_started()

                asr_running = (
                    process_alive(asr_process)
                    or pid_is_running(external_asr_pid)
                )
                if not asr_running:
                    allowed, wait_left = restart_gate("asr")
                    if not allowed:
                        watchdog_log(
                            f"本地 Whisper ASR 重启退避中，{wait_left:.0f}s 后再尝试"
                        )
                    else:
                        watchdog_log("本地 Whisper ASR 服务退出，准备重启")
                        stop_process(asr_process)
                        stop_pid(external_asr_pid)
                        asr_process = None
                        external_asr_pid = running_agent_pid(ASR_LOCK_PATH)
                        if external_asr_pid:
                            watchdog_log(
                                f"重启等待期间检测到 ASR 服务 PID={external_asr_pid}，继续复用"
                            )
                        else:
                            asr_process, external_asr_pid = ensure_asr_started()
                        mark_component_restarted("asr")
                else:
                    asr_state = read_json(ASR_STATE_PATH)
                    asr_bad, asr_reason, asr_bad_age = should_restart_bad(
                        "asr",
                        asr_state,
                        {"error"},
                        ASR_ERROR_RESTART_SECONDS,
                    )
                    if asr_bad:
                        watchdog_log(
                            f"ASR 持续错误 {asr_bad_age:.0f}s，准备重启；原因：{asr_reason}"
                        )
                        stop_process(asr_process)
                        stop_pid(external_asr_pid)
                        asr_process = None
                        external_asr_pid = None
                        mark_component_restarted("asr")
                        asr_process, external_asr_pid = ensure_asr_started()

                guard_running = (
                    process_alive(guard_process)
                    or pid_is_running(external_guard_pid)
                )
                if not guard_running:
                    allowed, wait_left = restart_gate("guard")
                    if not allowed:
                        watchdog_log(
                            f"录制守护重启退避中，{wait_left:.0f}s 后再尝试"
                        )
                    else:
                        watchdog_log("录制守护进程退出，准备重启")
                        stop_process(guard_process)
                        stop_pid(external_guard_pid)
                        guard_process = None
                        external_guard_pid = running_agent_pid(GUARD_LOCK_PATH)
                        if external_guard_pid:
                            watchdog_log(
                                f"重启等待期间检测到录制守护 PID={external_guard_pid}，继续复用"
                            )
                        else:
                            guard_process, external_guard_pid = ensure_guard_started()
                        mark_component_restarted("guard")

                if screen_pause_active(BUYIN_SCREEN_PAUSE_PATH, "百应登录暂停"):
                    if process_alive(buyin_agent_process):
                        watchdog_log("检测到百应登录暂停标记，停止百应无头采集器")
                        stop_process(buyin_agent_process)
                        buyin_agent_process = None
                    if pid_is_running(external_buyin_agent_pid):
                        watchdog_log(
                            f"检测到百应登录暂停标记，停止既有百应采集器 "
                            f"PID={external_buyin_agent_pid}"
                        )
                        stop_pid(external_buyin_agent_pid)
                    external_buyin_agent_pid = None
                else:
                    buyin_state = read_json(BUYIN_SCREEN_STATE_PATH)
                    buyin_age = state_age_seconds(BUYIN_SCREEN_STATE_PATH)
                    buyin_running = (
                        process_alive(buyin_agent_process)
                        or pid_is_running(external_buyin_agent_pid)
                    )
                    buyin_status = str(buyin_state.get("status") or "unknown")
                    buyin_threshold = (
                        AGENT_CRASH_RESTART_SECONDS
                        if buyin_status in crash_status(buyin_status)
                        else AGENT_PERSISTENT_RESTART_SECONDS
                    )
                    buyin_bad, buyin_bad_reason, buyin_bad_age = should_restart_bad(
                        "buyin",
                        buyin_state,
                        auto_restart_status(buyin_status),
                        buyin_threshold,
                    )
                    if buyin_status in needs_manual_action_status(buyin_status):
                        notice_manual(
                            "百应采集器",
                            buyin_status,
                            str(buyin_state.get("error") or buyin_status),
                        )
                    buyin_healthy = buyin_running and not buyin_bad and (
                        time.monotonic() - buyin_agent_started_at
                        <= AGENT_STARTUP_GRACE_SECONDS
                        or (
                            buyin_age is not None
                            and buyin_age
                            <= max(
                                45,
                                (buyin_state.get("intervalSeconds") or 10) * 4,
                            )
                        )
                    )
                    if not buyin_healthy:
                        if buyin_bad:
                            reason = (
                                f"状态持续异常 {buyin_bad_age:.0f}s：{buyin_bad_reason}"
                            )
                        else:
                            reason = (
                                f"心跳超时 {buyin_age:.0f}s"
                                if buyin_running and buyin_age is not None
                                else "进程退出或尚未写入心跳"
                            )
                        allowed, wait_left = restart_gate("buyin")
                        if not allowed:
                            watchdog_log(
                                f"百应直播中控台采集器异常（{reason}），"
                                f"重启退避中 {wait_left:.0f}s 后再尝试"
                            )
                        else:
                            watchdog_log(
                                f"百应直播中控台采集器异常（{reason}），准备重启"
                            )
                            stop_process(buyin_agent_process)
                            stop_pid(external_buyin_agent_pid)
                            time.sleep(RESTART_DELAY_SECONDS)
                            buyin_agent_process = None
                            external_buyin_agent_pid = running_agent_pid(
                                BUYIN_AGENT_LOCK_PATH
                            )
                            if external_buyin_agent_pid:
                                watchdog_log(
                                    f"重启等待期间检测到百应采集器 "
                                    f"PID={external_buyin_agent_pid}，继续复用"
                                )
                            else:
                                (
                                    buyin_agent_process,
                                    external_buyin_agent_pid,
                                ) = ensure_buyin_agent_started(node_path)
                            mark_component_restarted("buyin")
                            buyin_agent_started_at = time.monotonic()

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

                screen_state = read_json(SCREEN_STATE_PATH)
                age = state_age_seconds()
                agent_running = process_alive(agent_process) or pid_is_running(external_agent_pid)
                screen_status = str(screen_state.get("status") or "unknown")
                screen_threshold = (
                    AGENT_CRASH_RESTART_SECONDS
                    if screen_status in crash_status(screen_status)
                    else AGENT_PERSISTENT_RESTART_SECONDS
                )
                screen_bad, screen_bad_reason, screen_bad_age = should_restart_bad(
                    "screen",
                    screen_state,
                    auto_restart_status(screen_status),
                    screen_threshold,
                )
                if screen_status in needs_manual_action_status(screen_status):
                    notice_manual(
                        "直播大屏采集器",
                        screen_status,
                        str(screen_state.get("error") or screen_status),
                    )
                agent_healthy = agent_running and not screen_bad and (
                    time.monotonic() - agent_started_at <= AGENT_STARTUP_GRACE_SECONDS
                    or (
                        age is not None
                        and age
                        <= max(
                            45,
                            (screen_state.get("intervalSeconds") or 10) * 4,
                        )
                    )
                )
                if not agent_healthy:
                    if screen_bad:
                        reason = (
                            f"状态持续异常 {screen_bad_age:.0f}s：{screen_bad_reason}"
                        )
                    else:
                        reason = (
                            f"心跳超时 {age:.0f}s"
                            if agent_running and age is not None
                            else "进程退出或尚未写入心跳"
                        )
                    watchdog_log(f"直播大屏采集器异常（{reason}），准备重启")
                    allowed, wait_left = restart_gate("screen")
                    if not allowed:
                        watchdog_log(
                            f"直播大屏采集器重启退避中，{wait_left:.0f}s 后再尝试"
                        )
                    else:
                        stop_process(agent_process)
                        stop_pid(external_agent_pid)
                        time.sleep(RESTART_DELAY_SECONDS)
                        agent_process = None
                        external_agent_pid = running_agent_pid()
                        if external_agent_pid:
                            watchdog_log(f"重启等待期间检测到采集器 PID={external_agent_pid}，继续复用")
                        else:
                            agent_process, external_agent_pid = ensure_agent_started(node_path)
                        mark_component_restarted("screen")
                        agent_started_at = time.monotonic()
            except Exception as exc:
                watchdog_log(f"看门狗巡检异常：{exc}")
            time.sleep(5)
    finally:
        stop_process(asr_process)
        stop_pid(external_asr_pid)
        stop_process(guard_process)
        stop_pid(external_guard_pid)
        stop_process(recorder_process)
        stop_pid(external_recorder_pid)
        stop_process(buyin_agent_process)
        stop_pid(external_buyin_agent_pid)
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
