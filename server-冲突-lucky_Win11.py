from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SNAPSHOT_PATH = DATA_DIR / "qianchuan-snapshot.json"
CONFIG_PATH = ROOT / "qianchuan.config.json"
TOKEN_FILE_PATH = DATA_DIR / "qianchuan-token.json"
MCP_CONFIG_PATH = DATA_DIR / "qianchuan-mcp.json"
LIVE_SCREEN_STATE_PATH = DATA_DIR / "live-screen-metrics.json"
HLS_DIR = DATA_DIR / "hls"

HISTORY_DAYS = 182
DEFAULT_PORT = 8765
DEFAULT_SYNC_INTERVAL_SECONDS = 10
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_PAGE_SIZE = 100

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
    "marketingGoal": "LIVE_PROM_GOODS",
    "adlabScene": "UNI_PROJECT",
    "historyDays": 7,
    "materialPlanLimit": 20,
    "materialHistoryDays": 7,
    "materialCacheSeconds": 900,
    "materialCacheHours": 6,
    "materialMaxPages": 50,
    "materialType": "VIDEO",
    "materialReportSmartBidTypes": ["0", "7"],
    "materialReportEcpAppIds": ["1"],
    "materialReportPageSize": 200,
    "materialReportMaxPages": 100,
    "materialReportDimensions": [
        "stat_time_day",
        "roi2_material_video_name",
        "roi2_material_video_type",
        "material_id",
    ],
    "materialReportLiveDimensions": [
        "stat_time_day",
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


def resolve_access_token(config: dict[str, Any]) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    token = os.getenv("QIANCHUAN_ACCESS_TOKEN", "").strip()
    token_info: dict[str, Any] = {}

    configured_token_file = os.getenv("QIANCHUAN_TOKEN_FILE", "").strip()
    token_path = Path(configured_token_file) if configured_token_file else TOKEN_FILE_PATH
    token_info = read_token_file(token_path)
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
                "persona": {"age": "—", "region": "—", "gender": "—"},
                "materialStatus": "已投放",
                "auditStatus": None,
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
                    )
                )
            ),
            None,
        )
        if room is None:
            raise QianchuanMCPError(f"{self.LIVE_REPORT_TOOL} 未返回可识别的直播报表数据")
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
        """Read MCP trade metrics for fallback and cross-checking screen values."""
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
                "total_pay_order_gmv_include_coupon_for_roi2",
                "total_pay_order_count_for_roi2",
                "total_prepay_and_pay_order_roi2",
                "total_cost_per_pay_order_for_roi2",
                "total_pay_order_coupon_amount_for_roi2",
                "total_ecom_platform_subsidy_amount_for_roi2",
                "total_prepay_order_count_for_roi2",
                "total_prepay_order_gmv_for_roi2",
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
                or "total_pay_order_gmv_include_coupon_for_roi2" in item
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
            except TimeoutError as exc:
                raise QianchuanAPIError("千川接口请求超时") from exc

            try:
                result = json.loads(body)
            except json.JSONDecodeError as exc:
                raise QianchuanAPIError("千川接口返回了非 JSON 内容", response=body[:500]) from exc
            code = result.get("code", result.get("err_no"))
            if str(code) not in {"0", "None"}:
                message = result.get("message") or result.get("msg") or "千川接口返回错误"
                if str(code) == "40100" and attempt < 2:
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
    ) -> list[dict[str, Any]]:
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
                    "persona": {"age": "—", "region": "—", "gender": "—"},
                    "materialStatus": info.get("material_status"),
                    "auditStatus": info.get("audit_status"),
                    "cover": (video.get("cover_image") or {}).get("image_url"),
                    "videoUrl": video.get("url"),
                }
            return list(by_id.values())

        materials = normalize_rows(rows)
        expected_total = 0
        for raw in raw_pages:
            data = raw.get("data") or {}
            page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
            total = page_info.get("total_number") or page_info.get("total_num") or page_info.get("totalNumber")
            if total is not None:
                expected_total = max(expected_total, int(total))

        # 同一跑量值并列时，单次分页顺序可能漂移，导致跨页重复并漏项。
        # 当唯一素材数少于接口 total_number 时，用反向排序补拉并仅合并缺失 ID。
        if expected_total > len(materials):
            fallback_params = dict(params)
            fallback_params["order_type"] = "ASC" if str(params.get("order_type")).upper() != "ASC" else "DESC"
            fallback_rows, _fallback_pages = self._fetch_campaign_pages(
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
        return materials

    def fetch_uni_promotion_material_report(
        self,
        advertiser_id: str,
        aweme_id: str,
        start_date: str,
        end_date: str,
        material_type: str = "VIDEO",
    ) -> list[dict[str, Any]]:
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
                    rows, _pages = self._fetch_campaign_pages(
                        endpoint=endpoint,
                        params=params,
                        page_size=page_size,
                        max_pages=max_pages,
                        request_interval=interval,
                    )
                    raw_rows.extend(rows)
                    successful_queries += 1
                except QianchuanAPIError as exc:
                    errors.append(exc)
        if not successful_queries and errors:
            raise errors[0]
        return normalize_uni_promotion_material_report(
            raw_rows,
            aweme_id,
            "LIVE_ROOM" if is_live else "VIDEO",
            {
                "start": start_date,
                "end": end_date,
                "days": (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1,
            },
        )

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
        self.live_screen_path = snapshot_path.parent / LIVE_SCREEN_STATE_PATH.name
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

    def mcp_field_descriptions(self, tool_name: str) -> dict[str, Any]:
        """Return the remote MCP field schema for a supported tool."""
        client = self._get_mcp_client()
        if client is None:
            raise QianchuanMCPError("未配置千川 MCP")
        name = str(tool_name or "").strip()
        if not name or not all(char.isalnum() or char == "_" for char in name):
            raise QianchuanMCPError("MCP 工具名无效")
        result = client.call_tool(
            "get_tool_response_field_desc",
            {"tool_name": name},
        )
        with self.mcp_lock:
            self.mcp_last_error = None
        return {
            "ok": True,
            "tool": name,
            "fieldDescriptionTool": "get_tool_response_field_desc",
            "result": copy.deepcopy(result),
            "syncedAt": now_iso(),
        }

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
                material.update(copy.deepcopy(report))
                material["reportId"] = report.get("id")
                material["planId"] = plan.get("id")
                material["planName"] = plan.get("name")
                material["reportMatched"] = True
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
            known_ids = {
                str(item.get("id"))
                for item in fallback.get("materials") or []
                if isinstance(item, dict)
            }
            for item in unmatched:
                if str(item.get("id")) in known_ids:
                    continue
                fallback.setdefault("materials", []).append(item)
                known_ids.add(str(item.get("id")))
            fallback["materialsWindow"] = copy.deepcopy(window)
            fallback["materialReportSyncedAt"] = now_iso()
        return len(matched_ids)

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
            if plans:
                material_limit = (
                    max(0, int(campaign_config.get("materialPlanLimit", 20)))
                    if sync_materials
                    else 0
                )
                material_history_days = max(1, int(campaign_config.get("materialHistoryDays", 7)))
                material_cache_seconds = max(
                    30,
                    int(
                        campaign_config.get(
                            "materialCacheSeconds",
                            max(1, int(campaign_config.get("materialCacheHours", 2))) * 3600,
                        )
                    ),
                )
                # Include today's intraday cumulative value; past complete days
                # remain in the same rolling window.
                material_end_date = date.today()
                material_start_date = material_end_date - timedelta(days=material_history_days - 1)
                material_window = {
                    "start": material_start_date.isoformat(),
                    "end": material_end_date.isoformat(),
                    "days": material_history_days,
                }
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
                    if sum(row.get("spend", 0) for row in plan.get("data", [])) <= 0:
                        continue
                    previous_plan = previous_by_id.get(plan["id"])
                    if previous_plan and previous_plan.get("materials") and previous_plan.get("materialsSyncedAt"):
                        try:
                            synced_at = datetime.fromisoformat(str(previous_plan["materialsSyncedAt"]))
                            age_seconds = (datetime.now(timezone.utc).astimezone() - synced_at).total_seconds()
                            if age_seconds < material_cache_seconds:
                                plan["materials"] = copy.deepcopy(previous_plan["materials"])
                                plan["materialsSyncedAt"] = previous_plan["materialsSyncedAt"]
                                plan["materialsWindow"] = copy.deepcopy(
                                    previous_plan.get("materialsWindow") or material_window
                                )
                                continue
                        except (TypeError, ValueError):
                            pass
                    try:
                        materials = client.fetch_uni_promotion_materials(
                            account["advertiserId"],
                            plan["id"],
                            material_start_date.isoformat(),
                            material_end_date.isoformat(),
                            material_type="VIDEO",
                        )
                        try:
                            materials.extend(client.fetch_uni_promotion_materials(
                                account["advertiserId"],
                                plan["id"],
                                material_start_date.isoformat(),
                                material_end_date.isoformat(),
                                material_type="LIVE_ROOM",
                            ))
                        except QianchuanAPIError:
                            pass
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
                        seen_materials = set()
                        plan["materials"] = [
                            item for item in materials
                            if not (item["id"] in seen_materials or seen_materials.add(item["id"]))
                        ]
                        plan["materialsSyncedAt"] = now_iso()
                        plan["materialsWindow"] = material_window
                    except QianchuanAPIError as exc:
                        errors.append(
                            {
                                "scope": "campaign_materials",
                                "accountId": account["id"],
                                "advertiserId": account["advertiserId"],
                                "code": "campaign_material_failed",
                                "message": f"计划 {plan['id']} 素材同步失败：{exc}",
                            }
                        )
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
                    material_report_synced_at = None
                    if aweme_plans and has_material_activity and sync_materials:
                        try:
                            material_report_rows.extend(
                                client.fetch_uni_promotion_material_report(
                                    account["advertiserId"],
                                    aweme_id,
                                    material_start_date.isoformat(),
                                    material_end_date.isoformat(),
                                    "VIDEO",
                                )
                            )
                        except QianchuanAPIError as exc:
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
                            material_report_rows.extend(
                                client.fetch_uni_promotion_material_report(
                                    account["advertiserId"],
                                    aweme_id,
                                    material_start_date.isoformat(),
                                    material_end_date.isoformat(),
                                    "LIVE_ROOM",
                                )
                            )
                        except QianchuanAPIError as exc:
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
                        if material_report_rows:
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
                        }
                    )
                account["plans"] = plans
                account["awemes"] = awemes
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

    def _sync_locked(self, realtime_only: bool = False) -> dict[str, Any]:
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
            materials_due = not realtime_only
            if materials_due and previous_material_sync_at:
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

    def sync(self, realtime_only: bool = False) -> dict[str, Any]:
        with self.sync_lock:
            return self._sync_locked(realtime_only=realtime_only)

    def _run_background_sync(self, realtime_only: bool) -> None:
        try:
            self.sync(realtime_only=realtime_only)
        except Exception as exc:
            self.last_sync_error = str(exc)
            print(f"后台同步失败: {exc}")
        finally:
            with self.sync_state_lock:
                self.sync_running = False
                self.sync_finished_at = now_iso()

    def request_sync(self, realtime_only: bool = True) -> bool:
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
            args=(realtime_only,),
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
            "ok": status in {"ok", "partial"} and not stale,
            "stale": stale,
            "ageSeconds": round(age_seconds, 2) if age_seconds is not None else None,
        }

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
                overall_gmv = to_number(
                    record.get("total_pay_order_gmv_include_coupon_for_roi2")
                )
                if overall_gmv is None:
                    overall_gmv = to_number(
                        record.get("total_pay_order_gmv_for_roi2")
                    )
                gmv = round(
                    overall_gmv or 0.0,
                    2,
                )
                orders = round(
                    to_number(record.get("total_pay_order_count_for_roi2")) or 0.0,
                    4,
                )
                order_cost = to_number(
                    record.get("total_cost_per_pay_order_for_roi2")
                )
                if order_cost is None and orders:
                    order_cost = spend / orders
                roi = gmv / spend if spend else 0.0
                payload = {
                    "ok": True,
                    "status": "ok",
                    "source": "qianchuan_mcp",
                    "sourceLabel": (
                        "千川 MCP · 全域推广交易校验"
                    ),
                    "refundPolicy": "mcp_report",
                    "refundPolicyLabel": "MCP 整体成交金额 · 仅作兜底和校验",
                    "tool": report["tool"],
                    "arguments": report.get("arguments") or {},
                    "metrics": {
                        "spend": spend,
                        "gmv": gmv,
                        "orders": orders,
                        "orderCost": round(float(order_cost or 0.0), 2),
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

        advertiser_id = str(account.get("advertiserId") or account.get("qianchuanId"))
        trade = self.live_trade_snapshot(advertiser_id)
        behavior = self.live_screen_status()
        trade_metrics = trade.get("metrics") if isinstance(trade.get("metrics"), dict) else {}
        behavior_metrics = (
            behavior.get("metrics")
            if isinstance(behavior.get("metrics"), dict)
            else {}
        )
        trade_usable = bool(trade_metrics)
        behavior_usable = bool(behavior_metrics) and str(
            behavior.get("status") or ""
        ) not in {"login_required", "config_required", "disabled"}
        live = trade_usable or behavior_usable
        transaction_keys = ("spend", "gmv", "orders", "orderCost", "roi")
        screen_transaction_complete = all(
            behavior_metrics.get(key) is not None
            for key in transaction_keys
        )
        metrics: dict[str, Any] = {}
        metrics.update(copy.deepcopy(trade_metrics))
        for key, value in behavior_metrics.items():
            if value is not None and (
                key not in transaction_keys or screen_transaction_complete
            ):
                metrics[key] = value
        metric_sources: dict[str, dict[str, Any]] = {}
        for key, value in trade_metrics.items():
            if value is not None:
                metric_sources[key] = {
                    "source": "qianchuan_mcp",
                    "refundPolicy": trade.get("refundPolicy") or "mcp_report",
                    "sourceLabel": trade.get("sourceLabel")
                    or "千川 MCP 全域推广交易校验",
                }
        for key, value in behavior_metrics.items():
            if value is not None and (
                key not in transaction_keys or screen_transaction_complete
            ):
                metric_sources[key] = {
                    "source": "puppeteer-core",
                    "refundPolicy": "before_refund",
                    "sourceLabel": behavior.get("sourceLabel")
                    or "千川大屏页面抓取",
                }
        transaction_source = (
            "qianchuan_live_screen"
            if screen_transaction_complete
            else "qianchuan_mcp"
            if trade_usable
            else "unavailable"
        )

        errors: list[dict[str, Any]] = []
        if not trade.get("ok"):
            errors.append(
                {
                    "scope": "trade_channel",
                    "code": "trade_channel_unavailable",
                    "message": trade.get("error") or "MCP 交易通道不可用",
                }
            )
        if not behavior.get("ok"):
            errors.append(
                {
                    "scope": "behavior_channel",
                    "code": f"behavior_{behavior.get('status') or 'unavailable'}",
                    "message": behavior.get("error")
                    or (
                        f"大屏采集状态 {behavior.get('status')}，"
                        f"心跳年龄 {behavior.get('ageSeconds')} 秒"
                    ),
                }
            )
        stale_reasons = [
            reason
            for reason in (
                trade.get("staleWarning") if trade.get("status") == "stale" else "",
                (
                    f"大屏采集心跳已延迟 {behavior.get('ageSeconds')} 秒"
                    if behavior.get("stale") and behavior_usable
                    else ""
                ),
            )
            if reason
        ]
        room = copy.deepcopy(behavior.get("room") or {})
        if behavior.get("pageTitle") and not room.get("title"):
            room["title"] = behavior.get("pageTitle")
        payload = {
            "live": live,
            "room": room,
            "metrics": metrics,
            "flows": {},
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
            "source": "qianchuan_live_dual_channel",
            "sourceLabel": (
                "千川大屏退款前交易 + 无头 Chrome 行为"
                if screen_transaction_complete
                else "MCP 交易兜底 + 无头 Chrome 大屏行为"
                if trade_usable
                else "无头 Chrome 大屏行为"
            ),
            "transactionSource": transaction_source,
            "transactionSourceLabel": (
                "千川大屏页面 · 退款前"
                if screen_transaction_complete
                else "千川 MCP 报表 · 大屏交易字段缺失时兜底"
                if trade_usable
                else "大屏交易字段暂未返回"
            ),
            "tradeRefundPolicy": (
                "before_refund"
                if screen_transaction_complete
                else "mcp_report"
                if trade_usable
                else "unavailable"
            ),
            "tradeRefundPolicyLabel": (
                "千川直播大屏退款前口径"
                if screen_transaction_complete
                else "MCP 报表兜底口径，待大屏字段恢复"
                if trade_usable
                else "大屏退款前交易字段待恢复"
            ),
            "metricSources": metric_sources,
            "behaviorPolicy": "screen_cumulative",
            "channels": {
                "trade": copy.deepcopy(trade),
                "behavior": copy.deepcopy(behavior),
            },
            "staleWarning": "；".join(stale_reasons),
        }
        if not live:
            with self.live_lock:
                previous = self.live_cache.get(cache_key)
            if previous and previous[1].get("live"):
                payload = copy.deepcopy(previous[1])
                payload["live"] = True
                payload["staleWarning"] = "双通道暂时不可用，保留上一次有效值"
                payload["errors"] = errors
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
        if host not in {"douyincdn.com", "byteimg.com"} and not (
            host.endswith(".douyincdn.com") or host.endswith(".byteimg.com")
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
            if path == "/api/mcp/field-descriptions":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                tool_name = (query.get("tool") or [""])[0]
                try:
                    self._send_json(
                        200,
                        store.mcp_field_descriptions(str(tool_name)),
                    )
                except Exception as exc:
                    self._send_json(
                        502,
                        {
                            "ok": False,
                            "tool": str(tool_name),
                            "error": f"千川 MCP 字段说明读取失败：{exc}",
                        },
                    )
                return
            if path == "/api/dashboard":
                payload = store.dashboard()
                payload["syncRequest"] = store.sync_state()
                self._send_json(200, payload)
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
                started = store.request_sync(realtime_only=realtime_only)
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
) -> None:
    interval = max(10, int(interval_seconds))
    full_interval = max(60, int(full_interval_seconds))
    last_full_sync = time.time()
    next_cycle = time.monotonic() + interval
    while True:
        delay = next_cycle - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        cycle_started = time.monotonic()
        now = time.time()
        if store.backoff_until > now:
            time.sleep(min(interval, max(1, store.backoff_until - now)))
            continue
        realtime_only = now - last_full_sync < full_interval
        try:
            store.sync(realtime_only=realtime_only)
            if not realtime_only:
                last_full_sync = time.time()
        except Exception as exc:
            print(f"定时同步失败: {exc}")
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

    store.request_sync(realtime_only=True)
    threading.Thread(
        target=periodic_sync,
        args=(store, interval, full_interval),
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
