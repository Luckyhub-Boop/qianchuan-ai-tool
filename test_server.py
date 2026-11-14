from __future__ import annotations

import copy
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer
from io import BytesIO
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
        self.assertIn('metricValue("orderCost"', html)
        for metric in ("spend", "gmv", "orders", "roi", "cost"):
            self.assertIn(f'data-metric="{metric}"', html)
        self.assertIn("accountOrderRank", html)
        self.assertIn("ADVERTISER_TOTALS", html)
        self.assertIn("千川广告主账户", html)
        self.assertIn("return `¥${formatNumber(value, 2)}`", html)
        self.assertIn("syncFollowupGeneration", html)
        self.assertIn("全域推广报表数据", html)
        self.assertNotIn("直播大屏双通道", html)
        self.assertIn("实时监控曲线", html)
        self.assertIn('id="dataLiveKpis"', html)
        self.assertIn("千川直播大屏页面直接抓取", html)
        self.assertIn("抓取失败", html)
        self.assertIn("MCP 优先", html)
        self.assertIn("/api/campaign/diagnostics", html)
        self.assertIn("近 30 天真实日均", html)
        self.assertIn("直播大屏采集器", html)
        self.assertIn("function captureNotLive(payload)", html)
        self.assertIn("四个账号均已确认未开播", html)
        self.assertIn("playbackUrl: serverStream.proxyUrl || serverStream.url", html)
        self.assertIn("enableStashBuffer: true", html)
        self.assertIn("hasAudio: false", html)
        self.assertIn("MCP 当前未提供素材维度工具", html)
        self.assertIn("按曝光量降序", html)
        self.assertIn("待核对上传时间", html)
        self.assertIn('id="materialSelectToggle"', html)
        self.assertIn('id="materialSelectAll"', html)
        self.assertIn('id="materialExportBtn"', html)
        self.assertIn('id="materialGrade"', html)
        self.assertIn("buildMaterialXlsx", html)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", html)
        self.assertIn('id="learningDocUploadBtn"', html)
        self.assertIn('id="learningDocsList"', html)
        self.assertIn('id="learningReindexBtn"', html)
        self.assertIn('id="aiDiagnosisLearning"', html)
        self.assertIn("/api/learning/documents", html)
        self.assertIn("/api/learning/search", html)
        self.assertIn("/api/assistant/chat", html)
        self.assertIn('id="knowledgeChatForm"', html)
        self.assertIn('id="knowledgeChatLog"', html)
        self.assertIn('id="knowledgeProgressBar"', html)
        self.assertIn('id="knowledgeOutcomeSummary"', html)
        self.assertIn("data-knowledge-app-status", html)
        self.assertIn("学习成果已应用到", html)
        self.assertIn("learningAdvice", html)
        self.assertIn("产品学习资料", html)
        self.assertIn("knowledge-source-note", html)
        self.assertIn("经验底线校验", html)
        self.assertIn("/api/live/refresh", html)
        self.assertIn("正在拉取最新数据...", html)
        self.assertIn("manualRefreshAll", html)
        self.assertIn("优先使用千川 MCP", html)
        self.assertIn("大屏直抓", html)
        self.assertIn("MCP 优先", html)
        self.assertIn("不跨数据源混算", html)
        self.assertIn("大屏直抓（MCP暂不可用）", html)
        self.assertIn("流量占比", html)
        self.assertIn("成交金额占比", html)
        self.assertIn("千次观看成交", html)
        self.assertIn("大屏渠道明细", html)
        self.assertNotIn('["消耗 / 时"', html)
        self.assertNotIn('["付费流量", paid', html)
        self.assertIn("/api/campaign/operation-forecast", html)
        self.assertIn("教培直播间承接动作", html)
        self.assertIn("知识库只补充教培直播间投放逻辑", html)
        self.assertNotIn("未剔除退款", html)
        self.assertNotIn('id="dataLiveTrendChart"', html)
        self.assertNotIn('id="dataLiveBoard"', html)


class OAuthTests(unittest.TestCase):
    def test_authorize_url_contains_registered_callback_and_state(self) -> None:
        config = {
            "appId": "app-123",
            "appSecret": "secret",
            "redirectUri": "http://127.0.0.1:8767/oauth/callback",
            "scope": ["qianchuan.report", "qianchuan.material"],
        }
        url = server.build_oauth_authorize_url(config, "state-456")
        parsed = server.urllib.parse.urlparse(url)
        query = server.urllib.parse.parse_qs(parsed.query)
        self.assertEqual(parsed.netloc, "open.oceanengine.com")
        self.assertEqual(parsed.path, "/audit/oauth.html")
        self.assertEqual(query["app_id"], ["app-123"])
        self.assertEqual(query["state"], ["state-456"])
        self.assertEqual(
            query["redirect_uri"],
            ["http://127.0.0.1:8767/oauth/callback"],
        )
        self.assertEqual(
            query["scope"],
            ["qianchuan.report,qianchuan.material"],
        )

    def test_oauth_token_response_sets_expiry_without_losing_refresh_token(self) -> None:
        record = server.oauth_token_record(
            {
                "code": 0,
                "data": {
                    "access_token": "access-new",
                    "refresh_token": "refresh-new",
                    "expires_in": 3600,
                    "scope": ["qianchuan.report"],
                },
            },
            "app-123",
        )
        self.assertEqual(record["accessToken"], "access-new")
        self.assertEqual(record["refreshToken"], "refresh-new")
        self.assertEqual(record["appId"], "app-123")
        self.assertTrue(record["expiresAt"])
        self.assertNotEqual(record["expiresAt"], "未获取")

    def test_expired_token_is_flagged_for_refresh(self) -> None:
        expired = {
            "accessToken": "old",
            "expiresAt": (
                datetime.now().astimezone() - timedelta(minutes=1)
            ).isoformat(timespec="seconds"),
        }
        valid = {
            "accessToken": "new",
            "expiresAt": (
                datetime.now().astimezone() + timedelta(hours=1)
            ).isoformat(timespec="seconds"),
        }
        self.assertTrue(server.token_needs_refresh(expired))
        self.assertFalse(server.token_needs_refresh(valid))


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

    def test_registry_accepts_bytefcdn_redirect_host(self) -> None:
        registry = server.LiveStreamRegistry()
        result = registry.register(
            {
                "roomId": "123456789",
                "url": "https://112-45-41-64.bytefcdnrd.com/live.flv?sign=test",
                "type": "flv",
            }
        )
        self.assertEqual(result["roomId"], "123456789")
        self.assertEqual(registry.resolve("123456789")["type"], "flv")

    def test_registry_prefers_signed_origin_over_bad_certificate_redirect(self) -> None:
        registry = server.LiveStreamRegistry()
        origin = (
            "https://pull-x3-f5.douyincdn.com/third/stream.flv"
            "?expire=1794642278&sign=origin-secret"
        )
        redirect = (
            "https://2408_8720_800_422_8000_0_b00_146.bytefcdnrd.com"
            "/third/stream.flv?redirect_from=pod"
            "&fp_user_url=" + urllib.parse.quote(origin, safe="")
        )
        registry.register(
            {
                "roomId": "123456789",
                "url": redirect,
                "type": "flv",
            }
        )
        resolved = registry.resolve("123456789")
        self.assertEqual(resolved["url"], origin)


class MaterialTests(unittest.TestCase):
    def test_video_library_uses_documented_create_time_as_upload_time(self) -> None:
        config = json.loads(json.dumps(server.DEFAULT_CONFIG))
        client = server.QianchuanClient(config, "test-token")
        page = {
            "data": {
                "list": [
                    {
                        "material_id": "m-video-1",
                        "id": "v-video-1",
                        "filename": "测试视频",
                        "duration": 31.5,
                        "create_time": "2026-01-01 08:30:00",
                        "poster_url": "https://example.test/cover.jpg",
                    }
                ],
                "page_info": {"total_number": 1, "total_page": 1},
            }
        }
        with patch.object(
            client,
            "_fetch_campaign_pages",
            return_value=([page["data"]["list"][0]], [page]),
        ):
            materials, meta = client.fetch_qianchuan_video_library(
                "advertiser-1",
                with_meta=True,
            )
        self.assertEqual(materials[0]["uploadedAt"][:10], "2026-01-01")
        self.assertGreater(materials[0]["uploadAgeDays"], 40)
        self.assertEqual(
            materials[0]["uploadTimeSource"],
            "千川素材库视频 create_time",
        )
        self.assertTrue(meta["complete"])
        self.assertEqual(meta["uploadTimeCount"], 1)

    def test_video_library_metadata_overlays_plan_material(self) -> None:
        plans = [{
            "id": "plan-1",
            "materials": [{
                "id": "m-video-1",
                "uploadedAt": "未获取",
                "uploadAgeDays": None,
                "duration": "—",
                "cover": None,
                "videoUrl": None,
                "impressions": 10,
                "orders": 0,
            }, {
                "id": "m-history-only",
                "uploadedAt": "未获取",
                "uploadAgeDays": None,
                "impressions": 5,
                "orders": 0,
            }],
        }]
        library = [{
            "id": "m-video-1",
            "duration": 42,
            "cover": "https://example.test/cover.jpg",
            "videoUrl": "https://example.test/video.mp4",
            "uploadedAt": "2026-01-01T08:30:00+08:00",
            "uploadAgeDays": 297,
            "uploadTimeSource": "千川素材库视频 create_time",
        }]
        matched = server.DashboardStore._merge_video_library_metadata(plans, library)
        material = plans[0]["materials"][0]
        self.assertEqual(matched, 1)
        self.assertEqual(material["uploadedAt"][:10], "2026-01-01")
        self.assertEqual(material["uploadAgeDays"], 297)
        self.assertEqual(material["duration"], 42)
        self.assertTrue(material["deleteRecommendation"])
        self.assertFalse(material["deleteReviewRequired"])
        unmatched = plans[0]["materials"][1]
        self.assertFalse(unmatched["deleteRecommendation"])
        self.assertTrue(unmatched["deleteReviewRequired"])

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
                    "total_order_settle_amount_for_roi2_1h": 456.78,
                    "total_order_settle_count_for_roi2_1h": 9,
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

    def test_material_upload_age_controls_delete_recommendation(self) -> None:
        base_row = {
            "dimensions": {
                "material_id": {"Value": "m-age"},
                "roi2_material_video_name": {"Value": "低效素材"},
                "roi2_material_video_type": {"Value": "2"},
            },
            "metrics": {
                "stat_cost_for_roi2": {"Value": 1.0},
                "live_show_count_for_roi2_v2": {"Value": 10.0},
                "total_pay_order_count_for_roi2": {"Value": 0.0},
            },
        }
        known = server.normalize_uni_promotion_material_report(
            [
                {
                    **base_row,
                    "dimensions": {
                        **base_row["dimensions"],
                        "material_create_time": {"Value": "2026-01-01 00:00:00"},
                    },
                }
            ],
            "aweme-1",
            "VIDEO",
            {"start": "2026-07-01", "end": "2026-10-24", "days": 116},
        )[0]
        unknown = server.normalize_uni_promotion_material_report(
            [base_row],
            "aweme-1",
            "VIDEO",
            {"start": "2026-07-01", "end": "2026-10-24", "days": 116},
        )[0]

        self.assertTrue(known["deleteRecommendation"])
        self.assertFalse(known["deleteReviewRequired"])
        self.assertEqual(known["uploadedAt"][:10], "2026-01-01")
        self.assertEqual(unknown["uploadedAt"], "未获取")
        self.assertIsNone(unknown["uploadAgeDays"])
        self.assertFalse(unknown["deleteRecommendation"])
        self.assertTrue(unknown["deleteReviewRequired"])

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
                    "total_order_settle_amount_for_roi2_1h": {"Value": 20.0},
                    "total_order_settle_count_for_roi2_1h": {"Value": 2.0},
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
                    "total_order_settle_amount_for_roi2_1h": {"Value": 7.5},
                    "total_order_settle_count_for_roi2_1h": {"Value": 1.0},
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
        dimensions = json.loads(params["dimensions"])
        self.assertNotIn("stat_time_day", dimensions)
        self.assertIn("material_id", dimensions)

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
        }, {
            "id": "deleted-material",
            "name": "已从素材库删除",
            "spend": 9.0,
            "gmv": 18.0,
            "orders": 1.0,
            "impressions": 500.0,
            "clicks": 20.0,
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
        self.assertEqual(len(plans[0]["materials"]), 1)
        self.assertEqual(plans[0]["materialReportUnmatchedCount"], 1)
        self.assertEqual(plans[0]["materialReportUnmatchedIds"], ["deleted-material"])

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
    def test_net_settled_metrics_are_canonical_and_gross_is_audit_only(self) -> None:
        metrics = server.settled_transaction_metrics(
            {
                "stat_cost": 100.0,
                "total_order_settle_amount_for_roi2_1h": 56.0,
                "total_order_settle_count_for_roi2_1h": 2,
                "total_prepay_and_pay_settle_roi2_1h": 0.56,
                "total_pay_order_gmv_for_roi2": 80.0,
                "total_pay_order_count_for_roi2": 3,
                "total_prepay_and_pay_order_roi2": 0.8,
            }
        )
        self.assertEqual(metrics["gmv"], 56.0)
        self.assertEqual(metrics["orders"], 2)
        self.assertEqual(metrics["roi"], 0.56)
        self.assertEqual(metrics["grossGmv"], 80.0)
        self.assertEqual(metrics["grossOrders"], 3)
        self.assertEqual(metrics["gmvScope"], "net")
        self.assertEqual(metrics["grossGmvScope"], "gross_including_refund")

    def test_normalizes_and_merges_duplicate_dates(self) -> None:
        rows = [
            {
                "stat_date": "2026-10-18",
                "stat_cost": "10.5",
                "total_order_settle_amount_for_roi2_1h": "20",
                "total_order_settle_count_for_roi2_1h": 2,
            },
            {
                "stat_date": "2026-10-18",
                "stat_cost": 4.5,
                "total_order_settle_amount_for_roi2_1h": 5,
                "total_order_settle_count_for_roi2_1h": 1,
            },
            {
                "date": "2026-10-17",
                "spend": 3,
                "total_order_settle_amount_for_roi2_1h": 9,
                "total_order_settle_count_for_roi2_1h": 1,
            },
            {
                "date": "2026-04-19",
                "spend": 99,
                "total_order_settle_amount_for_roi2_1h": 99,
                "total_order_settle_count_for_roi2_1h": 99,
            },
        ]
        result = server.normalize_daily_rows(rows, server.DEFAULT_FIELD_MAP, "2026-04-20", "2026-10-18")
        self.assertEqual([row["date"] for row in result], ["2026-10-17", "2026-10-18"])
        self.assertEqual(result[1]["spend"], 15.0)
        self.assertEqual(result[1]["gmv"], 25.0)
        self.assertEqual(result[1]["orders"], 3.0)
        self.assertEqual(result[1]["gmvScope"], "net")

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
            "total_order_settle_amount_for_roi2_1h": 250000,
            "total_order_settle_count_for_roi2_1h": 3,
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
        fields = call.call_args.args[1]["fields"]
        self.assertEqual(fields[:3], [
            "stat_cost",
            "total_order_settle_amount_for_roi2_1h",
            "total_order_settle_amount_realtime_for_roi2_1h",
        ])
        for field in (
            "total_live_watch_cnt",
            "live_watch_one_minute_count",
            "gpm",
            "online_count",
        ):
            self.assertIn(field, fields)

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
                {
                    "stat_date": "2026-10-17",
                    "stat_cost": 10,
                    "total_order_settle_amount_for_roi2_1h": 20,
                    "total_order_settle_count_for_roi2_1h": 2,
                },
                {
                    "stat_date": "2026-10-18",
                    "stat_cost": 11,
                    "total_order_settle_amount_for_roi2_1h": 22,
                    "total_order_settle_count_for_roi2_1h": 3,
                },
            ]
            realtime_account_row = {
                "stat_date": today,
                "stat_cost": 7,
                "total_order_settle_amount_for_roi2_1h": 14,
                "total_order_settle_count_for_roi2_1h": 1,
            }
            fake_plans = [
                {
                    "id": "c-1",
                    "name": "测试计划 A",
                    "status": "已暂停",
                    "data": [
                        {"date": "2026-10-17", "spend": 10.0, "gmv": 20.0, "orders": 2.0, "gmvScope": "net"},
                        {"date": "2026-10-18", "spend": 11.0, "gmv": 22.0, "orders": 3.0, "gmvScope": "net"},
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
                        "total_order_settle_amount_for_roi2_1h": 800000,
                        "total_order_settle_count_for_roi2_1h": 2,
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
                 patch.object(
                     server.QianchuanClient,
                     "fetch_uni_promotion_materials",
                     return_value=(
                         [],
                         {
                             "sourceTotal": 0,
                             "uniqueCount": 0,
                             "missingCount": 0,
                             "totalReported": True,
                             "complete": True,
                         },
                     ),
                 ) as material_fetch:
                result = store.sync()
            self.assertGreaterEqual(material_fetch.call_count, 1)
            material_args = material_fetch.call_args_list[0].args
            material_start = date.fromisoformat(material_args[2])
            material_end = date.fromisoformat(material_args[3])
            self.assertEqual(material_start, date(2026, 7, 1))
            self.assertEqual(material_end, date.today() - timedelta(days=1))
            self.assertEqual(result["syncStatus"], "success")
            self.assertEqual(result["mode"], "live")
            self.assertEqual(result["accounts"][0]["data"], [
                {"date": "2026-10-17", "spend": 10.0, "gmv": 20.0, "orders": 2.0, "gmvScope": "net"},
                {"date": "2026-10-18", "spend": 11.0, "gmv": 22.0, "orders": 3.0, "gmvScope": "net"},
                {
                    "date": today,
                    "spend": 7.0,
                    "gmv": 14.0,
                    "orders": 1.0,
                    "gmvScope": "net",
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

    def test_dashboard_uses_screen_only_as_labelled_mcp_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            today = date.today().isoformat()
            snapshot = store.dashboard()
            account = snapshot["accounts"][0]
            if not account.get("awemes"):
                account["awemes"] = [
                    {
                        "id": "live-aweme",
                        "name": "测试直播号",
                        "status": "直播中",
                        "data": [],
                    }
                ]
            aweme = account["awemes"][0]
            aweme["id"] = "live-aweme"
            aweme["data"] = [
                {
                    "date": today,
                    "spend": 4500.0,
                    "gmv": 2016.0,
                    "orders": 12.0,
                    "grossGmv": 2520.0,
                    "grossOrders": 15.0,
                    "gmvScope": "net",
                }
            ]
            account["data"] = copy.deepcopy(aweme["data"])
            store.snapshot = snapshot
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "ok",
                    "live": True,
                    "syncedAt": server.now_iso(),
                    "heartbeatAt": server.now_iso(),
                    "room": {
                        "id": "room-1",
                        "awemeId": "live-aweme",
                    },
                    "metrics": {
                        "spend": 4535.17,
                        "gmv": 1512.0,
                        "orders": 12.0,
                        "roi": 0.33,
                        "orderCost": 377.93,
                    },
                },
            )

            dashboard = store.dashboard()
            dashboard_account = dashboard["accounts"][0]
            dashboard_aweme = dashboard_account["awemes"][0]
            account_today = next(
                row for row in dashboard_account["data"] if row["date"] == today
            )
            aweme_today = next(
                row for row in dashboard_aweme["data"] if row["date"] == today
            )
            self.assertEqual(account_today["gmv"], 1512.0)
            self.assertEqual(account_today["grossGmv"], 2520.0)
            self.assertEqual(account_today["gmvScope"], "screen_net")
            self.assertEqual(account_today["metricSource"], "live_screen_fallback")
            self.assertEqual(account_today["source"], "大屏直抓（MCP暂不可用）")
            self.assertEqual(aweme_today["gmv"], 1512.0)
            self.assertEqual(
                dashboard["realtime"]["sources"]["live_screen_fallback"],
                1,
            )
            self.assertEqual(dashboard["transactionScope"], "screen_fallback")
            self.assertEqual(
                dashboard_account["reconciliation"]["difference"]["gmv"],
                0.0,
            )

    def test_dashboard_prefers_cached_mcp_over_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            today = date.today().isoformat()
            snapshot = store.dashboard()
            account = snapshot["accounts"][0]
            account["awemes"] = [
                {
                    "id": "live-aweme",
                    "name": "测试直播号",
                    "status": "直播中",
                    "data": [],
                }
            ]
            account["data"] = [
                {
                    "date": today,
                    "spend": 100.0,
                    "gmv": 120.0,
                    "orders": 2.0,
                    "gmvScope": "net",
                }
            ]
            store.snapshot = snapshot
            with store.live_lock:
                store.campaign_cache["fashion"] = (
                    time.time(),
                    {
                        "ok": True,
                        "mcpAvailable": True,
                        "syncedAt": server.now_iso(),
                        "room": {"awemeId": "live-aweme"},
                        "metrics": {
                            "spend": 900.0,
                            "gmv": 480.0,
                            "orders": 8.0,
                            "roi": 0.53,
                            "cost": 112.5,
                        },
                    },
                )
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "ok",
                    "live": True,
                    "syncedAt": server.now_iso(),
                    "heartbeatAt": server.now_iso(),
                    "room": {"id": "room-1", "awemeId": "live-aweme"},
                    "metrics": {
                        "spend": 950.0,
                        "gmv": 500.0,
                        "orders": 9.0,
                        "roi": 0.52,
                        "orderCost": 105.56,
                    },
                },
            )

            dashboard = store.dashboard()
            today_row = next(
                row
                for row in dashboard["accounts"][0]["data"]
                if row["date"] == today
            )
            self.assertEqual(today_row["gmv"], 480.0)
            self.assertEqual(today_row["orders"], 8.0)
            self.assertEqual(today_row["metricSource"], "mcp")
            self.assertEqual(today_row["source"], "千川 MCP · 主数据源")
            self.assertEqual(dashboard["transactionScope"], "mcp")

    def test_account_realtime_falls_back_to_official_plan_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.json"
            store = server.DashboardStore(snapshot_path)
            today = date.today().isoformat()
            history_rows = [{
                "stat_date": "2026-10-20",
                "stat_cost": 10,
                "total_order_settle_amount_for_roi2_1h": 20,
                "total_order_settle_count_for_roi2_1h": 2,
            }]
            historical_plan = [{
                "id": "c-1",
                "name": "测试计划",
                "status": "投放中",
                "data": [{"date": "2026-10-20", "spend": 10.0, "gmv": 20.0, "orders": 2.0, "gmvScope": "net"}],
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
                    "total_order_settle_amount_for_roi2_1h": 1800000,
                    "total_order_settle_count_for_roi2_1h": 3,
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
                 patch.object(
                     server.QianchuanClient,
                     "fetch_uni_promotion_materials",
                     return_value=(
                         [],
                         {
                             "sourceTotal": 0,
                             "uniqueCount": 0,
                             "missingCount": 0,
                             "totalReported": True,
                             "complete": True,
                         },
                     ),
                 ):
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

    def test_live_snapshot_never_falls_back_to_mcp_trade(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "partial",
                    "source": "puppeteer-core",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "watchCount": 12800,
                        "productClicks": 2345,
                        "peakOnline": 386,
                        "gpm": 912.35,
                        "online": 88,
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(
                store,
                "live_trade_snapshot",
                side_effect=AssertionError("MCP trade fallback must not be called"),
            ), patch.object(
                store,
                "live_five_dimension",
                return_value={"status": "partial", "values": {"watch": 12800}, "sources": {}, "missing": []},
            ):
                payload = store.live_snapshot("fashion")
            self.assertTrue(payload["live"])
            self.assertEqual(payload["source"], "qianchuan_live_screen_direct")
            self.assertFalse(payload["channels"]["trade"]["ok"])
            self.assertTrue(payload["channels"]["behavior"]["ok"])
            self.assertNotIn("spend", payload["metrics"])
            self.assertEqual(payload["metrics"]["watchCount"], 12800)
            self.assertIn("抓取失败", payload["errors"][0]["message"])

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
                        "spend": 120.5,
                        "gmv": 360.75,
                        "orders": 5,
                        "orderCost": 24.1,
                        "roi": 2.99,
                        "watchCount": 12800,
                        "productClicks": 2345,
                        "peakOnline": 386,
                        "gpm": 912.35,
                        "online": 88,
                    },
                    "flows": [
                        {"key": "live_pc_qian_chuan", "label": "千川PC", "value": 60, "unit": "percent"}
                    ],
                }),
                encoding="utf-8",
            )
            with patch.object(
                store,
                "live_five_dimension",
                return_value={"status": "ok", "values": {"watch": 12800}, "sources": {"watch": "mcp"}, "missing": []},
            ):
                payload = store.live_snapshot("fashion")
            self.assertTrue(payload["live"])
            self.assertEqual(payload["source"], "qianchuan_live_screen_direct")
            self.assertTrue(payload["channels"]["trade"]["ok"])
            self.assertTrue(payload["channels"]["behavior"]["ok"])
            self.assertEqual(payload["room"]["id"], "room-screen")
            self.assertEqual(payload["metrics"]["spend"], 120.5)
            self.assertEqual(payload["metrics"]["gmv"], 360.75)
            self.assertEqual(payload["metrics"]["orders"], 5)
            self.assertEqual(payload["metrics"]["orderCost"], 24.1)
            self.assertEqual(payload["metrics"]["roi"], 2.99)
            self.assertEqual(payload["metrics"]["watchCount"], 12800)
            self.assertEqual(payload["metrics"]["productClicks"], 2345)
            self.assertEqual(payload["metrics"]["peakOnline"], 386)
            self.assertEqual(payload["metrics"]["gpm"], 912.35)

    def test_live_snapshot_uses_screen_data_when_mcp_returns_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "partial",
                    "source": "puppeteer-core",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "spend": 2802.41,
                        "gmv": 1008,
                        "orders": 6,
                        "orderCost": 467.07,
                        "roi": 0.36,
                        "watchCount": 735,
                        "watchOneMinute": 521,
                        "comments": 38,
                        "productClicks": 184,
                        "gpm": 1161.29,
                        "exposure": 21440,
                        "online": 3,
                    },
                }),
                encoding="utf-8",
            )
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            http_error = server.urllib.error.HTTPError(
                "https://example.test/mcp",
                400,
                "Bad Request",
                None,
                None,
            )

            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(client, "fetch_live_room", side_effect=http_error):
                payload = store.live_snapshot("fashion")
                deadline = time.monotonic() + 2
                while (
                    "five:fashion" in store.five_dimension_inflight
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)

            self.assertTrue(payload["live"])
            self.assertEqual(payload["source"], "qianchuan_live_screen_direct")
            self.assertEqual(payload["captureStatus"], "partial")
            self.assertEqual(payload["metrics"]["spend"], 2802.41)
            self.assertEqual(payload["metrics"]["gmv"], 1008)
            self.assertEqual(payload["metrics"]["orders"], 6)
            self.assertEqual(payload["metrics"]["roi"], 0.36)
            self.assertEqual(payload["fiveDimension"]["values"]["watch"], 735)
            self.assertEqual(
                payload["fiveDimension"]["sources"]["watch"],
                "screen:live_board",
            )
            self.assertIn(
                payload["fiveDimension"]["mcpStatus"],
                {"pending", "error"},
            )
            self.assertIn("HTTP Error 400", store.five_dimension_last_error["five:fashion"])
            self.assertEqual(payload["error"], "")

    def test_live_snapshot_survives_unhandled_five_dimension_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "partial",
                    "source": "puppeteer-core",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "spend": 3697.6,
                        "gmv": 1512,
                        "orders": 9,
                        "orderCost": 410.84,
                        "roi": 0.41,
                        "watchCount": 954,
                        "productClicks": 240,
                        "gpm": 1341.61,
                        "online": 0,
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(
                store,
                "live_five_dimension",
                side_effect=RuntimeError("unexpected MCP failure"),
            ):
                payload = store.live_snapshot("fashion")

            self.assertTrue(payload["live"])
            self.assertEqual(payload["metrics"]["spend"], 3697.6)
            self.assertEqual(payload["metrics"]["gmv"], 1512)
            self.assertEqual(payload["metrics"]["orders"], 9)
            self.assertEqual(payload["fiveDimension"]["mcpStatus"], "error")
            self.assertIn("unexpected MCP failure", payload["fiveDimension"]["mcpError"])
            self.assertEqual(payload["error"], "")

    def test_live_login_required_is_not_reported_as_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "login_required",
                    "source": "puppeteer-core",
                    "metrics": {},
                    "error": "登录已过期，请执行 login-live-screen.bat",
                }),
                encoding="utf-8",
            )
            with patch.object(
                store,
                "live_five_dimension",
                return_value={"status": "partial", "values": {}, "sources": {}, "missing": []},
            ):
                payload = store.live_snapshot("fashion")

            self.assertFalse(payload["live"])
            self.assertEqual(payload["captureStatus"], "login_required")
            self.assertTrue(payload["loginRequired"])
            self.assertIn("登录已过期", payload["error"])
            self.assertEqual(payload["error"], "登录已过期，请重新登录")
            self.assertEqual(payload["channels"]["trade"]["error"], "登录已过期，请重新登录")
            self.assertEqual(payload["channels"]["behavior"]["error"], "登录已过期，请重新登录")
            self.assertTrue(
                all("登录已过期" in item["message"] for item in payload["errors"])
            )

    def test_confirmed_not_live_has_no_stale_metrics_or_capture_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            checked_accounts = [
                {"awemeId": "1", "name": "图解", "status": "not_live", "roomId": ""},
                {"awemeId": "2", "name": "精讲", "status": "not_live", "roomId": ""},
                {"awemeId": "3", "name": "拆解", "status": "not_live", "roomId": ""},
                {"awemeId": "4", "name": "通解", "status": "not_live", "roomId": ""},
            ]
            store.live_screen_path.write_text(
                json.dumps(
                    {
                        "heartbeatAt": server.now_iso(),
                        "intervalSeconds": 10,
                        "status": "not_live",
                        "detectionStatus": "not_live",
                        "source": "puppeteer-core",
                        "sourceLabel": "未开播",
                        "room": {},
                        "metrics": {},
                        "checkedAccounts": checked_accounts,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                store,
                "live_five_dimension",
                return_value={"status": "not_live", "values": {}, "sources": {}, "missing": []},
            ):
                payload = store.live_snapshot("fashion")

            self.assertFalse(payload["live"])
            self.assertEqual(payload["captureStatus"], "not_live")
            self.assertEqual(payload["sourceLabel"], "未开播")
            self.assertEqual(payload["detectionStatus"], "not_live")
            self.assertEqual(payload["checkedAccounts"], checked_accounts)
            self.assertEqual(payload["metrics"], {})
            self.assertEqual(payload["errors"], [])
            self.assertEqual(payload["error"], "未开播")
            self.assertEqual(payload["channels"]["trade"]["status"], "not_live")
            self.assertEqual(payload["channels"]["behavior"]["status"], "not_live")
            self.assertTrue(store.live_screen_status()["ok"])

    def test_fresh_stale_screen_values_remain_usable_when_mcp_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "stale",
                    "staleWarning": "本轮未取得新指标，保留上一次有效值",
                    "source": "puppeteer-core",
                    "room": {"id": "room-stale"},
                    "metrics": {
                        "spend": 3697.6,
                        "gmv": 1512,
                        "orders": 9,
                        "orderCost": 410.84,
                        "roi": 0.41,
                        "watchCount": 954,
                        "productClicks": 240,
                        "gpm": 1341.61,
                        "online": 0,
                    },
                }),
                encoding="utf-8",
            )
            with patch.object(store, "_get_mcp_client", return_value=None):
                payload = store.live_snapshot("fashion")

            self.assertTrue(payload["live"])
            self.assertEqual(payload["captureStatus"], "stale")
            self.assertEqual(payload["metrics"]["spend"], 3697.6)
            self.assertEqual(payload["metrics"]["gmv"], 1512)
            self.assertEqual(payload["metrics"]["orders"], 9)
            self.assertIn("保留上一次有效值", payload["staleWarning"])

    def test_live_history_is_persisted_and_bucketed_by_five_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            base = datetime.now().astimezone().replace(second=0, microsecond=0)
            first = base - timedelta(minutes=10)
            second = base - timedelta(minutes=5)
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": first.isoformat(),
                    "syncedAt": first.isoformat(),
                    "status": "ok",
                    "room": {"id": "room-history"},
                    "metrics": {
                        "spend": 10,
                        "gmv": 20,
                        "orders": 1,
                        "roi": 2,
                        "watchCount": 100,
                        "productClicks": 10,
                        "peakOnline": 8,
                        "gpm": 200,
                        "online": 5,
                    },
                    "flows": [{"key": "homepage_hot", "label": "直播推荐", "value": 70}],
                }),
                encoding="utf-8",
            )
            store.capture_live_screen_history()
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": second.isoformat(),
                    "syncedAt": second.isoformat(),
                    "status": "ok",
                    "room": {"id": "room-history"},
                    "metrics": {
                        "spend": 30,
                        "gmv": 60,
                        "orders": 3,
                        "roi": 2,
                        "watchCount": 200,
                        "productClicks": 20,
                        "peakOnline": 9,
                        "gpm": 300,
                        "online": 6,
                    },
                }),
                encoding="utf-8",
            )
            store.capture_live_screen_history()
            history = store.live_history_snapshot("fashion", bucket_minutes=5)
            self.assertTrue(store.live_history_path.is_file())
            self.assertEqual(history["bucketMinutes"], 5)
            self.assertGreaterEqual(len(history["points"]), 2)
            self.assertEqual(history["points"][-1]["roomId"] if "roomId" in history["points"][-1] else history["roomId"], "room-history")
            self.assertEqual(history["points"][-1]["spend"], 30)
            self.assertEqual(history["points"][-1]["watch"], 200)

    def test_corrupt_live_history_recovers_backup_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            first = {
                "version": 1,
                "days": {
                    "2026-10-25": {
                        "room-backup": [
                            {"t": 1, "spend": 10, "gmv": 20, "orders": 1}
                        ]
                    }
                },
            }
            second = {
                "version": 1,
                "days": {
                    "2026-10-25": {
                        "room-backup": [
                            {"t": 2, "spend": 30, "gmv": 60, "orders": 3}
                        ]
                    }
                },
            }
            store._write_live_history(first)
            store._write_live_history(second)
            store.live_history_path.write_text(
                '{"version":1,"days":{}}\n}\n',
                encoding="utf-8",
            )

            recovered = store._load_live_history()

            self.assertEqual(recovered["days"]["2026-10-25"]["room-backup"][0]["spend"], 10)
            self.assertIn("recoveryWarning", recovered)
            self.assertTrue(store.live_history_backup_path.is_file())
            self.assertTrue(
                any(store.live_history_path.parent.glob("live-screen-history.corrupt-*.json"))
            )

    def test_five_dimension_prefers_mcp_and_falls_back_per_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            response = {
                "tool": server.QianchuanMCPClient.LIVE_REPORT_TOOL,
                "room": {
                    "total_live_watch_cnt": 1000,
                    "total_live_comment_cnt": 80,
                    "pay_order_count": 12,
                },
                "payload": {},
                "arguments": {},
            }
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(client, "fetch_live_room", return_value=response):
                result = store.live_five_dimension(
                    "fashion",
                    {
                        "watchCount": 999,
                        "watchOneMinute": 420,
                        "comments": 1,
                        "orders": 1,
                    },
                    background=False,
                )
            self.assertEqual(result["values"]["watch"], 1000)
            self.assertEqual(result["values"]["stay"], 420)
            self.assertEqual(result["values"]["comments"], 80)
            self.assertEqual(result["sources"]["watch"], "mcp:qianchuan_report_live_get_v1")
            self.assertEqual(result["sources"]["stay"], "screen:live_board")

    def test_five_dimension_uses_nonzero_today_live_fields_and_ignores_zero_pending(self) -> None:
        direct = server.DashboardStore._five_dimension_payload(
            {
                "watchCount": 999,
                "watchOneMinute": 420,
                "comments": 17,
                "orders": 3,
            },
            {},
            official_live={
                "status": "ok",
                "metrics": {
                    "watchCount": 1200,
                    "watchOneMinute": 480,
                    "comments": 30,
                    "orders": 4,
                },
            },
        )
        self.assertEqual(direct["values"]["watch"], 1200)
        self.assertEqual(direct["values"]["stay"], 480)
        self.assertEqual(direct["values"]["comments"], 30)
        self.assertEqual(direct["values"]["orders"], 4)
        self.assertEqual(
            direct["sources"]["stay"],
            "official:qianchuan_today_live",
        )
        sample = server.DashboardStore._screen_sample(
            {
                "metrics": {"watchCount": 999, "orders": 3},
                "syncedAt": "2026-11-05T05:00:00.000Z",
            },
            direct,
        )
        self.assertEqual(sample["watchOneMinute"], 480)
        self.assertEqual(sample["comments"], 30)

        zero_pending = server.DashboardStore._five_dimension_payload(
            {
                "watchCount": 999,
                "watchOneMinute": 420,
                "comments": 17,
                "orders": 3,
            },
            {},
            official_live={
                "status": "zero_pending",
                "metrics": {
                    "watchCount": 0,
                    "watchOneMinute": 0,
                    "comments": 0,
                    "orders": 0,
                },
            },
        )
        self.assertEqual(zero_pending["values"]["watch"], 999)
        self.assertEqual(zero_pending["values"]["stay"], 420)
        self.assertEqual(zero_pending["values"]["comments"], 17)
        self.assertEqual(zero_pending["values"]["orders"], 3)
        self.assertEqual(zero_pending["sources"]["stay"], "screen:live_board")

    def test_campaign_diagnostics_uses_real_mcp_and_30_day_basis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            snapshot = store.dashboard()
            today = date.today()
            snapshot["accounts"][0]["data"] = [
                {
                    "date": (today - timedelta(days=offset)).isoformat(),
                    "spend": 100.0,
                    "gmv": 180.0,
                    "orders": 2.0,
                }
                for offset in range(5)
            ]
            store.snapshot = snapshot
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            record = {
                "stat_cost": 10000000,
                "total_order_settle_amount_for_roi2_1h": 18000000,
                "total_order_settle_count_for_roi2_1h": 2,
                "total_prepay_and_pay_settle_roi2_1h": 1.8,
                "online_count": 35,
                "live_click_product_count_alias": 250,
                "total_live_watch_cnt": 3000,
            }
            payload = {
                "data": {
                    "room": {
                        "AllEcomFlowSource": {"live_pc_qian_chuan": 60, "homepage_hot": 40}
                    },
                    "users": {
                        "gender": [{"gender_type": "2", "value": 80}],
                        "age": [{"age_type": "25-34", "value": 70}],
                        "city": [{"city_name": "上海", "value": 50}],
                    },
                }
            }
            response = {
                "tool": server.QianchuanMCPClient.LIVE_REPORT_TOOL,
                "room": record,
                "payload": payload,
                "arguments": {},
            }
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(client, "fetch_live_room", return_value=response):
                result = store.campaign_diagnostics("fashion")
            self.assertTrue(result["ok"])
            self.assertEqual(result["source"], "qianchuan_mcp_realtime")
            self.assertEqual(result["metrics"]["spend"], 100.0)
            self.assertEqual(result["metrics"]["gmv"], 180.0)
            self.assertEqual(result["metrics"]["online"], 35)
            self.assertEqual(result["flows"]["live_pc_qian_chuan"], 60)
            self.assertEqual(result["users"]["gender"][0]["gender_type"], "2")
            self.assertEqual(result["history"]["activeDays"], 5)
            self.assertEqual(result["history"]["averages"]["spend"], 100.0)
            self.assertEqual(result["targets"], {"cost": 300.0, "productPrice": 168.0, "roi": 0.56})

    def test_campaign_diagnostics_uses_labelled_screen_fallback_only_when_mcp_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "ok",
                    "live": True,
                    "syncedAt": server.now_iso(),
                    "heartbeatAt": server.now_iso(),
                    "room": {
                        "id": "room-1",
                        "awemeId": "7637818476896437305",
                        "awemeName": "赵镭图解小数基本功",
                    },
                    "metrics": {
                        "spend": 100.0,
                        "gmv": 180.0,
                        "orders": 2,
                        "roi": 1.8,
                        "orderCost": 50.0,
                        "online": 20,
                        "watchCount": 500,
                        "productClicks": 30,
                    },
                    "flows": [
                        {"key": "live_pc_qian_chuan", "value": 60},
                        {"key": "homepage_hot", "value": 40},
                    ],
                    "flowBreakdown": {
                        "source": "qianchuan_board_network",
                        "items": [
                            {
                                "key": "live_pc_qian_chuan",
                                "label": "千川PC",
                                "trafficShare": 60,
                                "gmvShare": 55,
                                "gpm": 1800,
                            },
                            {
                                "key": "homepage_hot",
                                "label": "直播推荐",
                                "trafficShare": 40,
                                "gmvShare": 45,
                                "gpm": 1500,
                            },
                        ],
                    },
                },
            )
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(
                     client,
                     "fetch_live_room",
                     side_effect=server.QianchuanMCPError("MCP empty"),
                 ):
                result = store.campaign_diagnostics("fashion")

            self.assertTrue(result["ok"])
            self.assertTrue(result["fallbackFromMCP"])
            self.assertFalse(result["mcpAvailable"])
            self.assertEqual(result["source"], "live_screen_fallback")
            self.assertEqual(
                result["sourceLabel"],
                "千川大屏直抓（MCP与百应暂不可用）",
            )
            self.assertEqual(result["metrics"]["gmv"], 180.0)
            self.assertEqual(result["flows"]["live_pc_qian_chuan"], 60)
            self.assertEqual(result["flowDetails"][0]["gmvShare"], 55)
            self.assertEqual(result["flowDetails"][0]["gpm"], 1800)

    def test_campaign_diagnostics_keeps_mcp_values_when_screen_differs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "ok",
                    "live": True,
                    "syncedAt": server.now_iso(),
                    "heartbeatAt": server.now_iso(),
                    "room": {"id": "room-1", "awemeId": "7637818476896437305"},
                    "metrics": {
                        "spend": 999.0,
                        "gmv": 888.0,
                        "orders": 9,
                        "roi": 0.89,
                    },
                },
            )
            response = {
                "tool": server.QianchuanMCPClient.LIVE_REPORT_TOOL,
                "room": {
                    "room_id": "room-1",
                    "stat_cost": 10000000,
                    "total_pay_order_gmv_for_roi2": 18000000,
                    "total_pay_order_count_for_roi2": 2,
                    "total_prepay_and_pay_order_roi2": 1.8,
                    "online_count": 35,
                },
                "payload": {},
                "arguments": {},
            }
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(client, "fetch_live_room", return_value=response):
                result = store.campaign_diagnostics("fashion")

            self.assertTrue(result["mcpAvailable"])
            self.assertFalse(result["fallbackFromMCP"])
            self.assertEqual(result["source"], "qianchuan_mcp_realtime")
            self.assertEqual(result["metrics"]["spend"], 100.0)
            self.assertEqual(result["metrics"]["gmv"], 180.0)
            self.assertEqual(result["metrics"]["orders"], 2)
            self.assertEqual(result["metrics"]["gmvScope"], "mcp_reported")

    def test_buyin_live_status_keeps_login_failure_separate_from_not_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            server.atomic_write_json(
                store.buyin_live_path,
                {
                    "status": "login_required",
                    "live": False,
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "metrics": {},
                    "channels": None,
                    "extras": [],
                    "error": "巨量百应登录已过期",
                },
            )
            status = store.buyin_live_status()
            self.assertFalse(status["available"])
            self.assertFalse(status["stale"])
            self.assertEqual(status["status"], "login_required")
            self.assertFalse(status["live"])

    def test_buyin_history_is_not_available_during_confirmed_not_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            server.atomic_write_json(
                store.buyin_live_path,
                {
                    "status": "ok",
                    "live": True,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "pageUrl": (
                        "https://compass.jinritemai.com/screen/live/talent"
                        "?live_room_id=7704532779547085622"
                    ),
                    "metrics": {"online": 10},
                    "channels": {"items": [{"key": "搜索", "trafficShare": 10}]},
                    "extras": [],
                },
            )
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "not_live",
                    "live": False,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "room": {},
                    "metrics": {},
                },
            )
            status = store.buyin_live_status()
            self.assertFalse(status["available"])
            self.assertTrue(status["confirmedNotLive"])
            self.assertFalse(status["currentRoomVerified"])

    def test_review_sessions_merge_local_recording_with_live_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            recordings_root = Path(temp_dir) / "recordings"
            session_dir = recordings_root / "2026-11-06_room-1_120000"
            (session_dir / "segments").mkdir(parents=True)
            (session_dir / "index.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
            (session_dir / "segments" / "part_000001.ts").write_bytes(b"video")
            server.recording_store.write_manifest(
                session_dir,
                {
                    "id": session_dir.name,
                    "accountId": "fashion",
                    "roomId": "room-1",
                    "awemeName": "测试直播号",
                    "date": "2026-11-06",
                    "startedAt": "2026-11-06T12:00:00+08:00",
                    "endedAt": "2026-11-06T12:10:00+08:00",
                    "status": "completed",
                },
            )
            start_ms = int(
                datetime.fromisoformat("2026-11-06T12:00:00+08:00").timestamp()
                * 1000
            )
            server.atomic_write_json(
                store.live_history_path,
                {
                    "version": 1,
                    "days": {
                        "2026-11-06": {
                            "room-1": [
                                {
                                    "t": start_ms,
                                    "spend": 0,
                                    "gmv": 0,
                                    "orders": 0,
                                    "watch": 0,
                                    "online": 20,
                                },
                                {
                                    "t": start_ms + 5 * 60 * 1000,
                                    "spend": 100,
                                    "gmv": 180,
                                    "orders": 2,
                                    "watch": 300,
                                    "online": 24,
                                },
                            ]
                        }
                    },
                },
            )
            server.atomic_write_json(
                store.buyin_audience_history_path,
                {
                    "version": 1,
                    "items": [
                        {
                            "t": start_ms + 60 * 1000,
                            "capturedAt": "2026-11-06T12:01:00+08:00",
                            "roomId": "room-1",
                            "profiles": {
                                "realtimeViewer": {
                                    "available": True,
                                    "gender": {"top": "女性", "distribution": []},
                                    "age": {"top": "31-35岁", "distribution": []},
                                    "region": {"top": "四川", "distribution": []},
                                    "summary": "女性居多",
                                    "source": "buyin_compass_live_screen_dom",
                                },
                                "recentBuyer": {
                                    "available": True,
                                    "gender": {"top": "女性", "distribution": []},
                                    "age": {"top": "25-30岁", "distribution": []},
                                    "region": {"top": "广东", "distribution": []},
                                    "summary": "女性居多",
                                    "source": "buyin_compass_live_screen_dom",
                                },
                            },
                        }
                    ],
                },
            )
            with patch.object(server, "RECORDINGS_DIR", recordings_root), \
                 patch.object(server, "REVIEW_ARCHIVE_DIR", Path(temp_dir) / "archive"):
                payload = store.review_sessions("fashion")

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["sessionCount"], 1)
            session = payload["sessions"][0]
            self.assertEqual(session["metrics"]["gmv"], 180)
            self.assertEqual(session["videoType"], "daily_hls")
            self.assertIn("/api/review/daily-playlist?", session["videoUrl"])
            self.assertIn("千川直播大屏", " ".join(session["dataSources"]))
            self.assertTrue(session["analysisSteps"])
            self.assertIn("asr", payload)
            self.assertEqual(payload["selectedDate"], "2026-11-06")
            self.assertEqual(payload["availableDates"], ["2026-11-06"])
            self.assertEqual(
                session["series"][0]["viewerPersona"]["region"],
                "四川",
            )
            self.assertEqual(
                session["series"][0]["buyerPersona"]["age"],
                "25-30岁",
            )
            self.assertGreaterEqual(payload["audienceHistory"]["matchedPoints"], 1)
            self.assertTrue(session["mcpTimeSeriesAttempted"])
            self.assertFalse(session["mcpTimeSeriesAvailable"])
            self.assertEqual(session["mcpTimeSeriesStatus"], "unsupported")
            self.assertIn("空 data", session["mcpTimeSeriesError"])
            self.assertEqual(payload["mcpTimeSeries"]["status"], "unsupported")
            self.assertIn("千川直播大屏", session["timeBucketSourceLabel"])

    def test_script_analysis_uses_archived_transcript_after_raw_video_delete(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = server.DashboardStore(root / "snapshot.json")
            recordings_root = root / "recordings"
            current_directory = recordings_root / "2026-11-08_room-1_190000"
            server.recording_store.write_manifest(
                current_directory,
                {
                    "id": current_directory.name,
                    "accountId": "fashion",
                    "roomId": "room-1",
                    "date": "2026-11-08",
                    "startedAt": "2026-11-08T19:00:00+08:00",
                    "status": "recording",
                },
            )

            archive_root = root / "archive"
            archived_directory = (
                archive_root / "sessions" / "2026-11-08_room-1_123419"
            )
            server.recording_store.write_manifest(
                archived_directory,
                {
                    "id": archived_directory.name,
                    "accountId": "fashion",
                    "roomId": "room-1",
                    "date": "2026-11-08",
                    "startedAt": "2026-11-08T12:34:19+08:00",
                    "status": "recording",
                },
            )
            server.atomic_write_json(
                archived_directory / "asr" / "transcript.json",
                {
                    "model": "faster-whisper-large-v3",
                    "segments": [
                        {
                            "id": "line-1",
                            "segmentId": "part_000001",
                            "text": "这是历史归档中的测试话术",
                            "startedAt": "2026-11-08T12:34:20+08:00",
                            "endedAt": "2026-11-08T12:34:28+08:00",
                        }
                    ],
                    "processedParts": ["part_000001"],
                },
            )
            start_ms = int(
                datetime.fromisoformat(
                    "2026-11-08T12:34:19+08:00"
                ).timestamp()
                * 1000
            )
            server.atomic_write_json(
                archived_directory / "asr" / "metrics.json",
                {
                    "samples": [
                        {
                            "t": start_ms,
                            "spend": 10,
                            "gmv": 0,
                            "orders": 0,
                            "online": 20,
                        },
                        {
                            "t": start_ms + 60_000,
                            "spend": 10,
                            "gmv": 168,
                            "orders": 1,
                            "online": 22,
                        },
                    ]
                },
            )
            server.atomic_write_json(
                store.live_history_path,
                {"version": 1, "days": {"2026-11-08": {"room-1": []}}},
            )

            with patch.object(server, "RECORDINGS_DIR", recordings_root), \
                 patch.object(server, "REVIEW_ARCHIVE_DIR", archive_root):
                payload = store.script_analysis("fashion")
                selected = store.script_analysis(
                    "fashion",
                    "2026-11-08",
                    archived_directory.name,
                )

            self.assertTrue(payload["available"])
            self.assertEqual(payload["selectedSessionId"], archived_directory.name)
            self.assertEqual(payload["sessionSource"], "archive")
            self.assertEqual(payload["session"]["status"], "archived_analysis")
            self.assertGreaterEqual(len(payload["phrases"]), 1)
            self.assertEqual(len(payload["availableDates"]), 1)
            self.assertTrue(
                next(
                    item
                    for item in payload["availableSessions"]
                    if item["id"] == archived_directory.name
                )["hasTranscript"]
            )
            self.assertEqual(selected["selectedSessionId"], archived_directory.name)
            self.assertIn("永久复盘归档", " ".join(
                [payload["summary"], payload["source"]]
            ))

    def test_review_sessions_loads_only_selected_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            recordings_root = Path(temp_dir) / "recordings"
            for day, room_id in (
                ("2026-11-05", "room-1"),
                ("2026-11-06", "room-2"),
            ):
                session_dir = recordings_root / f"{day}_{room_id}_120000"
                (session_dir / "segments").mkdir(parents=True)
                (session_dir / "index.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
                (session_dir / "segments" / "part_000001.ts").write_bytes(b"video")
                server.recording_store.write_manifest(
                    session_dir,
                    {
                        "id": session_dir.name,
                        "accountId": "fashion",
                        "roomId": room_id,
                        "date": day,
                        "startedAt": f"{day}T12:00:00+08:00",
                        "endedAt": f"{day}T12:05:00+08:00",
                        "status": "completed",
                    },
                )
            with patch.object(server, "RECORDINGS_DIR", recordings_root), \
                 patch.object(server, "REVIEW_ARCHIVE_DIR", Path(temp_dir) / "archive"):
                payload = store.review_sessions("fashion", "2026-11-05")

            self.assertEqual(
                payload["availableDates"],
                ["2026-11-05", "2026-11-06"],
            )
            self.assertEqual(payload["selectedDate"], "2026-11-05")
            self.assertEqual(payload["sessionCount"], 1)
            self.assertEqual(payload["sessions"][0]["date"], "2026-11-05")

    def test_campaign_diagnostics_prefers_buyin_over_qianchuan_when_mcp_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            server.atomic_write_json(
                store.buyin_live_path,
                {
                    "status": "ok",
                    "live": True,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "room": {
                        "id": "buyin-room-1",
                        "awemeName": "赵镭图解小数基本功",
                    },
                    "metrics": {
                        "spend": 120.0,
                        "gmv": 240.0,
                        "orders": 2,
                        "roi": 2.0,
                        "online": 20,
                    },
                    "gmvScope": "net",
                    "channels": {
                        "source": "buyin_live_board_network",
                        "sourceLabel": "巨量百应直播中控台 · 网络数据",
                        "items": [
                            {
                                "key": "live_pc_qian_chuan",
                                "label": "千川PC",
                                "trafficShare": 60,
                                "gmvShare": 55,
                                "gpm": 1800,
                            }
                        ],
                    },
                    "extras": [
                        {
                            "label": "商品点击率",
                            "value": 12.5,
                            "unit": "percent",
                            "source": "buyin_live_board_dom",
                        },
                        {
                            "label": "女性用户占比",
                            "value": 65,
                            "unit": "percent",
                            "source": "buyin_live_board_dom",
                        }
                    ],
                },
            )
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "ok",
                    "live": True,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "room": {"id": "qianchuan-room-1"},
                    "metrics": {
                        "spend": 999.0,
                        "gmv": 888.0,
                        "orders": 9,
                        "roi": 0.89,
                    },
                },
            )
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(
                     client,
                     "fetch_live_room",
                     side_effect=server.QianchuanMCPError("MCP empty"),
                 ):
                result = store.campaign_diagnostics("fashion")

            self.assertTrue(result["ok"])
            self.assertTrue(result["buyinAvailable"])
            self.assertTrue(result["buyinUsed"])
            self.assertFalse(result["qianchuanScreenUsed"])
            self.assertEqual(result["source"], "buyin_live_screen_fallback")
            self.assertEqual(result["metrics"]["spend"], 120.0)
            self.assertEqual(result["metrics"]["gmv"], 240.0)
            self.assertEqual(result["flowDetails"][0]["gpm"], 1800)
            self.assertEqual(result["flowValueKind"], "buyin_reported")
            self.assertEqual(
                result["fieldSources"]["spend"],
                "buyin_live_screen",
            )
            self.assertEqual(result["users"]["gender"][0]["gender_type"], "2")
            self.assertEqual(result["fieldSources"]["users"], "buyin_live_screen")

    def test_campaign_diagnostics_uses_buyin_only_to_fill_mcp_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            server.atomic_write_json(
                store.buyin_live_path,
                {
                    "status": "ok",
                    "live": True,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "metrics": {
                        "spend": 999.0,
                        "gmv": 888.0,
                        "orders": 9,
                    },
                    "gmvScope": "net",
                    "channels": {
                        "source": "buyin_compass_live_screen_dom",
                        "items": [
                            {
                                "key": "homepage_hot",
                                "label": "直播推荐",
                                "trafficShare": 75,
                                "gmvShare": 70,
                                "gpm": 1500,
                            }
                        ]
                    },
                    "extras": [
                        {
                            "label": "商品点击率",
                            "value": 12.5,
                            "unit": "percent",
                            "source": "buyin_live_board_dom",
                        }
                    ],
                },
            )
            response = {
                "tool": server.QianchuanMCPClient.LIVE_REPORT_TOOL,
                "room": {
                    "room_id": "room-1",
                    "stat_cost": 10000000,
                    "total_order_settle_amount_for_roi2_1h": 18000000,
                    "total_order_settle_count_for_roi2_1h": 2,
                    "total_prepay_and_pay_settle_roi2_1h": 1.8,
                },
                "payload": {},
                "arguments": {},
            }
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(client, "fetch_live_room", return_value=response):
                result = store.campaign_diagnostics("fashion")

            self.assertTrue(result["mcpAvailable"])
            self.assertTrue(result["buyinAvailable"])
            self.assertTrue(result["buyinSupplemented"])
            self.assertFalse(result["buyinUsed"])
            self.assertEqual(result["source"], "qianchuan_mcp_realtime")
            self.assertEqual(result["metrics"]["spend"], 100.0)
            self.assertEqual(result["metrics"]["gmv"], 180.0)
            self.assertEqual(result["fieldSources"]["flows"], "buyin_live_screen")
            self.assertEqual(result["flowValueKind"], "native")
            self.assertIn("flows", result["mcpMissingFields"])
            self.assertEqual(len(result["buyin"]["extras"]), 1)

    def test_campaign_diagnostics_does_not_treat_buyin_gross_as_net(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            server.atomic_write_json(
                store.buyin_live_path,
                {
                    "status": "ok",
                    "live": True,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "gmvScope": "buyin_reported",
                    "metrics": {
                        "spend": 120.0,
                        "gmv": 500.0,
                        "orders": 3,
                    },
                    "channels": None,
                    "extras": [],
                },
            )
            server.atomic_write_json(
                store.live_screen_path,
                {
                    "status": "ok",
                    "live": True,
                    "heartbeatAt": server.now_iso(),
                    "syncedAt": server.now_iso(),
                    "room": {"id": "qianchuan-room-1"},
                    "metrics": {
                        "spend": 100.0,
                        "gmv": 180.0,
                        "orders": 2,
                        "roi": 1.8,
                    },
                },
            )
            with patch.object(store, "_get_mcp_client", return_value=client), \
                 patch.object(
                     client,
                     "fetch_live_room",
                     side_effect=server.QianchuanMCPError("MCP empty"),
                 ):
                result = store.campaign_diagnostics("fashion")

            self.assertTrue(result["buyinAvailable"])
            self.assertFalse(result["buyinUsed"])
            self.assertTrue(result["qianchuanScreenUsed"])
            self.assertEqual(result["metrics"]["gmv"], 180.0)
            self.assertEqual(
                result["fieldSources"]["gmv"],
                "qianchuan_live_screen",
            )

    def test_discover_live_room_returns_precise_room_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            room = {
                "room_id": 7699337106561846035,
                "room_status": "LIVING",
                "aweme_id": 7637818476896437305,
                "stat_cost": 100000,
                "total_order_settle_amount_for_roi2_1h": 250000,
                "total_order_settle_count_for_roi2_1h": 3,
                "total_prepay_and_pay_settle_roi2_1h": 2.5,
                "live_pay_order_gmv_alias": 250000,
                "live_pay_order_count_alias": 3,
                "live_pay_order_gmv_roi": 2.5,
                "total_live_watch_cnt": 1200,
                "live_watch_one_minute_count": 480,
                "live_click_product_count_alias": 75,
                "total_live_comment_cnt": 30,
                "total_live_follow_cnt": 12,
                "room_delivery": 2,
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
            self.assertEqual(payload["officialLive"]["status"], "ok")
            self.assertEqual(payload["officialLive"]["metrics"]["spend"], 1.0)
            self.assertEqual(payload["officialLive"]["metrics"]["gmv"], 2.5)
            self.assertEqual(payload["officialLive"]["metrics"]["orders"], 3)
            self.assertEqual(payload["officialLive"]["metrics"]["watchCount"], 1200)
            self.assertIn("online", payload["officialLive"]["missingMetrics"])
            self.assertIn("gpm", payload["officialLive"]["missingMetrics"])

    def test_discover_live_room_checks_every_configured_aweme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            config = json.loads(json.dumps(server.DEFAULT_CONFIG))
            aweme_ids = [
                "7637818476896437305",
                "2904261216450640",
                "7665361622538945585",
                "7534976849169040442",
            ]
            config["accounts"][0]["awemeIds"] = aweme_ids
            config["accounts"][0]["awemeAccounts"] = [
                {"id": "7637818476896437305", "name": "赵镭图解小数基本功"},
                {"id": "2904261216450640", "name": "赵镭精讲小数基本功"},
                {"id": "7665361622538945585", "name": "赵镭拆解小数基本功"},
                {"id": "7534976849169040442", "name": "赵镭通解小数基本功"},
            ]

            def fetch_rooms(_advertiser_id: str, aweme_id: str, _date: str) -> list[dict]:
                if aweme_id != "7534976849169040442":
                    return []
                return [
                    {
                        "room_id": 7701192872432700202,
                        "room_status": "LIVING",
                        "aweme_id": aweme_id,
                    }
                ]

            with patch.dict(
                "os.environ", {"QIANCHUAN_ACCESS_TOKEN": "test-token"}, clear=True
            ), patch.object(
                server, "load_config", return_value=config
            ), patch.object(
                server.QianchuanClient,
                "fetch_live_rooms",
                side_effect=fetch_rooms,
            ) as fetch:
                payload = store.discover_live_room("fashion")

            self.assertEqual(
                [call.args[1] for call in fetch.call_args_list],
                aweme_ids,
            )
            self.assertEqual(payload["status"], "live")
            self.assertEqual(payload["roomId"], "7701192872432700202")
            self.assertEqual(payload["awemeName"], "赵镭通解小数基本功")
            self.assertEqual(
                [item["status"] for item in payload["checkedAccounts"]],
                ["not_live", "not_live", "not_live", "live"],
            )

    def test_discover_live_room_reports_not_live_only_after_all_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            config = json.loads(json.dumps(server.DEFAULT_CONFIG))
            aweme_ids = [
                "7637818476896437305",
                "2904261216450640",
                "7665361622538945585",
                "7534976849169040442",
            ]
            config["accounts"][0]["awemeIds"] = aweme_ids
            with patch.dict(
                "os.environ", {"QIANCHUAN_ACCESS_TOKEN": "test-token"}, clear=True
            ), patch.object(
                server, "load_config", return_value=config
            ), patch.object(
                server.QianchuanClient,
                "fetch_live_rooms",
                return_value=[],
            ) as fetch:
                payload = store.discover_live_room("fashion")

            self.assertEqual(fetch.call_count, len(aweme_ids))
            self.assertFalse(payload["live"])
            self.assertEqual(payload["status"], "not_live")
            self.assertEqual(payload["statusLabel"], "未开播")
            self.assertTrue(payload["discoveryComplete"])
            self.assertEqual(len(payload["checkedAccounts"]), len(aweme_ids))

    def test_request_live_screen_refresh_waits_for_exact_capture_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.DashboardStore(Path(temp_dir) / "snapshot.json")
            release = threading.Event()

            def publish_capture() -> None:
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    request = server.load_json(store.live_refresh_request_path, {})
                    request_id = str(request.get("requestId") or "")
                    if request_id:
                        server.atomic_write_json(
                            store.live_screen_path,
                            {
                                "status": "ok",
                                "live": True,
                                "syncedAt": server.now_iso(),
                                "heartbeatAt": server.now_iso(),
                                "captureRequestId": request_id,
                                "captureRequestStatus": "ok",
                                "metrics": {"spend": 88.8},
                            },
                        )
                        release.set()
                        return
                    time.sleep(0.02)

            worker = threading.Thread(target=publish_capture, daemon=True)
            worker.start()
            with patch.object(
                store,
                "live_snapshot",
                return_value={"live": True, "metrics": {"spend": 88.8}},
            ) as live_snapshot:
                result = store.request_live_screen_refresh("fashion", timeout_seconds=3)
            worker.join(timeout=1)

            self.assertTrue(release.is_set())
            self.assertTrue(result["ok"])
            self.assertTrue(result["completed"])
            self.assertEqual(result["captureStatus"], "ok")
            self.assertEqual(result["live"]["metrics"]["spend"], 88.8)
            live_snapshot.assert_called_once_with("fashion", force=True)


class HandlerTests(unittest.TestCase):
    def test_recording_endpoint_supports_byte_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            recording = root / "recordings" / "session" / "session.mp4"
            recording.parent.mkdir(parents=True)
            recording.write_bytes(bytes(range(256)) * 8)
            store = server.DashboardStore(root / "snapshot.json")
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store, root))
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                port = httpd.server_address[1]
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/recordings/session/session.mp4",
                    headers={"Range": "bytes=100-199"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    body = response.read()
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.headers["Content-Range"], "bytes 100-199/2048")
                    self.assertEqual(response.headers["Accept-Ranges"], "bytes")
                    self.assertEqual(len(body), 100)
            finally:
                httpd.shutdown()
                thread.join(timeout=2)
                httpd.server_close()

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
            self.assertIn("buyinLiveCapture", health)
            self.assertIn("liveRecorder", health)
            self.assertIn("localAsr", health)
            self.assertEqual(mcp_tools["tools"][0]["name"], "qianchuan_report_live_get_v1")
            self.assertFalse(live["live"])
            self.assertEqual(synced["syncStatus"], "degraded")
            self.assertEqual(synced["revision"], dashboard["revision"] + 1)

    def test_live_endpoint_returns_screen_data_when_mcp_returns_400(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "partial",
                    "source": "puppeteer-core",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "spend": 2802.41,
                        "gmv": 1008,
                        "orders": 6,
                        "orderCost": 467.07,
                        "roi": 0.36,
                        "watchCount": 735,
                        "productClicks": 184,
                        "gpm": 1161.29,
                        "online": 3,
                    },
                }),
                encoding="utf-8",
            )
            httpd = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server.make_handler(store, root),
            )
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})
            http_error = server.urllib.error.HTTPError(
                "https://example.test/mcp",
                400,
                "Bad Request",
                None,
                None,
            )
            try:
                port = httpd.server_address[1]
                started = time.monotonic()
                with patch.object(store, "_get_mcp_client", return_value=client), \
                     patch.object(client, "fetch_live_room", side_effect=http_error):
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/live?account=fashion",
                        timeout=5,
                    ) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                        status = response.status
                elapsed = time.monotonic() - started
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=2)

            self.assertEqual(status, 200)
            self.assertTrue(payload["live"])
            self.assertEqual(payload["metrics"]["spend"], 2802.41)
            self.assertEqual(payload["metrics"]["gmv"], 1008)
            self.assertEqual(payload["metrics"]["orders"], 6)
            self.assertEqual(payload["metrics"]["roi"], 0.36)
            self.assertLess(elapsed, 2.0)
            self.assertIn(
                payload["fiveDimension"]["mcpStatus"],
                {"pending", "error"},
            )

    def test_live_endpoint_returns_screen_immediately_when_mcp_hangs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            store.live_screen_path.write_text(
                json.dumps({
                    "heartbeatAt": server.now_iso(),
                    "intervalSeconds": 10,
                    "status": "partial",
                    "source": "puppeteer-core",
                    "room": {"id": "room-screen"},
                    "metrics": {
                        "spend": 3697.6,
                        "gmv": 1512,
                        "orders": 9,
                        "orderCost": 410.84,
                        "roi": 0.41,
                        "watchCount": 954,
                        "productClicks": 240,
                        "gpm": 1341.61,
                        "online": 0,
                    },
                }),
                encoding="utf-8",
            )
            httpd = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server.make_handler(store, root),
            )
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            release = threading.Event()
            client = server.QianchuanMCPClient({"url": "https://example.test/mcp"})

            def hanging_mcp(*_args, **_kwargs):
                release.wait(10)
                raise TimeoutError("simulated MCP timeout")

            try:
                port = httpd.server_address[1]
                with patch.object(store, "_get_mcp_client", return_value=client), \
                     patch.object(client, "fetch_live_room", side_effect=hanging_mcp):
                    started = time.monotonic()
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/live?account=fashion",
                        timeout=3,
                    ) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                        status = response.status
                    elapsed = time.monotonic() - started
            finally:
                release.set()
                deadline = time.monotonic() + 2
                while (
                    "five:fashion" in store.five_dimension_inflight
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=2)

            self.assertEqual(status, 200)
            self.assertLess(elapsed, 2.0)
            self.assertTrue(payload["live"])
            self.assertEqual(payload["metrics"]["spend"], 3697.6)
            self.assertEqual(payload["metrics"]["gmv"], 1512)
            self.assertEqual(payload["metrics"]["orders"], 9)
            self.assertTrue(payload["fiveDimension"]["mcpPending"])

    def test_quick_sync_endpoint_returns_within_three_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(store, root))
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            release = threading.Event()

            def slow_sync(realtime_only=True, force_materials=False):
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


class CampaignOperationForecastTests(unittest.TestCase):
    def test_json_object_extraction_ignores_trailing_prose(self) -> None:
        parsed = server._extract_json_object(
            '以下是结果：\n```json\n'
            '{"summary":"含 } 字符的 JSON",'
            '"forecast":{"roi":{"low":0.4,"base":0.5,"high":0.6}}}\n'
            "```\n补充说明：不要关注 {非 JSON 内容}"
        )
        self.assertEqual(parsed["summary"], "含 } 字符的 JSON")
        self.assertEqual(parsed["forecast"]["roi"]["base"], 0.5)

    @staticmethod
    def _snapshot() -> dict[str, object]:
        start = 1_794_500_000_000
        points = []
        for index in range(13):
            points.append(
                {
                    "t": start + index * 5 * 60_000,
                    "time": f"{(index * 5) // 60:02d}:{(index * 5) % 60:02d}",
                    "spend": 1000 + index * 280,
                    "gmv": 480 + index * 160,
                    "orders": 3 + index,
                    "watch": 100 + index * 12,
                    "online": 18 + index % 5,
                    "productClicks": 50 + index * 4,
                }
            )
        return {
            "metrics": {
                "spend": 4360,
                "gmv": 2400,
                "orders": 15,
                "roi": 0.55,
                "cost": 290.67,
                "watchCount": 244,
                "productClicks": 98,
                "online": 20,
            },
            "operationBasis": {
                "spend": 22000,
                "gmv": 11214,
                "orders": 66.6,
                "roi": 0.51,
                "aov": 168.3,
                "cost": 330.3,
                "currentSpend": 11818,
                "currentRoi": 0.48,
                "currentClicks": 716,
                "activeDays": 8,
            },
            "recentSeries": points,
            "anomalies": [
                {
                    "time": "14:30",
                    "metric": "5 分钟消耗增加 ¥300，成交不增",
                    "suggestion": "检查课程承接",
                }
            ],
            "flowDetails": [
                {"key": "live_recommend", "trafficShare": 35, "gmvShare": 20}
            ],
            "room": {"title": "小数基本功直播间"},
        }

    def test_model_is_primary_and_learning_is_auxiliary(self) -> None:
        captured: dict[str, object] = {}

        class FakeAI:
            def status(self):
                return {
                    "configured": True,
                    "productModel": "deepseek-flash",
                    "mode": "deepseek",
                }

            def model_id(self, purpose="product"):
                return "deepseek-flash" if purpose == "product" else "deepseek-v4-pro"

            def generate(self, messages, **kwargs):
                captured["messages"] = messages
                captured["kwargs"] = kwargs
                return {
                    "ok": True,
                    "model": "deepseek-flash",
                    "responseModel": "deepseek-flash",
                    "text": json.dumps(
                        {
                            "summary": "小步放量后流量可能增加，但订单成本仍需观察。",
                            "confidence": 72,
                            "forecast": {
                                "spend": {"low": 2600, "base": 2850, "high": 3100},
                                "gmv": {"low": 1350, "base": 1570, "high": 1800},
                                "orders": {"low": 7.5, "base": 9, "high": 10.5},
                                "roi": {"low": 0.5, "base": 0.55, "high": 0.6},
                                "cost": {"low": 280, "base": 317, "high": 350},
                                "clicks": {"low": 110, "base": 125, "high": 140},
                            },
                            "rationale": ["近 60 分钟转化稳定。"],
                            "risks": ["课程讲解切换可能降低承接。"],
                            "guardrails": ["订单成本超过 350 元停止继续加量。"],
                            "educationActions": ["先强化课程效果证明和价格锚点。"],
                            "knowledgeNotes": ["教培千川SOP.md：先稳定承接再加预算"],
                            "knowledgeConflicts": [],
                            "assumptions": ["未提供到课和退款数据。"],
                        },
                        ensure_ascii=False,
                    ),
                    "usage": {"total_tokens": 100},
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            learning = server.LearningDocumentStore(Path(temp_dir))
            learning.save(
                "教培千川SOP.md",
                (
                    "教培直播间投放逻辑：ROI 稳定且商品点击增长时小步加预算。"
                    "订单成本连续升高时先检查课程讲解承接。"
                ).encode("utf-8"),
                "text/markdown",
            )
            result = server.generate_campaign_operation_forecast(
                self._snapshot(),
                {
                    "id": "scale-boost",
                    "title": "放量追投",
                    "description": "小步提高预算",
                    "kind": "boost",
                    "direction": 1,
                },
                10,
                learning,
                FakeAI(),
            )

        self.assertEqual(result["source"], "deepseek_product_primary")
        self.assertEqual(result["model"], "deepseek-flash")
        self.assertEqual(result["confidence"], 72)
        self.assertTrue(result["knowledge"]["usedByModel"])
        self.assertEqual(result["horizonMinutes"], 60)
        self.assertAlmostEqual(result["forecast"]["roi"]["base"], 0.55)
        self.assertIn("订单成本超过 350 元", result["guardrails"][0])
        messages = captured["messages"]
        combined_prompt = json.dumps(messages, ensure_ascii=False)
        self.assertIn("知识库只是辅助校准", combined_prompt)
        self.assertIn("教培课程直播间", combined_prompt)
        self.assertIn("教培千川SOP.md", combined_prompt)
        self.assertEqual(captured["kwargs"]["purpose"], "product")

    def test_model_failure_returns_visible_local_fallback(self) -> None:
        class FailingAI:
            def status(self):
                return {
                    "configured": True,
                    "productModel": "deepseek-flash",
                    "mode": "deepseek",
                }

            def model_id(self, purpose="product"):
                return "deepseek-flash"

            def generate(self, messages, **kwargs):
                return {
                    "ok": False,
                    "model": "deepseek-flash",
                    "error": "timeout",
                }

        result = server.generate_campaign_operation_forecast(
            self._snapshot(),
            {
                "id": "reduce-all",
                "title": "一键控量",
                "description": "降低低效计划预算",
                "kind": "reduce",
                "direction": -1,
            },
            15,
            None,
            FailingAI(),
        )
        self.assertEqual(result["source"], "local_rule_fallback")
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["action"]["signedPercent"], -15)
        self.assertIn("timeout", result["aiFallback"]["error"])
        self.assertTrue(result["forecast"]["spend"]["base"] < result["baseline"]["spend"])

    def test_operation_forecast_http_endpoint_uses_product_model(self) -> None:
        class FakeAI:
            def status(self):
                return {
                    "configured": True,
                    "productModel": "deepseek-flash",
                    "mode": "deepseek",
                }

            def model_id(self, purpose="product"):
                return "deepseek-flash"

            def generate(self, messages, **kwargs):
                return {
                    "ok": True,
                    "model": "deepseek-flash",
                    "responseModel": "deepseek-flash",
                    "text": json.dumps(
                        {
                            "summary": "模型已完成推演。",
                            "confidence": 66,
                            "forecast": {
                                "spend": {"low": 2500, "base": 2800, "high": 3000},
                                "gmv": {"low": 1350, "base": 1550, "high": 1750},
                                "orders": {"low": 7, "base": 8, "high": 9},
                                "roi": {"low": 0.5, "base": 0.55, "high": 0.6},
                                "cost": {"low": 280, "base": 320, "high": 350},
                                "clicks": {"low": 110, "base": 125, "high": 140},
                            },
                        },
                        ensure_ascii=False,
                    ),
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            httpd = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server.make_handler(store, root, ai_client=FakeAI()),
            )
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                request = urllib.request.Request(
                    (
                        f"http://127.0.0.1:{httpd.server_address[1]}"
                        "/api/campaign/operation-forecast"
                    ),
                    data=json.dumps(
                        {
                            "snapshot": self._snapshot(),
                            "action": {
                                "id": "scale-boost",
                                "title": "放量追投",
                                "description": "小步提高预算",
                                "kind": "boost",
                                "direction": 1,
                            },
                            "percent": 10,
                        },
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=2)
        self.assertEqual(result["source"], "deepseek_product_primary")
        self.assertEqual(result["model"], "deepseek-flash")
        self.assertEqual(result["action"]["signedPercent"], 10)


class LearningDocumentTests(unittest.TestCase):
    def test_store_marks_text_documents_ready_and_removes_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.LearningDocumentStore(Path(temp_dir))
            document = store.save(
                "内部复盘.md",
                "投放规则：ROI 达到 1.2 后小步放量。".encode("utf-8"),
                "text/markdown",
            )

            self.assertTrue(document["learningReady"])
            self.assertEqual(document["status"], "ready")
            self.assertGreater(document["textCharacters"], 0)
            self.assertNotIn("storedFilename", document)

            payload = store.payload()
            self.assertEqual(len(payload["documents"]), 1)
            resolved, path = store.resolve(document["id"])
            self.assertEqual(resolved["id"], document["id"])
            self.assertTrue(path.is_file())

            store.delete(document["id"])
            self.assertEqual(store.payload()["documents"], [])
            self.assertFalse(path.exists())

    def test_learning_hits_include_filename_and_numbered_markdown_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.LearningDocumentStore(Path(temp_dir))
            store.save(
                "千川投放skill-v1.md",
                (
                    "# 千川投放 Skill\n\n"
                    "## 一、基本信息\n\n"
                    "ROI 目标参考线为 0.56。\n\n"
                    "## 二、稳定跑量阶段\n\n"
                    "订单成本高于 300 元时，优先检查素材和人群并小步控量。\n"
                ).encode("utf-8"),
                "text/markdown",
            )
            search = store.search("稳定跑量 订单成本 控量", limit=3)

            self.assertEqual(search["status"], "matched")
            self.assertTrue(search["hits"])
            hit = search["hits"][0]
            self.assertEqual(hit["documentName"], "千川投放skill-v1.md")
            self.assertIn("第二节 稳定跑量阶段", hit["sectionLabel"])
            self.assertEqual(
                hit["citationLabel"],
                "千川投放skill-v1.md 第二节 稳定跑量阶段",
            )

    def test_docx_is_indexed_retrieved_and_applied_to_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.LearningDocumentStore(Path(temp_dir))
            buffer = BytesIO()
            document_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>策略规则：ROI 低于 0.8 时暂停放量，'
                '先检查素材和人群；订单成本高于 300 元时优先控量。</w:t></w:r></w:p>'
                '</w:body></w:document>'
            )
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("word/document.xml", document_xml)
            document = store.save(
                "投放策略SOP.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            self.assertTrue(document["learningReady"])
            self.assertGreater(document["chunks"], 0)
            self.assertEqual(document["extractionMethod"], "docx_xml")
            search = store.search("ROI 低 暂停放量 订单成本", limit=3)
            self.assertEqual(search["status"], "matched")
            self.assertIn("投放策略SOP.docx", search["hits"][0]["documentName"])
            answer = store.answer("ROI 低时应该怎么处理？")
            self.assertEqual(answer["status"], "matched")
            self.assertIn("投放策略SOP.docx", answer["answer"])
            self.assertTrue(answer["citations"])
            self.assertEqual(answer["mode"], "local_grounded_extraction")

            payload = {
                "ok": True,
                "metrics": {"roi": 0.4, "cost": 420},
                "decision": {
                    "action": "一键控量",
                    "reason": "ROI 低于参考线且订单成本偏高。",
                    "guardrail": "ROI 未回升前不恢复预算。",
                    "confidence": 60,
                    "expected": ["降低预算"],
                },
                "anomalies": [],
                "missingReasons": [],
            }
            enriched = server.enrich_campaign_with_learning(payload, store)
            self.assertTrue(enriched["decision"]["learningApplied"])
            self.assertEqual(enriched["decision"]["confidence"], 60)
            self.assertEqual(enriched["decision"]["learningMode"], "guardrail")
            self.assertTrue(enriched["decision"]["learningAdvice"])
            self.assertIn("learningConflict", enriched["decision"])
            self.assertTrue(enriched["decision"]["learningCheckNote"])
            self.assertTrue(
                any(
                    "经验底线校验" in item or "过往习惯" in item
                    for item in enriched["decision"]["expected"]
                )
            )
            self.assertTrue(enriched["learning"]["hits"])

            unavailable = {
                "ok": False,
                "metrics": {},
                "decision": {"action": "等待数据", "confidence": 0},
                "anomalies": [],
                "missingReasons": ["MCP 不可用"],
            }
            guarded = server.enrich_campaign_with_learning(unavailable, store)
            self.assertNotIn("learningApplied", guarded["decision"])

    def test_delivery_profile_extracts_habits_logic_and_guardrails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = server.LearningDocumentStore(Path(temp_dir))
            store.save(
                "投放经验.md",
                (
                    "投放底线：ROI 低于 0.5 时绝对不能放量。"
                    "加预算习惯：ROI 达到 1.2 且消耗稳定时，给达标计划加 20% 预算。"
                    "操作逻辑：订单成本连续两小时高于 300 元时，先降出价 10% 再观察。"
                ).encode("utf-8"),
                "text/markdown",
            )

            profile = store.profile()
            self.assertEqual(profile["mode"], "local_heuristic")
            self.assertGreaterEqual(profile["stats"]["guardrailCount"], 1)
            self.assertGreaterEqual(profile["stats"]["habitCount"], 1)
            self.assertGreaterEqual(profile["stats"]["logicCount"], 1)
            guardrail = profile["guardrails"][0]
            self.assertIn("ROI", guardrail["rule"])
            self.assertEqual(guardrail["source"]["documentName"], "投放经验.md")

            matches = store.profile_matches("ROI 低于 0.5 能放量吗", limit=5)
            self.assertTrue(matches)
            self.assertEqual(matches[0]["category"], "guardrails")

    def test_pdf_text_stream_is_extracted(self) -> None:
        content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Length 90 >>\nstream\n"
            b"BT /F1 12 Tf 50 100 Td "
            b"(When ROI is below 0.8, pause budget and review creatives.) Tj ET\n"
            b"endstream\nendobj\n%%EOF"
        )
        text, method = server._extract_learning_text(content, ".pdf")
        self.assertEqual(method, "pdf_text_stream")
        self.assertIn("pause budget", text)

    def test_xlsx_and_pptx_xml_text_are_extracted(self) -> None:
        xlsx_buffer = BytesIO()
        with zipfile.ZipFile(xlsx_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "xl/sharedStrings.xml",
                "<sst><si><t>ROI</t></si><si><t>低于 0.8 暂停放量</t></si></sst>",
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                '<worksheet><sheetData><row r="1">'
                '<c r="A1" t="s"><v>0</v></c>'
                '<c r="B1" t="s"><v>1</v></c>'
                "</row></sheetData></worksheet>",
            )
        xlsx_text, xlsx_method = server._extract_learning_text(
            xlsx_buffer.getvalue(),
            ".xlsx",
        )
        self.assertEqual(xlsx_method, "xlsx_xml")
        self.assertIn("A1: ROI", xlsx_text)
        self.assertIn("暂停放量", xlsx_text)

        pptx_buffer = BytesIO()
        with zipfile.ZipFile(pptx_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "ppt/slides/slide1.xml",
                "<p:sld xmlns:p=\"urn:p\" xmlns:a=\"urn:a\">"
                "<a:p><a:r><a:t>晚场先控成本追投，订单成本超过 300 时停止。</a:t></a:r></a:p>"
                "</p:sld>",
            )
        pptx_text, pptx_method = server._extract_learning_text(
            pptx_buffer.getvalue(),
            ".pptx",
        )
        self.assertEqual(pptx_method, "pptx_xml")
        self.assertIn("控成本追投", pptx_text)

    def test_learning_document_http_upload_download_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("ok", encoding="utf-8")
            store = server.DashboardStore(root / "snapshot.json")
            httpd = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server.make_handler(store, root),
            )
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                port = httpd.server_address[1]
                base_url = f"http://127.0.0.1:{port}"
                filename = server.urllib.parse.quote("产品学习资料.md")
                content = (
                    "字段说明：成交金额使用用户实付成交口径。"
                    "策略规则：ROI 低于 0.8 且订单成本高时暂停放量，先检查素材和人群。"
                ).encode("utf-8")
                request = urllib.request.Request(
                    f"{base_url}/api/learning/documents",
                    data=content,
                    method="POST",
                    headers={
                        "Content-Type": "text/markdown",
                        "X-File-Name": filename,
                    },
                )
                with urllib.request.urlopen(request) as response:
                    uploaded = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 201)

                document = uploaded["document"]
                self.assertEqual(document["name"], "产品学习资料.md")
                with urllib.request.urlopen(f"{base_url}/api/learning/documents") as response:
                    listing = json.loads(response.read().decode("utf-8"))
                self.assertEqual(listing["documents"][0]["id"], document["id"])
                self.assertGreater(listing["index"]["chunkCount"], 0)
                reindex_request = urllib.request.Request(
                    f"{base_url}/api/learning/reindex",
                    data=b"",
                    method="POST",
                )
                with urllib.request.urlopen(reindex_request) as response:
                    reindexed = json.loads(response.read().decode("utf-8"))
                self.assertTrue(reindexed["ok"])
                self.assertGreater(reindexed["index"]["chunkCount"], 0)
                search_query = server.urllib.parse.quote("成交金额 用户实付")
                with urllib.request.urlopen(
                    f"{base_url}/api/learning/search?q={search_query}"
                ) as response:
                    search = json.loads(response.read().decode("utf-8"))
                self.assertEqual(search["status"], "matched")
                self.assertEqual(search["hits"][0]["documentId"], document["id"])
                chat_request = urllib.request.Request(
                    f"{base_url}/api/assistant/chat",
                    data=json.dumps(
                        {
                            "message": "ROI 低于 0.8 时怎么处理？",
                            "history": [
                                {"role": "user", "content": "我们在讨论订单成本。"},
                                {"role": "assistant", "content": "请继续。"},
                            ],
                        },
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(chat_request) as response:
                    chat = json.loads(response.read().decode("utf-8"))
                self.assertEqual(chat["status"], "matched")
                self.assertIn("产品学习资料.md", chat["answer"])
                self.assertTrue(chat["citations"])

                campaign_payload = {
                    "ok": True,
                    "metrics": {"roi": 0.4, "cost": 420},
                    "decision": {
                        "action": "一键控量",
                        "reason": "ROI 偏低且订单成本偏高。",
                        "guardrail": "ROI 回升前不恢复预算。",
                        "confidence": 55,
                        "expected": ["降低预算"],
                    },
                    "anomalies": [],
                    "missingReasons": [],
                }
                with patch.object(
                    store,
                    "campaign_diagnostics",
                    return_value=campaign_payload,
                ):
                    with urllib.request.urlopen(
                        f"{base_url}/api/campaign/diagnostics?account=fashion"
                    ) as response:
                        campaign = json.loads(response.read().decode("utf-8"))
                self.assertTrue(campaign["decision"]["learningApplied"])
                self.assertEqual(campaign["decision"]["confidence"], 55)
                self.assertEqual(campaign["decision"]["learningMode"], "guardrail")
                self.assertTrue(campaign["decision"]["learningCheckNote"])

                download_url = (
                    f"{base_url}/api/learning/documents/download?id={document['id']}"
                )
                with urllib.request.urlopen(download_url) as response:
                    downloaded = response.read()
                    disposition = response.headers.get("Content-Disposition", "")
                self.assertEqual(downloaded, content)
                self.assertIn("filename*=UTF-8''", disposition)

                delete_request = urllib.request.Request(
                    f"{base_url}/api/learning/documents?id={document['id']}",
                    method="DELETE",
                )
                with urllib.request.urlopen(delete_request) as response:
                    deleted = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, 200)
                self.assertTrue(deleted["ok"])
                with urllib.request.urlopen(f"{base_url}/api/learning/documents") as response:
                    listing = json.loads(response.read().decode("utf-8"))
                self.assertEqual(listing["documents"], [])

                invalid_request = urllib.request.Request(
                    f"{base_url}/api/learning/documents",
                    data=b"not supported",
                    method="POST",
                    headers={"X-File-Name": "payload.exe"},
                )
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(invalid_request)
                self.assertEqual(context.exception.code, 415)
            finally:
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
