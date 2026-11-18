"""换机 / 换目录自检。

一条命令看清"这台机器现在缺什么"：
外部根、Python、Node、puppeteer、模型、ffmpeg、录屏目录、机器身份、
子进程环境继承、残留写死路径、服务健康。

只读检查：不安装、不启动、不删除（唯一写动作是录屏目录的可写探测文件，用完立刻删）。

退出码：0 = 全部 PASS；1 = 有 FAIL（WARN 不影响退出码）
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = ROOT.parent.parent

ROWS: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str, warn: bool = False) -> None:
    status = "PASS" if ok else ("WARN" if warn else "FAIL")
    ROWS.append((name, status, detail))


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, (result.stdout or result.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def scan_hardcoded() -> list[str]:
    patterns = ("D:\\AI投放产品", "WINDOWS-MT4H69T")
    suffixes = {".py", ".js", ".ps1", ".bat", ".vbs"}
    # 自检脚本本身要写这些字符串当搜索条件，跳过自己，避免误报。
    skip_names = {"check_paths.py", "check-paths.ps1", "check-paths.bat"}
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if path.name in skip_names:
            continue
        parts = {part.lower() for part in path.parts}
        if "data" in parts or "node_modules" in parts or ".git" in parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for pattern in patterns:
                if pattern in line:
                    hits.append(f"{path.name}:{number}（{pattern}）")
    return hits


def main() -> int:
    env_root = (os.getenv("QIANCHUAN_EXTERNAL_ROOT") or "").strip()
    check(
        "外部根",
        True,
        f"{EXTERNAL_ROOT}（来源：{'环境变量' if env_root else '按程序位置推算'}）",
    )

    # Python 自身
    check("Python 运行时", True, f"{sys.executable}（{sys.version.split()[0]}）")

    # Node
    node_exe = EXTERNAL_ROOT / "runtime" / "node" / "node.exe"
    if node_exe.is_file():
        code, out = run([str(node_exe), "--version"])
        check("Node 运行时", code == 0, f"{node_exe}（{out}）")
    else:
        check("Node 运行时", False, f"缺 {node_exe} —— 先跑 setup-runtime.ps1")

    puppeteer = EXTERNAL_ROOT / "node_modules" / "puppeteer-core" / "package.json"
    check(
        "puppeteer-core",
        puppeteer.is_file(),
        str(puppeteer) if puppeteer.is_file() else f"缺 {puppeteer} —— 在外部根执行 npm install puppeteer-core",
    )

    models_dir = EXTERNAL_ROOT / "models"
    if models_dir.is_dir():
        names = sorted(item.name for item in models_dir.iterdir() if item.is_dir())
        whisper = (models_dir / "whisper-large-v3").is_dir()
        check(
            "AI 模型",
            whisper,
            f"whisper-large-v3={'在' if whisper else '缺'}；已装 {len(names)} 个：{', '.join(names)}",
            warn=not whisper,
        )
    else:
        check("AI 模型", False, f"缺 {models_dir} —— 首次启动会自动下载，或跑 setup-runtime.ps1")

    # 用程序自己的模块回答，避免两套判断
    sys.path.insert(0, str(ROOT))
    import paths  # noqa: E402
    import recording_store  # noqa: E402
    import machine_identity  # noqa: E402

    ffmpeg_path, ffmpeg_source = paths.resolve_ffmpeg()
    check("ffmpeg", bool(ffmpeg_path), f"{ffmpeg_path or '未找到'}（来源：{ffmpeg_source or '未找到'}）")
    if ffmpeg_source.startswith("遗留"):
        check(
            "ffmpeg 可移植性",
            False,
            f"当前依赖第三方目录，换机必失效：把 ffmpeg.exe 放到 {EXTERNAL_ROOT}\\tools\\ffmpeg\\ffmpeg.exe",
            warn=True,
        )

    recordings = recording_store.RECORDINGS_DIR
    writable = recording_store.dir_is_writable(recordings)
    check(
        "录屏目录",
        writable and not recording_store.RECORDINGS_DIR_PROBLEM,
        f"{recordings}（来源：{recording_store.recordings_dir_source(recordings)}；"
        f"可写={'是' if writable else '否'}；告警={recording_store.RECORDINGS_DIR_PROBLEM or '无'}）",
    )

    try:
        import av  # noqa: F401
        import numpy  # noqa: F401
        import sherpa_onnx  # noqa: F401
        import faster_whisper  # noqa: F401
        import opencc  # noqa: F401

        check("核心 Python 包", True, "av/numpy/sherpa_onnx/faster_whisper/opencc 全部可 import")
    except Exception as exc:  # noqa: BLE001
        check("核心 Python 包", False, f"import 失败：{exc}")

    try:
        import live_watchdog  # noqa: E402

        child_root = live_watchdog.child_environment().get("QIANCHUAN_EXTERNAL_ROOT", "")
        check(
            "子进程继承",
            child_root == str(paths.EXTERNAL_ROOT),
            f"子进程={child_root}；父进程={paths.EXTERNAL_ROOT}",
        )
    except Exception as exc:  # noqa: BLE001
        check("子进程继承", False, f"检查失败：{exc}")

    data_dir = ROOT / "data"
    try:
        role, payload = machine_identity.resolve_role(data_dir)
        check(
            "机器身份",
            role == machine_identity.ROLE_PRIMARY,
            f"{machine_identity.describe(role, payload)}；{machine_identity.claim_hint(data_dir)}",
            warn=role != machine_identity.ROLE_PRIMARY,
        )
    except Exception as exc:  # noqa: BLE001
        check("机器身份", False, f"检查失败：{exc}")

    hits = scan_hardcoded()
    check(
        "写死路径/主机名",
        not hits,
        "未发现 D 盘绝对路径或旧主机名" if not hits else "；".join(hits[:6]),
    )

    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=6) as response:
            health = json.loads(response.read().decode("utf-8"))
        subs = []
        for name in (
            "liveScreenCapture",
            "buyinLiveCapture",
            "liveRecorder",
            "localAsr",
            "liveRecordingGuard",
        ):
            item = health.get(name)
            if isinstance(item, dict):
                subs.append(f"{name}={item.get('status')}")
        ok = str(health.get("status")) == "ok"
        check("服务健康", ok, f"status={health.get('status')}；{'；'.join(subs)}", warn=not ok)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        check("服务健康", False, f"接口不可达（程序没启动时正常）：{exc}", warn=True)

    print("=" * 78)
    print("  换机自检结果")
    print("=" * 78)
    for name, status, detail in ROWS:
        print(f"  [{status}] {name:-<10} {detail}")
    fails = sum(1 for _, status, _ in ROWS if status == "FAIL")
    warns = sum(1 for _, status, _ in ROWS if status == "WARN")
    print()
    print(f"  合计：PASS {len(ROWS) - fails - warns} / WARN {warns} / FAIL {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
