from __future__ import annotations

import copy
import hashlib
import http.client
import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SNAPSHOT_PATH = DATA_DIR / "qianchuan-snapshot.json"
CONFIG_PATH = ROOT / "qianchuan.config.json"
TOKEN_FILE_PATH = DATA_DIR / "qianchuan-token.json"
OAUTH_CONFIG_PATH = DATA_DIR / "qianchuan-oauth.json"
MCP_CONFIG_PATH = DATA_DIR / "qianchuan-mcp.json"
LIVE_SCREEN_STATE_PATH = DATA_DIR / "live-screen-metrics.json"
LIVE_SCREEN_HISTORY_PATH = DATA_DIR / "live-screen-history.json"
HLS_DIR = DATA_DIR / "hls"
LEARNING_DOCUMENT_MAX_BYTES = 25 * 1024 * 1024
LEARNING_DOCUMENT_MAX_CHARS = 1_000_000
LEARNING_CHUNK_SIZE = 900
LEARNING_CHUNK_OVERLAP = 140
LEARNING_DOCUMENT_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".json",
    ".md",
    ".pdf",
    ".ppt",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
}
LEARNING_TEXT_EXTENSIONS = {".csv", ".json", ".md", ".txt"}
LEARNING_OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}

OAUTH_AUTHORIZE_URL = "https://open.oceanengine.com/audit/oauth.html"
OAUTH_ACCESS_TOKEN_URL = "https://ad.oceanengine.com/open_api/oauth2/access_token/"
OAUTH_REFRESH_TOKEN_URL = "https://ad.oceanengine.com/open_api/oauth2/refresh_token/"
TOKEN_REFRESH_SKEW_SECONDS = 300

HISTORY_DAYS = 182
DEFAULT_PORT = 8765
DEFAULT_SYNC_INTERVAL_SECONDS = 10
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_PAGE_SIZE = 100
CAMPAIGN_TARGET_COST = 300.0
CAMPAIGN_PRODUCT_PRICE = 168.0
CAMPAIGN_TARGET_ROI = 0.56
FIVE_DIMENSION_CACHE_SECONDS = 8.0
FIVE_DIMENSION_RETRY_SECONDS = 30.0

DEFAULT_FIELDS = ["stat_cost", "pay_order_amount", "pay_order_count"]
DEFAULT_FIELD_MAP = {
    "date": ["stat_date", "date", "time"],
    "spend": ["stat_cost", "cost", "spend"],
    "gmv": ["pay_order_amount", "gmv", "user_pay_amount"],
    "orders": ["pay_order_count", "order_count", "orders"],
    "viewers": ["live_watch_count", "watch_count", "viewers"],
}

DEFAULT_CAMPAIGN_CONFIG: dict[str, Any] = {
    "enabled": True,
    "listEndpoint": "/open_api/v1.0/qianchuan/uni_promotion/list/",
    "reportEndpoint": "",
    "materialsEndpoint": "/open_api/v1.0/qianchuan/uni_promotion/ad/material/get/",
    "materialReportEndpoint": "/open_api/v1.0/qianchuan/report/uni_promotion/data/get/",
    "videoLibraryEndpoint": "/open_api/v1.0/qianchuan/video/get/",
    "videoLibraryPageSize": 100,
    "videoLibraryMaxPages": 100,
    "marketingGoal": "LIVE_PROM_GOODS",
    "adlabScene": "UNI_PROJECT",
    "historyDays": 30,
    "materialPlanLimit": 20,
    "materialHistoryDays": 116,
    "materialStartDate": "2026-07-01",
    "materialEndOffsetDays": 1,
    "materialCacheSeconds": 150,
    "materialSyncIntervalSeconds": 180,
    "materialReconcileSeconds": 10800,
    "materialCacheHours": 6,
    "materialMaxPages": 50,
    "materialType": "VIDEO",
    "materialReportSmartBidTypes": ["0", "7"],
    "materialReportEcpAppIds": ["1"],
    "materialReportPageSize": 200,
    "materialReportMaxPages": 100,
    "materialReportDimensions": [
        "roi2_material_video_name",
        "roi2_material_video_type",
        "material_id",
    ],
    "materialReportLiveDimensions": [
        "roi2_material_anchor_name",
        "roi2_material_anchor_show_id",
        "anchor_id",
    ],
    "materialReportMetrics": [
        "live_show_count_for_roi2_v2",
        "live_watch_count_for_roi2_v2",
        "live_cvr_rate_for_roi2_v2",
        "total_pay_order_count_for_roi2",
        "stat_cost_for_roi2",
        "total_pay_order_gmv_for_roi2",
        "total_prepay_and_pay_order_roi2",
        "total_cost_per_pay_order_for_roi2",
        "video_play_count_for_roi2_v2",
        "video_play_finish_rate_for_roi2_v2",
        "video_avg_watch_duration_for_roi2",
    ],
    "materialReportLiveMetrics": [
        "live_show_count_exclude_video_for_roi2",
        "live_watch_count_exclude_video_for_roi2",
        "live_cvr_rate_exclude_video_for_roi2",
        "total_pay_order_count_for_roi2_fork",
        "stat_cost_for_roi2_fork",
        "total_pay_order_gmv_for_roi2_fork",
        "total_prepay_and_pay_order_roi2_fork",
        "total_cost_per_pay_order_for_roi2_fork",
    ],
    "method": "GET",
    "timeoutSeconds": DEFAULT_TIMEOUT_SECONDS,
    "pageSize": DEFAULT_PAGE_SIZE,
    "maxPages": 20,
    "requestIntervalSeconds": 0.8,
    "extraParams": {},
    "filtering": {},
    "campaignIdFilterKey": "campaign_ids",
    "moneyDivisor": 100000,
    "fields": [
        "stat_cost",
        "total_pay_order_gmv_for_roi2",
        "total_pay_order_count_for_roi2",
        "total_prepay_and_pay_order_roi2",
        "total_cost_per_pay_order_for_roi2",
    ],
    "materialFields": [
        "stat_cost_for_roi2",
        "total_pay_order_gmv_for_roi2",
        "total_pay_order_count_for_roi2",
        "total_prepay_and_pay_order_roi2",
        "total_cost_per_pay_order_for_roi2",
        "live_show_count_for_roi2_v2",
        "live_watch_count_for_roi2_v2",
        "live_cvr_rate_for_roi2_v2",
        "live_convert_rate_for_roi2_v2",
        "video_play_finish_rate_for_roi2_v2",
        "video_avg_watch_duration_for_roi2",
    ],
    "liveRoomFields": [
        "stat_cost_for_roi2",
        "total_pay_order_gmv_for_roi2",
        "total_pay_order_count_for_roi2",
        "total_prepay_and_pay_order_roi2",
        "total_cost_per_pay_order_for_roi2",
        "live_show_count_exclude_video_for_roi2",
        "live_watch_count_exclude_video_for_roi2",
        "live_cvr_rate_exclude_video_for_roi2",
        "live_convert_rate_exclude_video_for_roi2",
    ],
    "fieldMap": {
        "campaignId": ["ad_info.id", "campaign_id", "id"],
        "campaignName": ["ad_info.name", "campaign_name", "name"],
        "status": ["ad_info.status", "status", "opt_status", "campaign_status"],
        "date": ["stat_date", "stat_datetime", "date", "time"],
        "spend": ["stats_info.stat_cost", "stat_cost", "cost", "spend"],
        "gmv": ["stats_info.total_pay_order_gmv_for_roi2", "pay_order_amount", "gmv", "user_pay_amount"],
        "orders": ["stats_info.total_pay_order_count_for_roi2", "pay_order_count", "order_count", "orders"],
        "materialId": ["material_id", "creative_id", "ad_id", "id"],
        "materialName": ["material_name", "creative_name", "ad_name", "name"],
        "materialType": ["material_type", "type", "creative_material_mode"],
        "impressions": ["live_show_count_for_roi2_v2", "show_cnt", "impressions"],
        "clicks": ["live_watch_count_for_roi2_v2", "click_cnt", "clicks"],
        "ctr": ["live_cvr_rate_for_roi2_v2", "ctr"],
        "completionRate": ["video_play_finish_rate_for_roi2_v2", "play_over_rate", "completion_rate"],
        "dwellTime": ["video_avg_watch_duration_for_roi2", "average_watch_duration", "dwell_time"],
    },
    "statusMap": {
        "CREATE": "新建",
        "DRAFT": "草稿",
        "PRE_ONLINE": "预上线",
        "DELIVERY_OK": "投放中",
        "DISABLE": "已暂停",
        "DELETE": "已删除",
        "DELETED": "已删除",
        "AUDIT": "审核中",
        "REAUDIT": "审核中",
        "FROZEN": "已终止",
        "TIME_DONE": "已完成",
        "NO_SCHEDULE": "未排期",
        "LIVE_ROOM_OFF": "直播间未开播",
        "OFFLINE_AUDIT": "审核不通过",
        "OFFLINE_BALANCE": "余额不足",
        "OFFLINE_BUDGET": "预算不足",
        "ENABLE": "投放中",
        "OFFLINE": "已下线",
        "SYSTEM_DISABLE": "系统暂停",
        "ROI2_DISABLE": "ROI目标暂停",
    },
}

DEFAULT_LIVE_CONFIG: dict[str, Any] = {
    "enabled": True,
    "roomListEndpoint": "/open_api/v1.0/qianchuan/today_live/room/get/",
    "flowEndpoint": "/open_api/v1.0/qianchuan/today_live/room/flow_performance/get/",
    "userEndpoint": "/open_api/v1.0/qianchuan/today_live/room/user/get/",
    "productEndpoint": "/open_api/v1.0/qianchuan/today_live/room/product_list/get/",
    "cacheSeconds": 10,
    "moneyDivisor": 100000,
    "streamUrl": "",
    "streamType": "auto",
    "streamSource": "",
    "roomFields": [
        "stat_cost",
        "total_live_watch_cnt",
        "live_watch_one_minute_count",
        "luban_live_pay_order_count",
        "live_pay_order_count_alias",
        "luban_live_pay_order_gmv",
        "live_pay_order_gmv_alias",
        "live_pay_order_gmv_roi",
        "ad_live_prepay_and_pay_order_gmv_roi",
        "ecp_convert_rate",
        "live_click_product_count_alias",
        "total_live_comment_cnt",
        "room_delivery",
        "total_live_follow_cnt",
    ],
    "flowSources": ["AllEcomFlowSource", "AllEcomGmvSource"],
}

SEED_ROWS = [
    {"date": "2026-10-11", "spend": 13825.55, "gmv": 5880, "orders": 35},
    {"date": "2026-10-12", "spend": 16512.16, "gmv": 10248, "orders": 61},
    {"date": "2026-10-13", "spend": 7260.43, "gmv": 5208, "orders": 31},
    {"date": "2026-10-14", "spend": 11813.40, "gmv": 9239, "orders": 55},
    {"date": "2026-10-15", "spend": 9339.20, "gmv": 6720, "orders": 40},
    {"date": "2026-10-16", "spend": 6691.69, "gmv": 3695.86, "orders": 22},
    {"date": "2026-10-17", "spend": 8400.79, "gmv": 4871.60, "orders": 29},
]

DEFAULT_ACCOUNT = {
    "id": "fashion",
    "advertiserId": "1744479430946824",
    "name": "TT-申坤-赵镭老师(店播)-小学数学-自运营",
    "handle": "赵镭精讲小数基本功",
    "avatar": "赵",
    "color": "#0b7a58",
    "awemeIds": [
        "2904261216450640",
        "7534976849169040442",
        "7665361622538945585",
        "7637818476896437305",
    ],
    "awemeAccounts": [
        {"id": "7637818476896437305", "name": "赵镭图解小数基本功"},
        {"id": "2904261216450640", "name": "赵镭精讲小数基本功"},
        {"id": "7665361622538945585", "name": "赵镭拆解小数基本功"},
        {"id": "7534976849169040442", "name": "赵镭通解小数基本功"},
        {"id": "21334542186", "name": "赵镭小数基本功"},
    ],
}

DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "baseUrl": "https://api.oceanengine.com",
        "reportEndpoint": "/open_api/v1.0/qianchuan/report/uni_promotion/get/",
        "advertiserListEndpoint": "",
        "method": "GET",
        "timeoutSeconds": DEFAULT_TIMEOUT_SECONDS,
        "pageSize": DEFAULT_PAGE_SIZE,
        "maxPages": 20,
        "requestIntervalSeconds": 0.25,
        "extraParams": {},
        "fields": DEFAULT_FIELDS,
        "fieldMap": DEFAULT_FIELD_MAP,
        "listKeys": ["list", "rows", "data"],
    },
    "campaigns": DEFAULT_CAMPAIGN_CONFIG,
    "live": DEFAULT_LIVE_CONFIG,
    "sync": {
        "intervalSeconds": DEFAULT_SYNC_INTERVAL_SECONDS,
        "reportCacheSeconds": 120,
        "awemeCacheSeconds": 120,
        "realtimeCacheSeconds": 5,
        "fullSyncIntervalSeconds": 180,
        "includeToday": True,
    },
    "accounts": [DEFAULT_ACCOUNT],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def business_cutoff(today: date | None = None) -> date:
    """Qianchuan reports only completed natural days."""
    reference = today if today is not None else date.today()
    return reference - timedelta(days=1)


def build_date_range(days: int = HISTORY_DAYS, end_date_input: date | None = None) -> tuple[str, str]:
    safe_days = max(1, int(days))
    if end_date_input is not None:
        end_date = end_date_input - timedelta(days=1)
    else:
        end_date = business_cutoff()
    start_date = end_date - timedelta(days=safe_days - 1)
    return start_date.isoformat(), end_date.isoformat()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return copy.deepcopy(default)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取配置文件 {path.name}: {exc}") from exc


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


class LearningDocumentError(ValueError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _decode_learning_text(content: bytes) -> tuple[str, str] | tuple[None, None]:
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if b"\x00" in content and encoding != "utf-16":
            continue
        if text.strip():
            return text, encoding
    return None, None


def _xml_local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _extract_docx_text(content: bytes) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = [
            name
            for name in archive.namelist()
            if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", name)
        ]
        for name in sorted(names):
            root = ET.fromstring(archive.read(name))
            for paragraph in root.iter():
                if _xml_local_name(paragraph.tag) != "p":
                    continue
                text = "".join(
                    str(node.text or "")
                    for node in paragraph.iter()
                    if _xml_local_name(node.tag) in {"t", "instrText"}
                ).strip()
                if text:
                    paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pptx_text(content: bytes) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = [
            name
            for name in archive.namelist()
            if re.match(r"ppt/slides/slide\d+\.xml$", name)
        ]
        names.sort(
            key=lambda name: int(re.search(r"(\d+)", Path(name).name).group(1))
            if re.search(r"(\d+)", Path(name).name)
            else 0
        )
        for name in names:
            root = ET.fromstring(archive.read(name))
            for paragraph in root.iter():
                if _xml_local_name(paragraph.tag) != "p":
                    continue
                text = "".join(
                    str(node.text or "")
                    for node in paragraph.iter()
                    if _xml_local_name(node.tag) == "t"
                ).strip()
                if text:
                    paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_xlsx_text(content: bytes) -> str:
    rows_text: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        shared_strings: list[str] = []
        shared_name = "xl/sharedStrings.xml"
        if shared_name in archive.namelist():
            root = ET.fromstring(archive.read(shared_name))
            for item in root.iter():
                if _xml_local_name(item.tag) != "si":
                    continue
                text = "".join(
                    str(node.text or "")
                    for node in item.iter()
                    if _xml_local_name(node.tag) == "t"
                )
                shared_strings.append(text)

        sheet_names = [
            name
            for name in archive.namelist()
            if re.match(r"xl/worksheets/sheet\d+\.xml$", name)
        ]
        sheet_names.sort(
            key=lambda name: int(re.search(r"(\d+)", Path(name).name).group(1))
            if re.search(r"(\d+)", Path(name).name)
            else 0
        )
        for name in sheet_names:
            root = ET.fromstring(archive.read(name))
            for row in root.iter():
                if _xml_local_name(row.tag) != "row":
                    continue
                cells: list[str] = []
                for cell in row:
                    if _xml_local_name(cell.tag) != "c":
                        continue
                    reference = str(cell.attrib.get("r") or "")
                    cell_type = str(cell.attrib.get("t") or "")
                    value = ""
                    for child in cell.iter():
                        local = _xml_local_name(child.tag)
                        if local == "v":
                            value = str(child.text or "")
                        elif local == "t":
                            value += str(child.text or "")
                    if cell_type == "s" and value.isdigit():
                        index = int(value)
                        value = shared_strings[index] if index < len(shared_strings) else value
                    if value.strip():
                        cells.append(f"{reference}: {value.strip()}" if reference else value.strip())
                if cells:
                    rows_text.append(" | ".join(cells))
                if len(rows_text) >= 10_000:
                    break
            if len(rows_text) >= 10_000:
                break
    return "\n".join(rows_text)


def _decode_pdf_literal(raw: bytes) -> str:
    output = bytearray()
    index = 0
    while index < len(raw):
        if raw[index] != 92 or index + 1 >= len(raw):
            output.append(raw[index])
            index += 1
            continue
        index += 1
        escaped = raw[index]
        mappings = {
            ord("n"): 10,
            ord("r"): 13,
            ord("t"): 9,
            ord("b"): 8,
            ord("f"): 12,
            ord("("): 40,
            ord(")"): 41,
            ord("\\"): 92,
        }
        if escaped in mappings:
            output.append(mappings[escaped])
            index += 1
            continue
        if 48 <= escaped <= 55:
            digits = bytes([escaped])
            index += 1
            while index < len(raw) and len(digits) < 3 and 48 <= raw[index] <= 55:
                digits += bytes([raw[index]])
                index += 1
            output.append(int(digits, 8))
            continue
        if escaped in {10, 13}:
            index += 1
            continue
        output.append(escaped)
        index += 1
    return output.decode("latin-1", errors="ignore")


def _extract_pdf_text(content: bytes) -> str:
    streams: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", content, flags=re.S):
        raw = match.group(1)
        try:
            streams.append(zlib.decompress(raw))
        except zlib.error:
            streams.append(raw)

    cmap: dict[bytes, str] = {}
    code_widths: set[int] = set()
    for stream in streams:
        if b"begincmap" not in stream:
            continue
        for source, target in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", stream):
            if len(source) % 2 or len(target) < 4:
                continue
            try:
                source_bytes = bytes.fromhex(source.decode("ascii"))
                target_text = bytes.fromhex(target.decode("ascii")).decode(
                    "utf-16-be", errors="ignore"
                )
            except ValueError:
                continue
            if source_bytes and target_text:
                cmap[source_bytes] = target_text
                code_widths.add(len(source_bytes))

    def decode_hex(value: bytes) -> str:
        widths = sorted(code_widths or {len(value)})
        for width in widths:
            if not width or len(value) % width:
                continue
            pieces = [value[offset : offset + width] for offset in range(0, len(value), width)]
            if cmap and any(piece in cmap for piece in pieces):
                return "".join(cmap.get(piece, "") for piece in pieces)
        if b"\x00" in value and len(value) % 2 == 0:
            return value.decode("utf-16-be", errors="ignore")
        return value.decode("latin-1", errors="ignore")

    token_pattern = re.compile(
        rb"\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]+>|\bT\*|\bTd\b|\bTD\b|\bET\b",
        flags=re.S,
    )
    parts: list[str] = []
    for stream in streams:
        if not any(marker in stream for marker in (b"BT", b"Tj", b"TJ")):
            continue
        for match in token_pattern.finditer(stream):
            token = match.group(0)
            if token in {b"T*", b"Td", b"TD", b"ET"}:
                parts.append("\n")
                continue
            if token.startswith(b"("):
                text = _decode_pdf_literal(token[1:-1])
            else:
                hex_value = re.sub(rb"\s+", b"", token[1:-1])
                if not hex_value or len(hex_value) % 2:
                    continue
                try:
                    text = decode_hex(bytes.fromhex(hex_value.decode("ascii")))
                except ValueError:
                    continue
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", "", text)
            if text.strip():
                parts.append(text)
    extracted = "".join(parts)
    extracted = re.sub(r"[ \t]+", " ", extracted)
    extracted = re.sub(r"\n{3,}", "\n\n", extracted).strip()
    printable = sum(
        1
        for character in extracted
        if character.isprintable() or character in "\n\t"
    )
    semantic = sum(
        1
        for character in extracted
        if character.isalnum() or "\u3400" <= character <= "\u9fff"
    )
    if not extracted or printable / len(extracted) < 0.75 or semantic < 8:
        return ""
    return extracted


def _extract_learning_text(content: bytes, extension: str) -> tuple[str, str]:
    if extension in LEARNING_TEXT_EXTENSIONS:
        text, encoding = _decode_learning_text(content)
        if text is None:
            raise ValueError("文件不是可识别的 UTF-8、GB18030 或 UTF-16 文本")
        return text, f"plain_text:{encoding}"
    if extension == ".docx":
        return _extract_docx_text(content), "docx_xml"
    if extension == ".xlsx":
        return _extract_xlsx_text(content), "xlsx_xml"
    if extension == ".pptx":
        return _extract_pptx_text(content), "pptx_xml"
    if extension == ".pdf":
        return _extract_pdf_text(content), "pdf_text_stream"
    raise ValueError("当前格式无法抽取文本，请在源软件中另存为 PDF、DOCX、XLSX、PPTX 或文本文件")


def _chunk_learning_text(text: str) -> list[str]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        return []
    normalized = normalized[:LEARNING_DOCUMENT_MAX_CHARS]
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        hard_end = min(len(normalized), start + LEARNING_CHUNK_SIZE)
        end = hard_end
        if hard_end < len(normalized):
            preferred_start = start + int(LEARNING_CHUNK_SIZE * 0.58)
            boundary = max(
                normalized.rfind(marker, preferred_start, hard_end)
                for marker in ("\n", "。", "！", "？", "；", ".", ";")
            )
            if boundary >= preferred_start:
                end = boundary + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(start + 1, end - LEARNING_CHUNK_OVERLAP)
    return chunks


LEARNING_TOKEN_STOPWORDS = {
    "一个",
    "可以",
    "我们",
    "需要",
    "进行",
    "以及",
    "并且",
    "同时",
    "然后",
    "就是",
    "不是",
    "没有",
    "如果",
    "这个",
    "当前",
}


def _learning_tokens(text: str) -> list[str]:
    normalized = str(text or "").lower()
    tokens = [
        token
        for token in re.findall(r"[a-z][a-z0-9_]{1,}|[0-9]+(?:\.[0-9]+)?", normalized)
        if token not in LEARNING_TOKEN_STOPWORDS
    ]
    for segment in re.findall(r"[\u3400-\u9fff]+", normalized):
        if len(segment) == 1:
            tokens.append(segment)
            continue
        for index in range(0, max(0, len(segment) - 1)):
            token = segment[index : index + 2]
            if token not in LEARNING_TOKEN_STOPWORDS:
                tokens.append(token)
    return tokens


def _learning_excerpt(text: str, limit: int = 260) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _learning_action_sentence(excerpt: str) -> str:
    sentences = [
        item.strip()
        for item in re.split(r"(?<=[。！？；;])|\n+", str(excerpt or ""))
        if item.strip()
    ]
    action_terms = (
        "建议",
        "优先",
        "必须",
        "暂停",
        "降低",
        "提高",
        "放量",
        "控量",
        "观察",
        "止损",
        "预算",
        "ROI",
        "成本",
    )
    ranked = sorted(
        sentences,
        key=lambda item: sum(term.lower() in item.lower() for term in action_terms),
        reverse=True,
    )
    return _learning_excerpt(ranked[0] if ranked else excerpt, 180)


class LearningDocumentStore:
    """Persist internal product-learning documents below one project root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.data_dir = self.root / "data"
        self.documents_dir = self.data_dir / "learning-documents"
        self.metadata_path = self.data_dir / "learning-documents.json"
        self.index_path = self.data_dir / "learning-index.json"
        self._lock = threading.RLock()
        self._retrieval_cache: tuple[
            str,
            list[tuple[str, dict[str, Any], dict[str, Any]]],
            list[Counter],
            Counter,
            dict[str, Any],
        ] | None = None

    def _load(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {"updatedAt": None, "documents": []}
        try:
            payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LearningDocumentError(f"学习资料清单读取失败：{exc}", 500) from exc
        documents = payload.get("documents") if isinstance(payload, dict) else None
        if not isinstance(documents, list):
            raise LearningDocumentError("学习资料清单格式无效", 500)
        return {
            "updatedAt": payload.get("updatedAt"),
            "documents": [item for item in documents if isinstance(item, dict)],
        }

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"updatedAt": None, "documents": {}}
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LearningDocumentError(f"学习索引读取失败：{exc}", 500) from exc
        documents = payload.get("documents") if isinstance(payload, dict) else None
        if not isinstance(documents, dict):
            raise LearningDocumentError("学习索引格式无效", 500)
        return {
            "updatedAt": payload.get("updatedAt"),
            "documents": {
                str(key): value
                for key, value in documents.items()
                if isinstance(value, dict)
            },
        }

    @staticmethod
    def _analyze_document(content: bytes, extension: str) -> dict[str, Any]:
        try:
            text, method = _extract_learning_text(content, extension)
            chunks = _chunk_learning_text(text)
            if not chunks:
                raise ValueError("文档已解析，但没有提取到足够的学习文本")
            return {
                "text": text[:LEARNING_DOCUMENT_MAX_CHARS],
                "chunks": chunks,
                "method": method,
                "error": "",
            }
        except Exception as exc:
            return {
                "text": "",
                "chunks": [],
                "method": "",
                "error": str(exc),
            }

    @staticmethod
    def _apply_analysis(record: dict[str, Any], analysis: dict[str, Any]) -> None:
        chunks = analysis["chunks"]
        record["learningReady"] = bool(chunks)
        record["status"] = "ready" if chunks else "stored"
        record["statusLabel"] = (
            f"可学习 · {len(chunks)} 段"
            if chunks
            else "已入库 · 文本提取失败"
        )
        record["textCharacters"] = len(analysis["text"])
        record["chunks"] = len(chunks)
        record["extractionMethod"] = analysis["method"]
        record["extractionError"] = analysis["error"]
        record["indexedAt"] = now_iso() if chunks else None

    def _ensure_indexes(
        self,
        metadata: dict[str, Any],
        index_payload: dict[str, Any],
    ) -> bool:
        changed = False
        indexed_documents = index_payload["documents"]
        active_ids = {str(item.get("id")) for item in metadata["documents"]}
        for stale_id in list(indexed_documents):
            if stale_id not in active_ids:
                indexed_documents.pop(stale_id, None)
                changed = True
        for record in metadata["documents"]:
            document_id = str(record.get("id") or "")
            if not document_id:
                continue
            indexed = indexed_documents.get(document_id)
            if indexed and indexed.get("sha256") == record.get("sha256"):
                continue
            target = self.documents_dir / str(record.get("storedFilename") or "")
            if not target.is_file():
                indexed_documents.pop(document_id, None)
                continue
            analysis = self._analyze_document(target.read_bytes(), str(record.get("extension") or ""))
            self._apply_analysis(record, analysis)
            if analysis["chunks"]:
                indexed_documents[document_id] = {
                    "sha256": record.get("sha256"),
                    "name": record.get("name"),
                    "extension": record.get("extension"),
                    "method": analysis["method"],
                    "indexedAt": now_iso(),
                    "chunks": [
                        {"index": chunk_index + 1, "text": chunk}
                        for chunk_index, chunk in enumerate(analysis["chunks"])
                    ],
                }
            else:
                indexed_documents.pop(document_id, None)
            changed = True
        if changed:
            index_payload["updatedAt"] = now_iso()
        return changed

    @staticmethod
    def _public_document(document: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in document.items()
            if key not in {"storedFilename", "source"}
        }

    def payload(self) -> dict[str, Any]:
        with self._lock:
            metadata = self._load()
            index_payload = self._load_index()
            if self._ensure_indexes(metadata, index_payload):
                atomic_write_json(self.index_path, index_payload)
                atomic_write_json(self.metadata_path, metadata)
            documents = [
                self._public_document(item)
                for item in metadata["documents"]
                if (self.documents_dir / str(item.get("storedFilename") or "")).is_file()
            ]
        indexed_documents = len(index_payload["documents"])
        indexed_chunks = sum(
            len(item.get("chunks") or [])
            for item in index_payload["documents"].values()
        )
        documents.sort(key=lambda item: str(item.get("uploadedAt") or ""), reverse=True)
        return {
            "ok": True,
            "updatedAt": metadata.get("updatedAt"),
            "documents": documents,
            "index": {
                "documentCount": indexed_documents,
                "chunkCount": indexed_chunks,
                "updatedAt": index_payload.get("updatedAt"),
                "mode": "local_tfidf_ngram",
            },
            "limits": {
                "maxBytes": LEARNING_DOCUMENT_MAX_BYTES,
                "extensions": sorted(LEARNING_DOCUMENT_EXTENSIONS),
            },
        }

    def save(
        self,
        raw_filename: str,
        content: bytes,
        content_type: str = "",
    ) -> dict[str, Any]:
        filename = urllib.parse.unquote(str(raw_filename or "")).strip()
        filename = filename.replace("\\", "/").rsplit("/", 1)[-1].replace("\x00", "")
        if not filename:
            raise LearningDocumentError("请选择需要上传的文档")
        if len(content) > LEARNING_DOCUMENT_MAX_BYTES:
            raise LearningDocumentError("单个文档不能超过 25 MB", 413)
        if not content:
            raise LearningDocumentError("不能上传空文档")

        extension = Path(filename).suffix.lower()
        if extension not in LEARNING_DOCUMENT_EXTENSIONS:
            allowed = "、".join(sorted(item.lstrip(".") for item in LEARNING_DOCUMENT_EXTENSIONS))
            raise LearningDocumentError(f"不支持该文件类型；可上传 {allowed}", 415)
        stem = Path(filename).stem[:150].strip() or "学习资料"
        filename = f"{stem}{extension}"

        document_id = uuid.uuid4().hex
        stored_filename = f"{document_id}{extension}"
        target = self.documents_dir / stored_filename
        analysis = self._analyze_document(content, extension)

        uploaded_at = now_iso()
        record = {
            "id": document_id,
            "name": filename,
            "extension": extension,
            "contentType": str(content_type or "application/octet-stream")[:160],
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "uploadedAt": uploaded_at,
            "storedFilename": stored_filename,
            "source": "data_page_upload",
        }
        self._apply_analysis(record, analysis)

        with self._lock:
            metadata = self._load()
            index_payload = self._load_index()
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            temporary_path = self.documents_dir / f".{document_id}.uploading"
            try:
                with temporary_path.open("wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, target)
                metadata["documents"].append(record)
                metadata["updatedAt"] = uploaded_at
                if analysis["chunks"]:
                    index_payload["documents"][document_id] = {
                        "sha256": record["sha256"],
                        "name": record["name"],
                        "extension": record["extension"],
                        "method": analysis["method"],
                        "indexedAt": record["indexedAt"],
                        "chunks": [
                            {"index": chunk_index + 1, "text": chunk}
                            for chunk_index, chunk in enumerate(analysis["chunks"])
                        ],
                    }
                else:
                    index_payload["documents"].pop(document_id, None)
                index_payload["updatedAt"] = uploaded_at
                atomic_write_json(self.index_path, index_payload)
                atomic_write_json(self.metadata_path, metadata)
                self._retrieval_cache = None
            except Exception:
                try:
                    temporary_path.unlink(missing_ok=True)
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
                raise
        return self._public_document(record)

    def reindex_all(self) -> dict[str, Any]:
        with self._lock:
            metadata = self._load()
            index_payload = self._load_index()
            index_payload["documents"] = {}
            self._ensure_indexes(metadata, index_payload)
            metadata["updatedAt"] = now_iso()
            index_payload["updatedAt"] = metadata["updatedAt"]
            atomic_write_json(self.index_path, index_payload)
            atomic_write_json(self.metadata_path, metadata)
            self._retrieval_cache = None
        payload = self.payload()
        return {
            "ok": True,
            "index": payload["index"],
            "documents": payload["documents"],
        }

    def search(self, query: str, limit: int = 3) -> dict[str, Any]:
        query_text = str(query or "").strip()[:4000]
        safe_limit = max(1, min(8, int(limit or 3)))
        with self._lock:
            metadata = self._load()
            index_payload = self._load_index()
            if self._ensure_indexes(metadata, index_payload):
                atomic_write_json(self.index_path, index_payload)
                atomic_write_json(self.metadata_path, metadata)
            records = {
                str(record.get("id")): record
                for record in metadata["documents"]
                if record.get("id")
            }
            indexed = index_payload["documents"]

        cache_key = str(index_payload.get("updatedAt") or "") + ":" + str(len(indexed))
        cached = self._retrieval_cache
        if cached and cached[0] == cache_key:
            _key, corpus, documents_tokens, document_frequency, index_stats = cached
        else:
            corpus: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
            for document_id, document_index in indexed.items():
                record = records.get(document_id)
                if not record:
                    continue
                for chunk in document_index.get("chunks") or []:
                    if isinstance(chunk, dict) and str(chunk.get("text") or "").strip():
                        corpus.append((document_id, record, chunk))
            index_stats = {
                "documentCount": len(indexed),
                "chunkCount": len(corpus),
                "updatedAt": index_payload.get("updatedAt"),
                "mode": "local_tfidf_ngram",
            }
            documents_tokens = [
                Counter(_learning_tokens(str(chunk.get("text") or "")))
                for _document_id, _record, chunk in corpus
            ]
            document_frequency = Counter()
            for token_counts in documents_tokens:
                document_frequency.update(token_counts.keys())
            self._retrieval_cache = (
                cache_key,
                corpus,
                documents_tokens,
                document_frequency,
                index_stats,
            )
        if not query_text:
            return {
                "ok": True,
                "status": "empty_query",
                "query": query_text,
                "hits": [],
                "index": index_stats,
            }
        if not corpus:
            return {
                "ok": True,
                "status": "empty",
                "query": query_text,
                "hits": [],
                "index": index_stats,
                "message": "还没有可检索的学习资料",
            }

        query_tokens = list(dict.fromkeys(_learning_tokens(query_text)))[:100]
        if not query_tokens:
            return {
                "ok": True,
                "status": "no_match",
                "query": query_text,
                "hits": [],
                "index": index_stats,
            }
        corpus_size = len(corpus)
        scored: list[tuple[float, int, list[str]]] = []
        for corpus_index, token_counts in enumerate(documents_tokens):
            score = 0.0
            matched: list[str] = []
            for token in query_tokens:
                frequency = token_counts.get(token, 0)
                if not frequency:
                    continue
                matched.append(token)
                inverse_frequency = math.log(
                    (corpus_size + 1) / (document_frequency.get(token, 0) + 0.5)
                ) + 1
                score += (1 + math.log(frequency)) * inverse_frequency
            if not matched:
                continue
            coverage = len(set(matched)) / max(1, len(set(query_tokens)))
            score *= 0.55 + coverage
            if score >= 2.0 and (
                len(set(matched)) >= 2
                or any(token in {"roi", "gpm", "cpm", "gmv"} for token in matched)
            ):
                scored.append((score, corpus_index, matched[:12]))
        scored.sort(reverse=True, key=lambda item: item[0])

        hits: list[dict[str, Any]] = []
        per_document: Counter = Counter()
        for score, corpus_index, matched in scored:
            document_id, record, chunk = corpus[corpus_index]
            if per_document[document_id] >= 2:
                continue
            excerpt = _learning_excerpt(str(chunk.get("text") or ""), 320)
            hits.append(
                {
                    "documentId": document_id,
                    "documentName": str(record.get("name") or ""),
                    "chunkIndex": int(chunk.get("index") or 0),
                    "score": round(score, 3),
                    "relevance": round(min(99.0, score / (score + 7) * 100), 1),
                    "matchedTerms": matched,
                    "excerpt": excerpt,
                    "suggestedAction": _learning_action_sentence(excerpt),
                }
            )
            per_document[document_id] += 1
            if len(hits) >= safe_limit:
                break
        return {
            "ok": True,
            "status": "matched" if hits else "no_match",
            "query": query_text,
            "hits": hits,
            "index": index_stats,
            "message": (
                f"命中 {len(hits)} 段已学习资料"
                if hits
                else "已学习资料中未找到足够相关的片段"
            ),
        }

    def resolve(self, document_id: str) -> tuple[dict[str, Any], Path]:
        safe_id = str(document_id or "").strip()
        if not safe_id:
            raise LearningDocumentError("缺少文档 ID")
        with self._lock:
            metadata = self._load()
            record = next(
                (item for item in metadata["documents"] if item.get("id") == safe_id),
                None,
            )
            if not record:
                raise LearningDocumentError("文档不存在或已删除", 404)
            stored_filename = str(record.get("storedFilename") or "")
            target = (self.documents_dir / stored_filename).resolve()
            if self.documents_dir.resolve() not in target.parents or not target.is_file():
                raise LearningDocumentError("文档文件不存在", 404)
        return self._public_document(record), target

    def delete(self, document_id: str) -> dict[str, Any]:
        safe_id = str(document_id or "").strip()
        if not safe_id:
            raise LearningDocumentError("缺少文档 ID")
        with self._lock:
            metadata = self._load()
            index_payload = self._load_index()
            record = next(
                (item for item in metadata["documents"] if item.get("id") == safe_id),
                None,
            )
            if not record:
                raise LearningDocumentError("文档不存在或已删除", 404)
            metadata["documents"] = [
                item for item in metadata["documents"] if item.get("id") != safe_id
            ]
            metadata["updatedAt"] = now_iso()
            target = (self.documents_dir / str(record.get("storedFilename") or "")).resolve()
            if target.parent == self.documents_dir.resolve() and target.is_file():
                target.unlink()
            index_payload["documents"].pop(safe_id, None)
            index_payload["updatedAt"] = metadata["updatedAt"]
            atomic_write_json(self.index_path, index_payload)
            atomic_write_json(self.metadata_path, metadata)
            self._retrieval_cache = None
        return self._public_document(record)


def build_learning_strategy_query(payload: dict[str, Any]) -> str:
    decision = payload.get("decision") or {}
    metrics = payload.get("metrics") or {}
    parts = [
        str(decision.get("action") or ""),
        str(decision.get("reason") or ""),
        str(decision.get("guardrail") or ""),
        "ROI",
        "成交",
        "订单成本",
        "消耗",
        "放量",
        "控量",
        "素材",
        "人群",
        "直播承接",
        "流量",
    ]
    if to_number(metrics.get("roi")) is not None:
        roi = to_number(metrics.get("roi"))
        parts.append("ROI 低" if roi is not None and roi < CAMPAIGN_TARGET_ROI else "ROI 达到参考线")
    if to_number(metrics.get("cost")) is not None:
        cost = to_number(metrics.get("cost"))
        parts.append(
            "订单成本高"
            if cost is not None and cost > CAMPAIGN_TARGET_COST
            else "订单成本可控"
        )
    for anomaly in (payload.get("anomalies") or [])[-3:]:
        parts.extend(
            [
                str(anomaly.get("metric") or ""),
                str(anomaly.get("cause") or ""),
                str(anomaly.get("suggestion") or ""),
            ]
        )
    parts.extend(str(item) for item in payload.get("missingReasons") or [])
    return " ".join(part for part in parts if part.strip())


def enrich_campaign_with_learning(
    payload: dict[str, Any],
    learning_store: LearningDocumentStore,
) -> dict[str, Any]:
    enriched = copy.deepcopy(payload)
    query = build_learning_strategy_query(enriched)
    try:
        context = learning_store.search(query, limit=3)
    except Exception as exc:
        enriched["learning"] = {
            "ok": False,
            "status": "error",
            "query": query,
            "hits": [],
            "index": {},
            "message": f"学习资料检索失败：{exc}",
        }
        return enriched
    enriched["learning"] = context
    hits = context.get("hits") or []
    if not hits or not enriched.get("ok"):
        return enriched

    decision = enriched.get("decision")
    if not isinstance(decision, dict):
        return enriched
    base_reason = str(decision.get("reason") or "")
    decision["baseReason"] = base_reason
    decision["learningApplied"] = True
    decision["learningEvidence"] = hits[:2]
    decision["learningAdvice"] = _learning_action_sentence(
        str(hits[0].get("suggestedAction") or hits[0].get("excerpt") or "")
    )
    base_confidence = int(to_number(decision.get("confidence")) or 0)
    decision["confidence"] = min(96, base_confidence + min(8, 2 + len(hits) * 2))
    expected = [
        str(item)
        for item in decision.get("expected") or []
        if str(item).strip()
    ]
    if "按学习资料复核执行边界" not in expected:
        expected.append("按学习资料复核执行边界")
    decision["expected"] = expected[:5]
    return enriched


def load_config() -> dict[str, Any]:
    config = deep_merge(DEFAULT_CONFIG, load_json(CONFIG_PATH, {}))

    env_ids = [
        item.strip()
        for item in os.getenv("QIANCHUAN_ADVERTISER_IDS", "").split(",")
        if item.strip()
    ]
    if env_ids:
        configured = {str(item.get("advertiserId")): item for item in config.get("accounts", [])}
        config["accounts"] = []
        for advertiser_id in env_ids:
            existing = configured.get(advertiser_id, {})
            config["accounts"].append(
                deep_merge(
                    {
                        "id": f"qc-{advertiser_id}",
                        "advertiserId": advertiser_id,
                        "name": f"千川账号 {advertiser_id}",
                        "handle": "待同步抖音号信息",
                        "avatar": advertiser_id[-1:],
                        "color": "#0b7a58",
                    },
                    existing,
                )
            )

    normalized_accounts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_account in enumerate(config.get("accounts", [])):
        advertiser_id = str(raw_account.get("advertiserId") or raw_account.get("qianchuanId") or "").strip()
        if not advertiser_id:
            continue
        account_id = str(raw_account.get("id") or f"qc-{advertiser_id}").strip()
        if account_id in seen_ids:
            account_id = f"{account_id}-{index + 1}"
        seen_ids.add(account_id)
        normalized_accounts.append(
            deep_merge(
                {
                    "id": account_id,
                    "advertiserId": advertiser_id,
                    "name": f"千川账号 {advertiser_id}",
                    "handle": "待同步抖音号信息",
                    "avatar": advertiser_id[-1:],
                    "color": "#0b7a58",
                },
                raw_account,
            )
            | {"id": account_id, "advertiserId": advertiser_id}
        )
    config["accounts"] = normalized_accounts
    return config


def load_mcp_config() -> dict[str, Any]:
    configured = load_json(MCP_CONFIG_PATH, {})
    if not isinstance(configured, dict):
        configured = {}
    env_url = os.getenv("QIANCHUAN_MCP_URL", "").strip()
    if env_url:
        configured["url"] = env_url
        configured["enabled"] = True
    configured.setdefault("enabled", bool(configured.get("url")))
    configured.setdefault("timeoutSeconds", 20)
    configured.setdefault("cacheSeconds", 5)
    configured.setdefault("rawVerified", False)
    configured["url"] = str(configured.get("url") or "").strip()
    return configured


def read_token_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


_token_refresh_lock = threading.Lock()


def atomic_write_secret_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_oauth_config() -> dict[str, Any]:
    configured = load_json(OAUTH_CONFIG_PATH, {})
    if not isinstance(configured, dict):
        configured = {}
    result = {
        "appId": str(
            os.getenv("QIANCHUAN_APP_ID", "").strip()
            or configured.get("appId")
            or configured.get("app_id")
            or ""
        ).strip(),
        "appSecret": str(
            os.getenv("QIANCHUAN_APP_SECRET", "").strip()
            or configured.get("appSecret")
            or configured.get("app_secret")
            or configured.get("secret")
            or ""
        ).strip(),
        "redirectUri": str(
            os.getenv("QIANCHUAN_REDIRECT_URI", "").strip()
            or configured.get("redirectUri")
            or configured.get("redirect_uri")
            or ""
        ).strip(),
        "scope": configured.get("scope") or os.getenv("QIANCHUAN_OAUTH_SCOPE", "").strip(),
        "authorizeUrl": str(configured.get("authorizeUrl") or OAUTH_AUTHORIZE_URL).strip(),
        "accessTokenUrl": str(configured.get("accessTokenUrl") or OAUTH_ACCESS_TOKEN_URL).strip(),
        "refreshTokenUrl": str(
            configured.get("refreshTokenUrl") or OAUTH_REFRESH_TOKEN_URL
        ).strip(),
    }
    return result


def save_oauth_config(config: dict[str, Any]) -> None:
    payload = {
        "appId": str(config.get("appId") or "").strip(),
        "appSecret": str(config.get("appSecret") or "").strip(),
        "redirectUri": str(config.get("redirectUri") or "").strip(),
        "scope": config.get("scope") or "",
        "authorizeUrl": str(config.get("authorizeUrl") or OAUTH_AUTHORIZE_URL).strip(),
        "accessTokenUrl": str(config.get("accessTokenUrl") or OAUTH_ACCESS_TOKEN_URL).strip(),
        "refreshTokenUrl": str(
            config.get("refreshTokenUrl") or OAUTH_REFRESH_TOKEN_URL
        ).strip(),
    }
    atomic_write_secret_json(OAUTH_CONFIG_PATH, payload)


def oauth_config_errors(config: dict[str, Any], *, require_redirect: bool = True) -> list[str]:
    errors: list[str] = []
    if not str(config.get("appId") or "").strip():
        errors.append("缺少 App ID。")
    if not str(config.get("appSecret") or "").strip():
        errors.append("缺少 App Secret。")
    if require_redirect and not str(config.get("redirectUri") or "").strip():
        errors.append("缺少 OAuth 回调地址 redirect_uri。")
    return errors


def build_oauth_authorize_url(config: dict[str, Any], state: str) -> str:
    params: dict[str, Any] = {
        "app_id": str(config.get("appId") or "").strip(),
        "state": str(state),
        "redirect_uri": str(config.get("redirectUri") or "").strip(),
    }
    scope = config.get("scope")
    if isinstance(scope, (list, tuple)):
        scope = ",".join(str(item) for item in scope if item)
    if scope:
        params["scope"] = scope
    base_url = str(config.get("authorizeUrl") or OAUTH_AUTHORIZE_URL).strip()
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urllib.parse.urlencode(params)}"


def _oauth_post_form(url: str, form: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Qianchuan-AI-Dashboard/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise QianchuanAPIError(
            f"OAuth 接口 HTTP {exc.code}", code=exc.code, response=body
        ) from exc
    except urllib.error.URLError as exc:
        raise QianchuanAPIError(f"无法连接巨量 OAuth 接口: {exc.reason}") from exc
    except TimeoutError as exc:
        raise QianchuanAPIError("巨量 OAuth 接口请求超时") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise QianchuanAPIError("巨量 OAuth 接口返回了非 JSON 内容", response=body[:500]) from exc
    code = payload.get("code", payload.get("err_no"))
    if str(code) not in {"0", "None"}:
        message = payload.get("message") or payload.get("msg") or "OAuth 授权失败"
        raise QianchuanAPIError(str(message), code=code, response=payload)
    return payload


def oauth_token_record(payload: dict[str, Any], app_id: str) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload
    access_token = str(
        data.get("access_token") or data.get("accessToken") or ""
    ).strip()
    refresh_token = str(
        data.get("refresh_token") or data.get("refreshToken") or ""
    ).strip()
    if not access_token:
        raise QianchuanAPIError("OAuth 响应成功，但没有返回 access_token", response=payload)

    def expiry_iso(raw_seconds: Any) -> str | None:
        try:
            seconds = int(float(raw_seconds))
        except (TypeError, ValueError):
            return None
        if seconds <= 0:
            return None
        return (
            datetime.now(timezone.utc) + timedelta(seconds=seconds)
        ).astimezone().isoformat(timespec="seconds")

    record: dict[str, Any] = {
        "accessToken": access_token,
        "appId": app_id,
        "obtainedAt": now_iso(),
        "tokenSource": "oceanengine_oauth2",
    }
    if refresh_token:
        record["refreshToken"] = refresh_token
    expires_at = expiry_iso(data.get("expires_in") or data.get("expiresIn"))
    if expires_at:
        record["expiresAt"] = expires_at
    refresh_expires_at = expiry_iso(
        data.get("refresh_token_expires_in") or data.get("refreshTokenExpiresIn")
    )
    if refresh_expires_at:
        record["refreshExpiresAt"] = refresh_expires_at
    scope = data.get("scope") or data.get("scopes")
    if scope:
        record["scope"] = scope
    if data.get("token_type") or data.get("tokenType"):
        record["tokenType"] = data.get("token_type") or data.get("tokenType")
    return record


def exchange_oauth_code(config: dict[str, Any], auth_code: str) -> dict[str, Any]:
    errors = oauth_config_errors(config, require_redirect=False)
    if errors:
        raise QianchuanAPIError("".join(errors))
    auth_code = str(auth_code or "").strip()
    if not auth_code:
        raise QianchuanAPIError("缺少授权回调中的 auth_code")
    payload = _oauth_post_form(
        str(config.get("accessTokenUrl") or OAUTH_ACCESS_TOKEN_URL),
        {
            "app_id": str(config.get("appId") or "").strip(),
            "secret": str(config.get("appSecret") or "").strip(),
            "auth_code": auth_code,
        },
    )
    return oauth_token_record(payload, str(config.get("appId") or "").strip())


def refresh_oauth_access_token(
    config: dict[str, Any], token_info: dict[str, Any]
) -> dict[str, Any]:
    errors = oauth_config_errors(config, require_redirect=False)
    if errors:
        raise QianchuanAPIError("".join(errors))
    refresh_token = str(
        token_info.get("refreshToken") or token_info.get("refresh_token") or ""
    ).strip()
    if not refresh_token:
        raise QianchuanAPIError("当前 Token 文件没有 refresh_token，无法自动刷新")
    payload = _oauth_post_form(
        str(config.get("refreshTokenUrl") or OAUTH_REFRESH_TOKEN_URL),
        {
            "app_id": str(config.get("appId") or "").strip(),
            "secret": str(config.get("appSecret") or "").strip(),
            "refresh_token": refresh_token,
        },
    )
    refreshed = oauth_token_record(payload, str(config.get("appId") or "").strip())
    if not refreshed.get("refreshToken"):
        refreshed["refreshToken"] = refresh_token
    if token_info.get("note"):
        refreshed["note"] = token_info["note"]
    return refreshed


def token_expiry(token_info: dict[str, Any]) -> datetime | None:
    raw = (
        token_info.get("expiresAt")
        or token_info.get("expires_at")
        or token_info.get("expireAt")
    )
    if raw in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def token_needs_refresh(token_info: dict[str, Any]) -> bool:
    expires_at = token_expiry(token_info)
    if expires_at is None:
        return False
    return expires_at <= datetime.now(timezone.utc) + timedelta(
        seconds=TOKEN_REFRESH_SKEW_SECONDS
    )


def token_save_path() -> Path:
    configured_token_file = os.getenv("QIANCHUAN_TOKEN_FILE", "").strip()
    return Path(configured_token_file) if configured_token_file else TOKEN_FILE_PATH


def resolve_access_token(config: dict[str, Any]) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    token = os.getenv("QIANCHUAN_ACCESS_TOKEN", "").strip()
    token_info: dict[str, Any] = {}

    token_path = token_save_path()
    token_info = read_token_file(token_path)
    if not token and token_needs_refresh(token_info):
        with _token_refresh_lock:
            latest = read_token_file(token_path)
            token_info = latest or token_info
            if token_needs_refresh(token_info):
                try:
                    oauth_config = load_oauth_config()
                    refreshed = refresh_oauth_access_token(oauth_config, token_info)
                    atomic_write_secret_json(token_path, refreshed)
                    token_info = refreshed
                except (QianchuanAPIError, ValueError, OSError) as exc:
                    errors.append(
                        {
                            "scope": "credentials",
                            "code": "token_refresh_failed",
                            "message": f"Access Token 即将过期，自动刷新失败：{exc}",
                        }
                    )
    if not token:
        token = str(
            os.getenv("QIANCHUAN_TOKEN", "")
            or token_info.get("accessToken")
            or token_info.get("access_token")
            or ""
        ).strip()

    if not token:
        errors.append(
            {
                "scope": "credentials",
                "code": "credentials_missing",
                "message": "未配置 QIANCHUAN_ACCESS_TOKEN 或 data/qianchuan-token.json，无法请求千川开放平台。",
            }
        )
    return token, token_info, errors


def oauth_status_payload(token_info: dict[str, Any] | None = None) -> dict[str, Any]:
    token_info = token_info or {}
    try:
        oauth_config = load_oauth_config()
        config_error = ""
    except ValueError as exc:
        oauth_config = {}
        config_error = str(exc)
    expires_at = token_expiry(token_info)
    refresh_token = str(
        token_info.get("refreshToken") or token_info.get("refresh_token") or ""
    ).strip()
    return {
        "oauthConfigured": not bool(config_error)
        and not oauth_config_errors(oauth_config),
        "appIdConfigured": bool(oauth_config.get("appId")),
        "appSecretConfigured": bool(oauth_config.get("appSecret")),
        "redirectUriConfigured": bool(oauth_config.get("redirectUri")),
        "accessTokenConfigured": bool(
            token_info.get("accessToken") or token_info.get("access_token")
        ),
        "refreshTokenConfigured": bool(refresh_token),
        "expiresAt": expires_at.isoformat(timespec="seconds") if expires_at else None,
        "expired": bool(expires_at and expires_at <= datetime.now(timezone.utc)),
        "needsRefresh": token_needs_refresh(token_info),
        "tokenSource": token_info.get("tokenSource"),
        "error": config_error,
    }


def lookup_value(source: Any, path: str) -> Any:
    current = source
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def pick_value(source: dict[str, Any], candidates: Any) -> Any:
    if isinstance(candidates, str):
        candidates = [candidates]
    for candidate in candidates or []:
        value = lookup_value(source, str(candidate))
        if value is not None and value != "":
            return value
    return None


def to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def report_value(source: Any, field: str) -> Any:
    """Read a value from Qianchuan report metric/dimension envelopes."""
    if not isinstance(source, dict):
        return None
    item = source.get(field)
    if isinstance(item, dict):
        if "Value" in item:
            return item.get("Value")
        if "ValueStr" in item:
            return item.get("ValueStr")
        return None
    return item


def normalize_external_datetime(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            return datetime.fromtimestamp(timestamp, timezone.utc).astimezone().isoformat(
                timespec="seconds"
            )
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return normalize_external_datetime(int(text))
    normalized = text.replace("/", "-")
    for candidate in (normalized, normalized.replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def apply_material_delete_policy(material: dict[str, Any]) -> None:
    impressions = to_number(material.get("impressions")) or 0.0
    orders = to_number(material.get("orders")) or 0.0
    upload_age_days = material.get("uploadAgeDays")
    try:
        upload_age_days = (
            int(upload_age_days) if upload_age_days is not None else None
        )
    except (TypeError, ValueError):
        upload_age_days = None
    low_performance = impressions < 60 and orders < 2
    material["deleteRecommendation"] = bool(
        low_performance
        and upload_age_days is not None
        and upload_age_days > 40
    )
    material["deleteReviewRequired"] = bool(
        low_performance and upload_age_days is None
    )
    material["deleteReason"] = (
        "曝光 < 60、订单 < 2，且上传超过 40 天"
        if material["deleteRecommendation"]
        else "曝光 < 60、订单 < 2，但上传时间未获取"
        if material["deleteReviewRequired"]
        else ""
    )


def normalize_qianchuan_video_library(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize the official Qianchuan video library.

    The API documents ``create_time`` as the video material upload time.
    Missing or invalid values remain unavailable instead of being inferred.
    """
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        material_id = str(row.get("material_id") or row.get("id") or "").strip()
        if not material_id:
            continue
        uploaded_at = normalize_external_datetime(row.get("create_time"))
        upload_age_days: int | None = None
        if uploaded_at:
            try:
                upload_age_days = max(
                    0,
                    (
                        datetime.now(timezone.utc).astimezone().date()
                        - datetime.fromisoformat(
                            uploaded_at.replace("Z", "+00:00")
                        ).date()
                    ).days,
                )
            except ValueError:
                upload_age_days = None
        result.append(
            {
                "id": material_id,
                "videoId": str(row.get("id") or "").strip() or None,
                "name": str(row.get("filename") or f"素材 {material_id}"),
                "type": "视频",
                "duration": row.get("duration"),
                "cover": row.get("poster_url"),
                "videoUrl": row.get("url"),
                "uploadedAt": uploaded_at or "未获取",
                "uploadAgeDays": upload_age_days,
                "source": row.get("source"),
                "isAiCreate": row.get("is_ai_create"),
                "uploadTimeSource": "千川素材库视频 create_time",
            }
        )
    return result


def normalize_uni_promotion_material_report(
    rows: list[dict[str, Any]],
    aweme_id: str,
    material_type: str,
    window: dict[str, Any],
) -> list[dict[str, Any]]:
    """Aggregate Qianchuan's official daily material report by material."""
    is_live = str(material_type).upper() == "LIVE_ROOM"
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        dimensions = row.get("dimensions") or {}
        metrics = row.get("metrics") or {}
        material_id = str(report_value(dimensions, "material_id") or "").strip()
        if not material_id:
            material_id = f"live-room-{aweme_id}"
        name = str(
            report_value(
                dimensions,
                "roi2_material_anchor_name" if is_live else "roi2_material_video_name",
            )
            or ("直播间画面" if is_live else f"素材 {material_id}")
        )
        type_label = "直播间画面" if is_live else "视频"
        if not is_live:
            raw_type = str(report_value(dimensions, "roi2_material_video_type") or "")
            type_label = "视频"

        raw_upload_time = next(
            (
                report_value(dimensions, field)
                for field in (
                    "material_create_time",
                    "material_upload_time",
                    "create_time",
                    "upload_time",
                )
                if report_value(dimensions, field) not in (None, "")
            ),
            None,
        )
        uploaded_at = normalize_external_datetime(raw_upload_time)
        upload_age_days: int | None = None
        if uploaded_at:
            try:
                upload_age_days = max(
                    0,
                    (
                        datetime.now(timezone.utc).astimezone().date()
                        - datetime.fromisoformat(uploaded_at.replace("Z", "+00:00")).date()
                    ).days,
                )
            except ValueError:
                upload_age_days = None

        def metric(*fields: str) -> float:
            for field in fields:
                value = to_number(report_value(metrics, field))
                if value is not None:
                    return value
            return 0.0

        spend = metric("stat_cost_for_roi2", "stat_cost_for_roi2_fork")
        gmv = metric("total_pay_order_gmv_for_roi2", "total_pay_order_gmv_for_roi2_fork")
        orders = metric("total_pay_order_count_for_roi2", "total_pay_order_count_for_roi2_fork")
        impressions = metric(
            "live_show_count_for_roi2_v2",
            "live_show_count_exclude_video_for_roi2",
        )
        clicks = metric(
            "live_watch_count_for_roi2_v2",
            "live_watch_count_exclude_video_for_roi2",
        )
        play_count = metric("video_play_count_for_roi2_v2")
        completion_rate = metric("video_play_finish_rate_for_roi2_v2")
        dwell_time = metric("video_avg_watch_duration_for_roi2")
        weight = play_count or impressions or 1.0

        item = by_id.get(material_id)
        if item is None:
            item = {
                "id": material_id,
                "awemeId": str(aweme_id),
                "name": name,
                "type": type_label,
                "duration": "—",
                "spend": 0.0,
                "gmv": 0.0,
                "orders": 0.0,
                "impressions": 0.0,
                "clicks": 0.0,
                "ctr": 0.0,
                "completionRate": 0.0,
                "dwellTime": 0.0,
                "persona": {
                    "age": "未获取",
                    "region": "未获取",
                    "gender": "未获取",
                },
                "materialStatus": "已投放",
                "auditStatus": None,
                "uploadedAt": uploaded_at or "未获取",
                "uploadAgeDays": upload_age_days,
                "cover": None,
                "videoUrl": None,
                "materialWindow": copy.deepcopy(window),
                "reportSource": "千川素材维度报表",
                "_completionWeight": 0.0,
                "_completionWeighted": 0.0,
                "_dwellWeight": 0.0,
                "_dwellWeighted": 0.0,
            }
            by_id[material_id] = item
        item["spend"] += spend
        item["gmv"] += gmv
        item["orders"] += orders
        item["impressions"] += impressions
        item["clicks"] += clicks
        item["_completionWeight"] += weight
        item["_completionWeighted"] += completion_rate * weight
        item["_dwellWeight"] += weight
        item["_dwellWeighted"] += dwell_time * weight

    result: list[dict[str, Any]] = []
    for item in by_id.values():
        item["spend"] = round(item["spend"], 2)
        item["gmv"] = round(item["gmv"], 2)
        item["orders"] = round(item["orders"], 4)
        item["impressions"] = round(item["impressions"], 2)
        item["clicks"] = round(item["clicks"], 2)
        item["ctr"] = round(item["clicks"] / item["impressions"] * 100, 4) if item["impressions"] else 0.0
        completion_weight = item.pop("_completionWeight", 0.0)
        completion_weighted = item.pop("_completionWeighted", 0.0)
        dwell_weight = item.pop("_dwellWeight", 0.0)
        dwell_weighted = item.pop("_dwellWeighted", 0.0)
        item["completionRate"] = round(completion_weighted / completion_weight, 4) if completion_weight else 0.0
        item["dwellTime"] = round(dwell_weighted / dwell_weight, 4) if dwell_weight else 0.0
        item["deleteRecommendation"] = bool(
            item["impressions"] < 60
            and item["orders"] < 2
            and item["uploadAgeDays"] is not None
            and item["uploadAgeDays"] > 40
        )
        item["deleteReviewRequired"] = bool(
            item["impressions"] < 60
            and item["orders"] < 2
            and item["uploadAgeDays"] is None
        )
        item["deleteReason"] = (
            "曝光 < 60、订单 < 2，且上传超过 40 天"
            if item["deleteRecommendation"]
            else "曝光 < 60、订单 < 2，但上传时间未获取"
            if item["deleteReviewRequired"]
            else ""
        )
        result.append(item)
    return sorted(result, key=lambda material: (-material["spend"], -material["impressions"], material["id"]))


def normalize_daily_rows(
    rows: list[dict[str, Any]],
    field_map: dict[str, Any],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_date = pick_value(row, field_map.get("date", DEFAULT_FIELD_MAP["date"]))
        if raw_date is None:
            continue
        row_date = str(raw_date)[:10]
        if row_date < start_date or row_date > end_date:
            continue
        spend = to_number(pick_value(row, field_map.get("spend", DEFAULT_FIELD_MAP["spend"])))
        gmv = to_number(pick_value(row, field_map.get("gmv", DEFAULT_FIELD_MAP["gmv"])))
        orders = to_number(pick_value(row, field_map.get("orders", DEFAULT_FIELD_MAP["orders"])))
        if spend is None and gmv is None and orders is None:
            continue
        normalized = by_date.setdefault(
            row_date,
            {"date": row_date, "spend": 0.0, "gmv": 0.0, "orders": 0.0},
        )
        normalized["spend"] += spend or 0.0
        normalized["gmv"] += gmv or 0.0
        normalized["orders"] += orders or 0.0
        viewers = to_number(pick_value(row, field_map.get("viewers", DEFAULT_FIELD_MAP["viewers"])))
        if viewers is not None:
            normalized["viewers"] = normalized.get("viewers", 0.0) + viewers

    result = []
    for row_date in sorted(by_date):
        row = by_date[row_date]
        row["spend"] = round(row["spend"], 2)
        row["gmv"] = round(row["gmv"], 2)
        row["orders"] = round(row["orders"], 4)
        if "viewers" in row:
            row["viewers"] = round(row["viewers"], 4)
        result.append(row)
    return result


def upsert_daily_row(
    rows: list[dict[str, Any]],
    row: dict[str, Any],
    preserve_positive_on_zero: bool = True,
) -> list[dict[str, Any]]:
    """Replace one day's snapshot while protecting the last non-zero intraday value."""
    row_date = str(row.get("date") or "")[:10]
    if not row_date:
        return copy.deepcopy(rows)
    existing = [
        copy.deepcopy(item)
        for item in rows
        if isinstance(item, dict) and str(item.get("date") or "")[:10] != row_date
    ]
    previous = next(
        (
            item
            for item in rows
            if isinstance(item, dict) and str(item.get("date") or "")[:10] == row_date
        ),
        None,
    )
    metric_keys = ("spend", "gmv", "orders")
    current_positive = any((to_number(row.get(key)) or 0.0) > 0 for key in metric_keys)
    previous_positive = bool(previous) and any(
        (to_number(previous.get(key)) or 0.0) > 0 for key in metric_keys
    )
    if preserve_positive_on_zero and previous_positive and not current_positive:
        existing.append(copy.deepcopy(previous))
    else:
        existing.append(copy.deepcopy(row))
    existing.sort(key=lambda item: str(item.get("date") or ""))
    return existing


def normalize_campaign_status(value: Any, status_map: dict[str, Any]) -> str:
    if value is None or value == "":
        return "待同步"
    key = str(value).upper()
    return str(status_map.get(key) or value)


def normalize_campaign_plans(
    rows: list[dict[str, Any]],
    field_map: dict[str, Any],
    status_map: dict[str, Any],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    plans: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        campaign_id = str(pick_value(row, field_map.get("campaignId", ["campaign_id", "id"])) or "").strip()
        if not campaign_id or campaign_id in seen:
            continue
        seen.add(campaign_id)
        raw_status = pick_value(row, field_map.get("status", ["status", "opt_status"]))
        plans.append(
            {
                "id": campaign_id,
                "name": str(
                    pick_value(row, field_map.get("campaignName", ["campaign_name", "name"]))
                    or f"计划 {campaign_id}"
                ),
                "status": normalize_campaign_status(raw_status, status_map),
                "rawStatus": raw_status,
                "data": [],
                "materials": [],
                "source": "千川计划接口",
            }
        )
    return plans


def normalize_uni_promotion_plans(
    rows: list[dict[str, Any]],
    status_map: dict[str, Any],
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ad_info = row.get("ad_info") or {}
        plan_id = str(ad_info.get("id") or row.get("ad_id") or "").strip()
        if not plan_id:
            continue
        status = normalize_campaign_status(ad_info.get("status") or row.get("status"), status_map)
        stats = row.get("stats_info") or {}
        plans.append(
            {
                "id": plan_id,
                "name": str(ad_info.get("name") or f"计划 {plan_id}"),
                "status": status,
                "rawStatus": ad_info.get("status") or row.get("status"),
                "marketingGoal": ad_info.get("marketing_goal") or row.get("marketing_goal"),
                "adlabScene": ad_info.get("adlab_scene") or row.get("adlab_scene"),
                "smartBidType": ad_info.get("smart_bid_type"),
                "budget": ad_info.get("budget"),
                "budgetMode": ad_info.get("budget_mode"),
                "roiGoal": ad_info.get("roi2_goal"),
                "roomInfo": row.get("room_info") or [],
                "source": "千川全域推广计划接口",
                "stats": stats,
                "data": [],
                "materials": [],
            }
        )
    return plans


def normalize_campaign_daily_rows(
    rows: list[dict[str, Any]],
    field_map: dict[str, Any],
    start_date: str,
    end_date: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    by_campaign_date: dict[tuple[str, str], dict[str, Any]] = {}
    campaign_names: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        campaign_id = str(pick_value(row, field_map.get("campaignId", ["campaign_id", "id"])) or "").strip()
        raw_date = pick_value(row, field_map.get("date", ["stat_date", "date", "time"]))
        if not campaign_id or raw_date is None:
            continue
        row_date = str(raw_date)[:10]
        if row_date < start_date or row_date > end_date:
            continue
        campaign_name = pick_value(row, field_map.get("campaignName", ["campaign_name", "name"]))
        if campaign_name:
            campaign_names[campaign_id] = str(campaign_name)
        spend = to_number(pick_value(row, field_map.get("spend", DEFAULT_FIELD_MAP["spend"])))
        gmv = to_number(pick_value(row, field_map.get("gmv", DEFAULT_FIELD_MAP["gmv"])))
        orders = to_number(pick_value(row, field_map.get("orders", DEFAULT_FIELD_MAP["orders"])))
        if spend is None and gmv is None and orders is None:
            continue
        key = (campaign_id, row_date)
        normalized = by_campaign_date.setdefault(
            key,
            {"date": row_date, "spend": 0.0, "gmv": 0.0, "orders": 0.0},
        )
        normalized["spend"] += spend or 0.0
        normalized["gmv"] += gmv or 0.0
        normalized["orders"] += orders or 0.0

    by_campaign: dict[str, list[dict[str, Any]]] = {}
    for (campaign_id, _row_date), row in sorted(by_campaign_date.items()):
        row["spend"] = round(row["spend"], 2)
        row["gmv"] = round(row["gmv"], 2)
        row["orders"] = round(row["orders"], 4)
        by_campaign.setdefault(campaign_id, []).append(row)
    return by_campaign, campaign_names


def normalize_campaign_materials(
    rows: list[dict[str, Any]],
    field_map: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    by_campaign: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        campaign_id = str(pick_value(row, field_map.get("campaignId", ["campaign_id", "id"])) or "").strip()
        if not campaign_id:
            continue
        material_id = str(
            pick_value(row, field_map.get("materialId", ["material_id", "creative_id", "ad_id", "id"]))
            or f"{campaign_id}-material-{index + 1}"
        )
        impressions = to_number(pick_value(row, field_map.get("impressions", ["show_cnt", "impressions"]))) or 0.0
        clicks = to_number(pick_value(row, field_map.get("clicks", ["click_cnt", "clicks"]))) or 0.0
        by_campaign.setdefault(campaign_id, []).append(
            {
                "id": material_id,
                "campaignId": campaign_id,
                "name": str(
                    pick_value(row, field_map.get("materialName", ["material_name", "creative_name", "name"]))
                    or material_id
                ),
                "type": str(
                    pick_value(row, field_map.get("materialType", ["material_type", "type"]))
                    or "素材"
                ),
                "spend": to_number(pick_value(row, field_map.get("spend", DEFAULT_FIELD_MAP["spend"]))) or 0.0,
                "gmv": to_number(pick_value(row, field_map.get("gmv", DEFAULT_FIELD_MAP["gmv"]))) or 0.0,
                "orders": to_number(pick_value(row, field_map.get("orders", DEFAULT_FIELD_MAP["orders"]))) or 0.0,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": to_number(pick_value(row, field_map.get("ctr", ["ctr"]))) or 0.0,
                "completionRate": to_number(
                    pick_value(row, field_map.get("completionRate", ["play_over_rate", "completion_rate"]))
                ) or 0.0,
                "dwellTime": to_number(
                    pick_value(row, field_map.get("dwellTime", ["average_watch_duration", "dwell_time"]))
                ) or 0.0,
                "persona": {"age": "—", "region": "—", "gender": "—"},
            }
        )
    return by_campaign


class QianchuanMCPError(RuntimeError):
    pass


class QianchuanMCPClient:
    """Minimal stdlib MCP client for Qianchuan's remote HTTP MCP server."""

    LIVE_REPORT_TOOL = "qianchuan_report_live_get_v1"
    UNI_PROMOTION_REPORT_TOOL = "qianchuan_report_uni_promotion_get_v1"

    def __init__(self, config: dict[str, Any]):
        self.url = str(config.get("url") or "").strip()
        self.timeout = max(3.0, float(config.get("timeoutSeconds", 20)))
        self.session_id = ""
        self.protocol_version = "2025-03-26"
        self.message_url = ""
        self.request_id = 0
        self.initialized = False
        self._tools: list[dict[str, Any]] | None = None

    @staticmethod
    def _rpc_payload(body: str, request_id: int | None = None) -> Any:
        text = body.strip()
        if not text:
            return None
        try:
            decoded = json.loads(text)
            return decoded
        except json.JSONDecodeError:
            pass
        messages: list[Any] = []
        for event in text.replace("\r\n", "\n").split("\n\n"):
            data_lines = [
                line[5:].lstrip()
                for line in event.splitlines()
                if line.startswith("data:")
            ]
            if not data_lines:
                continue
            data = "\n".join(data_lines).strip()
            try:
                messages.append(json.loads(data))
            except json.JSONDecodeError:
                continue
        flattened: list[Any] = []
        for message in messages:
            if isinstance(message, list):
                flattened.extend(message)
            else:
                flattened.append(message)
        if request_id is not None:
            for message in flattened:
                if isinstance(message, dict) and message.get("id") == request_id:
                    return message
        return flattened[0] if flattened else None

    def _open_legacy_sse(self) -> None:
        request = urllib.request.Request(
            self.url,
            headers={
                "Accept": "text/event-stream",
                "User-Agent": "Qianchuan-AI-Dashboard-MCP/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                event_name = ""
                data_lines: list[str] = []
                while True:
                    raw = response.readline()
                    if not raw:
                        break
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if not line:
                        if event_name == "endpoint" and data_lines:
                            endpoint = "\n".join(data_lines).strip()
                            self.message_url = urllib.parse.urljoin(self.url, endpoint)
                            return
                        event_name = ""
                        data_lines = []
                        continue
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise QianchuanMCPError(
                f"MCP SSE HTTP {exc.code}: {response_body[:300] or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise QianchuanMCPError(f"无法连接千川 MCP SSE：{exc.reason}") from exc
        except TimeoutError as exc:
            raise QianchuanMCPError("千川 MCP SSE 请求超时") from exc
        raise QianchuanMCPError("MCP SSE 未返回消息端点")

    def _post(self, payload: dict[str, Any]) -> Any:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        target = self.message_url or self.url
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": "Qianchuan-AI-Dashboard-MCP/1.0",
            "MCP-Protocol-Version": self.protocol_version,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(target, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self.session_id = session_id
                response_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            if not self.message_url and exc.code in {400, 404, 405, 406, 415}:
                self._open_legacy_sse()
                return self._post(payload)
            raise QianchuanMCPError(
                f"MCP HTTP {exc.code}: {response_body[:300] or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise QianchuanMCPError(f"无法连接千川 MCP：{exc.reason}") from exc
        except TimeoutError as exc:
            raise QianchuanMCPError("千川 MCP 请求超时") from exc
        parsed = self._rpc_payload(response_body, payload.get("id"))
        if isinstance(parsed, dict) and parsed.get("error"):
            error = parsed.get("error") or {}
            raise QianchuanMCPError(
                str(error.get("message") or error.get("code") or "MCP 返回错误")
            )
        return parsed

    def initialize(self) -> None:
        if self.initialized:
            return
        self.request_id += 1
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "qianchuan-ai-dashboard",
                        "version": "1.0",
                    },
                },
            }
        )
        result = response.get("result", {}) if isinstance(response, dict) else {}
        self.protocol_version = str(
            result.get("protocolVersion") or self.protocol_version
        )
        self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )
        self.initialized = True

    def list_tools(self) -> list[dict[str, Any]]:
        if self._tools is not None:
            return copy.deepcopy(self._tools)
        self.initialize()
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(20):
            self.request_id += 1
            params = {"cursor": cursor} if cursor else {}
            response = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self.request_id,
                    "method": "tools/list",
                    "params": params,
                }
            )
            result = response.get("result", {}) if isinstance(response, dict) else {}
            tools.extend(
                item for item in result.get("tools", []) if isinstance(item, dict)
            )
            cursor = result.get("nextCursor")
            if not cursor:
                break
        self._tools = tools
        return copy.deepcopy(tools)

    def call_tool_raw(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        self.initialize()
        self.request_id += 1
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        return response if isinstance(response, dict) else {"response": response}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        response = self.call_tool_raw(name, arguments)
        result = response.get("result") if isinstance(response, dict) else None
        if isinstance(result, dict) and result.get("isError"):
            raise QianchuanMCPError(f"MCP 工具 {name} 返回错误")
        return result

    @staticmethod
    def result_json(result: Any) -> Any:
        if not isinstance(result, dict):
            return result
        if isinstance(result.get("structuredContent"), (dict, list)):
            return result["structuredContent"]
        decoded: list[Any] = []
        for item in result.get("content") or []:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("json"), (dict, list)):
                decoded.append(item["json"])
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            try:
                decoded.append(json.loads(text))
            except json.JSONDecodeError:
                continue
        if len(decoded) == 1:
            return decoded[0]
        return decoded or result

    @staticmethod
    def iter_dicts(value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from QianchuanMCPClient.iter_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from QianchuanMCPClient.iter_dicts(child)

    def _tool_arguments(
        self,
        tool: dict[str, Any],
        advertiser_id: str,
        aweme_id: str,
        today: str,
    ) -> dict[str, Any] | None:
        schema = tool.get("inputSchema") or {}
        properties = schema.get("properties") if isinstance(schema, dict) else {}
        properties = properties if isinstance(properties, dict) else {}
        candidates = {
            "advertiser_id": advertiser_id,
            "advertiser_ids": [advertiser_id],
            "advertiserId": advertiser_id,
            "aweme_id": aweme_id,
            "aweme_ids": [aweme_id],
            "awemeId": aweme_id,
            "date": today,
            "start_date": today,
            "end_date": today,
            "start_time": f"{today} 00:00:00",
            "end_time": f"{today} 23:59:59",
            "marketing_goal": "LIVE_PROM_GOODS",
            "page": 1,
            "page_size": 100,
            "page_info": {"page": 1, "page_size": 100},
            "fields": [
                "stat_cost",
                "pay_order_amount",
                "pay_order_count",
                "total_pay_order_gmv_for_roi2",
                "total_pay_order_count_for_roi2",
                "total_prepay_and_pay_order_roi2",
                "total_live_watch_cnt",
                "live_watch_one_minute_count",
                "live_click_product_count_alias",
                "total_live_comment_cnt",
                "total_live_follow_cnt",
                "live_show_count",
                "online_count",
                "current_online_count",
                "gpm",
            ],
            "filtering": {},
            "order_field": "stat_cost",
            "order_type": "DESC",
        }
        arguments: dict[str, Any] = {}
        for key in properties:
            if key in candidates:
                arguments[key] = copy.deepcopy(candidates[key])
        for required in schema.get("required", []) if isinstance(schema, dict) else []:
            if required not in arguments:
                return None
        return arguments

    def fetch_live_room(
        self,
        advertiser_id: str,
        aweme_id: str,
        today: str,
    ) -> dict[str, Any]:
        tool = next(
            (
                item
                for item in self.list_tools()
                if str(item.get("name") or "") == self.LIVE_REPORT_TOOL
            ),
            None,
        )
        if tool is None:
            raise QianchuanMCPError(f"MCP 未开放工具 {self.LIVE_REPORT_TOOL}")
        arguments = self._tool_arguments(tool, advertiser_id, aweme_id, today)
        if arguments is None:
            raise QianchuanMCPError(
                f"{self.LIVE_REPORT_TOOL} 缺少必要参数或参数 schema 不受支持"
            )
        result = self.call_tool(self.LIVE_REPORT_TOOL, arguments)
        payload = self.result_json(result)
        records = list(self.iter_dicts(payload))
        room = next(
            (
                item
                for item in records
                if any(
                    key in item
                    for key in (
                        "stat_cost",
                        "pay_order_amount",
                        "pay_order_count",
                        "room_id",
                        "room_status",
                        "total_live_watch_cnt",
                        "luban_live_pay_order_gmv",
                        "total_live_comment_cnt",
                        "live_click_product_count_alias",
                        "online_count",
                        "gpm",
                    )
                )
            ),
            None,
        )
        if room is None:
            raise QianchuanMCPError(
                f"{self.LIVE_REPORT_TOOL} 未返回可识别的直播报表数据（可能返回空 data）"
            )
        return {
            "tool": self.LIVE_REPORT_TOOL,
            "room": copy.deepcopy(room),
            "payload": copy.deepcopy(payload),
            "arguments": arguments,
        }

    def fetch_uni_promotion_trade(
        self,
        advertiser_id: str,
        start_time: str,
        end_time: str,
    ) -> dict[str, Any]:
        """Read account-level trade metrics from the official uni-promotion report."""
        tool = next(
            (
                item
                for item in self.list_tools()
                if str(item.get("name") or "") == self.UNI_PROMOTION_REPORT_TOOL
            ),
            None,
        )
        if tool is None:
            raise QianchuanMCPError(
                f"MCP 未开放工具 {self.UNI_PROMOTION_REPORT_TOOL}"
            )
        schema = tool.get("inputSchema") or {}
        properties = schema.get("properties") if isinstance(schema, dict) else {}
        properties = properties if isinstance(properties, dict) else {}
        candidates: dict[str, Any] = {
            "advertiser_id": int(advertiser_id),
            "start_date": start_time,
            "end_date": end_time,
            "fields": [
                "stat_cost",
                "total_pay_order_gmv_for_roi2",
                "total_pay_order_count_for_roi2",
                "total_prepay_and_pay_order_roi2",
            ],
            "marketing_goal": "ALL",
            "order_platform": "ALL",
            "filtering": {},
        }
        if properties.get("advertiser_id", {}).get("type") == "string":
            candidates["advertiser_id"] = str(advertiser_id)
        arguments = {
            key: copy.deepcopy(candidates[key])
            for key in properties
            if key in candidates
        }
        for required in schema.get("required", []) if isinstance(schema, dict) else []:
            if required not in arguments:
                raise QianchuanMCPError(
                    f"{self.UNI_PROMOTION_REPORT_TOOL} 参数 {required} 不受当前构造器支持"
                )
        result = self.call_tool(self.UNI_PROMOTION_REPORT_TOOL, arguments)
        payload = self.result_json(result)
        if isinstance(payload, dict) and payload.get("code") not in {None, 0, "0"}:
            raise QianchuanMCPError(
                f"{self.UNI_PROMOTION_REPORT_TOOL} 返回错误 "
                f"{payload.get('code')}: {payload.get('message') or '未知错误'}"
            )
        record = next(
            (
                item
                for item in self.iter_dicts(payload)
                if "stat_cost" in item
                or "total_pay_order_gmv_for_roi2" in item
                or "total_pay_order_count_for_roi2" in item
            ),
            None,
        )
        if record is None:
            raise QianchuanMCPError(
                f"{self.UNI_PROMOTION_REPORT_TOOL} 未返回可识别的交易指标"
            )
        return {
            "tool": self.UNI_PROMOTION_REPORT_TOOL,
            "record": copy.deepcopy(record),
            "payload": copy.deepcopy(payload),
            "arguments": arguments,
        }


class QianchuanAPIError(RuntimeError):
    def __init__(self, message: str, code: Any = None, response: Any = None):
        super().__init__(message)
        self.code = code
        self.response = response


class QianchuanClient:
    _throttle_lock = threading.Lock()
    _last_request_at = 0.0
    _min_request_gap = 0.35

    def __init__(self, config: dict[str, Any], access_token: str):
        api = config.get("api", {})
        self.base_url = str(api.get("baseUrl", DEFAULT_CONFIG["api"]["baseUrl"])).rstrip("/")
        self.report_endpoint = str(api.get("reportEndpoint", DEFAULT_CONFIG["api"]["reportEndpoint"]))
        self.advertiser_list_endpoint = str(api.get("advertiserListEndpoint") or "").strip()
        self.method = str(api.get("method", "GET")).upper()
        self.timeout = float(api.get("timeoutSeconds", DEFAULT_TIMEOUT_SECONDS))
        self.page_size = max(1, min(100, int(api.get("pageSize", DEFAULT_PAGE_SIZE))))
        self.max_pages = max(1, int(api.get("maxPages", 20)))
        self.request_interval = max(0.0, float(api.get("requestIntervalSeconds", 0.25)))
        self.fields = api.get("fields", DEFAULT_FIELDS)
        self.extra_params = api.get("extraParams", {})
        self.list_keys = api.get("listKeys", ["list", "rows", "data"])
        self.access_token = access_token
        self.campaigns = config.get("campaigns", DEFAULT_CAMPAIGN_CONFIG)
        self.live = config.get("live", DEFAULT_LIVE_CONFIG)

    def _request_json(
        self,
        params: dict[str, Any],
        payload: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint or self.report_endpoint}"
        headers = {
            "Access-Token": self.access_token,
            "Accept": "application/json",
            "User-Agent": "Qianchuan-AI-Dashboard/1.0",
        }
        for attempt in range(3):
            with QianchuanClient._throttle_lock:
                gap = time.time() - QianchuanClient._last_request_at
                if gap < QianchuanClient._min_request_gap:
                    time.sleep(QianchuanClient._min_request_gap - gap)
                QianchuanClient._last_request_at = time.time()
            if self.method == "GET":
                query = urllib.parse.urlencode(params, doseq=True)
                request = urllib.request.Request(f"{url}?{query}", headers=headers, method="GET")
            else:
                request_headers = dict(headers)
                request_headers["Content-Type"] = "application/json"
                data = json.dumps(payload or params, ensure_ascii=False).encode("utf-8")
                request = urllib.request.Request(url, data=data, headers=request_headers, method=self.method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < 2:
                    time.sleep(3 + attempt * 4)
                    continue
                raise QianchuanAPIError(
                    f"千川接口 HTTP {exc.code}", code=exc.code, response=body
                ) from exc
            except urllib.error.URLError as exc:
                raise QianchuanAPIError(f"无法连接千川开放平台: {exc.reason}") from exc
            except http.client.IncompleteRead as exc:
                if attempt < 2:
                    time.sleep(3 + attempt * 4)
                    continue
                raise QianchuanAPIError(
                    "千川接口响应不完整，重试后仍然失败",
                    response=str(exc),
                ) from exc
            except TimeoutError as exc:
                raise QianchuanAPIError("千川接口请求超时") from exc

            try:
                result = json.loads(body)
            except json.JSONDecodeError as exc:
                raise QianchuanAPIError("千川接口返回了非 JSON 内容", response=body[:500]) from exc
            code = result.get("code", result.get("err_no"))
            if str(code) not in {"0", "None"}:
                message = result.get("message") or result.get("msg") or "千川接口返回错误"
                if str(code) in {"40000", "40100", "429"} and attempt < 2:
                    time.sleep(3 + attempt * 4)
                    continue
                raise QianchuanAPIError(str(message), code=code, response=result)
            return result
        raise QianchuanAPIError("千川接口重试后仍然失败")

    def fetch_authorized_advertisers(self) -> list[dict[str, Any]]:
        if not self.advertiser_list_endpoint:
            return []
        response = self._request_json(
            {"access_token": self.access_token},
            {"access_token": self.access_token},
            endpoint=self.advertiser_list_endpoint,
        )
        data = response.get("data") or {}
        rows: Any = data.get("list") if isinstance(data, dict) else None
        if rows is None and isinstance(data, list):
            rows = data
        result: list[dict[str, Any]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            advertiser_id = str(
                row.get("advertiser_id")
                or row.get("advertiserId")
                or row.get("id")
                or ""
            ).strip()
            if not advertiser_id:
                continue
            result.append(
                {
                    "advertiserId": advertiser_id,
                    "name": str(row.get("advertiser_name") or row.get("name") or f"千川账号 {advertiser_id}"),
                }
            )
        return result

    def fetch_report(
        self,
        advertiser_id: str,
        start_date: str,
        end_date: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        all_rows: list[dict[str, Any]] = []
        raw_pages: list[dict[str, Any]] = []
        for page in range(1, self.max_pages + 1):
            params = {
                "advertiser_id": advertiser_id,
                "start_date": start_date,
                "end_date": end_date,
                "fields": json.dumps(self.fields, ensure_ascii=False),
                "page": page,
                "page_size": self.page_size,
            }
            params.update(self.extra_params)
            response = self._request_json(params, params)
            raw_pages.append(response)
            data = response.get("data") or {}
            rows: Any = None
            for key in self.list_keys:
                candidate = data.get(key) if isinstance(data, dict) else None
                if isinstance(candidate, list):
                    rows = candidate
                    break
            if rows is None and isinstance(data, list):
                rows = data
            rows = rows or []
            all_rows.extend(row for row in rows if isinstance(row, dict))

            page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
            total_page = page_info.get("total_page") or page_info.get("totalPage")
            if total_page is not None and page >= int(total_page):
                break
            if len(rows) < self.page_size:
                break
            if self.request_interval:
                time.sleep(self.request_interval)
        return all_rows, raw_pages

    def _extract_rows(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        data = response.get("data") or {}
        rows: Any = None
        for key in list(self.list_keys) + ["ad_list", "room_list", "ad_material_infos"]:
            candidate = data.get(key) if isinstance(data, dict) else None
            if isinstance(candidate, list):
                rows = candidate
                break
        if rows is None and isinstance(data, list):
            rows = data
        return [row for row in (rows or []) if isinstance(row, dict)]

    def _fetch_campaign_pages(
        self,
        endpoint: str,
        params: dict[str, Any],
        page_size: int,
        max_pages: int,
        request_interval: float,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        all_rows: list[dict[str, Any]] = []
        raw_pages: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            paged = dict(params)
            paged.update({"page": page, "page_size": page_size})
            response = None
            for attempt in range(2):
                try:
                    response = self._request_json(paged, paged, endpoint=endpoint)
                    break
                except QianchuanAPIError as exc:
                    if exc.code in (40000, 40100, 50000) and attempt == 0:
                        time.sleep(3.0)
                        continue
                    raise
            if response is None:
                raise QianchuanAPIError("千川接口反复限流，暂时无法获取计划数据", code=40100)
            raw_pages.append(response)
            rows = self._extract_rows(response)
            all_rows.extend(rows)
            data = response.get("data") or {}
            page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
            total_page = page_info.get("total_page") or page_info.get("totalPage")
            if total_page is not None and page >= int(total_page):
                break
            if len(rows) < page_size:
                break
            if request_interval:
                time.sleep(request_interval)
        return all_rows, raw_pages

    def fetch_campaigns(self, advertiser_id: str) -> list[dict[str, Any]]:
        config = self.campaigns
        endpoint = str(config.get("listEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return []
        params: dict[str, Any] = {"advertiser_id": advertiser_id}
        filtering = config.get("filtering") or {}
        if filtering:
            params["filtering"] = json.dumps(filtering, ensure_ascii=False)
        params.update(config.get("extraParams") or {})
        rows, _raw = self._fetch_campaign_pages(
            endpoint=endpoint,
            params=params,
            page_size=max(1, min(100, int(config.get("pageSize", DEFAULT_PAGE_SIZE)))),
            max_pages=max(1, int(config.get("maxPages", 20))),
            request_interval=max(0.0, float(config.get("requestIntervalSeconds", 0.25))),
        )
        return normalize_campaign_plans(
            rows,
            config.get("fieldMap", DEFAULT_CAMPAIGN_CONFIG["fieldMap"]),
            config.get("statusMap", DEFAULT_CAMPAIGN_CONFIG["statusMap"]),
        )

    def fetch_campaign_report(
        self,
        advertiser_id: str,
        campaign_ids: list[str],
        start_date: str,
        end_date: str,
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], list[dict[str, Any]]]:
        config = self.campaigns
        endpoint = str(config.get("reportEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return {}, {}, []
        filtering = copy.deepcopy(config.get("filtering") or {})
        if campaign_ids:
            filtering[str(config.get("campaignIdFilterKey") or "campaign_ids")] = campaign_ids
        params: dict[str, Any] = {
            "advertiser_id": advertiser_id,
            "start_date": start_date,
            "end_date": end_date,
            "fields": json.dumps(config.get("fields", DEFAULT_FIELDS), ensure_ascii=False),
        }
        if filtering:
            params["filtering"] = json.dumps(filtering, ensure_ascii=False)
        params.update(config.get("extraParams") or {})
        rows, raw_pages = self._fetch_campaign_pages(
            endpoint=endpoint,
            params=params,
            page_size=max(1, min(100, int(config.get("pageSize", DEFAULT_PAGE_SIZE)))),
            max_pages=max(1, int(config.get("maxPages", 20))),
            request_interval=max(0.0, float(config.get("requestIntervalSeconds", 0.25))),
        )
        by_campaign, names = normalize_campaign_daily_rows(
            rows,
            config.get("fieldMap", DEFAULT_CAMPAIGN_CONFIG["fieldMap"]),
            start_date,
            end_date,
        )
        return by_campaign, names, raw_pages

    def fetch_campaign_materials(
        self,
        advertiser_id: str,
        campaign_ids: list[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, list[dict[str, Any]]]:
        config = self.campaigns
        endpoint = str(config.get("materialsEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return {}
        filtering = copy.deepcopy(config.get("filtering") or {})
        if campaign_ids:
            filtering[str(config.get("campaignIdFilterKey") or "campaign_ids")] = campaign_ids
        fields = config.get("materialFields") or config.get("fields", DEFAULT_FIELDS)
        params: dict[str, Any] = {
            "advertiser_id": advertiser_id,
            "start_date": start_date,
            "end_date": end_date,
            "fields": json.dumps(fields, ensure_ascii=False),
        }
        if filtering:
            params["filtering"] = json.dumps(filtering, ensure_ascii=False)
        params.update(config.get("extraParams") or {})
        rows, _raw = self._fetch_campaign_pages(
            endpoint=endpoint,
            params=params,
            page_size=max(1, min(100, int(config.get("pageSize", DEFAULT_PAGE_SIZE)))),
            max_pages=max(1, int(config.get("maxPages", 20))),
            request_interval=max(0.0, float(config.get("requestIntervalSeconds", 0.25))),
        )
        return normalize_campaign_materials(
            rows,
            config.get("fieldMap", DEFAULT_CAMPAIGN_CONFIG["fieldMap"]),
        )

    def _campaign_money(self, value: Any) -> float:
        number = to_number(value)
        if number is None:
            return 0.0
        divisor = float(self.campaigns.get("moneyDivisor") or 1)
        return round(number / divisor, 2) if divisor else number

    def fetch_uni_promotion_plans_for_range(
        self,
        advertiser_id: str,
        start_time: str,
        end_time: str,
        marketing_goal: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        config = self.campaigns
        endpoint = str(config.get("listEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return [], []
        filtering = copy.deepcopy(config.get("filtering") or {})
        goal = marketing_goal or config.get("marketingGoal") or "LIVE_PROM_GOODS"
        if goal == "VIDEO_PROM_GOODS":
            filtering["status"] = filtering.get("status") or "ALL_INCLUDE_DELETED"
        else:
            filtering = {}
        params: dict[str, Any] = {
            "advertiser_id": advertiser_id,
            "start_time": start_time,
            "end_time": end_time,
            "marketing_goal": goal,
            "filtering": json.dumps(filtering, ensure_ascii=False),
            "fields": json.dumps(config.get("fields", DEFAULT_CAMPAIGN_CONFIG["fields"]), ensure_ascii=False),
            "adlab_scene": config.get("adlabScene") or "UNI_PROJECT",
        }
        params.update(config.get("extraParams") or {})
        rows, raw_pages = self._fetch_campaign_pages(
            endpoint=endpoint,
            params=params,
            page_size=max(10, min(100, int(config.get("pageSize", DEFAULT_PAGE_SIZE)))),
            max_pages=max(1, int(config.get("maxPages", 20))),
            request_interval=max(0.0, float(config.get("requestIntervalSeconds", 0.25))),
        )
        return normalize_uni_promotion_plans(
            rows,
            config.get("statusMap", DEFAULT_CAMPAIGN_CONFIG["statusMap"]),
        ), raw_pages

    def fetch_uni_promotion_daily(
        self,
        advertiser_id: str,
        start_date: str,
        end_date: str,
        cached_plans: list[dict[str, Any]] | None = None,
        refresh_days: int = 2,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        config = self.campaigns
        history_days = max(1, min(180, int(config.get("historyDays", 30))))
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if (end - start).days + 1 > history_days:
            start = end - timedelta(days=history_days - 1)
        plans_by_id: dict[str, dict[str, Any]] = {}
        for cached in cached_plans or []:
            if not isinstance(cached, dict) or not cached.get("id"):
                continue
            copy_plan = copy.deepcopy(cached)
            copy_plan.pop("stats", None)
            copy_plan.setdefault("data", [])
            plans_by_id[str(copy_plan["id"])] = copy_plan
        raw_pages: list[dict[str, Any]] = []
        interval = max(0.0, float(config.get("requestIntervalSeconds", 0.8)))

        try:
            aggregate_plans, aggregate_raw = self.fetch_uni_promotion_plans_for_range(
                advertiser_id,
                f"{start.isoformat()} 00:00:00",
                f"{end.isoformat()} 23:59:59",
            )
            raw_pages.extend(aggregate_raw)
            for plan in aggregate_plans:
                stats = plan.pop("stats", {}) or {}
                existing = plans_by_id.setdefault(plan["id"], plan)
                existing["name"] = plan["name"] or existing.get("name")
                existing["status"] = plan["status"] or existing.get("status")
                existing["rawStatus"] = plan.get("rawStatus") or existing.get("rawStatus")
                existing["roomInfo"] = plan.get("roomInfo") or existing.get("roomInfo")
                existing.setdefault("data", [])
                existing["period"] = {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "spend": self._campaign_money(stats.get("stat_cost")),
                    "gmv": self._campaign_money(stats.get("total_pay_order_gmv_for_roi2")),
                    "orders": to_number(stats.get("total_pay_order_count_for_roi2")) or 0.0,
                }
        except QianchuanAPIError:
            pass

        current = end
        refresh_start = end - timedelta(days=max(0, refresh_days) - 1)
        while current >= start:
            day = current.isoformat()
            cached_has_day = any(
                any(str(row.get("date"))[:10] == day for row in plan.get("data") or [])
                for plan in plans_by_id.values()
            )
            if cached_has_day and current < refresh_start:
                current -= timedelta(days=1)
                continue
            try:
                plans, raw = self.fetch_uni_promotion_plans_for_range(
                    advertiser_id,
                    f"{day} 00:00:00",
                    f"{day} 23:59:59",
                )
            except QianchuanAPIError as exc:
                if exc.code == 40100:
                    break
                raise
            raw_pages.extend(raw)
            for plan in plans:
                stats = plan.pop("stats", {}) or {}
                existing = plans_by_id.setdefault(plan["id"], plan)
                existing["name"] = plan["name"] or existing.get("name")
                existing["status"] = plan["status"] or existing.get("status")
                existing["rawStatus"] = plan.get("rawStatus") or existing.get("rawStatus")
                existing["roomInfo"] = plan.get("roomInfo") or existing.get("roomInfo")
                existing["data"] = [
                    row for row in existing.get("data", [])
                    if str(row.get("date"))[:10] != day
                ]
                existing["data"].append(
                    {
                        "date": day,
                        "spend": self._campaign_money(stats.get("stat_cost")),
                        "gmv": self._campaign_money(stats.get("total_pay_order_gmv_for_roi2")),
                        "orders": to_number(stats.get("total_pay_order_count_for_roi2")) or 0.0,
                    }
                )
            if interval:
                time.sleep(interval)
            current -= timedelta(days=1)

        for plan in plans_by_id.values():
            plan["data"].sort(key=lambda row: row["date"])
            period = plan.get("period")
            if not period:
                continue
            daily_spend = sum(row.get("spend", 0) for row in plan["data"])
            daily_orders = sum(row.get("orders", 0) for row in plan["data"])
            mismatch = (
                not plan["data"]
                or abs(daily_spend - period["spend"]) > max(2.0, period["spend"] * 0.12)
                or abs(daily_orders - period["orders"]) > max(1.0, period["orders"] * 0.12)
            )
            if mismatch:
                plan["data"] = [{
                    "date": end.isoformat(),
                    "spend": period["spend"],
                    "gmv": period["gmv"],
                    "orders": period["orders"],
                }]
                plan["aggregateOnly"] = True
            else:
                plan["aggregateOnly"] = False
        return list(plans_by_id.values()), raw_pages

    def fetch_aweme_daily(
        self,
        advertiser_id: str,
        aweme_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        metrics = [
            "stat_cost",
            "total_pay_order_gmv_for_roi2",
            "total_pay_order_count_for_roi2",
            "total_cost_per_pay_order_for_roi2",
            "total_prepay_and_pay_order_roi2",
        ]
        params = {
            "advertiser_id": advertiser_id,
            "aweme_id": aweme_id,
            "marketing_goal": "LIVE_PROM_GOODS",
            "start_time": f"{start_date} 00:00:00",
            "end_time": f"{end_date} 23:59:59",
            "metrics": json.dumps(metrics, ensure_ascii=False),
            "dimension": "TIME_GRANULARITY_DAILY",
            "page": 1,
            "page_size": 100,
        }
        response = self._request_json(
            params,
            {},
            endpoint="/open_api/v1.0/qianchuan/report/uni_promotion/dimension_data/author/get/",
        )
        rows = (response.get("data") or {}).get("list") or []
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_date = str(row.get("stat_datetime") or "")[:10]
            if row_date < start_date or row_date > end_date:
                continue
            result.append(
                {
                    "date": row_date,
                    "spend": to_number(row.get("stat_cost")) or 0.0,
                    "gmv": to_number(row.get("total_pay_order_gmv_for_roi2")) or 0.0,
                    "orders": to_number(row.get("total_pay_order_count_for_roi2")) or 0.0,
                }
            )
        return sorted(result, key=lambda item: item["date"])

    def fetch_uni_promotion_materials(
        self,
        advertiser_id: str,
        plan_id: str,
        start_date: str,
        end_date: str,
        material_type: str | None = None,
        with_meta: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        config = self.campaigns
        endpoint = str(config.get("materialsEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return []
        material_type = material_type or config.get("materialType") or "VIDEO"
        material_fields = (
            config.get("liveRoomFields", DEFAULT_CAMPAIGN_CONFIG["liveRoomFields"])
            if material_type == "LIVE_ROOM"
            else config.get("materialFields", DEFAULT_CAMPAIGN_CONFIG["materialFields"])
        )
        params: dict[str, Any] = {
            "advertiser_id": advertiser_id,
            "ad_id": plan_id,
            "filtering": json.dumps({"material_type": material_type}, ensure_ascii=False),
            "start_date": start_date,
            "end_date": end_date,
            "fields": json.dumps(material_fields, ensure_ascii=False),
            "order_type": "DESC",
            "order_field": "stat_cost_for_roi2",
        }
        page_size = max(10, min(100, int(config.get("pageSize", DEFAULT_PAGE_SIZE))))
        max_pages = max(1, int(config.get("materialMaxPages", config.get("maxPages", 20))))
        request_interval = max(0.0, float(config.get("requestIntervalSeconds", 0.25)))
        rows, raw_pages = self._fetch_campaign_pages(
            endpoint=endpoint,
            params=params,
            page_size=page_size,
            max_pages=max_pages,
            request_interval=request_interval,
        )

        def normalize_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            by_id: dict[str, dict[str, Any]] = {}
            for index, row in enumerate(source_rows):
                if not isinstance(row, dict):
                    continue
                info = row.get("material_info") or {}
                video = info.get("video_material") or {}
                room = info.get("room_material") or {}
                title_material = info.get("title_material") or {}
                image_material = info.get("image_material") or {}
                stats = row.get("stats_info") or {}
                metric_sources = [stats]
                if isinstance(stats, dict):
                    metric_sources.append(stats.get("metrics") or {})
                metric_sources.append(row)

                def material_metric(*keys: str) -> float:
                    for source in metric_sources:
                        if not isinstance(source, dict):
                            continue
                        value = pick_value(source, list(keys))
                        if value is not None and value != "":
                            return to_number(value) or 0.0
                    return 0.0

                material_id = (
                    video.get("material_id")
                    or room.get("material_id")
                    or title_material.get("material_id")
                    or image_material.get("material_id")
                    or f"{plan_id}-material-{index + 1}"
                )
                name = (
                    video.get("title")
                    or title_material.get("title")
                    or room.get("aweme_name")
                    or image_material.get("image_id")
                    or f"素材 {material_id}"
                )
                material_type_raw = str(info.get("material_type") or material_type)
                type_label = {
                    "VIDEO": "视频",
                    "LIVE_ROOM": "直播间画面",
                    "TITLE": "标题",
                    "IMAGE": "图片",
                    "CAROUSEL": "图文",
                }.get(material_type_raw, material_type_raw)
                uploaded_at = normalize_external_datetime(
                    pick_value(
                        row,
                        [
                            "material_info.create_time",
                            "material_info.created_at",
                            "material_info.upload_time",
                            "material_info.video_material.create_time",
                            "material_info.video_material.upload_time",
                            "create_time",
                            "created_at",
                            "upload_time",
                        ],
                    )
                )
                upload_age_days: int | None = None
                if uploaded_at:
                    try:
                        upload_age_days = max(
                            0,
                            (
                                datetime.now(timezone.utc).astimezone().date()
                                - datetime.fromisoformat(
                                    uploaded_at.replace("Z", "+00:00")
                                ).date()
                            ).days,
                        )
                    except ValueError:
                        upload_age_days = None
                by_id[str(material_id)] = {
                    "id": str(material_id),
                    "name": str(name),
                    "type": type_label,
                    "duration": str(video.get("video_duration") or "—"),
                    "spend": material_metric("stat_cost_for_roi2", "stat_cost", "cost", "spend"),
                    "gmv": material_metric(
                        "total_pay_order_gmv_for_roi2", "pay_order_amount", "gmv", "user_pay_amount"
                    ),
                    "orders": material_metric(
                        "total_pay_order_count_for_roi2", "pay_order_count", "order_count", "orders"
                    ),
                    "impressions": material_metric(
                        "live_show_count_for_roi2_v2",
                        "live_show_count_exclude_video_for_roi2",
                        "show_cnt",
                        "impressions",
                    ),
                    "clicks": material_metric(
                        "live_watch_count_for_roi2_v2",
                        "live_watch_count_exclude_video_for_roi2",
                        "click_cnt",
                        "clicks",
                    ),
                    "ctr": material_metric(
                        "live_cvr_rate_for_roi2_v2",
                        "live_cvr_rate_exclude_video_for_roi2",
                        "ctr",
                    ),
                    "completionRate": material_metric(
                        "video_play_finish_rate_for_roi2_v2", "play_over_rate", "completion_rate"
                    ),
                    "dwellTime": material_metric(
                        "video_avg_watch_duration_for_roi2", "average_watch_duration", "dwell_time"
                    ),
                    "persona": {
                        "age": "未获取",
                        "region": "未获取",
                        "gender": "未获取",
                    },
                    "materialStatus": info.get("material_status"),
                    "auditStatus": info.get("audit_status"),
                    "uploadedAt": uploaded_at or "未获取",
                    "uploadAgeDays": upload_age_days,
                    "cover": (video.get("cover_image") or {}).get("image_url"),
                    "videoUrl": video.get("url"),
                }
            return list(by_id.values())

        materials = normalize_rows(rows)
        expected_total = 0
        total_reported = False
        for raw in raw_pages:
            data = raw.get("data") or {}
            page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
            total = page_info.get("total_number") or page_info.get("total_num") or page_info.get("totalNumber")
            if total is not None:
                total_reported = True
                expected_total = max(expected_total, int(total))

        # 同一跑量值并列时，单次分页顺序可能漂移，导致跨页重复并漏项。
        # 当唯一素材数少于接口 total_number 时，用反向排序补拉并仅合并缺失 ID。
        if expected_total > len(materials):
            fallback_params = dict(params)
            fallback_params["order_type"] = "ASC" if str(params.get("order_type")).upper() != "ASC" else "DESC"
            fallback_rows, fallback_pages = self._fetch_campaign_pages(
                endpoint=endpoint,
                params=fallback_params,
                page_size=page_size,
                max_pages=max_pages,
                request_interval=request_interval,
            )
            by_id = {item["id"]: item for item in materials}
            for item in normalize_rows(fallback_rows):
                by_id.setdefault(item["id"], item)
            materials = list(by_id.values())
            for raw in fallback_pages:
                data = raw.get("data") or {}
                page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
                total = page_info.get("total_number") or page_info.get("total_num") or page_info.get("totalNumber")
                if total is not None:
                    total_reported = True
                    expected_total = max(expected_total, int(total))
        unique_count = len(materials)
        missing_count = max(0, expected_total - unique_count) if expected_total else 0
        meta = {
            "materialType": material_type,
            "source": "千川 Open API · 计划素材库",
            "sourceTotal": expected_total,
            "uniqueCount": unique_count,
            "missingCount": missing_count,
            "totalReported": total_reported,
            "complete": bool(
                (total_reported and missing_count == 0)
                or (not total_reported and not rows and bool(pages))
            ),
            "fetchedAt": now_iso(),
        }
        if with_meta:
            return materials, meta
        return materials

    def fetch_uni_promotion_material_report(
        self,
        advertiser_id: str,
        aweme_id: str,
        start_date: str,
        end_date: str,
        material_type: str = "VIDEO",
        with_meta: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch the account-level material report for one Douyin account."""
        config = self.campaigns
        endpoint = str(config.get("materialReportEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return []
        is_live = str(material_type).upper() == "LIVE_ROOM"
        data_topic = (
            "SITE_PROMOTION_POST_DATA_LIVE"
            if is_live
            else "SITE_PROMOTION_POST_DATA_VIDEO"
        )
        dimensions = config.get(
            "materialReportLiveDimensions" if is_live else "materialReportDimensions",
            DEFAULT_CAMPAIGN_CONFIG[
                "materialReportLiveDimensions" if is_live else "materialReportDimensions"
            ],
        )
        metrics = config.get(
            "materialReportLiveMetrics" if is_live else "materialReportMetrics",
            DEFAULT_CAMPAIGN_CONFIG[
                "materialReportLiveMetrics" if is_live else "materialReportMetrics"
            ],
        )
        smart_bid_types = config.get("materialReportSmartBidTypes") or ["0"]
        ecp_app_ids = config.get("materialReportEcpAppIds") or ["1"]
        page_size = max(10, min(200, int(config.get("materialReportPageSize", 200))))
        max_pages = max(1, int(config.get("materialReportMaxPages", 100)))
        interval = max(0.0, float(config.get("requestIntervalSeconds", 0.35)))
        raw_rows: list[dict[str, Any]] = []
        errors: list[QianchuanAPIError] = []
        successful_queries = 0
        query_meta: list[dict[str, Any]] = []
        for smart_bid_type in smart_bid_types:
            for ecp_app_id in ecp_app_ids:
                filters = [
                    {"field": "anchor_id", "operator": 7, "values": [str(aweme_id)]},
                    {
                        "field": "aggregate_smart_bid_type",
                        "operator": 7,
                        "values": [str(smart_bid_type)],
                    },
                    {"field": "ecp_app_id", "operator": 7, "values": [str(ecp_app_id)]},
                ]
                params = {
                    "advertiser_id": advertiser_id,
                    "data_topic": data_topic,
                    "dimensions": json.dumps(dimensions, ensure_ascii=False),
                    "metrics": json.dumps(metrics, ensure_ascii=False),
                    "filters": json.dumps(filters, ensure_ascii=False),
                    "start_time": f"{start_date} 00:00:00",
                    "end_time": f"{end_date} 23:59:59",
                    "order_by": json.dumps(
                        [
                            {
                                "type": 2,
                                "field": (
                                    "stat_cost_for_roi2_fork"
                                    if is_live
                                    else "stat_cost_for_roi2"
                                ),
                            }
                        ],
                        ensure_ascii=False,
                    ),
                }
                try:
                    rows, pages = self._fetch_campaign_pages(
                        endpoint=endpoint,
                        params=params,
                        page_size=page_size,
                        max_pages=max_pages,
                        request_interval=interval,
                    )
                    raw_rows.extend(rows)
                    successful_queries += 1
                    expected_total = 0
                    total_reported = False
                    for raw in pages:
                        data = raw.get("data") or {}
                        page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
                        total = (
                            page_info.get("total_number")
                            or page_info.get("total_num")
                            or page_info.get("totalNumber")
                        )
                        if total is not None:
                            total_reported = True
                            expected_total = max(expected_total, int(total))
                    missing_count = max(0, expected_total - len(rows))
                    query_meta.append(
                        {
                            "smartBidType": str(smart_bid_type),
                            "ecpAppId": str(ecp_app_id),
                            "sourceTotal": expected_total,
                            "rowCount": len(rows),
                            "missingCount": missing_count,
                            "totalReported": total_reported,
                            "complete": bool(
                                (total_reported and missing_count == 0)
                                or (not total_reported and not rows and bool(pages))
                            ),
                        }
                    )
                except QianchuanAPIError as exc:
                    errors.append(exc)
                    query_meta.append(
                        {
                            "smartBidType": str(smart_bid_type),
                            "ecpAppId": str(ecp_app_id),
                            "sourceTotal": 0,
                            "rowCount": 0,
                            "missingCount": 0,
                            "totalReported": False,
                            "complete": False,
                            "error": str(exc),
                        }
                    )
        if not successful_queries and errors:
            raise errors[0]
        materials = normalize_uni_promotion_material_report(
            raw_rows,
            aweme_id,
            "LIVE_ROOM" if is_live else "VIDEO",
            {
                "start": start_date,
                "end": end_date,
                "days": (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1,
            },
        )
        meta = {
            "materialType": "LIVE_ROOM" if is_live else "VIDEO",
            "source": "千川 Open API · 素材维度报表",
            "queries": query_meta,
            "rawRowCount": len(raw_rows),
            "uniqueCount": len(materials),
            "complete": bool(query_meta)
            and all(bool(item.get("complete")) for item in query_meta),
            "fetchedAt": now_iso(),
        }
        if with_meta:
            return materials, meta
        return materials

    def fetch_qianchuan_video_library(
        self,
        advertiser_id: str,
        with_meta: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch the account's official video library, including upload time."""
        config = self.campaigns
        endpoint = str(config.get("videoLibraryEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return ([], {
                "source": "千川 Open API · 素材库视频",
                "complete": False,
                "error": "素材库视频接口未配置",
            }) if with_meta else []
        page_size = max(
            10,
            min(100, int(config.get("videoLibraryPageSize", 100))),
        )
        max_pages = max(1, int(config.get("videoLibraryMaxPages", 100)))
        interval = max(0.0, float(config.get("requestIntervalSeconds", 0.25)))
        rows, pages = self._fetch_campaign_pages(
            endpoint=endpoint,
            params={"advertiser_id": str(advertiser_id)},
            page_size=page_size,
            max_pages=max_pages,
            request_interval=interval,
        )
        materials = normalize_qianchuan_video_library(rows)
        expected_total = 0
        total_reported = False
        for raw in pages:
            data = raw.get("data") or {}
            page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
            total = (
                page_info.get("total_number")
                or page_info.get("total_num")
                or page_info.get("totalNumber")
            )
            if total is not None:
                total_reported = True
                expected_total = max(expected_total, int(total))
        upload_time_count = sum(
            1 for item in materials if item.get("uploadedAt") != "未获取"
        )
        missing_count = max(0, expected_total - len(materials)) if expected_total else 0
        meta = {
            "source": "千川 Open API · 素材库视频",
            "sourceTotal": expected_total,
            "uniqueCount": len(materials),
            "missingCount": missing_count,
            "uploadTimeCount": upload_time_count,
            "uploadTimeMissingCount": max(0, len(materials) - upload_time_count),
            "complete": bool(
                (total_reported and missing_count == 0)
                or (not total_reported and not rows and bool(pages))
            ),
            "fetchedAt": now_iso(),
        }
        if with_meta:
            return materials, meta
        return materials

    def _live_money(self, value: Any) -> float:
        number = to_number(value)
        if number is None:
            return 0.0
        divisor = float(self.live.get("moneyDivisor") or 1)
        return round(number / divisor, 2) if divisor else number

    def fetch_live_rooms(self, advertiser_id: str, aweme_id: str, room_date: str) -> list[dict[str, Any]]:
        config = self.live
        endpoint = str(config.get("roomListEndpoint") or "").strip()
        if not endpoint or not config.get("enabled", True):
            return []
        params = {
            "advertiser_id": advertiser_id,
            "aweme_id": aweme_id,
            "date_time": room_date,
            "room_status": "ALL",
            "ad_status": "ALL",
            "fields": json.dumps(config.get("roomFields", DEFAULT_LIVE_CONFIG["roomFields"]), ensure_ascii=False),
            "page": 1,
            "page_size": 20,
        }
        response = self._request_json(params, {}, endpoint=endpoint)
        data = response.get("data") or {}
        rows = data.get("room_list") if isinstance(data, dict) else None
        return [row for row in (rows or []) if isinstance(row, dict)]

    def fetch_live_flow(self, advertiser_id: str, room_id: str, flow_source: str) -> dict[str, Any]:
        config = self.live
        endpoint = str(config.get("flowEndpoint") or "").strip()
        if not endpoint:
            return {}
        response = self._request_json(
            {"advertiser_id": advertiser_id, "room_id": room_id, "flow_source": flow_source},
            {},
            endpoint=endpoint,
        )
        data = response.get("data") or {}
        return data if isinstance(data, dict) else {}

    def fetch_live_users(self, advertiser_id: str, room_id: str, action_event: str) -> dict[str, Any]:
        config = self.live
        endpoint = str(config.get("userEndpoint") or "").strip()
        if not endpoint:
            return {}
        response = self._request_json(
            {
                "advertiser_id": advertiser_id,
                "room_id": room_id,
                "action_event": action_event,
                "dimension": json.dumps(["CITY", "GENDER", "AGE"]),
                "flow_source": "PC",
            },
            {},
            endpoint=endpoint,
        )
        data = response.get("data") or {}
        return data if isinstance(data, dict) else {}

    def fetch_live_products(self, advertiser_id: str, room_id: str) -> list[dict[str, Any]]:
        config = self.live
        endpoint = str(config.get("productEndpoint") or "").strip()
        if not endpoint:
            return []
        response = self._request_json(
            {
                "advertiser_id": advertiser_id,
                "room_id": room_id,
                "fields": json.dumps(
                    [
                        "live_cost_per_product",
                        "live_product_price",
                        "live_product_Inventory",
                        "live_pay_order_gmv_alias",
                        "luban_live_pay_order_gmv",
                        "live_pay_order_count_alias",
                        "luban_live_pay_order_count",
                        "live_pay_order_roi_per_product",
                        "product_click_pay_ucnt_ratio",
                    ]
                ),
                "explain_status": "ALL",
            },
            {},
            endpoint=endpoint,
        )
        data = response.get("data") or {}
        rows = data.get("list") if isinstance(data, dict) else None
        products = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            products.append(
                {
                    "id": str(row.get("productId") or row.get("product_id") or ""),
                    "name": str(row.get("title") or row.get("product_name") or ""),
                    "image": row.get("img_url") or row.get("product_image"),
                    "explainStatus": row.get("explain_status"),
                    "price": self._live_money(row.get("live_product_price")),
                    "stock": to_number(row.get("live_product_Inventory")),
                    "cost": self._live_money(row.get("live_cost_per_product")),
                    "gmv": self._live_money(row.get("live_pay_order_gmv_alias")),
                    "orders": to_number(row.get("live_pay_order_count_alias")) or 0,
                    "roi": to_number(row.get("live_pay_order_roi_per_product")),
                }
            )
        return products


def make_seed_snapshot() -> dict[str, Any]:
    cutoff = SEED_ROWS[-1]["date"]
    return {
        "revision": 1,
        "syncedAt": None,
        "lastAttemptAt": None,
        "dataCutoff": cutoff,
        "syncStatus": "degraded",
        "mode": "seed",
        "historyDays": HISTORY_DAYS,
        "accounts": [
            {
                **DEFAULT_ACCOUNT,
                "qianchuanId": DEFAULT_ACCOUNT["advertiserId"],
                "status": "待同步",
                "source": "千川全域推广 · 已确认快照",
                "dataCutoff": cutoff,
                "data": copy.deepcopy(SEED_ROWS),
                "raw": [],
                "plans": [],
                "campaignSource": "计划接口待配置",
            }
        ],
        "errors": [
            {
                "scope": "bootstrap",
                "code": "seed_snapshot",
                "message": "当前展示已确认的本地 7 天快照；尚未取得千川访问凭证。",
            }
        ],
    }


def account_last_date(account: dict[str, Any]) -> str | None:
    rows = account.get("data") or []
    dates = [str(row.get("date")) for row in rows if isinstance(row, dict) and row.get("date")]
    return max(dates) if dates else None


class DashboardStore:
    def __init__(self, snapshot_path: Path = SNAPSHOT_PATH):
        self.snapshot_path = snapshot_path
        self.lock = threading.RLock()
        self.sync_lock = threading.Lock()
        self.sync_state_lock = threading.Lock()
        self.live_lock = threading.Lock()
        self.mcp_lock = threading.Lock()
        self.mcp_client: QianchuanMCPClient | None = None
        self.mcp_client_url = ""
        self.mcp_last_error: str | None = None
        self.live_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.live_trade_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.campaign_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.five_dimension_inflight: set[str] = set()
        self.five_dimension_retry_after: dict[str, float] = {}
        self.five_dimension_last_error: dict[str, str] = {}
        self.live_screen_path = snapshot_path.parent / LIVE_SCREEN_STATE_PATH.name
        self.live_history_path = snapshot_path.parent / LIVE_SCREEN_HISTORY_PATH.name
        self.live_history_backup_path = self.live_history_path.with_suffix(".bak.json")
        self.live_history_cache_lock = threading.RLock()
        self.live_history_memory: dict[str, Any] | None = None
        self.live_history_mtime_ns: int | None = None
        self.live_history_last_error: str | None = None
        self.report_cache_seconds = 120.0
        self.aweme_cache_seconds = 120.0
        self.realtime_cache_seconds = 5.0
        self.include_today = True
        self.poll_interval_seconds = DEFAULT_SYNC_INTERVAL_SECONDS
        self.full_sync_interval_seconds = 180
        self.last_report_at = 0.0
        self.backoff_until = 0.0
        self.backoff_hits = 0
        self.last_sync_at: str | None = None
        self.sync_running = False
        self.sync_kind: str | None = None
        self.sync_started_at: str | None = None
        self.sync_finished_at: str | None = None
        self.last_sync_error: str | None = None
        self.snapshot = self._load_snapshot()

    def _load_snapshot(self) -> dict[str, Any]:
        try:
            loaded = load_json(self.snapshot_path, make_seed_snapshot())
            if isinstance(loaded, dict) and isinstance(loaded.get("accounts"), list):
                return loaded
        except ValueError:
            pass
        snapshot = make_seed_snapshot()
        atomic_write_json(self.snapshot_path, snapshot)
        return snapshot

    def dashboard(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.snapshot)

    def _get_mcp_client(self) -> QianchuanMCPClient | None:
        config = load_mcp_config()
        if not config.get("enabled") or not config.get("url"):
            return None
        url = str(config.get("url"))
        with self.mcp_lock:
            if self.mcp_client is None or self.mcp_client_url != url:
                self.mcp_client = QianchuanMCPClient(config)
                self.mcp_client_url = url
                self.mcp_last_error = None
            return self.mcp_client

    def mcp_tools(self) -> list[dict[str, Any]]:
        client = self._get_mcp_client()
        if client is None:
            return []
        try:
            tools = client.list_tools()
            with self.mcp_lock:
                self.mcp_last_error = None
            return [
                {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "inputSchema": tool.get("inputSchema"),
                }
                for tool in tools
            ]
        except QianchuanMCPError as exc:
            with self.mcp_lock:
                self.mcp_last_error = str(exc)
            raise

    def mcp_raw_live_report(
        self,
        advertiser_id: str,
        aweme_id: str,
        report_date: str,
    ) -> dict[str, Any]:
        """Call the live report tool without normalizing its response."""
        client = self._get_mcp_client()
        if client is None:
            raise QianchuanMCPError("未配置千川 MCP")
        tool = next(
            (
                item
                for item in client.list_tools()
                if str(item.get("name") or "") == QianchuanMCPClient.LIVE_REPORT_TOOL
            ),
            None,
        )
        if tool is None:
            raise QianchuanMCPError(
                f"MCP 未开放工具 {QianchuanMCPClient.LIVE_REPORT_TOOL}"
            )
        arguments = client._tool_arguments(
            tool,
            str(advertiser_id),
            str(aweme_id),
            str(report_date),
        )
        if arguments is None:
            return {
                "ok": False,
                "tool": QianchuanMCPClient.LIVE_REPORT_TOOL,
                "toolSchema": tool.get("inputSchema"),
                "error": "工具参数 schema 与当前构造参数不兼容，尚未发起调用",
            }
        raw_response = client.call_tool_raw(
            QianchuanMCPClient.LIVE_REPORT_TOOL,
            arguments,
        )
        return {
            "ok": True,
            "tool": QianchuanMCPClient.LIVE_REPORT_TOOL,
            "toolSchema": tool.get("inputSchema"),
            "arguments": arguments,
            "rawJsonRpcResponse": raw_response,
        }

    def _build_account_shell(
        self,
        config_account: dict[str, Any],
        previous_account: dict[str, Any] | None,
    ) -> dict[str, Any]:
        previous_account = previous_account or {}
        data = copy.deepcopy(previous_account.get("data") or [])
        last_date = max(
            [str(row.get("date")) for row in data if isinstance(row, dict) and row.get("date")],
            default=None,
        )
        return {
            "id": config_account["id"],
            "qianchuanId": config_account["advertiserId"],
            "advertiserId": config_account["advertiserId"],
            "name": config_account.get("name") or f"千川账号 {config_account['advertiserId']}",
            "handle": config_account.get("handle") or "待同步抖音号信息",
            "avatar": config_account.get("avatar") or config_account["advertiserId"][-1:],
            "color": config_account.get("color") or "#0b7a58",
            "status": previous_account.get("status") or "待同步",
            "source": previous_account.get("source") or "千川全域推广",
            "dataCutoff": last_date,
            "data": data,
            "raw": copy.deepcopy(previous_account.get("raw") or []),
            "plans": copy.deepcopy(previous_account.get("plans") or []),
            "awemeAccounts": copy.deepcopy(config_account.get("awemeAccounts") or []),
            "awemes": copy.deepcopy(previous_account.get("awemes") or []),
            "materialSyncAt": previous_account.get("materialSyncAt"),
            "materialWindow": copy.deepcopy(previous_account.get("materialWindow") or {}),
            "materialSource": previous_account.get("materialSource"),
            "materialMcpStatus": previous_account.get("materialMcpStatus"),
            "materialAudit": copy.deepcopy(previous_account.get("materialAudit") or {}),
            "materialReportAudit": copy.deepcopy(
                previous_account.get("materialReportAudit") or {}
            ),
        }

    @staticmethod
    def _merge_official_material_report(
        plans: list[dict[str, Any]],
        report_rows: list[dict[str, Any]],
        window: dict[str, Any],
    ) -> int:
        """Overlay official run metrics without discarding material metadata."""
        if not report_rows:
            return 0
        report_by_id = {
            str(item.get("id")): item
            for item in report_rows
            if isinstance(item, dict) and item.get("id")
        }
        matched_ids: set[str] = set()
        for plan in plans:
            materials = [item for item in plan.get("materials") or [] if isinstance(item, dict)]
            for material in materials:
                report = report_by_id.get(str(material.get("id")))
                if not report and str(material.get("type")) == "直播间画面":
                    report = next(
                        (
                            item for item in report_rows
                            if str(item.get("type")) == "直播间画面"
                            and str(item.get("name")) == str(material.get("name"))
                        ),
                        None,
                    )
                if not report:
                    continue
                report_copy = copy.deepcopy(report)
                for key, value in report_copy.items():
                    if (
                        key in {
                            "duration",
                            "cover",
                            "videoUrl",
                            "materialStatus",
                            "auditStatus",
                        }
                        and material.get(key) not in (None, "", "未获取")
                    ):
                        continue
                    if (
                        key
                        in {
                            "duration",
                            "cover",
                            "videoUrl",
                            "uploadedAt",
                            "uploadAgeDays",
                            "materialStatus",
                            "auditStatus",
                        }
                        and value in (None, "", "未获取")
                        and material.get(key) not in (None, "", "未获取")
                    ):
                        continue
                    material[key] = value
                material["reportId"] = report.get("id")
                material["planId"] = plan.get("id")
                material["planName"] = plan.get("name")
                material["reportMatched"] = True
                apply_material_delete_policy(material)
                matched_ids.add(str(report.get("id")))
            deduped: dict[str, dict[str, Any]] = {}
            for material in materials:
                material_id = str(material.get("id"))
                existing = deduped.get(material_id)
                if not existing or (
                    to_number(material.get("spend")) or 0.0
                ) > (to_number(existing.get("spend")) or 0.0):
                    deduped[material_id] = material
            plan["materials"] = list(deduped.values())
            plan["materialsWindow"] = copy.deepcopy(window)
            plan["materialReportSyncedAt"] = now_iso()

        unmatched = [
            item for material_id, item in report_by_id.items()
            if material_id not in matched_ids
        ]
        if unmatched and plans:
            fallback = max(
                plans,
                key=lambda plan: sum(
                    to_number(row.get("spend")) or 0.0
                    for row in plan.get("data") or []
                    if isinstance(row, dict)
                ),
            )
            fallback["materialReportUnmatchedCount"] = len(unmatched)
            fallback["materialReportUnmatchedIds"] = [
                str(item.get("id"))
                for item in unmatched[:100]
                if isinstance(item, dict) and item.get("id")
            ]
            fallback["materialReportUnmatchedNote"] = (
                "历史素材报表有记录，但当前计划素材库已不存在；"
                "按千川当前素材库执行删除同步，不重新加入全量表"
            )
        return len(matched_ids)

    @staticmethod
    def _merge_video_library_metadata(
        plans: list[dict[str, Any]],
        library_rows: list[dict[str, Any]],
    ) -> int:
        """Overlay official video upload time and static metadata by material ID."""
        library_by_id = {
            str(item.get("id")): item
            for item in library_rows
            if isinstance(item, dict) and item.get("id")
        }
        matched: set[str] = set()
        for plan in plans:
            for material in plan.get("materials") or []:
                if not isinstance(material, dict):
                    continue
                material_id = str(material.get("id") or "")
                metadata = library_by_id.get(material_id)
                if not metadata:
                    apply_material_delete_policy(material)
                    continue
                if metadata.get("uploadedAt") not in (None, "", "未获取"):
                    material["uploadedAt"] = metadata["uploadedAt"]
                    material["uploadAgeDays"] = metadata.get("uploadAgeDays")
                    material["uploadTimeSource"] = metadata.get("uploadTimeSource")
                for key in ("videoUrl", "cover"):
                    if metadata.get(key) and material.get(key) in (None, "", "未获取"):
                        material[key] = metadata[key]
                if metadata.get("duration") not in (None, "") and material.get("duration") in (
                    None,
                    "",
                    "—",
                ):
                    material["duration"] = metadata["duration"]
                apply_material_delete_policy(material)
                matched.add(material_id)
        return len(matched)

    @staticmethod
    def _merge_realtime_plan_rows(
        plans: list[dict[str, Any]],
        realtime_plans: list[dict[str, Any]],
        realtime_date: str,
        money_divisor: float,
    ) -> int:
        """Overlay today's cumulative plan metrics by plan ID."""
        if not realtime_plans:
            return 0
        plans_by_id = {
            str(plan.get("id")): plan
            for plan in plans
            if isinstance(plan, dict) and plan.get("id")
        }
        divisor = money_divisor if money_divisor > 0 else 1.0
        updated = 0
        for realtime_plan in realtime_plans:
            if not isinstance(realtime_plan, dict) or not realtime_plan.get("id"):
                continue
            plan_id = str(realtime_plan["id"])
            plan = plans_by_id.get(plan_id)
            if plan is None:
                plan = copy.deepcopy(realtime_plan)
                plan["data"] = []
                plans.append(plan)
                plans_by_id[plan_id] = plan
            name = realtime_plan.get("name")
            if name:
                plan["name"] = name
            for key in ("status", "rawStatus", "roomInfo", "marketingGoal", "adlabScene"):
                value = realtime_plan.get(key)
                if value not in (None, "", []):
                    plan[key] = copy.deepcopy(value)
            stats = realtime_plan.get("stats") or {}
            row = {
                "date": realtime_date,
                "spend": round((to_number(stats.get("stat_cost")) or 0.0) / divisor, 2),
                "gmv": round(
                    (to_number(stats.get("total_pay_order_gmv_for_roi2")) or 0.0)
                    / divisor,
                    2,
                ),
                "orders": to_number(stats.get("total_pay_order_count_for_roi2")) or 0.0,
                "realtime": True,
                "syncedAt": now_iso(),
            }
            plan["data"] = upsert_daily_row(plan.get("data") or [], row)
            updated += 1
        plans.sort(
            key=lambda item: sum(
                to_number(day.get("spend")) or 0.0
                for day in item.get("data") or []
                if isinstance(day, dict)
            ),
            reverse=True,
        )
        return updated

    def _sync_account_plans(
        self,
        client: QianchuanClient,
        account: dict[str, Any],
        start_date: str,
        end_date: str,
        errors: list[dict[str, Any]],
        sync_history: bool = True,
        sync_materials: bool = True,
        force_materials: bool = False,
    ) -> bool:
        campaign_config = client.campaigns
        if not campaign_config.get("enabled", True):
            return True
        if not (campaign_config.get("listEndpoint") or campaign_config.get("reportEndpoint")):
            return True
        try:
            if sync_history:
                plans, raw_pages = client.fetch_uni_promotion_daily(
                    account["advertiserId"],
                    start_date,
                    end_date,
                    cached_plans=account.get("plans") or [],
                )
            else:
                plans = copy.deepcopy(account.get("plans") or [])
                raw_pages = []
            realtime_date = date.today().isoformat()
            realtime_plan_ok = False
            realtime_plan_rows = 0
            if self.include_today and end_date < realtime_date:
                try:
                    realtime_plans, realtime_raw = client.fetch_uni_promotion_plans_for_range(
                        account["advertiserId"],
                        f"{realtime_date} 00:00:00",
                        f"{realtime_date} 23:59:59",
                    )
                    raw_pages.extend(realtime_raw)
                    realtime_plan_rows = self._merge_realtime_plan_rows(
                        plans,
                        realtime_plans,
                        realtime_date,
                        float(campaign_config.get("moneyDivisor") or 1),
                    )
                    realtime_plan_ok = True
                    account["realtimePlanSyncedAt"] = now_iso()
                    account["realtimePlanSource"] = "千川全域推广计划接口 · 今日累计"
                    account["realtimePlanRows"] = realtime_plan_rows
                except QianchuanAPIError as exc:
                    errors.append(
                        {
                            "scope": "campaign_realtime",
                            "accountId": account["id"],
                            "advertiserId": account["advertiserId"],
                            "code": "campaign_realtime_failed",
                            "message": f"计划今日累计同步失败：{exc}",
                        }
                    )
            if sync_materials and plans:
                material_limit = (
                    max(0, int(campaign_config.get("materialPlanLimit", 20)))
                    if sync_materials
                    else 0
                )
                material_history_days = max(1, int(campaign_config.get("materialHistoryDays", 7)))
                material_cache_seconds = max(
                    60,
                    int(
                        campaign_config.get(
                            "materialCacheSeconds",
                            max(1, int(campaign_config.get("materialCacheHours", 2))) * 3600,
                        )
                    ),
                )
                material_end_offset_days = max(
                    0, int(campaign_config.get("materialEndOffsetDays", 1))
                )
                material_end_date = date.today() - timedelta(days=material_end_offset_days)
                configured_start = str(
                    campaign_config.get("materialStartDate") or ""
                ).strip()
                try:
                    material_start_date = date.fromisoformat(configured_start)
                except ValueError:
                    material_start_date = material_end_date - timedelta(
                        days=material_history_days - 1
                    )
                if material_start_date > material_end_date:
                    material_start_date = material_end_date
                material_window = {
                    "start": material_start_date.isoformat(),
                    "end": material_end_date.isoformat(),
                    "days": (material_end_date - material_start_date).days + 1,
                }
                material_reconcile_seconds = max(
                    material_cache_seconds,
                    int(campaign_config.get("materialReconcileSeconds", 10800)),
                )
                material_sync_interval_seconds = max(
                    material_cache_seconds,
                    int(campaign_config.get("materialSyncIntervalSeconds", 180)),
                )
                previous_by_id = {
                    str(plan.get("id")): plan
                    for plan in account.get("plans") or []
                    if isinstance(plan, dict) and plan.get("id")
                }
                plans.sort(
                    key=lambda plan: sum(row.get("spend", 0) for row in plan.get("data", [])),
                    reverse=True,
                )
                for plan in plans[:material_limit]:
                    previous_plan = previous_by_id.get(plan["id"])
                    previous_window = (previous_plan or {}).get("materialsWindow") or {}
                    window_matches = (
                        str(previous_window.get("start") or "") == material_window["start"]
                        and str(previous_window.get("end") or "") == material_window["end"]
                    )
                    if (
                        previous_plan
                        and previous_plan.get("materials")
                        and previous_plan.get("materialsSyncedAt")
                        and window_matches
                    ):
                        try:
                            synced_at = datetime.fromisoformat(str(previous_plan["materialsSyncedAt"]))
                            age_seconds = (datetime.now(timezone.utc).astimezone() - synced_at).total_seconds()
                            if age_seconds < material_cache_seconds:
                                plan["materials"] = copy.deepcopy(previous_plan["materials"])
                                plan["materialsSyncedAt"] = previous_plan["materialsSyncedAt"]
                                plan["materialsWindow"] = copy.deepcopy(
                                    previous_plan.get("materialsWindow") or material_window
                                )
                                plan["materialAudit"] = copy.deepcopy(
                                    previous_plan.get("materialAudit") or {}
                                )
                                continue
                        except (TypeError, ValueError):
                            pass
                    try:
                        materials, video_meta = client.fetch_uni_promotion_materials(
                            account["advertiserId"],
                            plan["id"],
                            material_start_date.isoformat(),
                            material_end_date.isoformat(),
                            material_type="VIDEO",
                            with_meta=True,
                        )
                        type_meta = [video_meta]
                        try:
                            live_materials, live_meta = client.fetch_uni_promotion_materials(
                                account["advertiserId"],
                                plan["id"],
                                material_start_date.isoformat(),
                                material_end_date.isoformat(),
                                material_type="LIVE_ROOM",
                                with_meta=True,
                            )
                            materials.extend(live_materials)
                            type_meta.append(live_meta)
                        except QianchuanAPIError as exc:
                            type_meta.append(
                                {
                                    "materialType": "LIVE_ROOM",
                                    "source": "千川 Open API · 计划素材库",
                                    "sourceTotal": 0,
                                    "uniqueCount": 0,
                                    "missingCount": 0,
                                    "totalReported": False,
                                    "complete": False,
                                    "error": str(exc),
                                    "fetchedAt": now_iso(),
                                }
                            )
                        previous_materials = {
                            str(item.get("id")): item
                            for item in (previous_plan or {}).get("materials") or []
                            if isinstance(item, dict) and item.get("id")
                        }
                        metric_keys = (
                            "spend",
                            "gmv",
                            "orders",
                            "impressions",
                            "clicks",
                            "ctr",
                            "completionRate",
                            "dwellTime",
                        )
                        for item in materials:
                            previous_item = previous_materials.get(str(item.get("id")))
                            if not previous_item:
                                continue
                            current_has_metrics = any(
                                (to_number(item.get(key)) or 0.0) > 0
                                for key in ("spend", "gmv", "orders", "impressions", "clicks")
                            )
                            previous_has_metrics = any(
                                (to_number(previous_item.get(key)) or 0.0) > 0
                                for key in ("spend", "gmv", "orders", "impressions", "clicks")
                            )
                            if current_has_metrics or not previous_has_metrics:
                                continue
                            for key in metric_keys:
                                item[key] = copy.deepcopy(previous_item.get(key, item.get(key)))
                            item["materialWindow"] = copy.deepcopy(
                                previous_item.get("materialWindow")
                                or (previous_plan or {}).get("materialsWindow")
                                or material_window
                            )
                            item["cachedMetrics"] = True
                        deduped_materials: dict[str, dict[str, Any]] = {}
                        for item in materials:
                            material_id = str(item.get("id") or "")
                            if not material_id:
                                continue
                            existing = deduped_materials.get(material_id)
                            if not existing or (
                                to_number(item.get("spend")) or 0.0
                            ) >= (to_number(existing.get("spend")) or 0.0):
                                deduped_materials[material_id] = item
                        material_complete = all(
                            meta.get("complete") for meta in type_meta
                        )
                        previous_ids = set(previous_materials)
                        current_ids = set(deduped_materials)
                        if not material_complete:
                            for material_id, previous_item in previous_materials.items():
                                if material_id not in deduped_materials:
                                    cached_item = copy.deepcopy(previous_item)
                                    cached_item["cachedIncomplete"] = True
                                    deduped_materials[material_id] = cached_item
                        final_ids = set(deduped_materials)
                        removed_ids = sorted(previous_ids - final_ids) if material_complete else []
                        added_ids = sorted(final_ids - previous_ids)
                        source_total = sum(
                            int(meta.get("sourceTotal") or 0) for meta in type_meta
                        )
                        missing_count = sum(
                            int(meta.get("missingCount") or 0) for meta in type_meta
                        )
                        plan["materials"] = list(deduped_materials.values())
                        plan["materialsSyncedAt"] = now_iso()
                        plan["materialsWindow"] = material_window
                        plan["materialAudit"] = {
                            "source": "千川 Open API · 计划素材库",
                            "materialTypes": type_meta,
                            "sourceTotal": source_total,
                            "uniqueCount": len(final_ids),
                            "missingCount": missing_count,
                            "complete": material_complete,
                            "addedCount": len(added_ids),
                            "removedCount": len(removed_ids),
                            "removedMaterialIds": removed_ids[:100],
                            "staleFallbackCount": (
                                len(final_ids - current_ids) if not material_complete else 0
                            ),
                            "window": copy.deepcopy(material_window),
                            "fetchedAt": now_iso(),
                        }
                    except QianchuanAPIError as exc:
                        if previous_plan:
                            plan["materials"] = copy.deepcopy(
                                previous_plan.get("materials") or []
                            )
                            plan["materialsSyncedAt"] = previous_plan.get(
                                "materialsSyncedAt"
                            )
                            plan["materialsWindow"] = copy.deepcopy(
                                previous_plan.get("materialsWindow") or material_window
                            )
                            plan["materialAudit"] = {
                                **copy.deepcopy(previous_plan.get("materialAudit") or {}),
                                "complete": False,
                                "error": str(exc),
                                "failedAt": now_iso(),
                            }
                        errors.append(
                            {
                                "scope": "campaign_materials",
                                "accountId": account["id"],
                                "advertiserId": account["advertiserId"],
                                "code": "campaign_material_failed",
                                "message": f"计划 {plan['id']} 素材同步失败：{exc}",
                            }
                        )
                video_library_rows: list[dict[str, Any]] = []
                video_library_meta: dict[str, Any] = {}
                if sync_materials:
                    try:
                        video_library_rows, video_library_meta = (
                            client.fetch_qianchuan_video_library(
                                account["advertiserId"],
                                with_meta=True,
                            )
                        )
                        self._merge_video_library_metadata(plans, video_library_rows)
                    except QianchuanAPIError as exc:
                        video_library_meta = {
                            "source": "千川 Open API · 素材库视频",
                            "complete": False,
                            "error": str(exc),
                            "fetchedAt": now_iso(),
                        }
                        errors.append(
                            {
                                "scope": "material_upload_time",
                                "accountId": account["id"],
                                "advertiserId": account["advertiserId"],
                                "code": "material_upload_time_failed",
                                "message": f"素材上传时间同步失败：{exc}",
                            }
                        )
                audited_plans = plans[:material_limit]
                plan_audits = [
                    plan.get("materialAudit") or {}
                    for plan in audited_plans
                    if isinstance(plan, dict)
                ]
                unique_material_ids = {
                    str(material.get("id"))
                    for plan in audited_plans
                    for material in plan.get("materials") or []
                    if isinstance(material, dict) and material.get("id")
                }
                uploaded_time_material_ids = {
                    str(material.get("id"))
                    for plan in audited_plans
                    for material in plan.get("materials") or []
                    if isinstance(material, dict)
                    and material.get("id")
                    and material.get("uploadedAt") not in (None, "", "未获取")
                }
                account_upload_time_missing_ids = sorted(
                    unique_material_ids - uploaded_time_material_ids
                )
                previous_audit = account.get("materialAudit") or {}
                now = datetime.now(timezone.utc).astimezone()
                previous_reconciled_at = previous_audit.get("lastFullReconcileAt")
                reconcile_due = True
                if previous_reconciled_at:
                    try:
                        reconcile_due = (
                            now
                            - datetime.fromisoformat(str(previous_reconciled_at))
                        ).total_seconds() >= material_reconcile_seconds
                    except (TypeError, ValueError):
                        reconcile_due = True
                account["materialWindow"] = copy.deepcopy(material_window)
                account["materialSource"] = (
                    "千川 Open API · 计划素材库 + 素材维度报表 + 素材库视频上传时间"
                )
                account["materialMcpStatus"] = (
                    "MCP 工具列表未提供素材维度接口，素材数据不使用 MCP 补值"
                )
                last_full_reconcile_at = (
                    now if reconcile_due else previous_audit.get("lastFullReconcileAt")
                )
                try:
                    next_full_reconcile_at = (
                        datetime.fromisoformat(str(last_full_reconcile_at))
                        + timedelta(seconds=material_reconcile_seconds)
                    ).isoformat(timespec="seconds")
                except (TypeError, ValueError):
                    next_full_reconcile_at = (
                        now + timedelta(seconds=material_reconcile_seconds)
                    ).isoformat(timespec="seconds")
                account["materialAudit"] = {
                    "source": account["materialSource"],
                    "mcpMaterialToolAvailable": False,
                    "mcpNote": account["materialMcpStatus"],
                    "uploadTimeSource": video_library_meta.get("source"),
                    "uploadTimeComplete": video_library_meta.get("complete"),
                    "uploadTimeSourceTotal": video_library_meta.get("sourceTotal"),
                    "uploadTimeAvailableCount": video_library_meta.get("uploadTimeCount"),
                    "uploadTimeMissingCount": video_library_meta.get(
                        "uploadTimeMissingCount"
                    ),
                    "uploadTimeMatchedMaterialCount": len(uploaded_time_material_ids),
                    "uploadTimeUnmatchedMaterialCount": len(
                        account_upload_time_missing_ids
                    ),
                    "uploadTimeUnmatchedMaterialIds": account_upload_time_missing_ids[
                        :100
                    ],
                    "uploadTimeError": video_library_meta.get("error"),
                    "window": copy.deepcopy(material_window),
                    "autoRefreshSeconds": material_sync_interval_seconds,
                    "cacheSeconds": material_cache_seconds,
                    "reconcileSeconds": material_reconcile_seconds,
                    "syncedAt": now_iso(),
                    "lastFullReconcileAt": (
                        last_full_reconcile_at.isoformat(timespec="seconds")
                        if isinstance(last_full_reconcile_at, datetime)
                        else last_full_reconcile_at
                    ),
                    "nextFullReconcileAt": next_full_reconcile_at,
                    "planCount": len(audited_plans),
                    "completePlanCount": sum(
                        1 for audit in plan_audits if audit.get("complete")
                    ),
                    "sourceTotalAcrossPlans": sum(
                        int(audit.get("sourceTotal") or 0) for audit in plan_audits
                    ),
                    "uniqueMaterialCount": len(unique_material_ids),
                    "missingCount": sum(
                        int(audit.get("missingCount") or 0) for audit in plan_audits
                    ),
                    "addedCount": sum(
                        int(audit.get("addedCount") or 0) for audit in plan_audits
                    ),
                    "removedCount": sum(
                        int(audit.get("removedCount") or 0) for audit in plan_audits
                    ),
                    "complete": bool(plan_audits)
                    and all(bool(audit.get("complete")) for audit in plan_audits),
                }
                previous_awemes = {
                    str(item.get("id")): item
                    for item in account.get("awemes") or []
                    if isinstance(item, dict) and item.get("id")
                }
                awemes = []
                aweme_start_date = (date.fromisoformat(end_date) - timedelta(days=6)).isoformat()
                realtime_date = date.today().isoformat()
                for aweme in account.get("awemeAccounts") or []:
                    aweme_id = str(aweme.get("id"))
                    aweme_name = str(aweme.get("name") or aweme_id)
                    aweme_plans = [
                        plan for plan in plans
                        if any(
                            room.get("anchor_name") == aweme_name
                            for room in plan.get("roomInfo") or []
                            if isinstance(room, dict)
                        )
                    ]
                    previous_aweme = previous_awemes.get(aweme_id) or {}
                    previous_aweme_data = copy.deepcopy(previous_aweme.get("data") or [])
                    previous_history_data = [
                        copy.deepcopy(row)
                        for row in previous_aweme_data
                        if str(row.get("date") or "")[:10] != realtime_date
                    ]
                    history_synced_at = previous_aweme.get("historySyncedAt")
                    history_cached = False
                    if previous_history_data and history_synced_at:
                        try:
                            parsed_history_at = datetime.fromisoformat(str(history_synced_at))
                            history_cached = (
                                datetime.now(timezone.utc).astimezone() - parsed_history_at
                            ).total_seconds() < self.aweme_cache_seconds
                        except (TypeError, ValueError):
                            history_cached = False
                    history_synced_now = False
                    if not sync_history or history_cached:
                        aweme_data = previous_history_data
                    else:
                        try:
                            aweme_data = client.fetch_aweme_daily(
                                account["advertiserId"],
                                aweme_id,
                                aweme_start_date,
                                end_date,
                            )
                            history_synced_now = True
                        except QianchuanAPIError as exc:
                            aweme_data = previous_history_data
                            errors.append(
                                {
                                    "scope": "aweme_realtime",
                                    "accountId": account["id"],
                                    "advertiserId": account["advertiserId"],
                                    "awemeId": aweme_id,
                                    "code": "aweme_history_failed",
                                    "message": f"抖音号 {aweme_name} 历史日报同步失败：{exc}",
                                }
                            )
                    if not aweme_data and aweme_plans:
                        aweme_data = self._plans_to_daily(aweme_plans, aweme_start_date, end_date)
                    realtime_aweme_ok = False
                    realtime_aweme_source = None
                    if self.include_today:
                        try:
                            today_rows = client.fetch_aweme_daily(
                                account["advertiserId"],
                                aweme_id,
                                realtime_date,
                                realtime_date,
                            )
                            today_from_plans = (
                                []
                                if today_rows
                                else self._plans_to_daily(
                                    aweme_plans,
                                    realtime_date,
                                    realtime_date,
                                )
                            )
                            today_row = (
                                copy.deepcopy(today_rows[-1])
                                if today_rows
                                else copy.deepcopy(today_from_plans[-1])
                                if today_from_plans
                                else {
                                    "date": realtime_date,
                                    "spend": 0.0,
                                    "gmv": 0.0,
                                    "orders": 0.0,
                                }
                            )
                            today_row.update({"realtime": True, "syncedAt": now_iso()})
                            aweme_data = upsert_daily_row(aweme_data, today_row)
                            realtime_aweme_ok = True
                            realtime_aweme_source = (
                                "千川作者维度报表 · 今日累计"
                                if today_rows
                                else "千川计划接口 · 今日累计"
                                if today_from_plans
                                else "千川作者维度报表 · 今日无数据"
                            )
                        except QianchuanAPIError as exc:
                            today_from_plans = self._plans_to_daily(
                                aweme_plans,
                                realtime_date,
                                realtime_date,
                            )
                            if today_from_plans:
                                today_row = today_from_plans[-1]
                                today_row.update(
                                    {"realtime": True, "syncedAt": now_iso()}
                                )
                                aweme_data = upsert_daily_row(aweme_data, today_row)
                                realtime_aweme_ok = True
                                realtime_aweme_source = "千川计划接口 · 今日累计"
                            errors.append(
                                {
                                    "scope": "aweme_realtime",
                                    "accountId": account["id"],
                                    "advertiserId": account["advertiserId"],
                                    "awemeId": aweme_id,
                                    "code": "aweme_realtime_failed",
                                    "message": f"抖音号 {aweme_name} 今日实时同步失败：{exc}",
                                }
                            )
                    status = "投放中" if any(plan.get("status") == "投放中" for plan in aweme_plans) else "已暂停"
                    has_material_activity = any(
                        (to_number(row.get("spend")) or 0.0) > 0
                        for plan in aweme_plans
                        for row in plan.get("data") or []
                        if isinstance(row, dict)
                    )
                    material_report_rows: list[dict[str, Any]] = []
                    material_report_meta: list[dict[str, Any]] = []
                    material_report_synced_at = None
                    if aweme_plans and has_material_activity and sync_materials:
                        try:
                            video_report_rows, video_report_meta = (
                                client.fetch_uni_promotion_material_report(
                                    account["advertiserId"],
                                    aweme_id,
                                    material_start_date.isoformat(),
                                    material_end_date.isoformat(),
                                    "VIDEO",
                                    with_meta=True,
                                )
                            )
                            material_report_rows.extend(video_report_rows)
                            material_report_meta.append(video_report_meta)
                        except QianchuanAPIError as exc:
                            material_report_meta.append(
                                {
                                    "materialType": "VIDEO",
                                    "source": "千川 Open API · 素材维度报表",
                                    "complete": False,
                                    "error": str(exc),
                                    "fetchedAt": now_iso(),
                                }
                            )
                            errors.append(
                                {
                                    "scope": "campaign_material_report",
                                    "accountId": account["id"],
                                    "advertiserId": account["advertiserId"],
                                    "awemeId": aweme_id,
                                    "code": "campaign_material_report_failed",
                                    "message": f"抖音号 {aweme_name} 视频素材跑量同步失败：{exc}",
                                }
                            )
                        try:
                            live_report_rows, live_report_meta = (
                                client.fetch_uni_promotion_material_report(
                                    account["advertiserId"],
                                    aweme_id,
                                    material_start_date.isoformat(),
                                    material_end_date.isoformat(),
                                    "LIVE_ROOM",
                                    with_meta=True,
                                )
                            )
                            material_report_rows.extend(live_report_rows)
                            material_report_meta.append(live_report_meta)
                        except QianchuanAPIError as exc:
                            material_report_meta.append(
                                {
                                    "materialType": "LIVE_ROOM",
                                    "source": "千川 Open API · 素材维度报表",
                                    "complete": False,
                                    "error": str(exc),
                                    "fetchedAt": now_iso(),
                                }
                            )
                            errors.append(
                                {
                                    "scope": "campaign_material_report",
                                    "accountId": account["id"],
                                    "advertiserId": account["advertiserId"],
                                    "awemeId": aweme_id,
                                    "code": "campaign_live_material_report_failed",
                                    "message": f"抖音号 {aweme_name} 直播间画面跑量同步失败：{exc}",
                                }
                            )
                        self._merge_official_material_report(
                            aweme_plans,
                            material_report_rows,
                            material_window,
                        )
                        report_complete = bool(material_report_meta) and all(
                            bool(meta.get("complete"))
                            for meta in material_report_meta
                        )
                        if not report_complete and previous_by_id:
                            previous_material_metrics = {
                                str(material.get("id")): material
                                for plan in previous_by_id.values()
                                for material in plan.get("materials") or []
                                if isinstance(material, dict) and material.get("id")
                            }
                            for plan in aweme_plans:
                                for material in plan.get("materials") or []:
                                    if material.get("reportMatched"):
                                        continue
                                    previous_material = previous_material_metrics.get(
                                        str(material.get("id"))
                                    )
                                    if not previous_material:
                                        continue
                                    for key in (
                                        "spend",
                                        "gmv",
                                        "orders",
                                        "impressions",
                                        "clicks",
                                        "ctr",
                                        "completionRate",
                                        "dwellTime",
                                    ):
                                        material[key] = copy.deepcopy(
                                            previous_material.get(key)
                                        )
                                    material["materialWindow"] = copy.deepcopy(
                                        previous_material.get("materialWindow")
                                        or material_window
                                    )
                                    material["reportSource"] = previous_material.get(
                                        "reportSource"
                                    )
                                    material["cachedMetrics"] = True
                        if material_report_meta:
                            material_report_synced_at = now_iso()
                    awemes.append(
                        {
                            "id": aweme_id,
                            "name": aweme_name,
                            "status": status,
                            "data": aweme_data,
                            "plans": aweme_plans,
                            "historySyncedAt": (
                                now_iso() if history_synced_now else history_synced_at
                            ),
                            "realtimeSyncedAt": now_iso() if realtime_aweme_ok else previous_aweme.get("realtimeSyncedAt"),
                            "realtimeSource": realtime_aweme_source or previous_aweme.get("realtimeSource"),
                            "realtimeOk": realtime_aweme_ok,
                            "materialReportSyncedAt": material_report_synced_at or previous_aweme.get("materialReportSyncedAt"),
                            "materialReportSource": (
                                "千川素材维度报表"
                                if material_report_rows
                                else previous_aweme.get("materialReportSource")
                            ),
                            "materialReportRows": (
                                len(material_report_rows)
                                if material_report_rows
                                else previous_aweme.get("materialReportRows", 0)
                            ),
                            "materialReportAudit": {
                                "queries": material_report_meta,
                                "complete": bool(material_report_meta)
                                and all(
                                    bool(meta.get("complete"))
                                    for meta in material_report_meta
                                ),
                                "window": copy.deepcopy(material_window),
                                "source": "千川 Open API · 素材维度报表",
                                "mcpMaterialToolAvailable": False,
                                "syncedAt": material_report_synced_at
                                or previous_aweme.get("materialReportSyncedAt"),
                            },
                        }
                    )
                account["plans"] = plans
                account["awemes"] = awemes
                aweme_report_audits = [
                    aweme.get("materialReportAudit") or {}
                    for aweme in awemes
                    if (aweme.get("materialReportAudit") or {}).get("queries")
                ]
                account["materialReportAudit"] = {
                    "source": "千川 Open API · 素材维度报表",
                    "complete": bool(aweme_report_audits)
                    and all(bool(audit.get("complete")) for audit in aweme_report_audits),
                    "queryCount": sum(
                        len((aweme.get("materialReportAudit") or {}).get("queries") or [])
                        for aweme in awemes
                    ),
                    "materialReportRows": sum(
                        int(aweme.get("materialReportRows") or 0) for aweme in awemes
                    ),
                    "unmatchedCurrentLibraryCount": sum(
                        int(plan.get("materialReportUnmatchedCount") or 0)
                        for plan in plans
                    ),
                    "unmatchedPolicy": (
                        "历史报表存在但当前素材库不存在的素材不加入全量表，"
                        "仅保留审计记录"
                    ),
                    "mcpMaterialToolAvailable": False,
                    "mcpNote": "MCP 工具列表未提供素材维度接口",
                }
                account["campaignRaw"] = raw_pages
                account["campaignSource"] = "千川全域推广计划接口"
                account["realtimePlanOk"] = realtime_plan_ok
            return True
        except QianchuanAPIError as exc:
            message = str(exc)
            if exc.code is not None:
                message = f"{message}（code: {exc.code}）"
            errors.append(
                {
                    "scope": "campaigns",
                    "accountId": account["id"],
                    "advertiserId": account["advertiserId"],
                    "code": "campaign_sync_failed",
                    "message": f"计划列表或计划报表同步失败：{message}",
                }
            )
            return False

    def _plans_to_daily(
        self,
        plans: list[dict[str, Any]],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        by_date: dict[str, dict[str, Any]] = {}
        for plan in plans:
            for row in plan.get("data") or []:
                if not isinstance(row, dict):
                    continue
                row_date = str(row.get("date") or "")[:10]
                if not row_date or row_date < start_date or row_date > end_date:
                    continue
                item = by_date.setdefault(
                    row_date,
                    {"date": row_date, "spend": 0.0, "gmv": 0.0, "orders": 0.0},
                )
                item["spend"] += to_number(row.get("spend")) or 0.0
                item["gmv"] += to_number(row.get("gmv")) or 0.0
                item["orders"] += to_number(row.get("orders")) or 0.0
        result = []
        for row_date in sorted(by_date):
            row = by_date[row_date]
            row["spend"] = round(row["spend"], 2)
            row["gmv"] = round(row["gmv"], 2)
            row["orders"] = round(row["orders"], 4)
            result.append(row)
        return result

    @staticmethod
    def _build_reconciliation(account: dict[str, Any]) -> dict[str, Any]:
        """Expose official account totals versus aweme-attribution totals."""
        all_dates = [
            str(row.get("date"))[:10]
            for row in account.get("data") or []
            if isinstance(row, dict) and row.get("date")
        ]
        for aweme in account.get("awemes") or []:
            all_dates.extend(
                str(row.get("date"))[:10]
                for row in aweme.get("data") or []
                if isinstance(row, dict) and row.get("date")
            )
        report_date = max(all_dates, default=date.today().isoformat())
        account_row = next(
            (
                row
                for row in account.get("data") or []
                if str(row.get("date"))[:10] == report_date
            ),
            {},
        )
        aweme_totals = {"spend": 0.0, "gmv": 0.0, "orders": 0.0}
        for aweme in account.get("awemes") or []:
            row = next(
                (
                    item
                    for item in aweme.get("data") or []
                    if str(item.get("date"))[:10] == report_date
                ),
                {},
            )
            for key in aweme_totals:
                aweme_totals[key] += to_number(row.get(key)) or 0.0
        account_totals = {
            key: to_number(account_row.get(key)) or 0.0
            for key in ("spend", "gmv", "orders")
        }
        difference = {
            key: round(account_totals[key] - aweme_totals[key], 4)
            for key in account_totals
        }
        return {
            "date": report_date,
            "account": {key: round(value, 4) for key, value in account_totals.items()},
            "awemeAttribution": {
                key: round(value, 4) for key, value in aweme_totals.items()
            },
            "difference": difference,
            "source": "总账户使用千川广告主账户报表；账号拆分使用抖音号归因报表",
            "ok": all(abs(value) < 0.01 for value in difference.values()),
        }

    def _sync_locked(
        self,
        realtime_only: bool = False,
        force_materials: bool = False,
    ) -> dict[str, Any]:
        with self.lock:
            previous = copy.deepcopy(self.snapshot)
        previous_accounts = {
            str(account.get("id")): account
            for account in previous.get("accounts", [])
            if isinstance(account, dict) and account.get("id")
        }
        config = load_config()
        accounts = [
            self._build_account_shell(account_config, previous_accounts.get(account_config["id"]))
            for account_config in config.get("accounts", [])
        ]
        errors: list[dict[str, Any]] = []
        access_token, _token_info, credential_errors = resolve_access_token(config)
        errors.extend(credential_errors)
        start_date, end_date = build_date_range(HISTORY_DAYS)
        api_config = config.get("api", {})
        field_map = api_config.get("fieldMap", DEFAULT_FIELD_MAP)
        sync_config = config.get("sync", {})
        self.report_cache_seconds = max(60.0, float(sync_config.get("reportCacheSeconds", 120)))
        self.aweme_cache_seconds = max(60.0, float(sync_config.get("awemeCacheSeconds", 120)))
        self.realtime_cache_seconds = max(
            5.0, float(sync_config.get("realtimeCacheSeconds", 5))
        )
        self.include_today = bool(sync_config.get("includeToday", True))
        self.poll_interval_seconds = max(
            10, int(sync_config.get("intervalSeconds", DEFAULT_SYNC_INTERVAL_SECONDS))
        )
        self.full_sync_interval_seconds = max(
            60, int(sync_config.get("fullSyncIntervalSeconds", 180))
        )

        if not access_token:
            for account in accounts:
                if account.get("data"):
                    account["status"] = "凭证缺失 · 展示缓存"
                else:
                    account["status"] = "凭证缺失 · 无数据"
            self._apply_backoff(errors)
            snapshot = {
                "revision": int(previous.get("revision") or 0) + 1,
                "syncedAt": now_iso(),
                "lastAttemptAt": now_iso(),
                "dataCutoff": max(
                    [account.get("dataCutoff") for account in accounts if account.get("dataCutoff")],
                    default=None,
                ),
                "syncStatus": "degraded",
                "mode": "cache" if previous.get("mode") in {"live", "cache"} else "seed",
                "syncKind": "realtime" if realtime_only else "full",
                "pollIntervalSeconds": self.poll_interval_seconds,
                "syncBackoffSeconds": max(0, int(self.backoff_until - time.time())),
                "lastSyncAt": now_iso(),
                "historyDays": HISTORY_DAYS,
                "requestedStartDate": start_date,
                "requestedEndDate": end_date,
                "accounts": accounts,
                "errors": errors,
            }
            with self.lock:
                self.snapshot = snapshot
            atomic_write_json(self.snapshot_path, snapshot)
            return copy.deepcopy(snapshot)

        client = QianchuanClient(config, access_token)
        if api_config.get("discoverAccounts", False):
            try:
                discovered = client.fetch_authorized_advertisers()
                if discovered:
                    existing_by_advertiser = {
                        account["advertiserId"]: account for account in accounts
                    }
                    for item in discovered:
                        advertiser_id = item["advertiserId"]
                        if advertiser_id in existing_by_advertiser:
                            existing_by_advertiser[advertiser_id]["name"] = item["name"]
                            continue
                        account = self._build_account_shell(
                            {
                                "id": f"qc-{advertiser_id}",
                                "advertiserId": advertiser_id,
                                "name": item["name"],
                                "handle": "待同步抖音号信息",
                                "avatar": advertiser_id[-1:],
                                "color": "#0b7a58",
                            },
                            None,
                        )
                        accounts.append(account)
                        existing_by_advertiser[advertiser_id] = account
            except QianchuanAPIError as exc:
                errors.append(
                    {
                        "scope": "discovery",
                        "code": "account_discovery_failed",
                        "message": f"广告主发现失败，继续使用配置账户：{exc}",
                    }
                )
        success_count = 0
        for account in accounts:
            account_errors: list[dict[str, Any]] = []
            report_ok = False
            report_error: QianchuanAPIError | None = None
            account_succeeded = False
            cached_report = bool(account.get("data")) and (
                realtime_only
                or (time.time() - self.last_report_at) < self.report_cache_seconds
            )
            if cached_report:
                report_ok = True
                account["status"] = "数据已同步 · 账户报表缓存"
            else:
                try:
                    raw_rows, raw_pages = client.fetch_report(
                        account["advertiserId"],
                        start_date,
                        end_date,
                    )
                    normalized = normalize_daily_rows(raw_rows, field_map, start_date, end_date)
                    if not normalized:
                        raise QianchuanAPIError("接口返回成功，但半年日期范围内没有可识别的日报数据")
                    account["data"] = normalized
                    account["raw"] = raw_pages
                    account["dataCutoff"] = normalized[-1]["date"]
                    account["status"] = "数据已同步"
                    account["source"] = "千川全域推广 · 官方 Open API"
                    self.last_report_at = time.time()
                    report_ok = True
                except QianchuanAPIError as exc:
                    report_error = exc

            previous_material_sync_at = previous_accounts.get(account["id"], {}).get(
                "materialSyncAt"
            )
            material_cache_seconds = max(
                120, int(client.campaigns.get("materialCacheSeconds", 900))
            )
            materials_due = not realtime_only and (
                force_materials or not previous_material_sync_at
            )
            if materials_due and previous_material_sync_at and not force_materials:
                try:
                    materials_due = (
                        datetime.now(timezone.utc).astimezone()
                        - datetime.fromisoformat(str(previous_material_sync_at))
                    ).total_seconds() >= material_cache_seconds
                except (TypeError, ValueError):
                    materials_due = True
            plans_ok = self._sync_account_plans(
                client,
                account,
                start_date,
                end_date,
                errors,
                sync_history=not realtime_only,
                sync_materials=materials_due,
                force_materials=force_materials,
            )
            if materials_due and plans_ok:
                account["materialSyncAt"] = now_iso()
            elif previous_material_sync_at:
                account["materialSyncAt"] = previous_material_sync_at
            realtime_date = date.today().isoformat()
            realtime_account_ok = False
            realtime_account_source = None
            if self.include_today:
                try:
                    realtime_rows, realtime_raw = client.fetch_report(
                        account["advertiserId"],
                        realtime_date,
                        realtime_date,
                    )
                    realtime_normalized = normalize_daily_rows(
                        realtime_rows,
                        field_map,
                        realtime_date,
                        realtime_date,
                    )
                    realtime_from_plans = (
                        []
                        if realtime_normalized
                        else self._plans_to_daily(
                            account.get("plans") or [],
                            realtime_date,
                            realtime_date,
                        )
                    )
                    realtime_row = (
                        copy.deepcopy(realtime_normalized[-1])
                        if realtime_normalized
                        else copy.deepcopy(realtime_from_plans[-1])
                        if realtime_from_plans
                        else {
                            "date": realtime_date,
                            "spend": 0.0,
                            "gmv": 0.0,
                            "orders": 0.0,
                        }
                    )
                    realtime_row.update({"realtime": True, "syncedAt": now_iso()})
                    account["data"] = upsert_daily_row(account.get("data") or [], realtime_row)
                    account["realtimeRaw"] = realtime_raw
                    realtime_account_ok = True
                    realtime_account_source = (
                        "千川账户维度报表 · 今日累计"
                        if realtime_normalized
                        else "千川计划接口 · 今日累计"
                        if realtime_from_plans
                        else "千川账户维度报表 · 今日无数据"
                    )
                except QianchuanAPIError as exc:
                    today_from_plans = self._plans_to_daily(
                        account.get("plans") or [],
                        realtime_date,
                        realtime_date,
                    )
                    if today_from_plans:
                        realtime_row = today_from_plans[-1]
                        realtime_row.update(
                            {"realtime": True, "syncedAt": now_iso()}
                        )
                        account["data"] = upsert_daily_row(
                            account.get("data") or [],
                            realtime_row,
                        )
                        realtime_account_ok = True
                        realtime_account_source = "千川计划接口 · 今日累计"
                        account_errors.append(
                            {
                                "scope": "account_realtime",
                                "accountId": account["id"],
                                "advertiserId": account["advertiserId"],
                                "code": "account_realtime_fallback",
                                "message": (
                                    "账户维度今日实时报表不可用，已改用官方计划接口汇总："
                                    f"{exc}"
                                ),
                            }
                        )
                    else:
                        account_errors.append(
                            {
                                "scope": "account_realtime",
                                "accountId": account["id"],
                                "advertiserId": account["advertiserId"],
                                "code": "account_realtime_failed",
                                "message": f"账户今日实时同步失败：{exc}",
                            }
                        )
                account["realtime"] = {
                    "date": realtime_date,
                    "syncedAt": now_iso() if realtime_account_ok else previous_accounts.get(account["id"], {}).get("realtime", {}).get("syncedAt"),
                    "ok": realtime_account_ok,
                    "source": realtime_account_source,
                }
                if realtime_account_ok:
                    account["dataCutoff"] = account_last_date(account) or realtime_date
                    account["source"] = realtime_account_source
            if report_ok:
                if not plans_ok:
                    account["status"] = "数据已同步 · 计划失败"
                elif realtime_account_ok:
                    account["status"] = "今日实时已同步"
                success_count += 1
                account_succeeded = True
            elif plans_ok and account.get("plans"):
                derived = self._plans_to_daily(account["plans"], start_date, end_date)
                if derived:
                    existing_realtime_rows = [
                        copy.deepcopy(row)
                        for row in account.get("data") or []
                        if str(row.get("date") or "")[:10] == date.today().isoformat()
                    ]
                    for realtime_row in existing_realtime_rows:
                        derived = upsert_daily_row(derived, realtime_row)
                    account["data"] = derived
                    account["dataCutoff"] = derived[-1]["date"]
                    account["status"] = "数据已同步 · 计划汇总"
                    account["source"] = "千川全域推广 · 计划日报汇总"
                    success_count += 1
                    account_succeeded = True
                    account_errors.append(
                        {
                            "scope": "account",
                            "accountId": account["id"],
                            "advertiserId": account["advertiserId"],
                            "code": "account_report_fallback",
                            "message": (
                                "账户维度报表不可用，已改用计划日报汇总账户数据："
                                f"{report_error}"
                            ),
                        }
                    )
                else:
                    report_error = report_error or QianchuanAPIError("计划日报为空，无法汇总账户数据")
            if not account_succeeded and report_error is not None:
                message = str(report_error)
                if report_error.code is not None:
                    message = f"{message}（code: {report_error.code}）"
                account["status"] = "同步失败 · 展示缓存" if account.get("data") else "同步失败 · 无数据"
                account_errors.append(
                    {
                        "scope": "account",
                        "accountId": account["id"],
                        "advertiserId": account["advertiserId"],
                        "code": "qianchuan_api_error",
                        "message": message,
                    }
                )
            account["reconciliation"] = self._build_reconciliation(account)
            errors.extend(account_errors)

        has_campaign_errors = any(error.get("scope") == "campaigns" for error in errors)
        has_account_fallback = any(error.get("code") == "account_report_fallback" for error in errors)
        if success_count == len(accounts) and accounts and not has_campaign_errors and not has_account_fallback:
            sync_status = "success"
            mode = "live"
        elif success_count:
            sync_status = "partial"
            mode = "live"
        else:
            sync_status = "failed"
            mode = "cache" if previous.get("mode") in {"live", "cache"} else "seed"

        self._apply_backoff(errors)
        self.last_sync_at = now_iso()
        realtime_entries = [
            account.get("realtime") or {}
            for account in accounts
            if isinstance(account, dict)
        ]
        realtime_source_counts = {"official_account": 0, "plan_fallback": 0, "failed": 0}
        for entry in realtime_entries:
            source = str(entry.get("source") or "")
            if entry.get("ok") and "账户维度" in source:
                realtime_source_counts["official_account"] += 1
            elif entry.get("ok"):
                realtime_source_counts["plan_fallback"] += 1
            else:
                realtime_source_counts["failed"] += 1
        realtime_updated_count = (
            realtime_source_counts["official_account"]
            + realtime_source_counts["plan_fallback"]
        )
        realtime_status = (
            "success"
            if accounts and realtime_updated_count == len(accounts)
            else "partial"
            if realtime_updated_count
            else "failed"
        )
        snapshot = {
            "revision": int(previous.get("revision") or 0) + 1,
            "syncedAt": now_iso(),
            "lastAttemptAt": now_iso(),
            "dataCutoff": max(
                [account.get("dataCutoff") for account in accounts if account.get("dataCutoff")],
                default=None,
            ),
            "syncStatus": sync_status,
            "mode": mode,
            "syncKind": "realtime" if realtime_only else "full",
            "pollIntervalSeconds": self.poll_interval_seconds,
            "syncBackoffSeconds": max(0, int(self.backoff_until - time.time())),
            "lastSyncAt": self.last_sync_at,
            "historyDays": HISTORY_DAYS,
            "requestedStartDate": start_date,
            "requestedEndDate": end_date,
            "realtime": {
                "date": date.today().isoformat(),
                "updatedAt": now_iso() if realtime_updated_count else previous.get("realtime", {}).get("updatedAt"),
                "status": realtime_status,
                "updatedAccountCount": realtime_updated_count,
                "sources": realtime_source_counts,
            },
            "accounts": accounts,
            "errors": errors,
        }
        with self.lock:
            self.snapshot = snapshot
        atomic_write_json(self.snapshot_path, snapshot)
        return copy.deepcopy(snapshot)

    def _apply_backoff(self, errors: list[dict[str, Any]]) -> None:
        rate_limited = False
        for error in errors:
            text = f"{error.get('message', '')} {error.get('code', '')}".lower()
            if "40100" in text or "频率" in text or "限流" in text or "too many" in text or "429" in text:
                rate_limited = True
                break
        if rate_limited:
            self.backoff_hits += 1
            delay = min(300, 60 * (2 ** min(self.backoff_hits - 1, 3)))
            self.backoff_until = time.time() + delay
        else:
            self.backoff_hits = 0
            self.backoff_until = 0.0

    def sync(
        self,
        realtime_only: bool = False,
        force_materials: bool = False,
    ) -> dict[str, Any]:
        with self.sync_lock:
            return self._sync_locked(
                realtime_only=realtime_only,
                force_materials=force_materials,
            )

    def _run_background_sync(
        self,
        realtime_only: bool,
        force_materials: bool = False,
    ) -> None:
        try:
            self.sync(
                realtime_only=realtime_only,
                force_materials=force_materials,
            )
        except Exception as exc:
            self.last_sync_error = str(exc)
            print(f"后台同步失败: {exc}")
        finally:
            with self.sync_state_lock:
                self.sync_running = False
                self.sync_finished_at = now_iso()

    def request_sync(
        self,
        realtime_only: bool = True,
        force_materials: bool = False,
    ) -> bool:
        """Start one sync job without blocking the HTTP response."""
        with self.sync_state_lock:
            if self.sync_running:
                return False
            self.sync_running = True
            self.sync_kind = "realtime" if realtime_only else "full"
            self.sync_started_at = now_iso()
            self.sync_finished_at = None
            self.last_sync_error = None
        threading.Thread(
            target=self._run_background_sync,
            args=(realtime_only, force_materials),
            name=f"{self.sync_kind}-sync",
            daemon=True,
        ).start()
        return True

    def wait_for_sync(self, timeout_seconds: float = 2.5) -> bool:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() < deadline:
            with self.sync_state_lock:
                if not self.sync_running:
                    return True
            time.sleep(0.05)
        with self.sync_state_lock:
            return not self.sync_running

    def sync_state(self) -> dict[str, Any]:
        with self.sync_state_lock:
            return {
                "running": self.sync_running,
                "kind": self.sync_kind,
                "startedAt": self.sync_started_at,
                "finishedAt": self.sync_finished_at,
                "error": self.last_sync_error,
            }

    def live_screen_status(self) -> dict[str, Any]:
        state = load_json(self.live_screen_path, {})
        if not isinstance(state, dict) or not state:
            return {
                "status": "missing",
                "ok": False,
                "stale": True,
                "source": "puppeteer-core",
                "error": "直播大屏采集器尚未写入状态",
                "path": str(self.live_screen_path),
            }
        heartbeat = str(state.get("heartbeatAt") or "").strip()
        age_seconds: float | None = None
        if heartbeat:
            try:
                parsed = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
                age_seconds = max(
                    0.0,
                    (datetime.now(parsed.tzinfo) - parsed).total_seconds(),
                )
            except (TypeError, ValueError):
                age_seconds = None
        interval = max(3, int(to_number(state.get("intervalSeconds")) or 10))
        stale = age_seconds is None or age_seconds > max(30, interval * 3 + 5)
        status = str(state.get("status") or "unknown")
        return {
            **copy.deepcopy(state),
            "ok": status in {"ok", "partial", "stale"} and not stale,
            "stale": stale,
            "ageSeconds": round(age_seconds, 2) if age_seconds is not None else None,
        }

    @staticmethod
    def _screen_sample(
        state: dict[str, Any],
        five_dimension: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        metrics = state.get("metrics")
        if not isinstance(metrics, dict) or not metrics:
            return None
        raw_time = str(
            state.get("syncedAt")
            or state.get("heartbeatAt")
            or ""
        ).strip()
        timestamp: float | None = None
        parsed: datetime | None = None
        if raw_time:
            try:
                parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                timestamp = parsed.timestamp()
            except (TypeError, ValueError):
                parsed = None
                timestamp = None
        if timestamp is None:
            parsed = datetime.now().astimezone()
            timestamp = parsed.timestamp()

        def metric(key: str) -> float | None:
            value = to_number(metrics.get(key))
            return round(value, 6) if value is not None else None

        sample = {
            "t": int(timestamp * 1000),
            "syncedAt": now_iso(),
            "sourceAt": raw_time,
            "spend": metric("spend"),
            "gmv": metric("gmv"),
            "orders": metric("orders"),
            "roi": metric("roi"),
            "watch": metric("watchCount"),
            "exposure": metric("exposure"),
            "watchOneMinute": metric("watchOneMinute"),
            "productClicks": metric("productClicks"),
            "peakOnline": metric("peakOnline"),
            "gpm": metric("gpm"),
            "online": metric("online"),
            "comments": metric("comments"),
            "follows": metric("follows"),
            "entryRate": None,
            "flowItems": [],
        }
        flow_state = state.get("flows")
        if isinstance(flow_state, list):
            sample["flowItems"] = [
                {
                    "key": str(item.get("key") or ""),
                    "label": str(item.get("label") or item.get("key") or ""),
                    "value": item.get("value"),
                    "unit": str(item.get("unit") or ""),
                }
                for item in flow_state
                if isinstance(item, dict)
            ]
        elif isinstance(flow_state, dict):
            sample["flowItems"] = [
                {"key": str(key), "label": str(key), "value": value}
                for key, value in flow_state.items()
            ]
        if isinstance(five_dimension, dict):
            values = five_dimension.get("values") or {}
            exposure = to_number(values.get("exposure"))
            watch = to_number(values.get("watch"))
            if exposure and watch is not None:
                sample["entryRate"] = round(watch / exposure * 100, 4)
        return sample

    def capture_live_screen_history(
        self,
        five_dimension: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist every usable screen sample so charts survive reload and restart."""
        state = load_json(self.live_screen_path, {})
        if not isinstance(state, dict) or not state:
            return {"version": 1, "days": {}, "updatedAt": now_iso()}
        sample = self._screen_sample(state, five_dimension)
        if sample is None:
            history = self._load_live_history()
            return history if isinstance(history, dict) else {"version": 1, "days": {}}
        raw_date = str(
            state.get("syncedAt") or state.get("heartbeatAt") or ""
        ).strip()
        try:
            parsed = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            day = parsed.astimezone().date().isoformat()
        except (TypeError, ValueError):
            day = date.today().isoformat()
        room_id = str((state.get("room") or {}).get("id") or "").strip()
        if not room_id:
            return {"version": 1, "days": {}, "updatedAt": now_iso()}
        history = self._load_live_history()
        if not isinstance(history, dict):
            history = {}
        days = history.setdefault("days", {})
        if not isinstance(days, dict):
            days = {}
            history["days"] = days
        rooms = days.setdefault(day, {})
        if not isinstance(rooms, dict):
            rooms = {}
            days[day] = rooms
        samples = rooms.setdefault(room_id, [])
        if not isinstance(samples, list):
            samples = []
            rooms[room_id] = samples
        if samples:
            previous = samples[-1]
            if sample["t"] < int(previous.get("t") or 0):
                sample["t"] = int(previous.get("t") or 0) + 1
            if sample["t"] - int(previous.get("t") or 0) < 5000:
                samples[-1] = sample
            else:
                samples.append(sample)
        else:
            samples.append(sample)
        del samples[:-6000]
        history["version"] = 1
        history["updatedAt"] = now_iso()
        self._write_live_history(history)
        return copy.deepcopy(history)

    def _load_live_history(self) -> dict[str, Any]:
        try:
            mtime_ns = self.live_history_path.stat().st_mtime_ns
        except OSError:
            mtime_ns = None
        with self.live_history_cache_lock:
            if (
                self.live_history_memory is not None
                and mtime_ns is not None
                and self.live_history_mtime_ns == mtime_ns
            ):
                return copy.deepcopy(self.live_history_memory)
        try:
            history = load_json(self.live_history_path, {})
            if (
                isinstance(history, dict)
                and (history or not self.live_history_backup_path.is_file())
            ):
                self.live_history_last_error = None
                with self.live_history_cache_lock:
                    self.live_history_memory = copy.deepcopy(history)
                    self.live_history_mtime_ns = mtime_ns
                return history
        except ValueError as exc:
            self.live_history_last_error = str(exc)

        recovery_error = self.live_history_last_error or "历史文件不是有效对象"
        corrupt_copy = self.live_history_path.with_name(
            f"{self.live_history_path.stem}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        try:
            if self.live_history_path.exists():
                shutil.copy2(self.live_history_path, corrupt_copy)
        except OSError:
            pass

        recovered: dict[str, Any] = {}
        try:
            backup = load_json(self.live_history_backup_path, {})
            if isinstance(backup, dict):
                recovered = backup
        except ValueError:
            recovered = {}
        if not recovered:
            recovered = {
                "version": 1,
                "days": {},
                "updatedAt": now_iso(),
                "recoveryWarning": recovery_error,
            }
        else:
            recovered = {
                **recovered,
                "recoveryWarning": recovery_error,
                "recoveredFromBackupAt": now_iso(),
            }
        try:
            atomic_write_json(self.live_history_path, recovered)
        except OSError:
            pass
        try:
            recovered_mtime_ns = self.live_history_path.stat().st_mtime_ns
        except OSError:
            recovered_mtime_ns = None
        with self.live_history_cache_lock:
            self.live_history_memory = copy.deepcopy(recovered)
            self.live_history_mtime_ns = recovered_mtime_ns
        return copy.deepcopy(recovered)

    def _write_live_history(self, history: dict[str, Any]) -> None:
        with self.live_history_cache_lock:
            current = copy.deepcopy(self.live_history_memory)
        if current:
            atomic_write_json(self.live_history_backup_path, current)
        atomic_write_json(self.live_history_path, history)
        try:
            mtime_ns = self.live_history_path.stat().st_mtime_ns
        except OSError:
            mtime_ns = None
        with self.live_history_cache_lock:
            self.live_history_memory = copy.deepcopy(history)
            self.live_history_mtime_ns = mtime_ns

    def live_history_snapshot(
        self,
        account_id: str | None = None,
        bucket_minutes: int = 5,
        five_dimension: dict[str, Any] | None = None,
        lightweight: bool = False,
    ) -> dict[str, Any]:
        if lightweight:
            with self.live_history_cache_lock:
                # The cached object is replaced atomically by writers and is not
                # mutated after publication. Avoid copying multi-megabyte history
                # on the real-time /api/live path.
                history = self.live_history_memory
            if history is None:
                return {
                    "points": [],
                    "bucketMinutes": max(1, int(bucket_minutes)),
                    "source": "screen_persisted_5m",
                    "error": "历史快照缓存预热中，不影响当前实时数据",
                    "nonBlocking": True,
                }
        else:
            try:
                history = self.capture_live_screen_history(five_dimension)
            except Exception as exc:
                return {
                    "points": [],
                    "bucketMinutes": max(1, int(bucket_minutes)),
                    "source": "screen_persisted_5m",
                    "error": f"直播大屏历史归档读取失败，不影响当前实时数据：{exc}",
                }
        days = history.get("days") if isinstance(history, dict) else {}
        days = days if isinstance(days, dict) else {}
        if not days:
            return {
                "points": [],
                "bucketMinutes": max(1, int(bucket_minutes)),
                "source": "screen_persisted_5m",
                "error": "直播大屏采集器尚未形成历史快照",
            }
        date_keys = sorted(days)
        state = load_json(self.live_screen_path, {})
        state = state if isinstance(state, dict) else {}
        current_room = str((state.get("room") or {}).get("id") or "")
        state_date = str(state.get("syncedAt") or state.get("heartbeatAt") or "")
        try:
            day_key = datetime.fromisoformat(
                state_date.replace("Z", "+00:00")
            ).astimezone().date().isoformat()
        except (TypeError, ValueError):
            day_key = date_keys[-1]
        rooms = days.get(day_key) or {}
        if not isinstance(rooms, dict):
            rooms = {}
        room_id = current_room if current_room in rooms else (next(reversed(rooms), "") if rooms else "")
        samples = rooms.get(room_id) if room_id else None
        if not isinstance(samples, list) or not samples:
            return {
                "points": [],
                "bucketMinutes": max(1, int(bucket_minutes)),
                "source": "screen_persisted_5m",
                "date": day_key,
                "roomId": room_id,
                "error": "当前直播间没有可用历史快照",
            }
        width = max(1, int(bucket_minutes)) * 60
        buckets: dict[int, dict[str, Any]] = {}
        for sample in samples:
            if any(
                sample.get(key) is None
                for key in ("spend", "gmv", "orders", "roi", "watch")
            ):
                continue
            timestamp = int(to_number(sample.get("t")) or 0)
            if timestamp <= 0:
                continue
            bucket = timestamp // 1000 // width * width
            previous = buckets.get(bucket)
            if previous is None or timestamp >= int(previous.get("t") or 0):
                point = copy.deepcopy(sample)
                point["bucketAt"] = datetime.fromtimestamp(
                    bucket, tz=datetime.now().astimezone().tzinfo
                ).isoformat()
                point["time"] = datetime.fromtimestamp(
                    bucket, tz=datetime.now().astimezone().tzinfo
                ).strftime("%H:%M")
                buckets[bucket] = point
        points = [buckets[key] for key in sorted(buckets)]
        return {
            "points": points,
            "bucketMinutes": max(1, int(bucket_minutes)),
            "date": day_key,
            "roomId": room_id,
            "source": "screen_persisted_5m",
            "updatedAt": history.get("updatedAt") or now_iso(),
            "error": "",
        }

    @staticmethod
    def _first_number(source: dict[str, Any], keys: tuple[str, ...]) -> float | None:
        for key in keys:
            value = to_number(source.get(key))
            if value is not None:
                return value
        return None

    def _account_for(self, account_id: str | None = None) -> dict[str, Any] | None:
        accounts = self.dashboard().get("accounts") or []
        return next(
            (
                item
                for item in accounts
                if account_id in {
                    item.get("id"),
                    item.get("awemeId"),
                    item.get("advertiserId"),
                    item.get("qianchuanId"),
                }
            ),
            accounts[0] if accounts else None,
        )

    def _account_aweme_ids(self, account: dict[str, Any]) -> list[str]:
        if account.get("awemeId"):
            return [str(account.get("awemeId"))]
        config = load_config()
        config_account = next(
            (
                item
                for item in config.get("accounts", [])
                if str(item.get("advertiserId")) == str(account.get("advertiserId"))
            ),
            {},
        )
        values = (
            config_account.get("awemeIds")
            or account.get("awemeIds")
            or DEFAULT_ACCOUNT["awemeIds"]
        )
        return [str(item) for item in values if str(item).strip()]

    def live_five_dimension(
        self,
        account_id: str | None,
        screen_metrics: dict[str, Any],
        *,
        background: bool = True,
    ) -> dict[str, Any]:
        """Build the funnel from screen data immediately and enrich MCP in background."""
        account = self._account_for(account_id)
        if not account:
            return {
                "status": "error",
                "source": "none",
                "values": {},
                "sources": {},
                "error": "没有可用广告账户",
            }
        advertiser_id = str(account.get("advertiserId") or account.get("qianchuanId"))
        aweme_ids = self._account_aweme_ids(account)
        cache_key = f"five:{account.get('id')}"
        now = time.time()
        with self.live_lock:
            cached = self.live_cache.get(cache_key)
            if cached and now - cached[0] < FIVE_DIMENSION_CACHE_SECONDS:
                return copy.deepcopy(cached[1])
            in_flight = cache_key in self.five_dimension_inflight
            retry_after = self.five_dimension_retry_after.get(cache_key, 0.0)
            last_error = self.five_dimension_last_error.get(cache_key, "")

        client = self._get_mcp_client()
        if client is None:
            return self._five_dimension_payload(
                screen_metrics,
                {},
                mcp_error=last_error or "千川 MCP 未配置",
                mcp_status="disabled",
            )
        if not background:
            self._refresh_five_dimension_mcp(
                cache_key,
                advertiser_id,
                list(aweme_ids),
                copy.deepcopy(screen_metrics),
                client,
            )
            with self.live_lock:
                refreshed = self.live_cache.get(cache_key)
                if refreshed:
                    return copy.deepcopy(refreshed[1])
            return self._five_dimension_payload(
                screen_metrics,
                {},
                mcp_error=self.five_dimension_last_error.get(cache_key, ""),
                mcp_status="error",
            )
        if not in_flight and now >= retry_after:
            with self.live_lock:
                if cache_key not in self.five_dimension_inflight:
                    self.five_dimension_inflight.add(cache_key)
                    worker = threading.Thread(
                        target=self._refresh_five_dimension_mcp,
                        args=(
                            cache_key,
                            advertiser_id,
                            list(aweme_ids),
                            copy.deepcopy(screen_metrics),
                            client,
                        ),
                        name=f"five-dimension-{account.get('id')}",
                        daemon=True,
                    )
                    try:
                        worker.start()
                    except Exception as exc:
                        self.five_dimension_inflight.discard(cache_key)
                        self.five_dimension_last_error[cache_key] = (
                            f"无法启动 MCP 后台任务：{exc}"
                        )
                        self.five_dimension_retry_after[cache_key] = (
                            time.time() + FIVE_DIMENSION_RETRY_SECONDS
                        )
                in_flight = cache_key in self.five_dimension_inflight
        return self._five_dimension_payload(
            screen_metrics,
            {},
            mcp_error=(
                last_error
                or ("MCP 后台查询中，当前先返回直播大屏数据" if in_flight else "")
            ),
            mcp_pending=in_flight,
            mcp_status="pending" if in_flight else "error" if last_error else "idle",
        )

    @staticmethod
    def _five_dimension_payload(
        screen_metrics: dict[str, Any],
        mcp_record: dict[str, Any],
        *,
        mcp_error: str = "",
        mcp_pending: bool = False,
        mcp_status: str = "ready",
    ) -> dict[str, Any]:
        first_number = DashboardStore._first_number

        values: dict[str, Any] = {}
        sources: dict[str, str] = {}
        aliases = {
            "exposure": (
                "live_show_count",
                "total_live_show_cnt",
                "show_count",
                "exposure_count",
                "live_exposure_count",
            ),
            "watch": (
                "total_live_watch_cnt",
                "live_watch_count",
                "watch_count",
                "watchCount",
            ),
            "stay": (
                "live_watch_one_minute_count",
                "watch_one_minute_count",
                "watchOneMinute",
            ),
            "comments": (
                "total_live_comment_cnt",
                "comment_count",
                "comments",
            ),
            "orders": (
                "pay_order_count",
                "total_pay_order_count_for_roi2",
                "luban_live_pay_order_count",
                "live_pay_order_count_alias",
                "orders",
            ),
        }
        for key, keys in aliases.items():
            value = first_number(mcp_record, keys)
            if value is not None:
                values[key] = value
                sources[key] = "mcp:qianchuan_report_live_get_v1"
        fallback = {
            "exposure": "exposure",
            "watch": "watchCount",
            "stay": "watchOneMinute",
            "comments": "comments",
            "orders": "orders",
        }
        for key, screen_key in fallback.items():
            if key in values:
                continue
            value = to_number(screen_metrics.get(screen_key))
            if value is not None:
                values[key] = value
                sources[key] = "screen:live_board"
        missing = [key for key in aliases if key not in values]
        status = "ok" if not missing else "partial" if values else "error"
        exposure = to_number(values.get("exposure"))
        watch = to_number(values.get("watch"))
        payload = {
            "status": status,
            "source": "mcp_first_screen_fallback",
            "sourceLabel": (
                "五维四率：MCP 优先，缺失字段回退直播大屏"
                if mcp_status == "ready"
                else "五维四率：直播大屏即时返回，MCP 后台更新"
            ),
            "values": values,
            "sources": sources,
            "entryRate": (
                round(watch / exposure * 100, 4)
                if exposure and watch is not None
                else None
            ),
            "missing": missing,
            "mcpError": mcp_error,
            "mcpPending": mcp_pending,
            "mcpStatus": mcp_status,
            "syncedAt": now_iso(),
        }
        return payload

    def _refresh_five_dimension_mcp(
        self,
        cache_key: str,
        advertiser_id: str,
        aweme_ids: list[str],
        screen_metrics: dict[str, Any],
        client: QianchuanMCPClient,
    ) -> None:
        mcp_record: dict[str, Any] = {}
        mcp_error = ""
        try:
            for aweme_id in aweme_ids:
                try:
                    response = client.fetch_live_room(
                        advertiser_id,
                        aweme_id,
                        date.today().isoformat(),
                    )
                    mcp_record = response.get("room") or {}
                    if mcp_record:
                        break
                except Exception as exc:
                    mcp_error = str(exc) or exc.__class__.__name__
            if not mcp_record and not mcp_error:
                mcp_error = "MCP 直播报表返回空 data"
        except Exception as exc:
            mcp_error = str(exc) or exc.__class__.__name__

        mcp_status = "ready" if mcp_record else "error"
        payload = self._five_dimension_payload(
            screen_metrics,
            mcp_record,
            mcp_error=mcp_error,
            mcp_status=mcp_status,
        )
        with self.live_lock:
            self.live_cache[cache_key] = (time.time(), copy.deepcopy(payload))
            self.five_dimension_inflight.discard(cache_key)
            if mcp_record:
                self.five_dimension_last_error.pop(cache_key, None)
                self.five_dimension_retry_after.pop(cache_key, None)
            else:
                self.five_dimension_last_error[cache_key] = mcp_error
                self.five_dimension_retry_after[cache_key] = (
                    time.time() + FIVE_DIMENSION_RETRY_SECONDS
                )
        with self.mcp_lock:
            self.mcp_last_error = None if mcp_record else mcp_error

    @staticmethod
    def _mcp_flow_map(payload: Any) -> dict[str, float]:
        for record in QianchuanMCPClient.iter_dicts(payload):
            flow = record.get("AllEcomFlowSource")
            if not isinstance(flow, dict):
                continue
            normalized: dict[str, float] = {}
            for key, value in flow.items():
                number = to_number(value)
                if number is not None:
                    normalized[str(key)] = number
            if normalized:
                return normalized
        return {}

    @staticmethod
    def _mcp_user_dimensions(payload: Any) -> dict[str, list[dict[str, Any]]]:
        groups: dict[str, list[dict[str, Any]]] = {
            "gender": [],
            "age": [],
            "city": [],
        }
        seen: set[tuple[str, str, float]] = set()
        for record in QianchuanMCPClient.iter_dicts(payload):
            for group, key in (
                ("gender", "gender_type"),
                ("age", "age_type"),
                ("city", "city_name"),
            ):
                raw_label = record.get(key)
                raw_value = record.get("value")
                number = to_number(raw_value)
                if raw_label is None or number is None:
                    continue
                marker = (group, str(raw_label), number)
                if marker in seen:
                    continue
                seen.add(marker)
                groups[group].append({key: raw_label, "value": number})
        return {key: value for key, value in groups.items() if value}

    def _campaign_history_basis(self, account: dict[str, Any]) -> dict[str, Any]:
        today = date.today()
        start = (today - timedelta(days=29)).isoformat()
        end = today.isoformat()
        rows = [
            row
            for row in account.get("data", [])
            if isinstance(row, dict) and start <= str(row.get("date")) <= end
        ]
        active_rows = [
            row
            for row in rows
            if (to_number(row.get("spend")) or 0) > 0
            or (to_number(row.get("orders")) or 0) > 0
        ]
        spend = sum(to_number(row.get("spend")) or 0.0 for row in active_rows)
        gmv = sum(to_number(row.get("gmv")) or 0.0 for row in active_rows)
        orders = sum(to_number(row.get("orders")) or 0.0 for row in active_rows)
        days = len(active_rows)
        return {
            "available": days > 0,
            "window": {"start": start, "end": end, "days": 30},
            "observedDays": len(rows),
            "activeDays": days,
            "rows": copy.deepcopy(active_rows),
            "totals": {
                "spend": round(spend, 2),
                "gmv": round(gmv, 2),
                "orders": round(orders, 4),
            },
            "averages": {
                "spend": round(spend / days, 2) if days else None,
                "gmv": round(gmv / days, 2) if days else None,
                "orders": round(orders / days, 4) if days else None,
                "roi": round(gmv / spend, 4) if spend else None,
                "aov": round(gmv / orders, 2) if orders else None,
                "cost": round(spend / orders, 2) if orders else None,
            },
            "warning": (
                ""
                if days >= 10
                else f"近 30 天仅有 {days} 个有效消耗/成交日，推演置信度偏低"
            ),
        }

    def campaign_diagnostics(self, account_id: str | None = None) -> dict[str, Any]:
        account = self._account_for(account_id)
        if not account:
            return {
                "ok": False,
                "source": "qianchuan_mcp",
                "error": "没有可用广告账户",
                "missingReasons": ["没有可用广告账户"],
                "syncedAt": now_iso(),
            }
        cache_key = str(account.get("id"))
        with self.live_lock:
            cached = self.campaign_cache.get(cache_key)
            if cached and time.time() - cached[0] < 8:
                return copy.deepcopy(cached[1])

        advertiser_id = str(account.get("advertiserId") or account.get("qianchuanId"))
        aweme_ids = self._account_aweme_ids(account)
        client = self._get_mcp_client()
        record: dict[str, Any] = {}
        payload_raw: Any = {}
        tool = QianchuanMCPClient.LIVE_REPORT_TOOL
        error = ""
        if client is None:
            error = "千川 MCP 未配置"
        else:
            for aweme_id in aweme_ids:
                try:
                    response = client.fetch_live_room(
                        advertiser_id,
                        aweme_id,
                        date.today().isoformat(),
                    )
                    record = response.get("room") or {}
                    payload_raw = response.get("payload") or {}
                    tool = str(response.get("tool") or tool)
                    with self.mcp_lock:
                        self.mcp_last_error = None
                    break
                except QianchuanMCPError as exc:
                    error = str(exc)
            if error:
                with self.mcp_lock:
                    self.mcp_last_error = error
        if not record and not error:
            error = "MCP 直播报表返回空 data"

        live_config = load_config().get("live", DEFAULT_LIVE_CONFIG)
        divisor = to_number(live_config.get("moneyDivisor")) or 1.0

        def money(key: str) -> float | None:
            value = to_number(record.get(key))
            return round(value / divisor, 2) if value is not None else None

        spend = money("stat_cost")
        gmv = self._first_number(
            record,
            (
                "total_pay_order_gmv_for_roi2",
                "pay_order_amount",
                "luban_live_pay_order_gmv",
                "live_pay_order_gmv_alias",
            ),
        )
        if gmv is not None:
            gmv = round(gmv / divisor, 2)
        orders = self._first_number(
            record,
            (
                "pay_order_count",
                "total_pay_order_count_for_roi2",
                "luban_live_pay_order_count",
                "live_pay_order_count_alias",
                "orders",
            ),
        )
        roi = self._first_number(
            record,
            (
                "total_prepay_and_pay_order_roi2",
                "live_pay_order_gmv_roi",
                "ad_live_prepay_and_pay_order_gmv_roi",
                "roi",
            ),
        )
        if roi is None and spend and gmv is not None:
            roi = gmv / spend
        watch = self._first_number(
            record,
            ("total_live_watch_cnt", "live_watch_count", "watch_count", "watchCount"),
        )
        clicks = self._first_number(
            record,
            ("live_click_product_count_alias", "product_click_count", "productClicks"),
        )
        online = self._first_number(
            record,
            (
                "online_count",
                "current_online_count",
                "live_online_count",
                "room_online_count",
                "online",
            ),
        )
        gpm = self._first_number(
            record,
            ("gpm", "live_gpm", "overall_gpm", "gpm_amount"),
        )
        if gpm is None and gmv is not None and watch:
            gpm = gmv / watch * 1000
        comments = self._first_number(
            record,
            ("total_live_comment_cnt", "comment_count", "comments"),
        )
        follows = self._first_number(
            record,
            ("total_live_follow_cnt", "follow_count", "follows"),
        )
        metrics = {
            "spend": spend,
            "gmv": gmv,
            "orders": orders,
            "roi": round(roi, 4) if roi is not None else None,
            "gpm": round(gpm, 2) if gpm is not None else None,
            "online": online,
            "watchCount": watch,
            "productClicks": clicks,
            "comments": comments,
            "follows": follows,
            "aov": round(gmv / orders, 2) if gmv is not None and orders else None,
            "cost": round(spend / orders, 2) if spend is not None and orders else None,
        }
        flows = self._mcp_flow_map(payload_raw)
        users = self._mcp_user_dimensions(payload_raw)
        missing_reasons: list[str] = []
        solutions: list[str] = []
        for field, label in (
            ("spend", "消耗"),
            ("gmv", "成交金额"),
            ("orders", "成交订单"),
            ("roi", "ROI"),
            ("gpm", "GPM"),
            ("online", "在线人数"),
            ("productClicks", "商品点击"),
        ):
            if metrics.get(field) is None:
                missing_reasons.append(f"MCP 未返回{label}")
                unit_hint = (
                    "并核对金额/ROI 单位"
                    if field in {"spend", "gmv", "roi", "gpm"}
                    else "并核对字段、时间范围与报表维度"
                )
                solutions.append(
                    f"确认 {QianchuanMCPClient.LIVE_REPORT_TOOL} 已开放{label}字段，{unit_hint}。"
                )
        if not flows:
            missing_reasons.append("MCP 未返回流量渠道拆分")
            solutions.append("申请直播流量来源字段读取权限，或检查 MCP 工具是否返回 AllEcomFlowSource。")
        if not users:
            missing_reasons.append("MCP 未返回用户画像维度")
            solutions.append("申请直播用户洞察字段读取权限，补充性别、年龄、地域维度。")
        history = self._campaign_history_basis(account)
        history_points = self.live_history_snapshot(account_id, bucket_minutes=5)
        anomalies: list[dict[str, Any]] = []
        points = history_points.get("points") or []
        for previous, current in zip(points, points[1:]):
            spend_delta = (to_number(current.get("spend")) or 0) - (
                to_number(previous.get("spend")) or 0
            )
            gmv_delta = (to_number(current.get("gmv")) or 0) - (
                to_number(previous.get("gmv")) or 0
            )
            watch_delta = (to_number(current.get("watch")) or 0) - (
                to_number(previous.get("watch")) or 0
            )
            interval_roi = gmv_delta / spend_delta if spend_delta > 0 else None
            if spend_delta > 0 and (
                (interval_roi is not None and interval_roi < CAMPAIGN_TARGET_ROI * 0.7)
                or watch_delta <= 0
            ):
                tone = "高" if interval_roi is not None and interval_roi < CAMPAIGN_TARGET_ROI * 0.4 else "中"
                anomalies.append(
                    {
                        "time": current.get("time") or "",
                        "severity": tone,
                        "metric": (
                            f"5 分钟消耗增加 ¥{spend_delta:.2f}，"
                            f"成交增加 ¥{gmv_delta:.2f}，观看变化 {watch_delta:+.0f}"
                        ),
                        "cause": "基于直播大屏历史快照的增量推断，非后台事件日志",
                        "suggestion": (
                            "先检查该时段付费渠道和素材，优先控量而非继续放量。"
                            if interval_roi is not None and interval_roi < CAMPAIGN_TARGET_ROI
                            else "检查进人渠道是否断档，补充互动和福利承接。"
                        ),
                    }
                )
        anomalies = anomalies[-5:]

        usable = any(metrics.get(key) is not None for key in ("spend", "gmv", "orders", "roi"))
        roi_value = to_number(metrics.get("roi"))
        cost_value = to_number(metrics.get("cost"))
        if not usable:
            decision = {
                "action": "等待 MCP 实时数据",
                "percent": 0,
                "confidence": 0,
                "reason": error or "MCP 未返回可用直播投放指标。",
                "guardrail": "数据恢复前不执行放量、追投或控量。",
                "expected": ["不操作", "先修复 MCP 取数"],
            }
        elif cost_value is not None and cost_value > CAMPAIGN_TARGET_COST:
            decision = {
                "action": "一键控量",
                "percent": 10,
                "confidence": 68,
                "reason": (
                    f"当前成交成本 ¥{cost_value:.2f}，高于目标 ¥{CAMPAIGN_TARGET_COST:.0f}；"
                    "按大数据规则先降低低效消耗。"
                ),
                "guardrail": f"成交成本回到 ¥{CAMPAIGN_TARGET_COST:.0f} 以下再恢复。",
                "expected": ["消耗下降", "成本回落", "保留高 ROI 素材"],
            }
        elif roi_value is not None and roi_value >= CAMPAIGN_TARGET_ROI:
            decision = {
                "action": "控成本追投",
                "percent": 5,
                "confidence": 62,
                "reason": (
                    f"当前 ROI {roi_value:.2f} 已达到参考线 {CAMPAIGN_TARGET_ROI:.2f}，"
                    "小步追投并保留成本上限。"
                ),
                "guardrail": f"ROI 低于 {CAMPAIGN_TARGET_ROI:.2f} 或成本高于 ¥{CAMPAIGN_TARGET_COST:.0f} 时停止。",
                "expected": ["消耗 +5%", "订单小步增加", "ROI 保持接近当前值"],
            }
        else:
            decision = {
                "action": "暂停放量",
                "percent": 0,
                "confidence": 58,
                "reason": (
                    f"当前 ROI {roi_value if roi_value is not None else '—'} 低于参考线 "
                    f"{CAMPAIGN_TARGET_ROI:.2f}，先修复承接再增加预算。"
                ),
                "guardrail": "连续两个 5 分钟窗口未改善时不恢复预算。",
                "expected": ["保持监控", "优化素材和人群", "等待 ROI 回升"],
            }
        payload = {
            "ok": bool(record),
            "status": "ok" if record and not missing_reasons else "partial" if record else "error",
            "source": "qianchuan_mcp_realtime",
            "sourceLabel": f"千川 MCP · {tool} · 实时取数",
            "tool": tool,
            "room": {
                "id": str(record.get("room_id") or ""),
                "title": record.get("room_title"),
                "status": record.get("room_status"),
                "startTime": record.get("start_time"),
                "awemeId": str(record.get("aweme_id") or ""),
                "awemeName": record.get("aweme_name"),
            },
            "metrics": metrics,
            "moneyDivisor": divisor,
            "flows": flows,
            "users": users,
            "history": history,
            "anomalies": anomalies,
            "decision": decision,
            "targets": {
                "cost": CAMPAIGN_TARGET_COST,
                "productPrice": CAMPAIGN_PRODUCT_PRICE,
                "roi": CAMPAIGN_TARGET_ROI,
            },
            "missingReasons": missing_reasons,
            "solutions": solutions,
            "error": error,
            "syncedAt": now_iso(),
        }
        with self.live_lock:
            self.campaign_cache[cache_key] = (time.time(), copy.deepcopy(payload))
        return copy.deepcopy(payload)

    def discover_live_room(self, account_id: str | None = None) -> dict[str, Any]:
        """Return the currently living Qianchuan room from the official Open API."""
        dashboard = self.dashboard()
        accounts = dashboard.get("accounts") or []
        account = next(
            (
                item
                for item in accounts
                if account_id in {
                    item.get("id"),
                    item.get("awemeId"),
                    item.get("advertiserId"),
                    item.get("qianchuanId"),
                }
            ),
            accounts[0] if accounts else None,
        )
        if not account:
            return {"live": False, "error": "没有可用广告账户", "rooms": []}
        config = load_config()
        config_account = next(
            (
                item
                for item in config.get("accounts", [])
                if str(item.get("advertiserId")) == str(account.get("advertiserId"))
            ),
            {},
        )
        aweme_ids = (
            [str(account.get("awemeId"))]
            if account.get("awemeId")
            else config_account.get("awemeIds")
            or account.get("awemeIds")
            or DEFAULT_ACCOUNT["awemeIds"]
        )
        token, _token_info, credential_errors = resolve_access_token(config)
        if not token:
            return {
                "live": False,
                "error": (
                    credential_errors[0]["message"]
                    if credential_errors
                    else "未配置千川凭证"
                ),
                "rooms": [],
            }
        client = QianchuanClient(config, token)
        rooms: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        advertiser_id = str(account.get("advertiserId") or account.get("qianchuanId"))
        today = date.today().isoformat()
        for aweme_id in aweme_ids:
            try:
                rooms.extend(
                    client.fetch_live_rooms(advertiser_id, str(aweme_id), today)
                )
            except QianchuanAPIError as exc:
                errors.append({"awemeId": str(aweme_id), "message": str(exc)})
        living = next(
            (
                room
                for room in rooms
                if str(room.get("room_status") or "").upper() == "LIVING"
            ),
            None,
        )
        return {
            "live": bool(living),
            "advertiserId": advertiser_id,
            "roomId": str((living or {}).get("room_id") or ""),
            "awemeId": str(
                (living or {}).get("aweme_id")
                or (living or {}).get("awemeId")
                or ""
            ),
            "room": copy.deepcopy(living) if living else None,
            "rooms": copy.deepcopy(rooms),
            "errors": errors,
            "source": "qianchuan_open_api_today_live",
            "sourceLabel": "千川今日直播间 Open API",
            "syncedAt": now_iso(),
        }

    def compare_live_sources(self, account_id: str | None = None) -> dict[str, Any]:
        """Compare today's room API fields with the headless live-screen capture."""
        discovered = self.discover_live_room(account_id)
        if not discovered.get("live") or not isinstance(discovered.get("room"), dict):
            return {
                "ok": False,
                "live": False,
                "openApi": discovered,
                "screen": self.live_screen_status(),
                "comparison": [],
                "syncedAt": now_iso(),
            }
        config = load_config()
        token, _token_info, credential_errors = resolve_access_token(config)
        if not token:
            return {
                "ok": False,
                "live": True,
                "error": (
                    credential_errors[0]["message"]
                    if credential_errors
                    else "未配置千川凭证"
                ),
                "openApi": discovered,
                "screen": self.live_screen_status(),
                "comparison": [],
                "syncedAt": now_iso(),
            }
        client = QianchuanClient(config, token)
        room = discovered["room"]
        api_metrics = {
            "spend": client._live_money(room.get("stat_cost")),
            "gmv": client._live_money(
                room.get("live_pay_order_gmv_alias")
                or room.get("luban_live_pay_order_gmv")
            ),
            "orders": to_number(
                room.get("live_pay_order_count_alias")
                or room.get("luban_live_pay_order_count")
            )
            or 0,
            "roi": to_number(
                room.get("live_pay_order_gmv_roi")
                or room.get("ad_live_prepay_and_pay_order_gmv_roi")
            ),
            "watchCount": to_number(room.get("total_live_watch_cnt")) or 0,
            "productClicks": to_number(room.get("live_click_product_count_alias")) or 0,
            "watchOneMinute": to_number(room.get("live_watch_one_minute_count")) or 0,
            "comments": to_number(room.get("total_live_comment_cnt")) or 0,
        }
        screen_payload = self.live_screen_status()
        screen_metrics = (
            screen_payload.get("metrics")
            if isinstance(screen_payload.get("metrics"), dict)
            else {}
        )
        labels = {
            "spend": "消耗",
            "gmv": "成交金额",
            "orders": "成交订单",
            "roi": "ROI",
            "watchCount": "累计观看",
            "productClicks": "商品点击",
        }
        comparison = []
        for key, label in labels.items():
            api_value = api_metrics.get(key)
            screen_value = to_number(screen_metrics.get(key))
            comparison.append(
                {
                    "field": key,
                    "label": label,
                    "openApi": api_value,
                    "screen": screen_value,
                    "delta": (
                        round(screen_value - float(api_value), 4)
                        if screen_value is not None and api_value is not None
                        else None
                    ),
                    "bothAvailable": api_value is not None and screen_value is not None,
                }
            )
        for key, label in (
            ("watchOneMinute", "观看满 1 分钟"),
            ("comments", "累计评论"),
        ):
            comparison.append(
                {
                    "field": key,
                    "label": label,
                    "openApi": api_metrics.get(key),
                    "screen": None,
                    "delta": None,
                    "bothAvailable": False,
                }
            )
        for key, label in (
            ("exposure", "曝光次数"),
            ("gpm", "GPM"),
            ("online", "实时在线"),
            ("peakOnline", "观测峰值"),
        ):
            comparison.append(
                {
                    "field": key,
                    "label": label,
                    "openApi": None,
                    "screen": to_number(screen_metrics.get(key)),
                    "delta": None,
                    "bothAvailable": False,
                }
            )
        return {
            "ok": True,
            "live": True,
            "roomId": discovered.get("roomId"),
            "awemeId": discovered.get("awemeId"),
            "openApiMetrics": api_metrics,
            "screenMetrics": copy.deepcopy(screen_metrics),
            "comparison": comparison,
            "openApi": {
                "source": discovered.get("source"),
                "sourceLabel": discovered.get("sourceLabel"),
                "syncedAt": discovered.get("syncedAt"),
                "errors": discovered.get("errors") or [],
            },
            "screen": {
                "status": screen_payload.get("status"),
                "syncedAt": screen_payload.get("syncedAt"),
                "roomId": (screen_payload.get("room") or {}).get("id"),
                "error": screen_payload.get("error"),
            },
            "syncedAt": now_iso(),
        }

    def live_trade_snapshot(self, advertiser_id: str) -> dict[str, Any]:
        cache_seconds = 10.0
        cache_key = str(advertiser_id)
        with self.live_lock:
            cached = self.live_trade_cache.get(cache_key)
            if cached and time.time() - cached[0] < cache_seconds:
                return copy.deepcopy(cached[1])
        client = self._get_mcp_client()
        if client is None:
            payload = {
                "ok": False,
                "status": "unconfigured",
                "source": "qianchuan_mcp",
                "sourceLabel": "千川 MCP 交易通道未配置",
                "tool": QianchuanMCPClient.UNI_PROMOTION_REPORT_TOOL,
                "metrics": {},
                "error": "未配置千川 MCP",
                "syncedAt": now_iso(),
            }
        else:
            now = datetime.now().astimezone()
            today = now.date().isoformat()
            start_time = f"{today} 00:00:00"
            end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            try:
                report = client.fetch_uni_promotion_trade(
                    str(advertiser_id),
                    start_time,
                    end_time,
                )
                record = report.get("record") or {}
                spend = round(to_number(record.get("stat_cost")) or 0.0, 2)
                gmv = round(
                    to_number(record.get("total_pay_order_gmv_for_roi2")) or 0.0,
                    2,
                )
                orders = round(
                    to_number(record.get("total_pay_order_count_for_roi2")) or 0.0,
                    4,
                )
                roi = to_number(
                    record.get("total_prepay_and_pay_order_roi2")
                )
                if roi is None:
                    roi = gmv / spend if spend else 0.0
                payload = {
                    "ok": True,
                    "status": "ok",
                    "source": "qianchuan_mcp",
                    "sourceLabel": (
                        "千川 MCP · qianchuan_report_uni_promotion_get_v1"
                    ),
                    "tool": report["tool"],
                    "arguments": report.get("arguments") or {},
                    "metrics": {
                        "spend": spend,
                        "gmv": gmv,
                        "orders": orders,
                        "roi": round(float(roi or 0.0), 4),
                    },
                    "raw": copy.deepcopy(record),
                    "error": "",
                    "syncedAt": now_iso(),
                }
                with self.live_lock:
                    self.live_trade_cache[cache_key] = (
                        time.time(),
                        copy.deepcopy(payload),
                    )
            except QianchuanMCPError as exc:
                with self.live_lock:
                    previous = self.live_trade_cache.get(cache_key)
                if previous and previous[1].get("metrics"):
                    payload = copy.deepcopy(previous[1])
                    payload.update(
                        {
                            "ok": False,
                            "status": "stale",
                            "error": str(exc),
                            "staleWarning": str(exc),
                        }
                    )
                else:
                    payload = {
                        "ok": False,
                        "status": "error",
                        "source": "qianchuan_mcp",
                        "sourceLabel": (
                            "千川 MCP · qianchuan_report_uni_promotion_get_v1"
                        ),
                        "tool": QianchuanMCPClient.UNI_PROMOTION_REPORT_TOOL,
                        "metrics": {},
                        "error": str(exc),
                        "syncedAt": now_iso(),
                    }
        with self.live_lock:
            self.live_trade_cache[cache_key] = (
                time.time(),
                copy.deepcopy(payload),
            ) if payload.get("metrics") else self.live_trade_cache.get(cache_key, (0, payload))
        return copy.deepcopy(payload)

    def live_snapshot(self, account_id: str | None = None) -> dict[str, Any]:
        account = self._account_for(account_id)
        if not account:
            return {
                "live": False,
                "error": "没有可用广告账户",
                "syncedAt": now_iso(),
            }
        cache_key = str(account.get("id"))
        config = load_config()
        live_config = config.get("live", DEFAULT_LIVE_CONFIG)
        cache_seconds = max(5, int(live_config.get("cacheSeconds", 10)))
        with self.live_lock:
            cached = self.live_cache.get(cache_key)
            if cached and time.time() - cached[0] < cache_seconds:
                return copy.deepcopy(cached[1])

        behavior = self.live_screen_status()
        behavior_metrics = (
            behavior.get("metrics")
            if isinstance(behavior.get("metrics"), dict)
            else {}
        )
        metrics = {
            key: value
            for key, value in copy.deepcopy(behavior_metrics).items()
            if value is not None
        }
        try:
            five_dimension = self.live_five_dimension(account.get("id"), metrics)
        except Exception as exc:
            five_dimension = self._five_dimension_payload(
                metrics,
                {},
                mcp_error=f"MCP 五维补充失败，已使用直播大屏数据：{exc}",
                mcp_status="error",
            )
        history = self.live_history_snapshot(
            account.get("id"),
            bucket_minutes=5,
            five_dimension=five_dimension,
            lightweight=True,
        )
        screen_status = str(behavior.get("status") or "missing")
        login_required = screen_status == "login_required"
        screen_ready = (
            screen_status in {"ok", "partial", "stale"}
            and not bool(behavior.get("stale"))
        )
        trade_keys = ("spend", "gmv", "orders", "orderCost", "roi")
        behavior_keys = ("watchCount", "productClicks", "gpm", "online")
        missing_trade = [key for key in trade_keys if metrics.get(key) is None]
        missing_behavior = [key for key in behavior_keys if metrics.get(key) is None]
        trade_ok = screen_ready and not missing_trade
        behavior_ok = screen_ready and not missing_behavior
        live = screen_ready and bool(metrics)

        errors: list[dict[str, Any]] = []
        if not trade_ok:
            errors.append(
                {
                    "scope": "screen_trade",
                    "code": f"screen_trade_{screen_status}",
                    "message": (
                        "直播大屏交易字段抓取失败："
                        + (
                            "登录已过期，请重新登录"
                            if login_required
                            else (
                                "缺少 " + "、".join(missing_trade)
                                if missing_trade
                                else str(behavior.get("error") or "大屏采集不可用")
                            )
                        )
                    ),
                }
            )
        if not behavior_ok:
            errors.append(
                {
                    "scope": "screen_behavior",
                    "code": f"screen_behavior_{screen_status}",
                    "message": (
                        "直播大屏行为字段抓取失败："
                        + (
                            "登录已过期，请重新登录"
                            if login_required
                            else (
                                "缺少 " + "、".join(missing_behavior)
                                if missing_behavior
                                else str(behavior.get("error") or "大屏采集不可用")
                            )
                        )
                    ),
                }
            )
        room = copy.deepcopy(behavior.get("room") or {})
        if behavior.get("pageTitle") and not room.get("title"):
            room["title"] = behavior.get("pageTitle")
        flow_map: dict[str, float] = {}
        flow_items = behavior.get("flows") if isinstance(behavior.get("flows"), list) else []
        for item in flow_items:
            if not isinstance(item, dict):
                continue
            value = to_number(item.get("value"))
            key = str(item.get("key") or "").strip()
            if key and value is not None:
                flow_map[key] = value
        trade_channel = {
            "ok": trade_ok,
            "status": "ok" if trade_ok else "error" if not metrics else "partial",
            "source": "puppeteer-core_screen_direct",
            "sourceLabel": "千川直播大屏页面 · 直接抓取",
            "metrics": {
                key: metrics[key]
                for key in trade_keys
                if metrics.get(key) is not None
            },
            "missingMetrics": missing_trade,
            "error": (
                ""
                if trade_ok
                else "登录已过期，请重新登录"
                if login_required
                else "大屏交易字段抓取失败，未使用 MCP 兜底"
            ),
            "syncedAt": behavior.get("syncedAt") or now_iso(),
        }
        behavior_channel = {
            "ok": behavior_ok,
            "status": "ok" if behavior_ok else "error" if not metrics else "partial",
            "source": "puppeteer-core_screen_direct",
            "sourceLabel": "千川直播大屏页面 · 直接抓取",
            "metrics": {
                key: metrics[key]
                for key in behavior_keys
                if metrics.get(key) is not None
            },
            "missingMetrics": missing_behavior,
            "error": (
                ""
                if behavior_ok
                else "登录已过期，请重新登录"
                if login_required
                else "大屏行为字段抓取失败"
            ),
            "syncedAt": behavior.get("syncedAt") or now_iso(),
        }
        payload = {
            "live": live,
            "room": room,
            "metrics": metrics,
            "fiveDimension": five_dimension,
            "flows": {"AllEcomFlowSource": flow_map} if flow_map else {},
            "flowItems": copy.deepcopy(flow_items),
            "users": {},
            "products": [],
            "stream": {
                "url": str(live_config.get("streamUrl") or "").strip(),
                "type": str(live_config.get("streamType") or "auto").strip(),
                "source": str(live_config.get("streamSource") or "").strip(),
            },
            "errors": errors,
            "syncedAt": now_iso(),
            "date": date.today().isoformat(),
            "captureStatus": screen_status,
            "loginRequired": login_required,
            "source": "qianchuan_live_screen_direct",
            "sourceLabel": "千川直播大屏 · 页面直接抓取",
            "peakOnlineSource": behavior.get("peakOnlineSource"),
            "peakObservedAt": behavior.get("peakObservedAt"),
            "tradeRefundPolicy": "screen_displayed",
            "tradeRefundPolicyLabel": "直播大屏页面当前展示口径",
            "behaviorPolicy": "screen_cumulative",
            "channels": {
                "trade": trade_channel,
                "behavior": behavior_channel,
                "screen": copy.deepcopy(behavior),
            },
            "history": history,
            "staleWarning": (
                f"直播大屏心跳已延迟 {behavior.get('ageSeconds')} 秒，当前值不视为有效"
                if behavior.get("stale")
                else (
                    str(behavior.get("staleWarning") or "采集器本轮沿用上一次有效指标")
                    if screen_status == "stale"
                    else ""
                )
            ),
            "error": (
                ""
                if live
                else "登录已过期，请重新登录"
                if login_required
                else str(behavior.get("error") or "直播大屏抓取失败")
            ),
        }
        with self.live_lock:
            self.live_cache[cache_key] = (time.time(), copy.deepcopy(payload))
        return copy.deepcopy(payload)

    def _legacy_live_snapshot(self, account_id: str | None = None) -> dict[str, Any]:
        dashboard = self.dashboard()
        accounts = dashboard.get("accounts") or []
        account = next(
            (
                item
                for item in accounts
                if account_id in {
                    item.get("id"),
                    item.get("awemeId"),
                    item.get("advertiserId"),
                    item.get("qianchuanId"),
                }
            ),
            accounts[0] if accounts else None,
        )
        if not account:
            return {"live": False, "error": "没有可用广告账户", "syncedAt": now_iso()}
        cache_key = str(account.get("id"))
        config = load_config()
        live_config = config.get("live", DEFAULT_LIVE_CONFIG)
        cache_seconds = max(5, int(live_config.get("cacheSeconds", 20)))
        with self.live_lock:
            cached = self.live_cache.get(cache_key)
            if cached and time.time() - cached[0] < cache_seconds:
                return copy.deepcopy(cached[1])

        advertiser_id = str(account.get("advertiserId") or account.get("qianchuanId"))
        config_account = next(
            (
                item
                for item in config.get("accounts", [])
                if str(item.get("advertiserId")) == advertiser_id
            ),
            {},
        )
        aweme_ids = (
            [str(account.get("awemeId"))]
            if account.get("awemeId")
            else config_account.get("awemeIds")
            or account.get("awemeIds")
            or DEFAULT_ACCOUNT["awemeIds"]
        )
        room_date = date.today().isoformat()
        errors: list[dict[str, Any]] = []

        mcp_client = self._get_mcp_client()
        mcp_config = load_mcp_config()
        if mcp_client is not None and bool(mcp_config.get("rawVerified", False)):
            for aweme_id in aweme_ids:
                try:
                    mcp_live = mcp_client.fetch_live_room(
                        advertiser_id,
                        str(aweme_id),
                        room_date,
                    )
                    live_room = mcp_live["room"]
                    room_id = str(live_room.get("room_id") or "")
                    report_mode = (
                        mcp_live["tool"] == QianchuanMCPClient.LIVE_REPORT_TOOL
                    )
                    divisor = (
                        1.0
                        if report_mode
                        else float(live_config.get("moneyDivisor") or 1)
                    )

                    def mcp_money(value: Any) -> float:
                        number = to_number(value)
                        return round(number / divisor, 2) if number is not None and divisor else 0.0

                    live_orders = to_number(
                        live_room.get("pay_order_count")
                        or live_room.get("total_pay_order_count_for_roi2")
                        or live_room.get("luban_live_pay_order_count")
                        or live_room.get("live_pay_order_count_alias")
                    ) or 0
                    live_gmv = mcp_money(
                        live_room.get("pay_order_amount")
                        or live_room.get("total_pay_order_gmv_for_roi2")
                        or live_room.get("luban_live_pay_order_gmv")
                        or live_room.get("live_pay_order_gmv_alias")
                    )
                    live_spend = mcp_money(live_room.get("stat_cost"))
                    live_watch = to_number(
                        live_room.get("total_live_watch_cnt")
                        or live_room.get("live_watch_count")
                        or live_room.get("watch_count")
                    ) or 0
                    live_watch_one_minute = to_number(
                        live_room.get("live_watch_one_minute_count")
                        or live_room.get("watch_one_minute_count")
                    ) or 0
                    mcp_flows: dict[str, Any] = {}
                    for raw in QianchuanMCPClient.iter_dicts(mcp_live.get("payload")):
                        if "AllEcomFlowSource" in raw and isinstance(
                            raw["AllEcomFlowSource"], dict
                        ):
                            mcp_flows["AllEcomFlowSource"] = copy.deepcopy(
                                raw["AllEcomFlowSource"]
                            )
                        if "AllEcomGmvSource" in raw and isinstance(
                            raw["AllEcomGmvSource"], dict
                        ):
                            mcp_flows["AllEcomGmvSource"] = copy.deepcopy(
                                raw["AllEcomGmvSource"]
                            )
                    mcp_payload = {
                        "live": True,
                        "room": {
                            "id": room_id,
                            "title": live_room.get("room_title"),
                            "status": live_room.get("room_status")
                            or ("REPORT" if report_mode else "LIVING"),
                            "cover": (live_room.get("room_cover") or [None])[0],
                            "startTime": live_room.get("start_time"),
                            "endTime": live_room.get("end_time"),
                            "awemeId": str(live_room.get("aweme_id") or aweme_id),
                            "awemeName": live_room.get("aweme_name"),
                            "awemeAvatar": (live_room.get("aweme_avatar") or [None])[0],
                        },
                        "metrics": {
                            "spend": live_spend,
                            "watchCount": live_watch,
                            "watchOneMinute": live_watch_one_minute,
                            "orders": live_orders,
                            "gmv": live_gmv,
                            "ordersBeforeRefund": live_orders,
                            "gmvBeforeRefund": live_gmv,
                            "roi": to_number(
                                live_room.get("live_pay_order_gmv_roi")
                                or live_room.get("ad_live_prepay_and_pay_order_gmv_roi")
                            ) or (live_gmv / live_spend if live_spend else 0),
                            "cvr": to_number(
                                live_room.get("ecp_convert_rate")
                                or live_room.get("live_pay_order_rate")
                            ),
                            "productClicks": to_number(
                                live_room.get("live_click_product_count_alias")
                            ) or 0,
                            "comments": to_number(live_room.get("total_live_comment_cnt")) or 0,
                            "follows": to_number(live_room.get("total_live_follow_cnt")) or 0,
                            "deliveryPlans": to_number(live_room.get("room_delivery")) or 0,
                        },
                        "flows": mcp_flows,
                        "users": {},
                        "products": [],
                        "stream": {
                            "url": str(live_config.get("streamUrl") or "").strip(),
                            "type": str(live_config.get("streamType") or "auto").strip(),
                            "source": str(live_config.get("streamSource") or "").strip(),
                        },
                        "errors": [],
                        "syncedAt": now_iso(),
                        "date": room_date,
                        "reportMode": report_mode,
                        "source": "qianchuan_mcp_live_screen",
                        "sourceLabel": f"千川 MCP · {mcp_live['tool']}",
                        "refundPolicy": "before_refund",
                        "refundPolicyLabel": "退款前",
                        "mcp": {
                            "tool": mcp_live["tool"],
                            "arguments": mcp_live.get("arguments") or {},
                        },
                    }
                    with self.mcp_lock:
                        self.mcp_last_error = None
                    with self.live_lock:
                        self.live_cache[cache_key] = (time.time(), mcp_payload)
                    return copy.deepcopy(mcp_payload)
                except QianchuanMCPError as exc:
                    errors.append(
                        {
                            "scope": "mcp_live",
                            "awemeId": str(aweme_id),
                            "message": str(exc),
                        }
                    )
            with self.mcp_lock:
                self.mcp_last_error = errors[-1]["message"] if errors else None

        access_token, _token_info, credential_errors = resolve_access_token(config)
        if not access_token:
            return {
                "live": False,
                "error": credential_errors[0]["message"] if credential_errors else "未配置千川凭证",
                "syncedAt": now_iso(),
            }
        client = QianchuanClient(config, access_token)
        rooms: list[dict[str, Any]] = []
        for aweme_id in aweme_ids:
            try:
                rooms.extend(client.fetch_live_rooms(advertiser_id, str(aweme_id), room_date))
            except QianchuanAPIError as exc:
                errors.append({"awemeId": str(aweme_id), "message": str(exc)})
        live_room = next((room for room in rooms if str(room.get("room_status")) == "LIVING"), None)
        if not live_room:
            payload = {
                "live": False,
                "rooms": rooms,
                "errors": errors,
                "syncedAt": now_iso(),
                "date": room_date,
                "source": "qianchuan_live_screen",
                "sourceLabel": "千川直播大屏数据",
                "refundPolicy": "before_refund",
                "refundPolicyLabel": "退款前",
            }
            with self.live_lock:
                self.live_cache[cache_key] = (time.time(), payload)
            return copy.deepcopy(payload)

        room_id = str(live_room.get("room_id"))
        flows: dict[str, Any] = {}
        users: dict[str, Any] = {}
        products: list[dict[str, Any]] = []
        for source in live_config.get("flowSources", DEFAULT_LIVE_CONFIG["flowSources"]):
            try:
                flows[source] = client.fetch_live_flow(advertiser_id, room_id, source)
            except QianchuanAPIError as exc:
                errors.append({"scope": "flow", "source": source, "message": str(exc)})
        for action in ("ENTER", "PAY"):
            try:
                users[action] = client.fetch_live_users(advertiser_id, room_id, action)
            except QianchuanAPIError as exc:
                errors.append({"scope": "users", "action": action, "message": str(exc)})
        try:
            products = client.fetch_live_products(advertiser_id, room_id)
        except QianchuanAPIError as exc:
            errors.append({"scope": "products", "message": str(exc)})

        live_orders = to_number(
            live_room.get("luban_live_pay_order_count")
            or live_room.get("live_pay_order_count_alias")
        ) or 0
        live_gmv = client._live_money(
            live_room.get("luban_live_pay_order_gmv")
            or live_room.get("live_pay_order_gmv_alias")
        )
        metrics = {
            "spend": client._live_money(live_room.get("stat_cost")),
            "watchCount": to_number(live_room.get("total_live_watch_cnt")) or 0,
            "watchOneMinute": to_number(live_room.get("live_watch_one_minute_count")) or 0,
            "orders": live_orders,
            "gmv": live_gmv,
            "ordersBeforeRefund": live_orders,
            "gmvBeforeRefund": live_gmv,
            "roi": to_number(
                live_room.get("live_pay_order_gmv_roi") or live_room.get("ad_live_prepay_and_pay_order_gmv_roi")
            ),
            "cvr": to_number(live_room.get("ecp_convert_rate") or live_room.get("live_pay_order_rate")),
            "productClicks": to_number(live_room.get("live_click_product_count_alias")) or 0,
            "comments": to_number(live_room.get("total_live_comment_cnt")) or 0,
            "follows": to_number(live_room.get("total_live_follow_cnt")) or 0,
            "deliveryPlans": to_number(live_room.get("room_delivery")) or 0,
        }
        payload = {
            "live": True,
            "room": {
                "id": room_id,
                "title": live_room.get("room_title"),
                "status": live_room.get("room_status"),
                "cover": (live_room.get("room_cover") or [None])[0],
                "startTime": live_room.get("start_time"),
                "endTime": live_room.get("end_time"),
                "awemeId": str(live_room.get("aweme_id") or ""),
                "awemeName": live_room.get("aweme_name"),
                "awemeAvatar": (live_room.get("aweme_avatar") or [None])[0],
            },
            "metrics": metrics,
            "flows": flows,
            "users": users,
            "products": products,
            "stream": {
                "url": str(live_config.get("streamUrl") or "").strip(),
                "type": str(live_config.get("streamType") or "auto").strip(),
                "source": str(live_config.get("streamSource") or "").strip(),
            },
            "errors": errors,
            "syncedAt": now_iso(),
            "date": room_date,
            "source": "qianchuan_live_screen",
            "sourceLabel": "千川直播大屏数据",
            "refundPolicy": "before_refund",
            "refundPolicyLabel": "退款前",
        }
        with self.live_lock:
            self.live_cache[cache_key] = (time.time(), payload)
        return copy.deepcopy(payload)


class LiveStreamRegistry:
    """Short-lived, in-memory registry for signed live stream URLs.

    Qianchuan's board page receives a signed HTTP-FLV URL from an internal
    endpoint.  The URL is deliberately kept only in memory and is never
    written to the snapshot or logs.
    """

    def __init__(self, ttl_seconds: int = 1800) -> None:
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.lock = threading.Lock()
        self.rooms: dict[str, dict[str, Any]] = {}
        self.heartbeat_at = 0.0

    @staticmethod
    def _room_id(value: Any) -> str:
        room_id = "".join(char for char in str(value or "") if char.isalnum() or char in "-_")[:64]
        if not room_id:
            raise ValueError("缺少直播间 roomId")
        return room_id

    @staticmethod
    def _stream_type(url: str, hint: Any = "") -> str:
        value = str(hint or "").strip().lower()
        if value in {"flv", "hls", "mp4", "native"}:
            return value
        path = urllib.parse.urlparse(url).path.lower()
        if path.endswith(".flv"):
            return "flv"
        if path.endswith(".m3u8"):
            return "hls"
        if path.endswith((".mp4", ".webm")):
            return "mp4"
        return "auto"

    @staticmethod
    def _validate_url(url: Any) -> str:
        value = str(url or "").strip()
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("直播流地址必须是有效的 http/https URL")
        host = (parsed.hostname or "").lower()
        if host not in {"douyincdn.com", "byteimg.com", "bytefcdnrd.com"} and not (
            host.endswith(".douyincdn.com")
            or host.endswith(".byteimg.com")
            or host.endswith(".bytefcdnrd.com")
        ):
            raise ValueError("仅接受千川直播画面使用的抖音 CDN 地址")
        return value

    def heartbeat(self, room_id: Any = None) -> dict[str, Any]:
        now = time.time()
        refreshed_room = ""
        with self.lock:
            self.heartbeat_at = now
            if room_id not in {None, ""}:
                try:
                    safe = self._room_id(room_id)
                except ValueError:
                    safe = ""
                if safe and safe in self.rooms:
                    self.rooms[safe]["capturedTimestamp"] = now
                    refreshed_room = safe
        return {
            "ok": True,
            "online": True,
            "roomId": refreshed_room,
            "heartbeatAt": now_iso(),
        }

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        room_id = self._room_id(payload.get("roomId") or payload.get("room_id"))
        url = self._validate_url(payload.get("url"))
        stream_type = self._stream_type(url, payload.get("type"))
        captured_at = time.time()
        with self.lock:
            self.rooms[room_id] = {
                "url": url,
                "type": stream_type,
                "source": "qianchuan-board",
                "sourceLabel": "千川直播大屏自动采集",
                "capturedAt": now_iso(),
                "capturedTimestamp": captured_at,
            }
            self.heartbeat_at = captured_at
        return {
            "ok": True,
            "roomId": room_id,
            "type": stream_type,
            "capturedAt": now_iso(),
        }

    def latest_room_id(self) -> str:
        """Return the newest fresh capture without exposing its signed URL."""
        now = time.time()
        with self.lock:
            fresh_rooms: list[tuple[float, str]] = []
            for room_id, entry in list(self.rooms.items()):
                captured_timestamp = float(entry.get("capturedTimestamp") or 0)
                if now - captured_timestamp > self.ttl_seconds:
                    self.rooms.pop(room_id, None)
                    continue
                fresh_rooms.append((captured_timestamp, room_id))
            return max(fresh_rooms, default=(0.0, ""))[1]

    def resolve(self, room_id: Any) -> dict[str, Any] | None:
        safe = self._room_id(room_id)
        now = time.time()
        with self.lock:
            entry = self.rooms.get(safe)
            if not entry:
                return None
            if now - float(entry.get("capturedTimestamp") or 0) > self.ttl_seconds:
                self.rooms.pop(safe, None)
                return None
            return copy.deepcopy(entry)

    def status(self, room_id: Any = None) -> dict[str, Any]:
        now = time.time()
        explicit_room = room_id not in {None, ""}
        with self.lock:
            online = bool(self.heartbeat_at and now - self.heartbeat_at <= 75)
            safe = ""
            if explicit_room:
                try:
                    safe = self._room_id(room_id)
                except ValueError:
                    safe = ""
            elif self.rooms:
                fresh_rooms: list[tuple[float, str]] = []
                for candidate_id, entry in list(self.rooms.items()):
                    captured_timestamp = float(entry.get("capturedTimestamp") or 0)
                    if now - captured_timestamp > self.ttl_seconds:
                        self.rooms.pop(candidate_id, None)
                        continue
                    fresh_rooms.append((captured_timestamp, candidate_id))
                safe = max(fresh_rooms, default=(0.0, ""))[1]
            entry = self.rooms.get(safe) if safe else None
            fresh = bool(
                entry
                and now - float(entry.get("capturedTimestamp") or 0) <= self.ttl_seconds
            )
            return {
                "ok": True,
                "online": online,
                "active": bool(online or fresh),
                "roomId": safe,
                "captured": fresh,
                "capturedAt": entry.get("capturedAt") if fresh else None,
                "source": "qianchuan-board" if fresh else "",
            }


DEFAULT_FFMPEG_PATHS = [
    os.getenv("QIANCHUAN_FFMPEG", "").strip(),
    r"C:\Program Files (x86)\MarukoToolbox\tools\ffmpeg.exe",
    r"C:\Program Files (x86)\damai\resources\app\node_modules\ffmpeg-static-electron\bin\win\x64\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
]


def resolve_ffmpeg() -> str:
    for candidate in DEFAULT_FFMPEG_PATHS:
        if candidate and Path(candidate).is_file():
            return candidate
    return shutil.which("ffmpeg") or ""


class StreamTranscoder:
    """Pull an RTMP/FLV/HLS source with ffmpeg and republish it as local HLS."""

    def __init__(self, hls_dir: Path) -> None:
        self.hls_dir = hls_dir
        self.hls_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = resolve_ffmpeg()
        self.lock = threading.Lock()
        self.processes: dict[str, dict[str, Any]] = {}

    @staticmethod
    def safe_key(value: Any) -> str:
        cleaned = "".join(char for char in str(value or "") if char.isalnum() or char in "-_")
        return cleaned[:48] or f"stream-{int(time.time())}"

    @staticmethod
    def _tail(path: Path, lines: int = 8) -> str:
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            return " | ".join(content[-lines:])
        except OSError:
            return ""

    def _stop_locked(self, key: str) -> None:
        entry = self.processes.pop(key, None)
        if not entry:
            return
        process: subprocess.Popen = entry["process"]
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
        finally:
            try:
                entry["log"].close()
            except OSError:
                pass

    def stop(self, key: Any) -> dict[str, Any]:
        safe = self.safe_key(key)
        with self.lock:
            self._stop_locked(safe)
        return {"ok": True, "key": safe, "stopped": True}

    def start(self, source: Any, key: Any, mode: Any = "auto", height: Any = 720) -> dict[str, Any]:
        source_url = str(source or "").strip()
        scheme = urllib.parse.urlparse(source_url).scheme.lower()
        if scheme not in {"rtmp", "rtmps", "http", "https"}:
            raise ValueError("只支持 rtmp / rtmps / http / https 拉流地址")
        if not self.ffmpeg:
            raise RuntimeError("未找到 ffmpeg，无法做 RTMP/FLV 转封装")
        safe = self.safe_key(key)
        out_dir = self.hls_dir / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        with self.lock:
            self._stop_locked(safe)
        for pattern in ("seg_*.ts", "index.m3u8"):
            for path in out_dir.glob(pattern):
                try:
                    path.unlink()
                except OSError:
                    pass
        resolved_mode = "transcode" if str(mode) == "transcode" else "copy"
        try:
            target_height = max(360, min(1080, int(height)))
        except (TypeError, ValueError):
            target_height = 720
        args = [self.ffmpeg, "-hide_banner", "-loglevel", "warning", "-y", "-i", source_url]
        if resolved_mode == "copy":
            args += ["-c", "copy"]
        else:
            args += [
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
                "-vf", f"scale=-2:{target_height}", "-c:a", "aac", "-b:a", "128k",
            ]
        args += [
            "-f", "hls",
            "-hls_time", "2",
            "-hls_list_size", "6",
            "-hls_flags", "delete_segments+omit_endlist",
            "-hls_segment_filename", str(out_dir / "seg_%05d.ts"),
            str(out_dir / "index.m3u8"),
        ]
        log_path = out_dir / "ffmpeg.log"
        log_handle = open(log_path, "ab", buffering=0)
        creation_flags = 0x08000000 if os.name == "nt" else 0
        process = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=log_handle, creationflags=creation_flags
        )
        with self.lock:
            self.processes[safe] = {
                "process": process,
                "log": log_handle,
                "logPath": log_path,
                "source": source_url,
                "mode": resolved_mode,
                "startedAt": now_iso(),
            }
        time.sleep(1.5)
        if process.poll() is not None:
            tail = self._tail(log_path)
            with self.lock:
                self._stop_locked(safe)
            raise RuntimeError(f"ffmpeg 启动失败：{tail or '未知错误'}")
        return {
            "ok": True,
            "key": safe,
            "url": f"/hls/{safe}/index.m3u8",
            "mode": resolved_mode,
            "source": source_url,
        }

    def status(self, key: Any) -> dict[str, Any]:
        safe = self.safe_key(key)
        with self.lock:
            entry = self.processes.get(safe)
            process = entry["process"] if entry else None
            alive = bool(process and process.poll() is None)
            info = {
                "ok": True,
                "key": safe,
                "alive": alive,
                "mode": entry.get("mode") if entry else None,
                "source": entry.get("source") if entry else None,
                "startedAt": entry.get("startedAt") if entry else None,
            }
        directory = self.hls_dir / safe
        info["playlist"] = (directory / "index.m3u8").exists()
        info["segments"] = len(list(directory.glob("seg_*.ts")))
        info["log"] = "" if alive else self._tail(directory / "ffmpeg.log")
        return info


def make_handler(
    store: DashboardStore,
    directory: Path,
    transcoder: StreamTranscoder | None = None,
    stream_registry: LiveStreamRegistry | None = None,
):
    if transcoder is None:
        transcoder = StreamTranscoder(HLS_DIR)
    if stream_registry is None:
        stream_registry = LiveStreamRegistry()
    learning_documents = LearningDocumentStore(directory)
    class DashboardHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def _capture_origin(self) -> str:
            origin = self.headers.get("Origin", "").strip()
            if not origin:
                return ""
            if origin.startswith("chrome-extension://"):
                return origin
            parsed = urllib.parse.urlparse(origin)
            if parsed.scheme in {"http", "https"} and parsed.hostname in {
                "127.0.0.1", "localhost", "::1"
            }:
                return origin
            return "__denied__"

        def _send_json(self, status: int, payload: Any, cors_origin: str = "") -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if cors_origin and cors_origin != "__denied__":
                self.send_header("Access-Control-Allow-Origin", cors_origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _relay_live_flv(self, room_id: str) -> None:
            try:
                stream = stream_registry.resolve(room_id)
            except ValueError:
                stream = None
            if not stream:
                self._send_json(404, {"error": "live_stream_unavailable"})
                return
            request = urllib.request.Request(
                stream["url"],
                headers={
                    "Accept": "*/*",
                    "Accept-Encoding": "identity",
                    "Cache-Control": "no-cache",
                    "Referer": "https://qianchuan.jinritemai.com/",
                    "User-Agent": "Mozilla/5.0 Qianchuan-Live-Relay/1.0",
                },
            )
            try:
                upstream = urllib.request.urlopen(request, timeout=20)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                self._send_json(502, {"error": "live_stream_upstream_failed", "message": str(exc)})
                return
            self.send_response(200)
            self.send_header("Content-Type", "video/x-flv")
            self.send_header("Cache-Control", "no-store, no-transform")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                while True:
                    chunk = upstream.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                pass
            finally:
                try:
                    upstream.close()
                except OSError:
                    pass

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if not length:
                return {}
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
            return data if isinstance(data, dict) else {}

        def _serve_hls(self, path: str) -> None:
            relative = urllib.parse.unquote(path[len("/hls/") :])
            base = HLS_DIR.resolve()
            target = (HLS_DIR / relative).resolve()
            if base not in target.parents or not target.is_file():
                self._send_json(404, {"error": "hls_not_found"})
                return
            content_type = {
                ".m3u8": "application/vnd.apple.mpegurl",
                ".ts": "video/mp2t",
                ".m4s": "video/iso.segment",
            }.get(target.suffix.lower(), "application/octet-stream")
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/learning/documents":
                try:
                    self._send_json(200, learning_documents.payload())
                except LearningDocumentError as exc:
                    self._send_json(exc.status, {"ok": False, "error": str(exc)})
                except Exception as exc:
                    self._send_json(
                        500,
                        {"ok": False, "error": f"学习资料读取失败：{exc}"},
                    )
                return
            if path == "/api/learning/search":
                query_values = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                query_text = (query_values.get("q") or [""])[0]
                try:
                    limit = int((query_values.get("limit") or ["3"])[0])
                except ValueError:
                    limit = 3
                try:
                    self._send_json(
                        200,
                        learning_documents.search(query_text, limit=limit),
                    )
                except LearningDocumentError as exc:
                    self._send_json(exc.status, {"ok": False, "error": str(exc)})
                except Exception as exc:
                    self._send_json(
                        500,
                        {"ok": False, "error": f"学习资料检索失败：{exc}"},
                    )
                return
            if path == "/api/learning/documents/download":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                document_id = (query.get("id") or [""])[0]
                try:
                    document, target = learning_documents.resolve(document_id)
                    body = target.read_bytes()
                    quoted_name = urllib.parse.quote(document["name"], safe="")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header(
                        "Content-Disposition",
                        (
                            f'attachment; filename="learning-document-{document["id"]}'
                            f'{document["extension"]}"; filename*=UTF-8\'\'{quoted_name}'
                        ),
                    )
                    self.end_headers()
                    self.wfile.write(body)
                except LearningDocumentError as exc:
                    self._send_json(exc.status, {"ok": False, "error": str(exc)})
                except Exception as exc:
                    self._send_json(
                        500,
                        {"ok": False, "error": f"学习资料下载失败：{exc}"},
                    )
                return
            if path == "/api/mcp/raw/live":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                advertiser_id = (query.get("advertiser_id") or ["1744479430946824"])[0]
                aweme_id = (query.get("aweme_id") or ["7637818476896437305"])[0]
                report_date = (query.get("date") or [date.today().isoformat()])[0]
                try:
                    self._send_json(
                        200,
                        store.mcp_raw_live_report(
                            str(advertiser_id),
                            str(aweme_id),
                            str(report_date),
                        ),
                    )
                except Exception as exc:
                    self._send_json(
                        502,
                        {
                            "ok": False,
                            "tool": QianchuanMCPClient.LIVE_REPORT_TOOL,
                            "advertiser_id": str(advertiser_id),
                            "aweme_id": str(aweme_id),
                            "date": str(report_date),
                            "error": f"千川 MCP 原始直播报表调用失败：{exc}",
                        },
                    )
                return
            if path == "/api/mcp/tools":
                try:
                    self._send_json(200, {"ok": True, "tools": store.mcp_tools()})
                except Exception as exc:
                    self._send_json(
                        502,
                        {"ok": False, "error": f"千川 MCP 工具读取失败：{exc}"},
                    )
                return
            if path == "/api/dashboard":
                payload = store.dashboard()
                payload["syncRequest"] = store.sync_state()
                self._send_json(200, payload)
                return
            if path == "/api/oauth/status":
                token_info = read_token_file(token_save_path())
                self._send_json(
                    200,
                    {
                        "ok": True,
                        **oauth_status_payload(token_info),
                    },
                )
                return
            if path.startswith("/hls/"):
                self._serve_hls(path)
                return
            if path == "/api/live/stream.flv":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                room_id = (query.get("room") or [""])[0]
                self._relay_live_flv(room_id)
                return
            if path == "/api/live/stream/status":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                room_id = (query.get("room") or [None])[0]
                origin = self._capture_origin()
                if origin == "__denied__":
                    self._send_json(403, {"ok": False, "error": "origin_not_allowed"})
                    return
                self._send_json(200, stream_registry.status(room_id), origin)
                return
            if path == "/api/stream/status":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                key = (query.get("key") or [""])[0]
                self._send_json(200, transcoder.status(key))
                return
            if path == "/api/live/screen":
                screen = store.live_screen_status()
                screen.pop("matches", None)
                self._send_json(200, screen)
                return
            if path == "/api/live/discover":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                account_id = (query.get("account") or [None])[0]
                try:
                    self._send_json(200, store.discover_live_room(account_id))
                except Exception as exc:
                    self._send_json(
                        502,
                        {
                            "live": False,
                            "error": f"当前直播间探测失败：{exc}",
                            "syncedAt": now_iso(),
                        },
                    )
                return
            if path == "/api/live/compare":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                account_id = (query.get("account") or [None])[0]
                try:
                    self._send_json(200, store.compare_live_sources(account_id))
                except Exception as exc:
                    self._send_json(
                        502,
                        {
                            "ok": False,
                            "error": f"直播数据源对比失败：{exc}",
                            "syncedAt": now_iso(),
                        },
                    )
                return
            if path == "/api/live/history":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                account_id = (query.get("account") or [None])[0]
                bucket = int((query.get("bucket") or ["5"])[0] or 5)
                self._send_json(
                    200,
                    store.live_history_snapshot(
                        account_id,
                        bucket_minutes=max(1, min(60, bucket)),
                    ),
                )
                return
            if path == "/api/campaign/diagnostics":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                account_id = (query.get("account") or [None])[0]
                try:
                    payload = store.campaign_diagnostics(account_id)
                    payload = enrich_campaign_with_learning(
                        payload,
                        learning_documents,
                    )
                    self._send_json(
                        200,
                        payload,
                    )
                except Exception as exc:
                    self._send_json(
                        200,
                        {
                            "ok": False,
                            "status": "error",
                            "source": "qianchuan_mcp_realtime",
                            "error": f"千川 MCP 投放诊断读取失败：{exc}",
                            "missingReasons": [f"千川 MCP 投放诊断读取失败：{exc}"],
                            "solutions": ["检查 MCP 连接、API Key 和直播报表工具权限。"],
                            "syncedAt": now_iso(),
                        },
                    )
                return
            if path == "/api/live":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                account_id = (query.get("account") or [None])[0]
                try:
                    payload = store.live_snapshot(account_id)
                    room_id = str((payload.get("room") or {}).get("id") or "")
                    # The metrics API can be temporarily rate-limited while the
                    # board page is still receiving a valid signed media stream.
                    # In that case keep the captured room id so the player remains
                    # available and expose the metrics failure separately.
                    if not room_id:
                        room_id = stream_registry.latest_room_id()
                    capture_status = stream_registry.status(room_id or None)
                    stream = payload.get("stream")
                    if not isinstance(stream, dict):
                        stream = {}
                        payload["stream"] = stream
                    captured = stream_registry.resolve(room_id) if room_id else None
                    if captured and not str(stream.get("url") or "").strip():
                        stream.update({
                            "url": captured["url"],
                            "type": captured["type"],
                            "source": captured["source"],
                            "sourceLabel": captured["sourceLabel"],
                            "capturedAt": captured["capturedAt"],
                            "roomId": room_id,
                        })
                    if captured and room_id:
                        stream["proxyUrl"] = (
                            "/api/live/stream.flv?room=" + urllib.parse.quote(room_id, safe="")
                        )
                    stream["capture"] = capture_status
                    self._send_json(200, payload)
                except Exception as exc:
                    self._send_json(
                        200,
                        {
                            "live": False,
                            "error": f"实时直播数据读取失败：{exc}",
                            "syncedAt": now_iso(),
                        },
                    )
                return
            if path == "/api/health":
                dashboard = store.dashboard()
                configured_token_file = os.getenv("QIANCHUAN_TOKEN_FILE", "").strip()
                health_token_path = Path(configured_token_file) if configured_token_file else TOKEN_FILE_PATH
                health_token = read_token_file(health_token_path)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "status": dashboard.get("syncStatus"),
                        "mode": dashboard.get("mode"),
                        "revision": dashboard.get("revision"),
                        "syncedAt": dashboard.get("syncedAt"),
                        "lastSyncAt": dashboard.get("lastSyncAt"),
                        "pollIntervalSeconds": dashboard.get("pollIntervalSeconds"),
                        "syncBackoffSeconds": dashboard.get("syncBackoffSeconds"),
                        "dataCutoff": dashboard.get("dataCutoff"),
                        "realtime": dashboard.get("realtime"),
                        "realtimeUpdatedAt": (dashboard.get("realtime") or {}).get("updatedAt"),
                        "mcpConfigured": bool(load_mcp_config().get("url")),
                        "mcpLastError": store.mcp_last_error,
                        "liveScreenCapture": {
                            key: value
                            for key, value in store.live_screen_status().items()
                            if key not in {"metrics", "matches"}
                        },
                        "syncRequest": store.sync_state(),
                        "reconciliation": next(
                            (
                                account.get("reconciliation")
                                for account in dashboard.get("accounts", [])
                                if account.get("reconciliation")
                            ),
                            None,
                        ),
                        "accountCount": len(dashboard.get("accounts", [])),
                        "streamCaptureOnline": bool(stream_registry.status().get("active")),
                        "oauth": oauth_status_payload(health_token),
                        "credentialsConfigured": bool(
                            os.getenv("QIANCHUAN_ACCESS_TOKEN", "").strip()
                            or health_token.get("accessToken")
                            or health_token.get("access_token")
                        ),
                    },
                )
                return
            super().do_GET()

        def do_OPTIONS(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            if path not in {"/api/live/stream", "/api/live/stream/heartbeat", "/api/live/stream/status"}:
                self._send_json(404, {"error": "not_found"})
                return
            origin = self._capture_origin()
            if origin == "__denied__":
                self._send_json(403, {"ok": False, "error": "origin_not_allowed"})
                return
            self.send_response(204)
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            origin = self._capture_origin()
            if path == "/api/learning/reindex":
                try:
                    self._send_json(200, learning_documents.reindex_all())
                except LearningDocumentError as exc:
                    self._send_json(exc.status, {"ok": False, "error": str(exc)})
                except Exception as exc:
                    self._send_json(
                        500,
                        {"ok": False, "error": f"学习资料重建索引失败：{exc}"},
                    )
                return
            if path == "/api/learning/documents":
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                except ValueError:
                    self._send_json(400, {"ok": False, "error": "无效的请求长度"})
                    return
                if length <= 0:
                    self._send_json(400, {"ok": False, "error": "不能上传空文档"})
                    return
                if length > LEARNING_DOCUMENT_MAX_BYTES:
                    self.close_connection = True
                    self._send_json(
                        413,
                        {"ok": False, "error": "单个文档不能超过 25 MB"},
                    )
                    return
                content = self.rfile.read(length)
                try:
                    document = learning_documents.save(
                        self.headers.get("X-File-Name", ""),
                        content,
                        self.headers.get("Content-Type", ""),
                    )
                    self._send_json(201, {"ok": True, "document": document})
                except LearningDocumentError as exc:
                    self._send_json(
                        exc.status,
                        {"ok": False, "error": str(exc)},
                    )
                except Exception as exc:
                    self._send_json(
                        500,
                        {"ok": False, "error": f"学习资料保存失败：{exc}"},
                    )
                return
            if path in {"/api/live/stream", "/api/live/stream/heartbeat"}:
                if origin == "__denied__":
                    self._send_json(403, {"ok": False, "error": "origin_not_allowed"})
                    return
                if path == "/api/live/stream/heartbeat":
                    body = self._read_json()
                    self._send_json(200, stream_registry.heartbeat(body.get("roomId")), origin)
                    return
                body = self._read_json()
                try:
                    result = stream_registry.register(body)
                    self._send_json(200, result, origin)
                except ValueError as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)}, origin)
                return
            if path == "/api/stream/start":
                body = self._read_json()
                try:
                    result = transcoder.start(
                        body.get("source"),
                        body.get("key"),
                        body.get("mode", "auto"),
                        body.get("height", 720),
                    )
                    self._send_json(200, result)
                except Exception as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                return
            if path == "/api/stream/stop":
                body = self._read_json()
                self._send_json(200, transcoder.stop(body.get("key")))
                return
            if path != "/api/sync":
                self._send_json(404, {"error": "not_found"})
                return
            try:
                body = self._read_json()
                realtime_only = str(body.get("mode") or "realtime").lower() != "full"
                force_materials = bool(body.get("forceMaterials"))
                started = store.request_sync(
                    realtime_only=realtime_only,
                    force_materials=force_materials,
                )
                requested_wait = to_number(body.get("waitSeconds")) or 0.75
                store.wait_for_sync(timeout_seconds=min(0.75, max(0.1, requested_wait)))
                snapshot = store.dashboard()
                snapshot["syncRequest"] = store.sync_state()
                snapshot["syncRequest"]["started"] = started
                status_code = 202 if snapshot["syncRequest"].get("running") else 200
                self._send_json(status_code, snapshot)
            except Exception as exc:  # Keep the UI informed instead of returning a blank 500.
                dashboard = store.dashboard()
                dashboard["syncStatus"] = "failed"
                dashboard["errors"] = list(dashboard.get("errors", [])) + [
                    {
                        "scope": "server",
                        "code": "sync_exception",
                        "message": f"同步任务异常：{exc}",
                    }
                ]
                self._send_json(500, dashboard)

        def do_DELETE(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            if path != "/api/learning/documents":
                self._send_json(404, {"error": "not_found"})
                return
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            document_id = (query.get("id") or [""])[0]
            try:
                document = learning_documents.delete(document_id)
                self._send_json(200, {"ok": True, "document": document})
            except LearningDocumentError as exc:
                self._send_json(exc.status, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send_json(
                    500,
                    {"ok": False, "error": f"学习资料删除失败：{exc}"},
                )

        def end_headers(self) -> None:
            if not urllib.parse.urlparse(self.path).path.startswith("/api/"):
                self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def log_message(self, format_string: str, *args: Any) -> None:
            print(f"[{self.log_date_time_string()}] {format_string % args}")

    return DashboardHandler


def periodic_sync(
    store: DashboardStore,
    interval_seconds: int,
    full_interval_seconds: int = 180,
    material_interval_seconds: int = 180,
) -> None:
    interval = max(10, int(interval_seconds))
    full_interval = max(60, int(full_interval_seconds))
    material_interval = max(60, int(material_interval_seconds))
    last_full_sync = time.time()
    next_material_sync = time.monotonic() + material_interval
    next_cycle = time.monotonic() + interval
    while True:
        delay = next_cycle - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        cycle_started = time.monotonic()
        now = time.time()
        try:
            store.capture_live_screen_history()
        except Exception as exc:
            print(f"直播大屏历史归档失败: {exc}")
        if store.backoff_until > now:
            time.sleep(min(interval, max(1, store.backoff_until - now)))
            continue
        material_sync_due = time.monotonic() >= next_material_sync
        realtime_only = not material_sync_due and now - last_full_sync < full_interval
        force_materials = material_sync_due
        try:
            store.sync(
                realtime_only=realtime_only,
                force_materials=force_materials,
            )
            if not realtime_only:
                last_full_sync = time.time()
            if material_sync_due:
                next_material_sync = cycle_started + material_interval
        except Exception as exc:
            print(f"定时同步失败: {exc}")
            if material_sync_due:
                next_material_sync = time.monotonic() + 30
        next_cycle = max(cycle_started + interval, time.monotonic() + 0.5)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HLS_DIR.mkdir(parents=True, exist_ok=True)
    store = DashboardStore()
    transcoder = StreamTranscoder(HLS_DIR)
    stream_registry = LiveStreamRegistry()
    port = int(os.getenv("QIANCHUAN_PORT", str(DEFAULT_PORT)))
    config = load_config()
    sync_config = config.get("sync", {})
    interval_env = os.getenv("QIANCHUAN_SYNC_INTERVAL_SECONDS", "").strip()
    interval = int(interval_env) if interval_env else int(
        sync_config.get("intervalSeconds", DEFAULT_SYNC_INTERVAL_SECONDS)
    )
    full_interval = int(sync_config.get("fullSyncIntervalSeconds", 180))
    material_interval = int(
        config.get("campaigns", {}).get("materialSyncIntervalSeconds", 180)
    )

    store.request_sync(realtime_only=True)
    threading.Thread(
        target=periodic_sync,
        args=(store, interval, full_interval, material_interval),
        name="periodic-sync",
        daemon=True,
    ).start()

    server = ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(store, ROOT, transcoder, stream_registry)
    )
    server.daemon_threads = True
    print(f"千川 AI 投放诊断已启动: http://127.0.0.1:{port}")
    print(
        f"启动实时同步已触发；实时同步间隔 {max(10, interval)} 秒，"
        f"完整同步间隔 {max(60, full_interval)} 秒。"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
