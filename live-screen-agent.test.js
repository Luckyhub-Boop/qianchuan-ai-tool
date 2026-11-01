"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const {
  BROWSER_LAUNCH_ARGS,
  DEFAULT_CONFIG,
  LOGIN_URL,
  acquireAgentLock,
  buildLiveBoardUrl,
  buildLoginPageUrl,
  cleanupBrowserProfileState,
  extractFlows,
  extractMetrics,
  findStreamUrl,
  isConfiguredLiveScreenUrl,
  isLegacyQianchuanUrl,
  isLoginCompletePage,
  isLiveScreenPage,
  loginRequired,
  parseMetricNumber,
  releaseAgentLock,
  replaceRoomIdInUrl,
  roomIdFromUrl,
  safePageUrl
} = require("./live-screen-agent");

assert.ok(BROWSER_LAUNCH_ARGS.includes("--no-sandbox"));
assert.ok(BROWSER_LAUNCH_ARGS.includes("--disable-gpu"));
assert.ok(BROWSER_LAUNCH_ARGS.includes("--disable-gpu-sandbox"));
assert.equal(
  isConfiguredLiveScreenUrl("https://business.oceanengine.com/ebp/home"),
  false
);
assert.equal(
  isConfiguredLiveScreenUrl(
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?roomId=7698576510591994665"
  ),
  true
);
assert.equal(
  isConfiguredLiveScreenUrl(
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/list?ebpid=1855365007750474"
  ),
  true
);
assert.equal(
  isConfiguredLiveScreenUrl(
    "https://qianchuan.jinritemai.com/uni-prom?aavid=1744479430946824"
  ),
  false
);
assert.equal(
  isConfiguredLiveScreenUrl("https://qianchuan.jinritemai.com/board-next"),
  false
);
assert.equal(
  isConfiguredLiveScreenUrl(
    "https://qianchuan.jinritemai.com/board-next?live_room_id=7698576510591994665"
  ),
  true
);
assert.equal(
  isConfiguredLiveScreenUrl(
    "https://qianchuan.jinritemai.com/board-next"
  ),
  false
);
assert.equal(
  isLiveScreenPage({ bodyText: "首页 消耗 成交 账户管理" }, "https://business.oceanengine.com/ebp/home"),
  false
);
assert.equal(
  isLiveScreenPage(
    { bodyText: "累计观看 12,345" },
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail"
  ),
  false
);
assert.equal(
  isLiveScreenPage(
    { bodyText: "累计观看 12,345 商品点击 678" },
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail"
  ),
  true
);
assert.equal(
  isLoginCompletePage(
    { bodyText: "直播分析 消耗 成交" },
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/list?ebpid=1855365007750474"
  ),
  false
);
assert.equal(
  isLoginCompletePage(
    { bodyText: "" },
    "https://qianchuan.jinritemai.com/board-next?live_room_id=7698576510591994665"
  ),
  true
);
assert.equal(
  loginRequired({
    url: "https://business.oceanengine.com/check_login?from=https%3A%2F%2Fexample.test"
  }),
  true
);
assert.equal(
  isLoginCompletePage(
    { bodyText: "直播详情 整体消耗(元) 净成交金额(元)" },
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?roomId=7698576510591994665"
  ),
  true
);
assert.equal(
  isLiveScreenPage(
    { bodyText: "直播间详情 整体消耗 成交订单数 净成交ROI 直播间整体观看人数" },
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail"
  ),
  true
);

const lockDir = fs.mkdtempSync(path.join(os.tmpdir(), "qc-agent-lock-"));
const lockPath = path.join(lockDir, "agent.lock");
const firstLock = acquireAgentLock({ lockPath, mode: "test" });
assert.equal(firstLock.acquired, true);
const childCode = [
  `const agent=require(${JSON.stringify(path.resolve(__dirname, "live-screen-agent"))});`,
  `const result=agent.acquireAgentLock({lockPath:${JSON.stringify(lockPath)},mode:"child"});`,
  "console.log(JSON.stringify(result));",
  "if (result.acquired) agent.releaseAgentLock(lockPath);"
].join("");
const child = spawnSync(process.execPath, ["-e", childCode], { encoding: "utf8" });
assert.equal(child.status, 0, child.stderr);
assert.equal(JSON.parse(child.stdout.trim()).acquired, false);
releaseAgentLock(lockPath);
assert.equal(fs.existsSync(lockPath), false);

const staleLockPath = path.join(lockDir, "stale.lock");
fs.writeFileSync(
  staleLockPath,
  JSON.stringify({ pid: 2_000_000_000, mode: "agent" }),
  "utf8"
);
const staleReplacement = acquireAgentLock({ lockPath: staleLockPath, mode: "test" });
assert.equal(staleReplacement.acquired, true);
releaseAgentLock(staleLockPath);
assert.equal(fs.existsSync(staleLockPath), false);

const gracefulExitLockPath = path.join(lockDir, "graceful-exit.lock");
const gracefulExitCode = [
  `const agent=require(${JSON.stringify(path.resolve(__dirname, "live-screen-agent"))});`,
  `const lock=agent.acquireAgentLock({lockPath:${JSON.stringify(gracefulExitLockPath)},mode:"test"});`,
  "if (!lock.acquired) process.exit(2);",
  "setTimeout(() => process.emit('SIGTERM', 'SIGTERM'), 50);"
].join("");
const gracefulExit = spawnSync(process.execPath, ["-e", gracefulExitCode], {
  encoding: "utf8"
});
assert.equal(gracefulExit.status, 0, gracefulExit.stderr);
assert.equal(fs.existsSync(gracefulExitLockPath), false);

const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), "qc-profile-lock-"));
fs.writeFileSync(path.join(profileDir, "SingletonLock"), "stale");
fs.writeFileSync(path.join(profileDir, "DevToolsActivePort"), "9333");
fs.mkdirSync(path.join(profileDir, "Default"));
fs.writeFileSync(path.join(profileDir, "Default", "lockfile"), "stale");
fs.writeFileSync(path.join(profileDir, "keep.txt"), "keep");
cleanupBrowserProfileState(profileDir, { terminateOrphans: false });
assert.equal(fs.existsSync(path.join(profileDir, "SingletonLock")), false);
assert.equal(fs.existsSync(path.join(profileDir, "DevToolsActivePort")), false);
assert.equal(fs.existsSync(path.join(profileDir, "Default", "lockfile")), false);
assert.equal(fs.readFileSync(path.join(profileDir, "keep.txt"), "utf8"), "keep");
fs.rmSync(lockDir, { recursive: true, force: true });
fs.rmSync(profileDir, { recursive: true, force: true });

assert.equal(
  LOGIN_URL,
  "https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1"
);
const directBoard = buildLiveBoardUrl({
  roomId: "7698576510591994665",
  advertiserId: "1744479430946824",
  anchorId: "7637818476896437305"
});
assert.match(directBoard, /live_room_id=7698576510591994665/);
assert.match(directBoard, /aavid=1744479430946824/);
const directLogin = buildLoginPageUrl(directBoard);
assert.match(directLogin, /^https:\/\/business\.oceanengine\.com\/login\?/);
assert.match(directLogin, /ssoDomain=sso\.oceanengine\.com/);
assert.equal(parseMetricNumber("1.2万"), 12000);
assert.equal(parseMetricNumber("¥ 1,234.56"), 1234.56);
assert.equal(parseMetricNumber("3.5K"), 3500);
assert.equal(parseMetricNumber("暂无数据"), null);
assert.equal(isLegacyQianchuanUrl("https://qianchuan.jinritemai.com/live"), true);
assert.equal(isLegacyQianchuanUrl("https://qianchuan.jinritemai.com/board-next"), true);
assert.equal(
  isLegacyQianchuanUrl(
    "https://qianchuan.jinritemai.com/board-next?live_room_id=7698576510591994665"
  ),
  false
);
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
assert.equal(
  replaceRoomIdInUrl(
    "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?ebpid=1855365007750474&roomId=7698576510591994665&uuid=test",
    "7699999999999999999"
  ),
  "https://business.oceanengine.com/ebp/data-analysis/live-analysis/detail?ebpid=1855365007750474&roomId=7699999999999999999&uuid=test"
);

const result = extractMetrics(
  {
    lines: [
      "累计观看人数",
      "1.28万",
      "商品点击次数 2,345",
      "峰值在线人数 386",
      "GPM",
      "¥ 912.35"
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
    gpm: { labels: ["GPM"] }
  }
);

assert.deepEqual(result.metrics, {
  watchCount: 12800,
  productClicks: 2345,
  peakOnline: 386,
  gpm: 912.35
});
assert.deepEqual(result.missing, []);

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

const tradeResult = extractMetrics(
  {
    lines: [
      "整体消耗(元) 6,623.98",
      "净成交金额(元) 3,696.00",
      "成交订单数 26",
      "整体成交订单成本(元) 194.78",
      "净成交ROI 0.56",
      "直播间整体曝光次数 71,881",
      "直播间整体观看人数 1,803"
    ],
    fragments: [],
    selected: {}
  },
  {
    spend: { labels: ["整体消耗(元)", "消耗"] },
    gmv: { labels: ["净成交金额(元)", "成交金额"] },
    orders: { labels: ["成交订单数"] },
    orderCost: { labels: ["整体成交订单成本", "成交订单成本"] },
    roi: { labels: ["净成交ROI", "ROI"] },
    exposure: { labels: ["直播间整体曝光次数"] },
    watchCount: { labels: ["直播间整体观看人数"] }
  }
);
assert.deepEqual(tradeResult.metrics, {
  spend: 6623.98,
  gmv: 3696,
  orders: 26,
  orderCost: 194.78,
  roi: 0.56,
  exposure: 71881,
  watchCount: 1803
});

const currentLiveBoardResult = extractMetrics(
  {
    lines: [
      "整体消耗(元)",
      "2,901.00",
      "整体成交订单数",
      "15",
      "整体成交订单成本(元)",
      "194.78",
      "净成交ROI",
      "0.81",
      "直播间整体观看人数",
      "745"
    ],
    fragments: [],
    selected: {}
  },
  DEFAULT_CONFIG.metrics
);

const missingCountMetrics = extractMetrics(
  {
    lines: [
      "成交渠道构成 短视频及图文引流48.15% 其他24.07% 直播推荐9.26%",
      "直播间核心漏斗 直播间整体曝光次数 直播间观看次数 商品点击次数 成交订单数",
      "曝光观看率(次数) 2.91 %"
    ],
    fragments: [],
    selected: {}
  },
  DEFAULT_CONFIG.metrics
);
assert.equal(missingCountMetrics.metrics.productClicks, undefined);
assert.equal(missingCountMetrics.metrics.exposure, undefined);
assert.ok(missingCountMetrics.missing.includes("productClicks"));
assert.deepEqual(
  {
    spend: currentLiveBoardResult.metrics.spend,
    orders: currentLiveBoardResult.metrics.orders,
    orderCost: currentLiveBoardResult.metrics.orderCost,
    roi: currentLiveBoardResult.metrics.roi,
    watchCount: currentLiveBoardResult.metrics.watchCount
  },
  {
    spend: 2901,
    orders: 15,
    orderCost: 194.78,
    roi: 0.81,
    watchCount: 745
  }
);

const flowResult = extractFlows({
  lines: [
    "成交渠道构成 短视频及图文引流44% 搜索24% 直播推荐12% 其他12% 头条西瓜8%"
  ],
  fragments: []
});
assert.deepEqual(
  flowResult.items.map(item => [item.label, item.value]).sort(),
  [
    ["其他", 12],
    ["头条西瓜", 8],
    ["搜索", 24],
    ["直播推荐", 12],
    ["短视频及图文引流", 44]
  ].sort()
);

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
