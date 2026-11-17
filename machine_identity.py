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

# 采集主控机器名。只有这台机器在“主控文件缺失”时允许自我认领；
# 其他机器即使同步没跟上、读不到主控文件，也只进只读模式，绝不自认领。
PRIMARY_HOSTNAME = "WINDOWS-MT4H69T"

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


def can_self_claim() -> bool:
    """只有 PRIMARY_HOSTNAME 指定的机器可以在主控文件缺失时自我认领。"""
    return hostname().casefold() == PRIMARY_HOSTNAME.casefold()


def resolve_role(data_dir: Path, auto_claim: bool = True) -> tuple[str, dict[str, Any]]:
    """返回 (role, primary_payload)。

    - 主控文件存在且是本机：primary
    - 主控文件存在但不是本机：readonly（永不改写该文件）
    - 主控文件缺失：只有 PRIMARY_HOSTNAME 允许认领；其他机器返回 readonly/未认领
    """
    primary = read_primary(data_dir)
    if not primary:
        if auto_claim and can_self_claim():
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
