"use strict";

const assert = require("node:assert/strict");
const {
  DEFAULT_CONFIG,
  LOGIN_URL,
  extractMetrics,
  findStreamUrl,
  isLegacyQianchuanUrl,
  parseMetricNumber,
  roomIdFromUrl,
  safePageUrl
} = require("./live-screen-agent");

for (const key of ["spend", "gmv", "orders", "orderCost", "roi"]) {
  assert.ok(DEFAULT_CONFIG.metrics[key]?.labels?.length, `${key} labels missing`);
}

assert.equal(
  LOGIN_URL,
  "https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1"
);
assert.equal(parseMetricNumber("1.2万"), 12000);
assert.equal(parseMetricNumber("¥ 1,234.56"), 1234.56);
assert.equal(parseMetricNumber("3.5K"), 3500);
assert.equal(parseMetricNumber("暂无数据"), null);
assert.equal(isLegacyQianchuanUrl("https://qianchuan.jinritemai.com/live"), true);
assert.equal(
  isLegacyQianchuanUrl("https://business.oceanengine.com/ebp/live"),
  false
);
assert.equal(
  safePageUrl(
    "https://business.oceanengine.com/ebp/live?ebpid=1855365007750474&uuid=test&live_room_id=7637818476896437305&token=secret"
  ),
  "https://business.oceanengine.com/ebp/live?ebpid=1855365007750474&uuid=test&live_room_id=7637818476896437305"
);
assert.equal(
  roomIdFromUrl(
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?ebpid=1855365007750474&roomId=7698576510591994665"
  ),
  "7698576510591994665"
);

const result = extractMetrics(
  {
    lines: [
      "累计观看人数",
      "1.28万",
      "商品点击次数 2,345",
      "峰值在线人数 386",
      "GPM",
      "¥ 912.35",
      "整体消耗 4,511.88",
      "整体成交金额 3,456.78",
      "整体成单数 21",
      "整体成交订单成本 ¥ 214.85",
      "整体ROI 0.77"
    ],
    fragments: [
      { text: "累计观看人数 1.28万" },
      { text: "商品点击次数 2,345" }
    ],
    selected: {}
  },
  {
    watchCount: { labels: ["累计观看人数"] },
    productClicks: { labels: ["商品点击次数"] },
    peakOnline: { labels: ["峰值在线人数"] },
    gpm: { labels: ["GPM"] },
    spend: { labels: ["整体消耗"] },
    gmv: { labels: ["整体成交金额"] },
    orders: { labels: ["整体成单数"] },
    orderCost: { labels: ["整体成交订单成本"] },
    roi: { labels: ["整体ROI"] }
  }
);

assert.deepEqual(result.metrics, {
  watchCount: 12800,
  productClicks: 2345,
  peakOnline: 386,
  gpm: 912.35,
  spend: 4511.88,
  gmv: 3456.78,
  orders: 21,
  orderCost: 214.85,
  roi: 0.77
});
assert.deepEqual(result.missing, []);

const ambiguousTradeResult = extractMetrics(
  {
    lines: [
      "整体成交订单成本 ¥214.85",
      "整体GPM(元) 912.35"
    ],
    fragments: [],
    selected: {}
  },
  {
    gmv: { labels: ["成交金额"], excludeLabels: ["GPM", "千次观看"] },
    orders: { labels: ["成交订单"], excludeLabels: ["成本", "率"] },
    orderCost: { labels: ["整体成交订单成本"] }
  }
);
assert.equal(ambiguousTradeResult.metrics.gmv, undefined);
assert.equal(ambiguousTradeResult.metrics.orders, undefined);
assert.equal(ambiguousTradeResult.metrics.orderCost, 214.85);

const ebpResult = extractMetrics(
  {
    lines: [
      "观看数 0.00",
      "点击次数 2,345",
      "峰值在线人数 386",
      "整体GPM(元) 912.35"
    ],
    fragments: [],
    selected: {}
  },
  {
    watchCount: { labels: ["观看数"] },
    productClicks: { labels: ["点击次数"] },
    peakOnline: { labels: ["峰值在线人数"] },
    gpm: { labels: ["整体GPM(元)", "GPM"] }
  }
);
assert.deepEqual(ebpResult.metrics, {
  watchCount: 0,
  productClicks: 2345,
  peakOnline: 386,
  gpm: 912.35
});

const boardResult = extractMetrics(
  {
    lines: [
      "直播间整体观看人数 1,145",
      "商品点击次数 233",
      "实时在线人数 6",
      "GPM(元) 991.15"
    ],
    fragments: [],
    selected: {}
  },
  {
    watchCount: { labels: ["直播间整体观看人数"] },
    productClicks: { labels: ["商品点击次数"] },
    gpm: { labels: ["GPM(元)"] },
    online: { labels: ["实时在线人数"] }
  }
);
assert.deepEqual(boardResult.metrics, {
  watchCount: 1145,
  productClicks: 233,
  gpm: 991.15,
  online: 6
});

const streamPayload = {
  data: {
    room: {
      room_stream_flv_pull_url: {
        Value: "https://pull-flv.example.douyincdn.com/live.flv?sign=x"
      }
    }
  }
};
assert.equal(
  findStreamUrl(streamPayload),
  "https://pull-flv.example.douyincdn.com/live.flv?sign=x"
);

console.log("live-screen-agent tests passed");
