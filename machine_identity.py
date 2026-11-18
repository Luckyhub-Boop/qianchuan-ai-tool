"""机器归属判定：确保只有一台机器（采集主控）运行录制/采集/转写。

项目代码与 data 目录放在坚果云同步盘时，多台机器会读到同一份状态文件，
导致录制器、采集器、转写互相覆盖，并产生大量“冲突”副本。

规则：
- `data/primary-machine.json` 记录采集主控机器。
- 本机指纹与主控一致 -> primary：启动完整采集链路。
- 本机指纹与主控不一致 -> readonly：只启动后端服务供查看，不录制、不采集、不转写。
- 主控文件不存在 -> unclaimed：本机可认领（首次部署场景）。

指纹 = 计算机名 + 系统盘卷序列号，重装系统或换盘会变化。
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

PRIMARY_FILE_NAME = "primary-machine.json"
ALLOWLIST_FILE_NAME = "primary-allowlist.json"
ALLOWLIST_ENV = "QIANCHUAN_PRIMARY_HOSTNAME"

ROLE_PRIMARY = "primary"
ROLE_READONLY = "readonly"
ROLE_UNCLAIMED = "unclaimed"


def hostname() -> str:
    value = os.environ.get("COMPUTERNAME") or platform.node() or "unknown"
    return str(value).strip() or "unknown"


def volume_serial(drive: str | None = None) -> str:
    """读取系统盘卷序列号，失败返回空串（仅 Windows 有效）。"""
    drive_letter = (drive or os.environ.get("SystemDrive") or "C:").rstrip("\\")
    target = f"{drive_letter}\\"
    try:
        import ctypes

        volume_name = ctypes.create_unicode_buffer(261)
        fs_name = ctypes.create_unicode_buffer(261)
        serial = ctypes.c_ulong()
        max_component = ctypes.c_ulong()
        flags = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(target),
            volume_name,
            261,
            ctypes.byref(serial),
            ctypes.byref(max_component),
            ctypes.byref(flags),
            fs_name,
            261,
        )
        if not ok:
            return ""
        return f"{serial.value:08X}"
    except Exception:
        return ""


def fingerprint() -> str:
    return f"{hostname()}|{volume_serial()}"


def machine_id() -> str:
    return hashlib.sha1(fingerprint().encode("utf-8")).hexdigest()[:16]


def primary_path(data_dir: Path) -> Path:
    return data_dir / PRIMARY_FILE_NAME


def read_primary(data_dir: Path) -> dict[str, Any]:
    path = primary_path(data_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def claim_primary(data_dir: Path) -> dict[str, Any]:
    """把本机登记为采集主控。只在主控文件缺失或明确本机时调用。"""
    payload = {
        "machineId": machine_id(),
        "hostname": hostname(),
        "volumeSerial": volume_serial(),
        "roleLabel": "采集主控",
        "claimedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": "只有此机器允许启动录制/采集/转写；其他机器自动进入只读模式",
    }
    path = primary_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def allowlist_path(data_dir: Path) -> Path:
    return data_dir / ALLOWLIST_FILE_NAME


def allowed_hostnames(data_dir: Path) -> list[str]:
    """允许自我认领的机器名清单：环境变量优先，其次 data 下的配置文件。

    清单不在代码里写死：换机部署只需在配置文件里加一台机器名，
    不需要改 Python 再发版。
    """
    env_value = (os.environ.get(ALLOWLIST_ENV) or "").strip()
    if env_value:
        names = [item.strip() for item in env_value.split(",")]
        return [name for name in names if name]
    try:
        payload = json.loads(allowlist_path(data_dir).read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = payload.get("allowedHostnames") or payload.get("hostnames") or []
    else:
        raw = []
    return [str(item).strip() for item in raw if str(item).strip()]


def claim_hint(data_dir: Path) -> str:
    """说明本机当前的认领资格来自哪里，供启动日志原样打印。"""
    names = allowed_hostnames(data_dir)
    source = (
        f"环境变量 {ALLOWLIST_ENV}"
        if (os.environ.get(ALLOWLIST_ENV) or "").strip()
        else str(allowlist_path(data_dir))
    )
    if not names:
        return f"未配置可认领机器清单（{source} 不存在或为空），本机不会自我认领"
    return (
        f"可认领机器清单来自 {source}：{', '.join(names)}；"
        f"本机 {hostname()} "
        + ("在清单内，主控文件缺失时可自我认领" if can_self_claim(data_dir) else "不在清单内")
    )


def can_self_claim(data_dir: Path | None = None) -> bool:
    """主控文件缺失时，本机是否允许自我认领。

    只有出现在清单（环境变量或 data/primary-allowlist.json）里的机器才算。
    清单为空时一律不允许——宁可停在只读，也不让第二台机器悄悄变成主控。
    """
    if data_dir is None:
        return False
    names = {name.casefold() for name in allowed_hostnames(data_dir)}
    return hostname().casefold() in names


def resolve_role(data_dir: Path, auto_claim: bool = True) -> tuple[str, dict[str, Any]]:
    """返回 (role, primary_payload)。

    - 主控文件存在且是本机：primary
    - 主控文件存在但不是本机：readonly（永不改写该文件）
    - 主控文件缺失：只有清单里的机器允许认领；其他机器返回 unclaimed（按只读处理）
    """
    primary = read_primary(data_dir)
    if not primary:
        if auto_claim and can_self_claim(data_dir):
            return ROLE_PRIMARY, claim_primary(data_dir)
        return ROLE_UNCLAIMED, {}
    owner_id = str(primary.get("machineId") or "")
    if owner_id and owner_id == machine_id():
        return ROLE_PRIMARY, primary
    return ROLE_READONLY, primary


def describe(role: str, primary: dict[str, Any]) -> str:
    if role == ROLE_PRIMARY:
        return f"采集主控（{hostname()}）"
    owner = str(primary.get("hostname") or primary.get("machineId") or "未知机器")
    return f"只读（采集主控为 {owner}）"
