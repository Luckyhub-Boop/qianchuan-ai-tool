from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.request
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


class DateRangeTests(unittest.TestCase):
    def test_six_month_range_uses_completed_day(self) -> None:
        start, end = server.build_date_range(182, date(2026, 10, 19))
        self.assertEqual(end, "2026-10-18")
        self.assertEqual(start, "2026-04-20")

    def test_default_realtime_interval_and_aweme_order(self) -> None:
        self.assertEqual(server.DEFAULT_SYNC_INTERVAL_SECONDS, 10)
        self.assertEqual(server.DEFAULT_LIVE_CONFIG["cacheSeconds"], 10)
        names = [item["name"] for item in server.DEFAULT_ACCOUNT["awemeAccounts"]]
        self.assertEqual(names[:4], [
            "赵镭图解小数基本功",
            "赵镭精讲小数基本功",
            "赵镭拆解小数基本功",
            "赵镭通解小数基本功",
        ])


class FrontendContractTests(unittest.TestCase):
    def test_dashboard_has_multi_metric_chart_and_full_number_contract(self) -> None:
        html = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
        self.assertIn('chartMetrics: ["spend", "gmv"]', html)
        for metric in ("spend", "gmv", "orders", "roi", "cost"):
            self.assertIn(f'data-metric="{metric}"', html)
        self.assertIn("accountOrderRank", html)
        self.assertIn("ADVERTISER_TOTALS", html)
        self.assertIn("千川广告主账户", html)
        self.assertIn("return `¥${formatNumber(value, 2)}`", html)
        self.assertIn("syncFollowupGeneration", html)
        self.assertIn("全域推广报表数据", html)
        self.assertIn("千川直播大屏数据", html)
        self.assertIn("退款前", html)
        self.assertIn("成交订单成本", html)
        self.assertIn("qianchuan_report_uni_promotion_get_v1", html)
        self.assertIn("千川大屏页面", html)
        self.assertIn('id="dataLiveTrendChart"', html)


class LiveStreamRegistryTests(unittest.TestCase):
    def test_registry_keeps_signed_url_private_and_resolves_room(self) -> None:
        registry = server.LiveStreamRegistry(ttl_seconds=300)
        registry.heartbeat()
        result = registry.register(
            {
                "roomId": "7698595680801098550",
                "url": "https://pull-flv.example.douyincdn.com/live.flv?sign=secret",
                "type": "flv",
            }
        )
        self.assertTrue(result["ok"])
        self.assertNotIn("url", result)
        status = registry.status("7698595680801098550")
        self.assertTrue(status["online"])
        self.assertTrue(status["active"])
        self.assertTrue(status["captured"])
        self.assertNotIn("url", status)
        stream = registry.resolve("7698595680801098550")
        self.assertIsNotNone(stream)
        self.assertEqual(stream["type"], "flv")
        self.assertIn("sign=secret", stream["url"])
        implicit_status = registry.status()
        self.assertEqual(implicit_status["roomId"], "7698595680801098550")
        self.assertTrue(implicit_status["captured"])
        self.assertNotIn("url", implicit_status)

    def test_heartbeat_renews_active_room(self) -> None:
        registry = server.LiveStreamRegistry(ttl_seconds=60)
        room_id = "7698595680801098550"
        registry.register(
            {
                "roomId": room_id,
                "url": "https://pull-flv.example.douyincdn.com/live.flv?sign=secret",
            }
        )
        with registry.lock:
            registry.rooms[room_id]["capturedTimestamp"] = server.time.time() - 120
        self.assertFalse(registry.status(room_id)["captured"])
        registry.heartbeat(room_id)
        self.assertTrue(registry.status(room_id)["captured"])

    def test_registry_rejects_non_cdn_url(self) -> None:
        registry = server.LiveStreamRegistry()
        with self.assertRaises(ValueError):
            registry.register({"roomId": "123456789", "url": "http://127.0.0.1/private"})


class MaterialTests(unittest.TestCase):
    def test_material_fetch_normalizes_nested_real_time_metrics(self) -> None:
        config = json.loads(json.dumps(server.DEFAULT_CONFIG))
        client = server.QianchuanClient(config, "test-token")
        row = {
            "material_info": {
                "material_type": "VIDEO",
                "video_material": {
                    "material_id": "m-1",
                    "title": "测试素材",
                    "video_duration": 31,
                    "cover_image": {"image_url": "https://example.test/cover.jpg"},
                },
            },
            "stats_info": {
                "metrics": {
                    "stat_cost_for_roi2": 123.45,
                    "total_pay_order_gmv_for_roi2": 456.78,
                    "total_pay_order_count_for_roi2": 9,
                    "live_show_count_for_roi2_v2": 12000,
                    "live_watch_count_for_roi2_v2": 720,
                    "video_play_finish_rate_for_roi2_v2": 38.5,
                    "video_avg_watch_duration_for_roi2": 21.7,
                }
            },
        }
        with patch.object(client, "_fetch_campaign_pages", return_value=([row], [{"mock": True}])) as fetch:
            materials = client.fetch_uni_promotion_materials(
                "advertiser-1", "plan-1", "2026-10-14", "2026-10-20", "VIDEO"
            )
        self.assertEqual(len(materials), 1)
        self.assertEqual(materials[0]["spend"], 123.45)
        self.assertEqual(materials[0]["gmv"], 456.78)
        self.assertEqual(materials[0]["orders"], 9.0)
        self.assertEqual(materials[0]["impressions"], 12000.0)
        self.assertEqual(materials[0]["clicks"], 720.0)
        self.assertEqual(materials[0]["completionRate"], 38.5)
        self.assertEqual(materials[0]["dwellTime"], 21.7)
        params = fetch.call_args.kwargs["params"]
        self.assertEqual(params["start_date"], "2026-10-14")
        self.assertEqual(params["end_date"], "2026-10-20")
        self.assertEqual(fetch.call_args.kwargs["max_pages"], 50)

    def test_material_pagination_falls_back_when_unique_count_short(self) -> None:
        config = json.loads(json.dumps(server.DEFAULT_CONFIG))
        client = server.QianchuanClient(config, "test-token")

        def row(material_id: str, spend: float) -> dict:
            return {
                "material_info": {
                    "material_type": "VIDEO",
                    "video_material": {"material_id": material_id, "title": material_id},
                },
                "stats_info": {"metrics": {"stat_cost_for_roi2": spend}},
            }

        page_info = {"data": {"page_info": {"total_number": 2, "total_page": 1}}}
        first_rows = [row("m-1", 1.0), row("m-1", 1.0)]
        second_rows = [row("m-2", 2.0)]
        with patch.object(
            client,
            "_fetch_campaign_pages",
            side_effect=[(first_rows, [page_info]), (second_rows, [page_info])],
        ) as fetch:
            materials = client.fetch_uni_promotion_materials(
                "advertiser-1", "plan-1", "2026-10-14", "2026-10-20", "VIDEO"
            )
        self.assertEqual({item["id"] for item in materials}, {"m-1", "m-2"})
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(fetch.call_args_list[1].kwargs["params"]["order_type"], "ASC")

    def test_official_material_report_uses_aweme_filter_and_aggregates_days(self) -> None:
        config = json.loads(json.dumps(server.DEFAULT_CONFIG))
        config["campaigns"]["materialReportSmartBidTypes"] = ["0"]
        config["campaigns"]["materialReportEcpAppIds"] = ["1"]
        client = server.QianchuanClient(config, "test-token")
        rows = [
            {
                "dimensions": {
                    "material_id": {"Value": "m-1", "ValueStr": "m-1"},
                    "roi2_material_video_name": {"Value": "测试视频", "ValueStr": "测试视频"},
                    "roi2_material_video_type": {"Value": "2", "ValueStr": "优选投放视频"},
                    "stat_time_day": {"Value": "1", "ValueStr": "2026-10-20"},
                },
                "metrics": {
                    "stat_cost_for_roi2": {"Value": 10.0},
                    "total_pay_order_gmv_for_roi2": {"Value": 20.0},
                    "total_pay_order_count_for_roi2": {"Value": 2.0},
                    "live_show_count_for_roi2_v2": {"Value": 1000.0},
                    "live_watch_count_for_roi2_v2": {"Value": 80.0},
                    "video_play_count_for_roi2_v2": {"Value": 100.0},
                    "video_play_finish_rate_for_roi2_v2": {"Value": 20.0},
                    "video_avg_watch_duration_for_roi2": {"Value": 8.0},
                },
            },
            {
                "dimensions": {
                    "material_id": {"Value": "m-1", "ValueStr": "m-1"},
                    "roi2_material_video_name": {"Value": "测试视频", "ValueStr": "测试视频"},
                    "roi2_material_video_type": {"Value": "2", "ValueStr": "优选投放视频"},
                    "stat_time_day": {"Value": "2", "ValueStr": "2026-10-19"},
                },
                "metrics": {
                    "stat_cost_for_roi2": {"Value": 5.0},
                    "total_pay_order_gmv_for_roi2": {"Value": 7.5},
                    "total_pay_order_count_for_roi2": {"Value": 1.0},
                    "live_show_count_for_roi2_v2": {"Value": 500.0},
                    "live_watch_count_for_roi2_v2": {"Value": 20.0},
                    "video_play_count_for_roi2_v2": {"Value": 300.0},
                    "video_play_finish_rate_for_roi2_v2": {"Value": 30.0},
                    "video_avg_watch_duration_for_roi2": {"Value": 12.0},
                },
            },
        ]
        with patch.object(client, "_fetch_campaign_pages", return_value=(rows, [{"mock": True}])) as fetch:
            materials = client.fetch_uni_promotion_material_report(
                "advertiser-1",
                "7637818476896437305",
                "2026-10-14",
                "2026-10-20",
                "VIDEO",
            )
        self.assertEqual(len(materials), 1)
        material = materials[0]
        self.assertEqual(material["spend"], 15.0)
        self.assertEqual(material["gmv"], 27.5)
        self.assertEqual(material["orders"], 3.0)
        self.assertEqual(material["impressions"], 1500.0)
        self.assertEqual(material["clicks"], 100.0)
        self.assertEqual(material["completionRate"], 27.5)
        self.assertEqual(material["dwellTime"], 11.0)
        params = fetch.call_args.kwargs["params"]
        filters = json.loads(params["filters"])
        self.assertEqual(filters[0], {
            "field": "anchor_id",
            "operator": 7,
            "values": ["7637818476896437305"],
        })
        self.assertEqual(params["data_topic"], "SITE_PROMOTION_POST_DATA_VIDEO")
        self.assertEqual(fetch.call_args.kwargs["page_size"], 200)

    def test_official_material_report_overlays_plan_metadata(self) -> None:
        plans = [{
            "id": "plan-1",
            "name": "2026-06-30_直播全域投放_14:24:43",
            "data": [{"date": "2026-10-20", "spend": 15.0, "gmv": 27.5, "orders": 3.0}],
            "materials": [{"id": "m-1", "name": "缓存名称", "spend": 0.0}],
        }]
        reports = [{
            "id": "m-1",
            "name": "官方报表名称",
            "spend": 15.0,
            "gmv": 27.5,
            "orders": 3.0,
            "impressions": 1500.0,
            "clicks": 100.0,
        }]
        matched = server.DashboardStore._merge_official_material_report(
            plans,
            reports,
            {"start": "2026-10-14", "end": "2026-10-20", "days": 7},
        )
        self.assertEqual(matched, 1)
        self.assertEqual(plans[0]["materials"][0]["spend"], 15.0)
        self.assertEqual(plans[0]["materials"][0]["planId"], "plan-1")
        self.assertTrue(plans[0]["materials"][0]["reportMatched"])

    def test_official_live_material_report_reuses_plan_metadata(self) -> None:
        plans = [{
            "id": "plan-1",
            "name": "2026-06-30_直播全域投放_14:24:43",
            "data": [{"date": "2026-10-20", "spend": 5.0, "gmv": 0.0, "orders": 0.0}],
            "materials": [{
                "id": "metadata-live-id",
                "name": "赵镭图解小数基本功",
                "type": "直播间画面",
                "spend": 0.0,
            }],
        }]
        reports = [{
            "id": "live-room-7637818476896437305",
            "name": "赵镭图解小数基本功",
            "type": "直播间画面",
            "spend": 5.0,
            "impressions": 1000.0,
            "clicks": 10.0,
        }]
        matched = server.DashboardStore._merge_official_material_report(
            plans,
            reports,
            {"start": "2026-10-14", "end": "2026-10-20", "days": 7},
        )
        self.assertEqual(matched, 1)
        self.assertEqual(len(plans[0]["materials"]), 1)
        self.assertEqual(plans[0]["materials"][0]["reportId"], "live-room-7637818476896437305")


class NormalizationTests(unittest.TestCase):
    def test_normalizes_and_merges_duplicate_dates(self) -> None:
        rows = [
            {"stat_date": "2026-10-18", "stat_cost": "10.5", "pay_order_amount": "20", "pay_order_count": 2},
            {"stat_date": "2026-10-18", "stat_cost": 4.5, "pay_order_amount": 5, "pay_order_count": 1},
            {"date": "2026-10-17", "spend": 3, "gmv": 9, "orders": 1},
            {"date": "2026-04-19", "spend": 99, "gmv": 99, "orders": 99},
        ]
        result = server.normalize_daily_rows(rows, server.DEFAULT_FIELD_MAP, "2026-04-20", "2026-10-18")
        self.assertEqual([row["date"] for row in result], ["2026-10-17", "2026-10-18"])
        self.assertEqual(result[1]["spend"], 15.0)
        self.assertEqual(result[1]["gmv"], 25.0)
        self.assertEqual(result[1]["orders"], 3.0)

    def test_realtime_upsert_replaces_today_and_keeps_last_non_zero(self) -> None:
        rows = [
            {"date": "2026-10-20", "spend": 10.0, "gmv": 20.0, "orders": 2.0},
            {"date": "2026-10-21", "spend": 5.0, "gmv": 8.0, "orders": 1.0},
        ]
        updated = server.upsert_daily_row(
            rows,
            {"date": "2026-10-21", "spend": 7.0, "gmv": 12.0, "orders": 2.0},
        )
        self.assertEqual(updated[-1]["spend"], 7.0)
        protected = server.upsert_daily_row(
            updated,
            {"date": "2026-10-21", "spend": 0.0, "gmv": 0.0, "orders": 0.0},
        )
        self.assertEqual(protected[-1]["spend"], 7.0)
        self.assertEqual(sum(1 for row in protected if row["date"] == "2026-10-21"), 1)


class MCPTests(unittest.TestCase):
    def test_mcp_rpc_parses_sse_response(self) -> None:
        parsed = server.QianchuanMCPClient._rpc_payload(
            'event: message\n'
            'data: {"jsonrpc":"2.0","id":7,"result":{"tools":[{"name":"today_live"}]}}\n\n',
            7,
        )
        self.assertEqual(parsed["result"]["tools"][0]["name"], "today_live")

    def test_mcp_uni_promotion_trade_calls_exact_tool(self) -> None:
        client = server.QianchuanMCPClient(
            {"url": "https://example.test/mcp", "timeoutSeconds": 5}
        )
        tool = {
            "name": "qianchuan_report_uni_promotion_get_v1",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "advertiser_id": {"type": "integer"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "fields": {"type": "array"},
                    "marketing_goal": {"type": "string"},
                    "order_platform": {"type": "string"},
                },
                "required": [
                    "advertiser_id",
                    "start_date",
                    "end_date",
                    "fields",
                    "marketing_goal",
                ],
            },
        }
        result = {
            "structuredContent": {
                "code": 0,
                "data": {
                    "stat_cost": 100.0,
                    "total_pay_order_gmv_for_roi2": 250.0,
                    "total_pay_order_count_for_roi2": 3,
                    "total_prepay_and_pay_order_roi2": 2.5,
                },
            }
        }
        with patch.object(client, "list_tools", return_value=[tool]), \
             patch.object(client, "call_tool", return_value=result) as call:
            report = client.fetch_uni_promotion_trade(
                "1744479430946824",
                "2026-10-22 00:00:00",
                "2026-10-22 15:00:00",
            )
        self.assertEqual(
            call.call_args.args[0],
            "qianchuan_report_uni_promotion_get_v1",
        )
        self.assertEqual(call.call_args.args[1]["marketing_goal"], "ALL")
        self.assertEqual(call.call_args.args[1]["advertiser_id"], 1744479430946824)
        self.assertIn(
            "total_pay_order_gmv_include_coupon_for_roi2",
            call.call_args.args[1]["fields"],
        )
        self.assertEqual(report["record"]["stat_cost"], 100.0)

    def test_mcp_calls_exact_live_report_tool_and_normalizes_result(self) -> None:
        client = server.QianchuanMCPClient(
            {
                "url": "https://example.test/mcp",
                "preferredTools": ["today_live_room"],
            }
        )
        tools = [
            {
                "name": "qianchuan_live_screen_get",
                "description": "直播大屏工具，不应被调用",
                "inputSchema": {"properties": {}, "required": []},
            },
            {
                "name": "qianchuan_report_live_get_v1",
                "description": "获取今日直播报表数据",
                "inputSchema": {
                    "properties": {
                        "advertiser_id": {"type": "string"},
                        "aweme_id": {"type": "string"},
                        "date": {"type": "string"},
                        "fields": {"type": "array"},
                        "filtering": {"type": "object"},
                    },
                    "required": ["advertiser_id", "aweme_id", "date"],
                },
            },
        ]
        room = {
            "room_id": "room-1",
            "room_status": "LIVING",
            "stat_cost": 100000,
            "pay_order_amount": 250000,
            "pay_order_count": 3,
        }
        with patch.object(client, "list_tools", return_value=tools), \
             patch.object(
                 client,
                 "call_tool",
                 return_value={"structuredContent": {"data": {"room_list": [room]}}},
             ) as call:
            result = client.fetch_live_room("advertiser-1", "aweme-1", "2026-10-21")
        self.assertEqual(result["tool"], "qianchuan_report_live_get_v1")
        self.assertEqual(result["room"]["room_id"], "room-1")
        call.assert_called_once()
        self.assertEqual(call.call_args.args[0], "qianchuan_report_live_get_v1")
        self.assertEqual(call.call_args.args[1]["aweme_id"], "aweme-1")
        self.assertEqual(call.call_args.args[1]["fields"], [
            "stat_cost",
            "pay_order_amount",
            "pay_order_count",
        ])

    def test_mcp_raw_live_report_keeps_jsonrpc_response_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mcp_path = Path(temp_dir) / "mcp.json"
            mcp_path.write_text(
                json.dumps({
                    "enabled": True,
                    "url": "https://example.test/mcp?API_KEY=test",
                }),
                encoding="utf-8",
            )
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            schema = {
                "properties": {
                    "advertiser_id": {"type": "string"},
                    "aweme_id": {"type": "string"},
                    "date": {"type": "string"},
                    "fields": {"type": "array"},
                },
                "required": ["advertiser_id", "aweme_id", "date"],
            }
            raw = {
                "jsonrpc": "2.0",
                "id": 9,
                "result": {
                    "content": [{"type": "text", "text": '{"data":{"rows":[]}}'}],
                    "unknownField": "preserved",
                },
            }
            with patch.object(server, "MCP_CONFIG_PATH", mcp_path), \
                 patch.object(
                     server.QianchuanMCPClient,
                     "list_tools",
                     return_value=[{
                         "name": "qianchuan_report_live_get_v1",
                         "inputSchema": schema,
                     }],
                 ), \
                 patch.object(
                     server.QianchuanMCPClient,
                     "call_tool_raw",
                     return_value=raw,
                 ):
                result = store.mcp_raw_live_report(
                    "1744479430946824",
                    "7637818476896437305",
                    "2026-10-21",
                )
            self.assertTrue(result["ok"])
            self.assertEqual(result["rawJsonRpcResponse"], raw)
            self.assertEqual(result["arguments"]["advertiser_id"], "1744479430946824")
            self.assertEqual(result["arguments"]["aweme_id"], "7637818476896437305")
            self.assertEqual(result["arguments"]["date"], "2026-10-21")


class StoreTests(unittest.TestCase):
    def test_missing_credentials_degrades_without_fake_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            with patch.dict("os.environ", {}, clear=True), patch.object(server, "TOKEN_FILE_PATH", Path(temp_dir) / "missing-token.json"):
                store = server.DashboardStore(snapshot_path)
                result = store.sync()
            self.assertEqual(result["syncStatus"], "degraded")
            self.assertEqual(result["mode"], "seed")
            self.assertEqual(result["accounts"][0]["status"], "凭证缺失 · 展示缓存")
            self.assertTrue(any(error["code"] == "credentials_missing" for error in result["errors"]))
            self.assertTrue(snapshot_path.exists())

    def test_mock_live_sync_returns_all_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            store = server.DashboardStore(snapshot_path)
            today = date.today().isoformat()
            fake_rows = [
                {"stat_date": "2026-10-17", "stat_cost": 10, "pay_order_amount": 20, "pay_order_count": 2},
                {"stat_date": "2026-10-18", "stat_cost": 11, "pay_order_amount": 22, "pay_order_count": 3},
            ]
            realtime_account_row = {
                "stat_date": today,
                "stat_cost": 7,
                "pay_order_amount": 14,
                "pay_order_count": 1,
            }
            fake_plans = [
                {
                    "id": "c-1",
                    "name": "测试计划 A",
                    "status": "已暂停",
                    "data": [
                        {"date": "2026-10-17", "spend": 10.0, "gmv": 20.0, "orders": 2.0},
                        {"date": "2026-10-18", "spend": 11.0, "gmv": 22.0, "orders": 3.0},
                    ],
                    "materials": [],
                }
            ]
            realtime_plans = [
                {
                    "id": "c-1",
                    "name": "测试计划 A",
                    "status": "投放中",
                    "rawStatus": "DELIVERY_OK",
                    "roomInfo": [],
                    "stats": {
                        "stat_cost": 500000,
                        "total_pay_order_gmv_for_roi2": 800000,
                        "total_pay_order_count_for_roi2": 2,
                    },
                }
            ]

            def fake_report(_client, _advertiser_id, start_date, end_date):
                if start_date == today and end_date == today:
                    return [realtime_account_row], [{"mock": "today-account"}]
                return fake_rows, [{"mock": True}]

            def fake_aweme(_advertiser_id, _aweme_id, start_date, end_date):
                if start_date == today and end_date == today:
                    return [{
                        "date": today,
                        "spend": 3.0,
                        "gmv": 6.0,
                        "orders": 1.0,
                    }]
                return [
                    {"date": "2026-10-17", "spend": 1.0, "gmv": 2.0, "orders": 1.0},
                    {"date": "2026-10-18", "spend": 2.0, "gmv": 4.0, "orders": 1.0},
                ]

            with patch.dict("os.environ", {"QIANCHUAN_ACCESS_TOKEN": "test-token"}, clear=True), \
                 patch.object(server.QianchuanClient, "fetch_report", autospec=True, side_effect=fake_report), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_daily", return_value=(fake_plans, [{"mock": True}])), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_plans_for_range", return_value=(realtime_plans, [{"mock": "today-plan"}])), \
                 patch.object(server.QianchuanClient, "fetch_aweme_daily", side_effect=fake_aweme), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_materials", return_value=[]) as material_fetch:
                result = store.sync()
            self.assertGreaterEqual(material_fetch.call_count, 1)
            material_args = material_fetch.call_args_list[0].args
            material_start = date.fromisoformat(material_args[2])
            material_end = date.fromisoformat(material_args[3])
            self.assertEqual((material_end - material_start).days, 6)
            self.assertEqual(material_end, date.today())
            self.assertEqual(result["syncStatus"], "success")
            self.assertEqual(result["mode"], "live")
            self.assertEqual(result["accounts"][0]["data"], [
                {"date": "2026-10-17", "spend": 10.0, "gmv": 20.0, "orders": 2.0},
                {"date": "2026-10-18", "spend": 11.0, "gmv": 22.0, "orders": 3.0},
                {
                    "date": today,
                    "spend": 7.0,
                    "gmv": 14.0,
                    "orders": 1.0,
                    "realtime": True,
                    "syncedAt": result["accounts"][0]["data"][-1]["syncedAt"],
                },
            ])
            self.assertEqual(result["accounts"][0]["plans"][0]["id"], "c-1")
            self.assertEqual(result["accounts"][0]["plans"][0]["data"][-1]["date"], today)
            self.assertEqual(result["accounts"][0]["plans"][0]["data"][-1]["spend"], 5.0)
            self.assertEqual(result["dataCutoff"], today)
            self.assertEqual(result["realtime"]["status"], "success")
            self.assertEqual(result["accounts"][0]["awemes"][0]["data"][-1]["spend"], 3.0)
            reconciliation = result["accounts"][0]["reconciliation"]
            self.assertEqual(reconciliation["date"], today)
            self.assertEqual(reconciliation["account"]["spend"], 7.0)
            self.assertEqual(reconciliation["awemeAttribution"]["spend"], 15.0)
            self.assertEqual(reconciliation["difference"]["spend"], -8.0)

    def test_account_realtime_falls_back_to_official_plan_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            store = server.DashboardStore(snapshot_path)
            today = date.today().isoformat()
            history_rows = [{
                "stat_date": "2026-10-20",
                "stat_cost": 10,
                "pay_order_amount": 20,
                "pay_order_count": 2,
            }]
            historical_plan = [{
                "id": "c-1",
                "name": "测试计划",
                "status": "投放中",
                "data": [{"date": "2026-10-20", "spend": 10.0, "gmv": 20.0, "orders": 2.0}],
                "materials": [],
                "roomInfo": [],
            }]
            realtime_plan = [{
                "id": "c-1",
                "name": "测试计划",
                "status": "投放中",
                "rawStatus": "DELIVERY_OK",
                "roomInfo": [],
                "stats": {
                    "stat_cost": 900000,
                    "total_pay_order_gmv_for_roi2": 1800000,
                    "total_pay_order_count_for_roi2": 3,
                },
            }]

            def fake_report(_client, _advertiser_id, start_date, _end_date):
                if start_date == today:
                    return [], [{"mock": "empty-account-today"}]
                return history_rows, [{"mock": True}]

            with patch.dict("os.environ", {"QIANCHUAN_ACCESS_TOKEN": "test-token"}, clear=True), \
                 patch.object(server.QianchuanClient, "fetch_report", autospec=True, side_effect=fake_report), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_daily", return_value=(historical_plan, [])), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_plans_for_range", return_value=(realtime_plan, [])), \
                 patch.object(server.QianchuanClient, "fetch_aweme_daily", return_value=[]), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_materials", return_value=[]):
                result = store.sync()

            account = result["accounts"][0]
            today_row = next(row for row in account["data"] if row["date"] == today)
            self.assertEqual(today_row["spend"], 9.0)
            self.assertEqual(today_row["gmv"], 18.0)
            self.assertEqual(today_row["orders"], 3.0)
            self.assertEqual(account["realtime"]["source"], "千川计划接口 · 今日累计")
            self.assertEqual(result["realtime"]["status"], "success")
            self.assertFalse(any(
                error["code"] in {"account_realtime_fallback", "account_realtime_failed"}
                for error in result["errors"]
            ))

    def test_realtime_only_skips_history_and_material_fetches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            store = server.DashboardStore(snapshot_path)
            today = date.today().isoformat()
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            cached_plan = {
                "id": "c-1",
                "name": "缓存计划",
                "status": "投放中",
                "data": [
                    {"date": yesterday, "spend": 10.0, "gmv": 20.0, "orders": 2.0},
                    {"date": today, "spend": 1.0, "gmv": 2.0, "orders": 1.0},
                ],
                "materials": [{"id": "cached-material"}],
                "roomInfo": [],
            }
            store.snapshot = {
                "revision": 1,
                "syncedAt": None,
                "accounts": [{
                    **server.DEFAULT_ACCOUNT,
                    "qianchuanId": server.DEFAULT_ACCOUNT["advertiserId"],
                    "status": "今日实时已同步",
                    "dataCutoff": today,
                    "data": [
                        {"date": yesterday, "spend": 10.0, "gmv": 20.0, "orders": 2.0},
                        {"date": today, "spend": 1.0, "gmv": 2.0, "orders": 1.0},
                    ],
                    "plans": [cached_plan],
                    "awemes": [],
                }],
                "errors": [],
            }

            with patch.dict("os.environ", {"QIANCHUAN_ACCESS_TOKEN": "test-token"}, clear=True), \
                 patch.object(server.QianchuanClient, "fetch_report", return_value=([], [])), \
                 patch.object(
                     server.QianchuanClient,
                     "fetch_uni_promotion_daily",
                     side_effect=AssertionError("history fetch must be skipped"),
                 ), \
                 patch.object(
                     server.QianchuanClient,
                     "fetch_uni_promotion_materials",
                     side_effect=AssertionError("material fetch must be skipped"),
                 ), \
                 patch.object(server.QianchuanClient, "fetch_uni_promotion_plans_for_range", return_value=([], [])), \
                 patch.object(server.QianchuanClient, "fetch_aweme_daily", return_value=[]):
                result = store.sync(realtime_only=True)

            self.assertEqual(result["syncKind"], "realtime")
            self.assertEqual(result["accounts"][0]["plans"][0]["materials"][0]["id"], "cached-material")

    def test_live_trade_channel_uses_uni_promotion_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            trade = {
                "tool": "qianchuan_report_uni_promotion_get_v1",
                "record": {
                    "stat_cost": 120.5,
                    "total_pay_order_gmv_for_roi2": 360.75,
                    "total_pay_order_gmv_include_coupon_for_roi2": 450.0,
                    "total_pay_order_count_for_roi2": 5,
                    "total_prepay_and_pay_order_roi2": 2.99,
                    "total_cost_per_pay_order_for_roi2": 24.1,
                },
                "payload": {},
                "arguments": {"advertiser_id": 1744479430946824},
            }
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(
                     server.QianchuanMCPClient,
                     "fetch_uni_promotion_trade",
                     return_value=trade,
                 ):
                payload = store.live_snapshot("fashion")
            self.assertTrue(payload["live"])
            self.assertEqual(payload["source"], "qianchuan_live_dual_channel")
            self.assertEqual(payload["transactionSource"], "qianchuan_mcp")
            self.assertEqual(payload["tradeRefundPolicy"], "mcp_report")
            self.assertTrue(payload["channels"]["trade"]["ok"])
            self.assertFalse(payload["channels"]["behavior"]["ok"])
            self.assertEqual(payload["metrics"]["spend"], 120.5)
            self.assertEqual(payload["metrics"]["gmv"], 450.0)
            self.assertEqual(payload["metrics"]["orders"], 5.0)
            self.assertEqual(payload["metrics"]["orderCost"], 24.1)
            self.assertAlmostEqual(payload["metrics"]["roi"], 450.0 / 120.5, places=4)

    def test_live_behavior_channel_uses_headless_screen_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "ok",
                    "source": "puppeteer-core",
                    "sourceLabel": "千川直播大屏 · 无头 Chrome 抓取",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "watchCount": 12800,
                        "productClicks": 2345,
                        "peakOnline": 386,
                        "gpm": 912.35,
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(store, "_get_mcp_client", return_value=None):
                payload = store.live_snapshot("fashion")
            self.assertTrue(payload["live"])
            self.assertEqual(payload["source"], "qianchuan_live_dual_channel")
            self.assertFalse(payload["channels"]["trade"]["ok"])
            self.assertTrue(payload["channels"]["behavior"]["ok"])
            self.assertEqual(payload["room"]["id"], "room-screen")
            self.assertEqual(payload["metrics"]["watchCount"], 12800)
            self.assertEqual(payload["metrics"]["productClicks"], 2345)
            self.assertEqual(payload["metrics"]["peakOnline"], 386)
            self.assertEqual(payload["metrics"]["gpm"], 912.35)

    def test_live_screen_trade_metrics_override_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "ok",
                    "source": "puppeteer-core",
                    "sourceLabel": "千川直播大屏 · 无头 Chrome 抓取",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "watchCount": 12800,
                        "productClicks": 2345,
                        "peakOnline": 386,
                        "gpm": 912.35,
                        "spend": 500.0,
                        "gmv": 900.0,
                        "orders": 20.0,
                        "orderCost": 25.0,
                        "roi": 1.8,
                    },
                }),
                encoding="utf-8",
            )
            trade = {
                "ok": True,
                "status": "ok",
                "source": "qianchuan_mcp",
                "sourceLabel": "千川 MCP · 全域推广交易校验",
                "refundPolicy": "mcp_report",
                "metrics": {
                    "spend": 510.0,
                    "gmv": 700.0,
                    "orders": 18.0,
                    "orderCost": 28.33,
                    "roi": 1.37,
                },
            }
            with patch.object(store, "_get_mcp_client", return_value=object()), \
                 patch.object(store, "live_trade_snapshot", return_value=trade):
                payload = store.live_snapshot("fashion")
            self.assertEqual(payload["transactionSource"], "qianchuan_live_screen")
            self.assertEqual(payload["tradeRefundPolicy"], "before_refund")
            self.assertEqual(payload["metrics"]["spend"], 500.0)
            self.assertEqual(payload["metrics"]["gmv"], 900.0)
            self.assertEqual(payload["metrics"]["orders"], 20.0)
            self.assertEqual(payload["metrics"]["orderCost"], 25.0)
            self.assertEqual(payload["metrics"]["roi"], 1.8)
            self.assertEqual(
                payload["metricSources"]["gmv"]["refundPolicy"],
                "before_refund",
            )

    def test_incomplete_screen_trade_metrics_do_not_mix_with_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "ok",
                    "source": "puppeteer-core",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "watchCount": 12800,
                        "productClicks": 2345,
                        "peakOnline": 386,
                        "gpm": 912.35,
                        "spend": 500.0,
                        "gmv": 900.0,
                        "orders": 20.0,
                        "roi": 1.8,
                    },
                }),
                encoding="utf-8",
            )
            trade = {
                "ok": True,
                "status": "ok",
                "source": "qianchuan_mcp",
                "refundPolicy": "mcp_report",
                "metrics": {
                    "spend": 510.0,
                    "gmv": 700.0,
                    "orders": 18.0,
                    "orderCost": 28.33,
                    "roi": 1.37,
                },
            }
            with patch.object(store, "_get_mcp_client", return_value=object()), \
                 patch.object(store, "live_trade_snapshot", return_value=trade):
                payload = store.live_snapshot("fashion")
            self.assertEqual(payload["transactionSource"], "qianchuan_mcp")
            self.assertEqual(payload["metrics"]["spend"], 510.0)
            self.assertEqual(payload["metrics"]["gmv"], 700.0)
            self.assertEqual(payload["metrics"]["orderCost"], 28.33)
            self.assertEqual(
                payload["metricSources"]["gmv"]["refundPolicy"],
                "mcp_report",
            )

    def test_discover_live_room_returns_precise_room_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            room = {
                "room_id": 7699337106561846035,
                "room_status": "LIVING",
                "aweme_id": 7637818476896437305,
            }
            with patch.dict(
                "os.environ", {"QIANCHUAN_ACCESS_TOKEN": "test-token"}, clear=True
            ), patch.object(
                server.QianchuanClient,
                "fetch_live_rooms",
                return_value=[room],
            ):
                payload = store.discover_live_room("fashion")
            self.assertTrue(payload["live"])
            self.assertEqual(payload["roomId"], "7699337106561846035")
            self.assertEqual(payload["advertiserId"], "1744479430946824")


class HandlerTests(unittest.TestCase):
    def test_dashboard_and_health_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store, root))
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                port = httpd.server_address[1]
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/dashboard") as response:
                    dashboard = json.loads(response.read().decode("utf-8"))
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health") as response:
                    health = json.loads(response.read().decode("utf-8"))
                with patch.object(
                    store,
                    "mcp_tools",
                    return_value=[{"name": "qianchuan_report_live_get_v1"}],
                ):
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/mcp/tools") as response:
                        mcp_tools = json.loads(response.read().decode("utf-8"))
                with patch.object(store, "live_snapshot", return_value={"live": False, "syncedAt": "2026-10-19T21:00:00+08:00"}):
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/live?account=fashion") as response:
                        live = json.loads(response.read().decode("utf-8"))
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/sync",
                    data=b"",
                    method="POST",
                )
                with patch.dict("os.environ", {}, clear=True), \
                     patch.object(server, "TOKEN_FILE_PATH", root / "missing-token.json"):
                    with urllib.request.urlopen(request) as response:
                        synced = json.loads(response.read().decode("utf-8"))
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=2)
            self.assertEqual(dashboard["accounts"][0]["id"], "fashion")
            self.assertTrue(health["ok"])
            self.assertEqual(health["accountCount"], 1)
            self.assertEqual(mcp_tools["tools"][0]["name"], "qianchuan_report_live_get_v1")
            self.assertFalse(live["live"])
            self.assertEqual(synced["syncStatus"], "degraded")
            self.assertEqual(synced["revision"], dashboard["revision"] + 1)

    def test_quick_sync_endpoint_returns_within_three_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store, root))
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            release = threading.Event()

            def slow_sync(realtime_only=True):
                release.wait(6)
                return store.dashboard()

            try:
                port = httpd.server_address[1]
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/sync",
                    data=json.dumps({"mode": "realtime"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with patch.object(store, "sync", side_effect=slow_sync):
                    started = time.monotonic()
                    with urllib.request.urlopen(request, timeout=5) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                        elapsed = time.monotonic() - started
                self.assertLess(elapsed, 3.0)
                self.assertTrue(payload["syncRequest"]["running"])
                self.assertTrue(payload["syncRequest"]["started"])
            finally:
                release.set()
                store.wait_for_sync(timeout_seconds=1)
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=2)


class LiveStreamHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "index.html").write_text("ok", encoding="utf-8")
        self.store = server.DashboardStore(self.root / "snapshot.json")
        self.registry = server.LiveStreamRegistry(ttl_seconds=300)
        self.httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            server.make_handler(self.store, self.root, stream_registry=self.registry),
        )
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def test_capture_endpoints_and_live_merge(self) -> None:
        payload = {
            "roomId": "7698595680801098550",
            "url": "https://pull-flv.example.douyincdn.com/live.flv?sign=secret",
            "type": "flv",
        }
        request = urllib.request.Request(
            self.base + "/api/live/stream",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            registered = json.loads(response.read().decode("utf-8"))
        self.assertTrue(registered["ok"])
        self.assertNotIn("url", registered)

        with patch.object(
            self.store,
            "live_snapshot",
            return_value={
                "live": True,
                "room": {"id": "7698595680801098550"},
                "stream": {"url": "", "type": "auto", "source": ""},
            },
        ):
            with urllib.request.urlopen(self.base + "/api/live?account=fashion") as response:
                live = json.loads(response.read().decode("utf-8"))
        self.assertEqual(live["stream"]["source"], "qianchuan-board")
        self.assertEqual(live["stream"]["type"], "flv")
        self.assertIn("/api/live/stream.flv?room=", live["stream"]["proxyUrl"])
        self.assertTrue(live["stream"]["capture"]["captured"])

    def test_captured_stream_survives_temporary_live_metrics_failure(self) -> None:
        room_id = "7698595680801098550"
        self.registry.register(
            {
                "roomId": room_id,
                "url": "https://pull-flv.example.douyincdn.com/live.flv?sign=secret",
                "type": "flv",
            }
        )
        with patch.object(
            self.store,
            "live_snapshot",
            return_value={
                "live": False,
                "rooms": [],
                "errors": [{"message": "temporary rate limit"}],
                "stream": {"url": "", "type": "auto", "source": ""},
            },
        ):
            with urllib.request.urlopen(self.base + "/api/live?account=fashion") as response:
                live = json.loads(response.read().decode("utf-8"))
        self.assertFalse(live["live"])
        self.assertEqual(live["stream"]["roomId"], room_id)
        self.assertEqual(live["stream"]["source"], "qianchuan-board")
        self.assertIn(f"/api/live/stream.flv?room={room_id}", live["stream"]["proxyUrl"])
        self.assertTrue(live["stream"]["capture"]["captured"])

    def test_proxy_relays_registered_stream(self) -> None:
        self.registry.register(
            {
                "roomId": "7698595680801098550",
                "url": "https://pull-flv.example.douyincdn.com/live.flv?sign=secret",
                "type": "flv",
            }
        )

        class Upstream:
            def __init__(self) -> None:
                self.chunks = [b"FLV", b""]

            def read(self, _size: int) -> bytes:
                return self.chunks.pop(0)

            def close(self) -> None:
                pass

        original_urlopen = server.urllib.request.urlopen
        upstream_calls = []

        def fake_urlopen(target, *args, **kwargs):
            if isinstance(target, server.urllib.request.Request):
                upstream_calls.append(target.full_url)
                return Upstream()
            return original_urlopen(target, *args, **kwargs)

        with patch.object(server.urllib.request, "urlopen", side_effect=fake_urlopen):
            with urllib.request.urlopen(
                self.base + "/api/live/stream.flv?room=7698595680801098550"
            ) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type")
        self.assertEqual(body, b"FLV")
        self.assertEqual(content_type, "video/x-flv")
        self.assertEqual(len(upstream_calls), 1)


if __name__ == "__main__":
    unittest.main()
