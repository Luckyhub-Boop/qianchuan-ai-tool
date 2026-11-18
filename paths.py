"""项目路径解析：所有“外部根 / 模型 / 运行环境 / 浏览器档案”的唯一来源。

规则（换机器时只改环境，不改代码）：

1. 环境变量 ``QIANCHUAN_EXTERNAL_ROOT`` 优先；
2. 没有环境变量时按本文件位置推算：本文件位于
   ``<外部根>\\我的坚果云\\AI投放工具``，上退两级即外部根；
3. 推算出来的路径如果找不到 runtime/models/node_modules 等标志目录，
   再试上一级，避免有人把项目整体挪走一层后失效；
4. 解析结果会写回环境变量，保证 watchdog 拉起的子进程看到同一份根。
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

_MARKERS = (
    "runtime",
    "models",
    "node_modules",
    "chrome-profile",
    "buyin-chrome-profile",
)

# 旧版录屏目录名，保留原名是为了让本机历史录像原地继续用，不做迁移。
LEGACY_RECORDINGS_NAME = "DAI投放产品录屏备份"


def _clean_env(name: str) -> str:
    return (os.getenv(name) or "").strip().strip('"').strip("'")


def _looks_like_external_root(candidate: Path) -> bool:
    try:
        return any((candidate / marker).exists() for marker in _MARKERS)
    except OSError:
        return False


def _resolve_external_root() -> tuple[Path, str]:
    env_value = _clean_env("QIANCHUAN_EXTERNAL_ROOT")
    if env_value:
        return Path(env_value).expanduser().resolve(), "环境变量"

    primary = ROOT.parent.parent
    if _looks_like_external_root(primary):
        return primary.resolve(), "按程序位置推算"

    secondary = ROOT.parent
    if _looks_like_external_root(secondary):
        return secondary.resolve(), "按程序位置的上一级推算"

    return primary.resolve(), "按程序位置推算（未找到 runtime/models/node_modules 等标志目录）"


EXTERNAL_ROOT, EXTERNAL_ROOT_SOURCE = _resolve_external_root()
os.environ["QIANCHUAN_EXTERNAL_ROOT"] = str(EXTERNAL_ROOT)

MODELS_DIR = EXTERNAL_ROOT / "models"
RUNTIME_DIR = EXTERNAL_ROOT / "runtime"
NODE_MODULES_DIR = EXTERNAL_ROOT / "node_modules"
CHROME_PROFILE_DIR = EXTERNAL_ROOT / "chrome-profile"
BUYIN_CHROME_PROFILE_DIR = EXTERNAL_ROOT / "buyin-chrome-profile"
TOOLS_DIR = EXTERNAL_ROOT / "tools"


def recordings_candidates() -> list[Path]:
    """录屏目录候选：环境变量 > 旧同级目录 > 外部根下的 recordings。

    只给候选，不负责挑；挑哪个由 recording_store 的可写探测决定。
    """
    env_value = _clean_env("QIANCHUAN_RECORDINGS_DIR")
    if env_value:
        return [Path(env_value).expanduser()]
    return [
        EXTERNAL_ROOT.parent / LEGACY_RECORDINGS_NAME,
        EXTERNAL_ROOT / "recordings",
    ]


# 历史遗留的第三方 ffmpeg 位置：换机器基本不存在，只作最后兜底并明确标注来源。
_LEGACY_FFMPEG = (
    r"C:\Program Files (x86)\MarukoToolbox\tools\ffmpeg.exe",
    r"C:\Program Files (x86)\damai\resources\app\node_modules\ffmpeg-static-electron\bin\win\x64\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
)


def ffmpeg_candidates() -> list[tuple[str, str]]:
    """ffmpeg 候选及其来源，按优先级排列：环境变量 > 外部根 tools > PATH > 遗留路径。"""
    candidates: list[tuple[str, str]] = []
    env_value = _clean_env("QIANCHUAN_FFMPEG")
    if env_value:
        candidates.append((env_value, "环境变量 QIANCHUAN_FFMPEG"))
    for relative, label in (
        (Path("tools") / "ffmpeg" / "ffmpeg.exe", "外部根 tools/ffmpeg/ffmpeg.exe"),
        (Path("tools") / "ffmpeg" / "bin" / "ffmpeg.exe", "外部根 tools/ffmpeg/bin/ffmpeg.exe"),
        (Path("tools") / "ffmpeg.exe", "外部根 tools/ffmpeg.exe"),
    ):
        candidates.append((str(EXTERNAL_ROOT / relative), label))
    which = shutil.which("ffmpeg")
    if which:
        candidates.append((which, "系统 PATH"))
    for legacy in _LEGACY_FFMPEG:
        candidates.append((legacy, "遗留第三方目录（换机可能不存在）"))
    return candidates


def resolve_ffmpeg() -> tuple[str, str]:
    """返回 (ffmpeg 路径, 来源说明)；找不到时返回 ("", "")。"""
    for candidate, label in ffmpeg_candidates():
        try:
            if candidate and Path(candidate).is_file():
                return candidate, label
        except OSError:
            continue
    return "", ""


def describe() -> str:
    return (
        f"外部根={EXTERNAL_ROOT}（来源：{EXTERNAL_ROOT_SOURCE}）"
        f" | 项目根={ROOT}"
        f" | 模型={MODELS_DIR}"
        f" | 运行环境={RUNTIME_DIR}"
    )
