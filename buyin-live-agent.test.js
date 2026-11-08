"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {
  CONTROL_URL,
  LOGIN_URL,
  enableBuyinPhoneLogin,
  ensureCompassFlowAnalysis,
  extractBuyinPayload,
  extractChannelsFromSnapshot,
  extractCompassChannels,
  extractAudienceProfiles,
  extractAudienceSummary,
  extractLiveScreenRoomId,
  extractMetricsFromSnapshot,
  compassScreenUrlForRoom,
  isCompassScreenUrl,
  isBuyinTargetPage,
  loginRequired,
  mergeConfig,
  persistAudienceHistory,
  parseMetricNumber
} = require("./buyin-live-agent");

assert.equal(
  LOGIN_URL,
  "https://buyin.jinritemai.com/mpa/account/login?log_out=1&type=24"
);
assert.equal(CONTROL_URL, "https://buyin.jinritemai.com/dashboard/live/control");
assert.equal(parseMetricNumber("¥1.2万").value, 12000);
assert.equal(parseMetricNumber("63.5%").unit, "percent");
assert.equal(mergeConfig({ intervalSeconds: 10 }, { intervalSeconds: 1 }).intervalSeconds, 5);
assert.equal(typeof enableBuyinPhoneLogin, "function");
assert.equal(typeof ensureCompassFlowAnalysis, "function");
assert.equal(
  isCompassScreenUrl(
    "https://compass.jinritemai.com/screen/live/talent?live_room_id=1"
  ),
  true
);
assert.equal(
  extractLiveScreenRoomId({
    status: "ok",
    live: true,
    room: { id: "7705197544334166826" }
  }),
  "7705197544334166826"
);
assert.equal(
  extractLiveScreenRoomId({
    status: "not_live",
    live: false,
    room: { id: "7705197544334166826" }
  }),
  ""
);
const syncedCompassUrl = compassScreenUrlForRoom(
  "https://compass.jinritemai.com/screen/live/talent?live_room_id=7704903843406039850&live_app_id=1128",
  "7705197544334166826"
);
assert.equal(
  new URL(syncedCompassUrl).searchParams.get("live_room_id"),
  "7705197544334166826"
);
assert.equal(
  compassScreenUrlForRoom(
    "https://compass.jinritemai.com/screen/live/talent?live_room_id=7705197544334166826",
    "7705197544334166826"
  ),
  ""
);

assert.equal(
  isBuyinTargetPage(
    { bodyText: "直播中控台 人群流量占比 成交金额占比" },
    "https://buyin.jinritemai.com/dashboard/live/control?roomId=1"
  ),
  true
);
assert.equal(
  isBuyinTargetPage(
    { bodyText: "选择角色" },
    "https://buyin.jinritemai.com/mpa/account/roles-select"
  ),
  false
);
assert.equal(
  loginRequired({
    url: "https://buyin.jinritemai.com/mpa/account/login?type=24",
    bodyText: "扫码登录 打开 抖音App 扫码登录或使用 抖音手机号登录"
  }),
  true
);

const payload = {
  data: {
    StatsData: {
      Rows: [
        {
          Dimensions: {
            combined_first_compass_entrance_code: {
              Value: "live_pc_qian_chuan",
              ValueStr: "千川PC"
            }
          },
          Metrics: {
            total_live_watch_cnt_for_roi2: { Value: 1000 },
            total_live_pay_amt_for_roi2: { Value: 2500 },
            gpm: { Value: 2500 }
          }
        },
        {
          Dimensions: {
            combined_first_compass_entrance_code: {
              Value: "homepage_hot",
              ValueStr: "直播推荐"
            }
          },
          Metrics: {
            total_live_watch_cnt_for_roi2: { Value: 3000 },
            total_live_pay_amt_for_roi2: { Value: 1500 },
            gpm: { Value: 500 }
          }
        }
      ]
    },
    stat_cost: 800,
    total_order_settle_amount_for_roi2_1h: 4000
  }
};
const extracted = extractBuyinPayload(payload);
assert.equal(extracted.metrics.spend, 800);
assert.equal(extracted.metrics.gmv, 4000);
assert.equal(extracted.metrics.gmvScope, "net");
const qianchuanChannel = extracted.channels.items.find(
  item => item.key === "live_pc_qian_chuan"
);
assert.equal(qianchuanChannel.trafficShare, 25);
assert.equal(qianchuanChannel.gmvShare, 62.5);
assert.equal(qianchuanChannel.gpm, 2500);

const domMetrics = extractMetricsFromSnapshot({
  lines: ["人群流量占比 62.5%", "整体消耗 ¥1,280", "成交金额 ¥3,600"],
  fragments: []
});
assert.equal(domMetrics.metrics.spend, 1280);
assert.equal(domMetrics.metrics.gmv, 3600);

const domChannels = extractChannelsFromSnapshot({
  tables: [[
    ["渠道", "人群流量占比", "成交金额占比", "渠道千次观看成交"],
    ["千川PC", "60%", "55%", "¥1,800"],
    ["直播推荐", "40%", "45%", "¥1,500"]
  ]]
});
assert.equal(domChannels.items[0].trafficShare, 60);
assert.equal(domChannels.items[0].gmvShare, 55);
assert.equal(domChannels.items[0].gpm, 1800);

const compassChannels = extractCompassChannels({
  lines: [
    "渠道名称",
    "流量占比",
    "成交金额占比",
    "渠道千次观看成交",
    "短视频引流",
    "33.93%",
    "58.68%",
    "¥2,938.27",
    "全部流量渠道",
    "渠道名称",
    "流量占比",
    "成交金额占比",
    "渠道千次观看成交",
    "头条西瓜",
    "6.91%",
    "3.45%",
    "¥848.48"
  ]
});
assert.equal(compassChannels.source, "buyin_compass_live_screen_dom");
assert.equal(compassChannels.items[0].trafficShare, 33.93);
assert.equal(compassChannels.items[0].gmvShare, 58.68);
assert.equal(compassChannels.items[0].gpm, 2938.27);

const structuredCompassChannels = extractCompassChannels({
  lines: [],
  tables: [[
    ["渠道名称", "流量占比", "成交金额占比", "渠道千次观看成交"],
    ["短视频引流", "34.15%", "56.29%", "¥3,005.96"],
    ["其他", "26.66%", "9.38%", "¥642.04"]
  ]]
});
assert.equal(structuredCompassChannels.items.length, 2);
assert.equal(structuredCompassChannels.items[0].trafficShare, 34.15);
assert.equal(structuredCompassChannels.items[0].gmvShare, 56.29);
assert.equal(structuredCompassChannels.items[0].gpm, 3005.96);
assert.equal(
  extractAudienceSummary({
    lines: ["实时看播用户画像", "女性居多31-35岁居多四川居多..."]
  }),
  "女性居多31-35岁居多四川居多..."
);
const audienceProfiles = extractAudienceProfiles({
  lines: [
    "近1分钟看播用户画像",
    "女性 68%",
    "男性 32%",
    "31-35岁 42%",
    "25-30岁 28%",
    "四川 21%",
    "广东 18%",
    "近5分钟购买用户画像",
    "在线人数过少，无法展示画像",
    "全场累计用户画像",
    "女性居多31-35岁居多四川居多"
  ]
});
assert.equal(audienceProfiles.realtimeViewer.available, true);
assert.equal(audienceProfiles.realtimeViewer.gender.top, "女性");
assert.equal(audienceProfiles.realtimeViewer.age.top, "31-35岁");
assert.equal(audienceProfiles.realtimeViewer.region.top, "四川");
assert.equal(audienceProfiles.recentBuyer.available, false);
assert.match(audienceProfiles.recentBuyer.unavailableReason, /人数过少/);
assert.equal(audienceProfiles.fullViewer.gender.top, "女性");
assert.equal(audienceProfiles.fullViewer.region.top, "四川");
const unavailableAudience = extractAudienceProfiles({
  lines: ["无法查看用户画像"]
});
assert.equal(unavailableAudience.realtimeViewer.available, false);
assert.equal(unavailableAudience.recentBuyer.available, false);
assert.match(unavailableAudience.fullBuyer.unavailableReason, /无法展示用户画像/);
const historyRoot = fs.mkdtempSync(path.join(os.tmpdir(), "buyin-audience-"));
const historyPath = path.join(historyRoot, "history.json");
const historyResult = {
  room: { id: "7705197544334166826" },
  audienceProfiles
};
assert.equal(
  persistAudienceHistory(historyResult, new Date("2026-11-07T09:00:00Z"), historyPath),
  true
);
assert.equal(
  persistAudienceHistory(historyResult, new Date("2026-11-07T09:00:20Z"), historyPath),
  false
);
assert.equal(
  persistAudienceHistory(historyResult, new Date("2026-11-07T09:05:00Z"), historyPath),
  true
);
const audienceHistory = JSON.parse(fs.readFileSync(historyPath, "utf8"));
assert.equal(audienceHistory.items.length, 2);
assert.equal(audienceHistory.items[0].roomId, "7705197544334166826");
fs.rmSync(historyRoot, { recursive: true, force: true });

const netDomMetrics = extractMetricsFromSnapshot({
  lines: ["净成交金额 ¥3,600", "整体消耗 ¥1,280"],
  fragments: []
});
assert.equal(netDomMetrics.metrics.gmv, 3600);
assert.equal(netDomMetrics.metrics.gmvScope, "net");

const grossOnly = extractBuyinPayload({
  data: {
    total_pay_order_gmv_for_roi2: 5000
  }
});
assert.equal(grossOnly.metrics.gmv, 5000);
assert.equal(grossOnly.metrics.gmvScope, "buyin_reported");

process.stdout.write("buyin-live-agent tests passed\n");
