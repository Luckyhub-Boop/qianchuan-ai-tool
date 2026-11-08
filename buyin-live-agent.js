"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {
  BROWSER_LAUNCH_ARGS,
  cleanupBrowserProfileState,
  pidIsRunning,
  safePageUrl
} = require("./live-screen-agent");

const ROOT = __dirname;
const EXTERNAL_ROOT = process.env.QIANCHUAN_EXTERNAL_ROOT || "D:\\AI投放产品";
const DATA_DIR = path.join(ROOT, "data");
const CONFIG_PATH = path.join(DATA_DIR, "buyin-live.json");
const STATE_PATH = path.join(DATA_DIR, "buyin-live-metrics.json");
const SESSION_STATE_PATH = path.join(DATA_DIR, "buyin-live-session.json");
const LIVE_SCREEN_STATE_PATH = path.join(DATA_DIR, "live-screen-metrics.json");
const LOCK_PATH = path.join(DATA_DIR, "buyin-live-agent.lock");
const REFRESH_REQUEST_PATH = path.join(DATA_DIR, "buyin-live-refresh.request.json");
const PAUSE_PATH = path.join(DATA_DIR, "buyin-live-pause");
const AGENT_LOG_PATH = path.join(DATA_DIR, "buyin-live-agent.log");
const AUDIENCE_HISTORY_PATH = path.join(DATA_DIR, "buyin-live-audience-history.json");
const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";
const LOGIN_URL = "https://buyin.jinritemai.com/mpa/account/login?log_out=1&type=24";
const CONTROL_URL = "https://buyin.jinritemai.com/dashboard/live/control";
const HEARTBEAT_INTERVAL_MS = 5000;

function resolveUserDataDir(userDataDir) {
  const value = String(userDataDir || "");
  if (value === "data/chrome-profile" || value === "data\\chrome-profile") {
    return path.join(EXTERNAL_ROOT, "chrome-profile");
  }
  if (value === "data/buyin-chrome-profile" || value === "data\\buyin-chrome-profile") {
    return path.join(EXTERNAL_ROOT, "buyin-chrome-profile");
  }
  return path.isAbsolute(value) ? value : path.resolve(ROOT, value);
}
const TARGET_HOST = "buyin.jinritemai.com";
const COMPASS_HOST = "compass.jinritemai.com";
const TARGET_PATH_SIGNALS = [
  "/dashboard/live/control",
  "/buyin_live_control",
  "/dashboard/live/slice",
  "/dashboard/compass-home"
];
const TARGET_TEXT_SIGNALS = [
  "直播中控台",
  "直播大屏",
  "人群流量占比",
  "成交金额占比",
  "渠道千次观看成交",
  "千次观看成交",
  "实时在线",
  "累计观看"
];
const CORE_METRICS = [
  "spend",
  "gmv",
  "orders",
  "roi",
  "watchCount",
  "productClicks",
  "gpm",
  "online"
];
const METRIC_LABELS = {
  spend: ["整体消耗", "广告消耗", "投放消耗", "消耗金额", "实时消耗", "消耗"],
  netGmv: ["净成交金额"],
  netOrders: ["净成交订单数", "净成交订单"],
  netRoi: ["净成交ROI"],
  gmv: ["成交金额", "支付金额", "用户实付金额", "成交额"],
  orders: ["成交订单数", "成交订单", "支付订单数", "订单数"],
  roi: ["支付ROI", "整体ROI", "投产比", "ROI"],
  watchCount: ["累计观看人数", "累计观看", "观看人数", "直播间观看"],
  productClicks: ["商品点击次数", "商品点击", "点击次数"],
  gpm: ["渠道千次观看成交", "千次观看成交", "整体GPM", "GPM"],
  online: ["实时在线人数", "当前在线人数", "在线人数"],
  exposure: ["曝光次数", "曝光人数", "曝光量"],
  watchOneMinute: ["观看满1分钟人数", "观看满 1 分钟人数", "1分钟观看人数"],
  comments: ["累计评论次数", "评论次数"],
  follows: ["新增关注人数", "新增粉丝数", "新增关注"],
  clickRate: ["商品点击率", "点击率"],
  conversionRate: ["观看-成交率(人数)", "观看成交转化率", "成交转化率", "转化率"],
  averageWatch: ["人均观看时长", "平均停留时长"],
  refundRate: ["退款率"],
  refundAmount: ["退款金额"],
  interactionRate: ["互动率"]
};
const CHANNEL_FIELD_ALIASES = {
  trafficCount: [
    "total_live_watch_cnt_for_roi2",
    "live_watch_count",
    "watch_count",
    "traffic_count",
    "uv",
    "viewer_count"
  ],
  gmv: [
    "total_live_pay_amt_for_roi2",
    "total_pay_order_gmv_for_roi2",
    "pay_gmv",
    "gmv",
    "amount"
  ],
  orders: ["total_pay_order_count_for_roi2", "pay_order_count", "order_count"],
  gpm: ["gpm", "gmv_per_thousand", "thousand_watch_gmv"],
  trafficShare: ["traffic_share", "watch_share", "uv_ratio"],
  gmvShare: ["gmv_share", "pay_gmv_ratio", "amount_ratio"]
};
const METRIC_ALIASES = {
  spend: ["stat_cost", "total_cost", "spend", "cost"],
  netGmv: [
    "total_order_settle_amount_for_roi2_1h",
    "total_pay_order_settle_amount_for_roi2"
  ],
  netOrders: [
    "total_order_settle_count_for_roi2_1h",
    "total_pay_order_settle_count_for_roi2"
  ],
  netRoi: ["total_prepay_and_pay_settle_roi2_1h"],
  gmv: [
    "total_pay_order_gmv_for_roi2",
    "pay_gmv",
    "gmv"
  ],
  orders: [
    "total_pay_order_count_for_roi2",
    "pay_order_count",
    "order_count"
  ],
  roi: ["pay_roi", "roi"],
  watchCount: ["total_live_watch_cnt", "live_watch_count", "watch_count"],
  productClicks: ["live_click_product_count_alias", "product_click_count", "click_count"],
  gpm: ["gpm", "gmv_per_thousand"],
  online: ["online_count", "current_online_count", "room_online_count"],
  exposure: ["show_count", "exposure_count", "impression_count"],
  watchOneMinute: ["live_watch_one_minute_count", "watch_one_minute_count"],
  comments: ["total_live_comment_cnt", "comment_count"],
  follows: ["total_live_follow_cnt", "follow_count", "new_follower_count"],
  clickRate: ["product_click_rate", "click_rate"],
  conversionRate: ["conversion_rate", "pay_conversion_rate"],
  averageWatch: ["average_watch_duration", "avg_watch_duration"],
  refundRate: ["refund_rate"],
  refundAmount: ["refund_amount"],
  interactionRate: ["interaction_rate"]
};
const DIMENSION_ALIASES = [
  "combined_first_compass_entrance_code",
  "traffic_source_name",
  "flow_source_name",
  "channel_name",
  "source_name"
];
const DEFAULT_CONFIG = {
  enabled: true,
  loginUrl: LOGIN_URL,
  pageUrl: "",
  controlPageUrl: "",
  intervalSeconds: 10,
  headless: true,
  executablePath: "",
  userDataDir: "data/buyin-chrome-profile",
  serverUrl: DEFAULT_SERVER_URL,
  viewport: { width: 1600, height: 1000, deviceScaleFactor: 1 }
};

let activeBrowser = null;
let activePage = null;
let activeLockOwner = null;
let heartbeatTimer = null;
let heartbeatConfig = null;
let lastState = null;
let shuttingDown = false;

function nowIso() {
  return new Date().toISOString();
}

function log(message) {
  console.log(`[${nowIso()}] ${message}`);
  if (process.argv.includes("--login")) {
    try {
      fs.mkdirSync(DATA_DIR, { recursive: true });
      fs.appendFileSync(
        AGENT_LOG_PATH,
        `[${nowIso()}] [login] ${message}\n`,
        "utf8"
      );
    } catch (_) {}
  }
}

function ensureDataDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function readJson(filePath, fallback) {
  try {
    const value = JSON.parse(fs.readFileSync(filePath, "utf8"));
    return value && typeof value === "object" ? value : fallback;
  } catch (_) {
    return fallback;
  }
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(temporary, filePath);
}

function mergeConfig(base, override) {
  const merged = { ...base, ...(override || {}) };
  merged.viewport = {
    ...(base.viewport || {}),
    ...((override && override.viewport) || {})
  };
  merged.intervalSeconds = Math.max(
    5,
    Number(merged.intervalSeconds) || DEFAULT_CONFIG.intervalSeconds
  );
  return merged;
}

function loadConfig() {
  return mergeConfig(DEFAULT_CONFIG, readJson(CONFIG_PATH, {}));
}

function acquireLock() {
  const existing = readJson(LOCK_PATH, null);
  if (existing && Number(existing.pid) !== process.pid && pidIsRunning(existing.pid)) {
    return { acquired: false, owner: existing };
  }
  const owner = {
    pid: process.pid,
    mode: process.argv.includes("--login") ? "login" : "agent",
    profile: DEFAULT_CONFIG.userDataDir,
    startedAt: nowIso()
  };
  writeJsonAtomic(LOCK_PATH, owner);
  activeLockOwner = owner;
  return { acquired: true, owner };
}

function releaseLock() {
  if (!activeLockOwner) return;
  const current = readJson(LOCK_PATH, null);
  if (
    current &&
    Number(current.pid) !== process.pid &&
    pidIsRunning(current.pid)
  ) {
    activeLockOwner = null;
    return;
  }
  try {
    fs.unlinkSync(LOCK_PATH);
  } catch (error) {
    if (error?.code !== "ENOENT") log(`清理采集锁失败: ${error.message}`);
  }
  activeLockOwner = null;
}

function registerCleanup() {
  const cleanup = async () => {
    if (shuttingDown) return;
    shuttingDown = true;
    stopHeartbeat();
    await closeBrowser();
    releaseLock();
  };
  process.once("exit", () => {
    stopHeartbeat();
    releaseLock();
  });
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    process.once(signal, () => {
      cleanup().finally(() => process.exit(0));
    });
  }
}

async function closeBrowser() {
  if (!activeBrowser) return;
  try {
    await activeBrowser.close();
  } catch (_) {}
  activeBrowser = null;
  activePage = null;
}

function browserCandidates(config) {
  return [
    String(config.executablePath || "").trim(),
    String(process.env.BUYIN_BROWSER_PATH || "").trim(),
    path.join(process.env.ProgramFiles || "", "Microsoft", "Edge", "Application", "msedge.exe"),
    path.join(process.env["ProgramFiles(x86)"] || "", "Microsoft", "Edge", "Application", "msedge.exe"),
    path.join(process.env.ProgramFiles || "", "Google", "Chrome", "Application", "chrome.exe"),
    path.join(process.env["ProgramFiles(x86)"] || "", "Google", "Chrome", "Application", "chrome.exe")
  ].filter(Boolean);
}

function resolveBrowser(config) {
  const found = browserCandidates(config).find(candidate => {
    try {
      return fs.statSync(candidate).isFile();
    } catch (_) {
      return false;
    }
  });
  if (!found) throw new Error("未找到 Chrome/Edge，请设置 BUYIN_BROWSER_PATH");
  return found;
}

async function launchBrowser(puppeteer, config, headless) {
  const userDataDir = resolveUserDataDir(config.userDataDir || DEFAULT_CONFIG.userDataDir);
  cleanupBrowserProfileState(userDataDir, { terminateOrphans: true });
  fs.mkdirSync(userDataDir, { recursive: true });
  const visibleArgs = headless
    ? BROWSER_LAUNCH_ARGS
    : [
        ...BROWSER_LAUNCH_ARGS,
        "--window-size=1440,900",
        "--force-device-scale-factor=1"
      ];
  const browser = await puppeteer.launch({
    executablePath: resolveBrowser(config),
    headless: headless ? "new" : false,
    userDataDir,
    defaultViewport: headless ? config.viewport : null,
    args: visibleArgs
  });
  activeBrowser = browser;
  return browser;
}

async function loadPuppeteer() {
  try {
    return require("puppeteer-core");
  } catch (_) {
    throw new Error("缺少 puppeteer-core，请先在项目目录执行 npm install");
  }
}

function parseMetricNumber(rawValue) {
  if (typeof rawValue === "number") {
    return Number.isFinite(rawValue) ? rawValue : null;
  }
  let text = String(rawValue ?? "")
    .replace(/,/g, "")
    .replace(/\s+/g, "")
    .trim();
  if (!text || text === "-" || text === "—") return null;
  const multiplier = /亿/.test(text) ? 100000000 : /万|w/i.test(text) ? 10000 : 1;
  const percent = /%/.test(text);
  const currency = /[¥￥]/.test(text);
  text = text.replace(/[¥￥%元人民币人单次个]/g, "");
  const match = text.match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;
  const value = Number(match[0]) * multiplier;
  return {
    value,
    unit: percent ? "percent" : currency ? "currency" : "number"
  };
}

function scalarNumber(value) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string") {
    const parsed = parseMetricNumber(value);
    return parsed ? parsed.value : null;
  }
  if (value && typeof value === "object") {
    for (const key of ["Value", "value", "ValueStr", "valueStr", "amount", "Amount"]) {
      if (key in value) {
        const parsed = scalarNumber(value[key]);
        if (parsed !== null) return parsed;
      }
    }
  }
  return null;
}

function walkObjects(value, visitor, seen = new Set(), depth = 0) {
  if (!value || typeof value !== "object" || seen.has(value) || depth > 16) return;
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) walkObjects(item, visitor, seen, depth + 1);
    return;
  }
  visitor(value);
  for (const item of Object.values(value)) {
    walkObjects(item, visitor, seen, depth + 1);
  }
}

function firstAliasValue(record, aliases) {
  const candidates = [
    record,
    record?.Metrics,
    record?.metrics,
    record?.data,
    record?.result
  ].filter(item => item && typeof item === "object");
  for (const candidate of candidates) {
    for (const alias of aliases) {
      if (!(alias in candidate)) continue;
      const value = scalarNumber(candidate[alias]);
      if (value !== null) return value;
    }
  }
  return null;
}

function dimensionLabel(record) {
  const dimensions = record?.Dimensions;
  if (dimensions && typeof dimensions === "object") {
    for (const key of DIMENSION_ALIASES) {
      const dimension = dimensions[key];
      if (!dimension) continue;
      const value = String(dimension.Value || dimension.value || "").trim();
      const label = String(
        dimension.ValueStr || dimension.valueStr || value || ""
      ).trim();
      if (label) return { key: value || label, label };
    }
  }
  for (const key of DIMENSION_ALIASES) {
    if (!(key in record)) continue;
    const value = record[key];
    const objectValue = value && typeof value === "object" ? value : null;
    const keyValue = String(
      objectValue ? objectValue.Value || objectValue.value || "" : value || ""
    ).trim();
    const label = String(
      objectValue
        ? objectValue.ValueStr || objectValue.valueStr || keyValue
        : value || ""
    ).trim();
    if (label) return { key: keyValue || label, label };
  }
  return null;
}

function finalizeChannels(rows) {
  const merged = new Map();
  for (const row of rows) {
    if (!row?.key) continue;
    const current = merged.get(row.key) || {
      key: row.key,
      label: row.label || row.key,
      trafficCount: null,
      gmv: null,
      orders: null,
      gpm: null,
      trafficShare: null,
      gmvShare: null,
      source: row.source || "buyin_live_board_network"
    };
    for (const field of [
      "trafficCount",
      "gmv",
      "orders",
      "gpm",
      "trafficShare",
      "gmvShare"
    ]) {
      if (row[field] != null) current[field] = row[field];
    }
    merged.set(row.key, current);
  }
  const items = Array.from(merged.values());
  const trafficTotal = items.reduce((total, item) => total + (item.trafficCount || 0), 0);
  const gmvTotal = items.reduce((total, item) => total + (item.gmv || 0), 0);
  for (const item of items) {
    if (item.trafficShare == null && trafficTotal > 0 && item.trafficCount != null) {
      item.trafficShare = Number((item.trafficCount / trafficTotal * 100).toFixed(4));
    }
    if (item.gmvShare == null && gmvTotal > 0 && item.gmv != null) {
      item.gmvShare = Number((item.gmv / gmvTotal * 100).toFixed(4));
    }
    if (
      item.gpm == null &&
      item.gmv != null &&
      item.trafficCount != null &&
      item.trafficCount > 0
    ) {
      item.gpm = Number((item.gmv / item.trafficCount * 1000).toFixed(2));
    }
  }
  return {
    source: "buyin_live_board_network",
    sourceLabel: "巨量百应直播中控台 · 网络数据",
    totalTraffic: trafficTotal,
    totalGmv: Number(gmvTotal.toFixed(2)),
    items: items.sort(
      (left, right) =>
        (right.trafficShare ?? -1) - (left.trafficShare ?? -1) ||
        (right.gmvShare ?? -1) - (left.gmvShare ?? -1)
    ),
    capturedAt: nowIso()
  };
}

function extractCompassChannels(snapshot) {
  const tableRows = [];
  for (const table of snapshot?.tables || []) {
    if (!Array.isArray(table) || table.length < 2) continue;
    if (
      table[0]?.[0] !== "渠道名称" ||
      table[0]?.[1] !== "流量占比" ||
      table[0]?.[2] !== "成交金额占比" ||
      table[0]?.[3] !== "渠道千次观看成交"
    ) {
      continue;
    }
    for (const cells of table.slice(1)) {
      if (!cells?.[0]) continue;
      const traffic = parseMetricNumber(cells[1]);
      if (!traffic) continue;
      const gmvShare = parseMetricNumber(cells[2]);
      const gpm = parseMetricNumber(cells[3]);
      tableRows.push({
        key: cells[0],
        label: cells[0],
        trafficCount: null,
        gmv: null,
        orders: null,
        trafficShare: Number(traffic.value.toFixed(4)),
        gmvShare: gmvShare ? Number(gmvShare.value.toFixed(4)) : null,
        gpm: gpm ? Number(gpm.value.toFixed(2)) : null,
        native: true,
        source: "buyin_compass_live_screen_dom"
      });
    }
  }
  if (tableRows.length) {
    const result = finalizeChannels(tableRows);
    result.source = "buyin_compass_live_screen_dom";
    result.sourceLabel = "巨量百应直播大屏·专业版 · 流量分析";
    result.nativeFields = ["trafficShare", "gmvShare", "gpm"];
    return result;
  }
  const lines = (snapshot?.lines || [])
    .map(line => String(line || "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
  const rows = [];
  for (let index = 0; index < lines.length; index += 1) {
    if (lines[index] !== "渠道名称") continue;
    if (
      lines[index + 1] !== "流量占比" ||
      lines[index + 2] !== "成交金额占比" ||
      lines[index + 3] !== "渠道千次观看成交"
    ) {
      continue;
    }
    let cursor = index + 4;
    while (cursor + 3 < lines.length) {
      const label = lines[cursor];
      if (
        !label ||
        label === "渠道名称" ||
        label === "全部流量渠道" ||
        /^完整榜单|^查看更多/.test(label)
      ) {
        break;
      }
      const traffic = parseMetricNumber(lines[cursor + 1]);
      if (!traffic) break;
      const gmvShare = parseMetricNumber(lines[cursor + 2]);
      const gpm = parseMetricNumber(lines[cursor + 3]);
      rows.push({
        key: label,
        label,
        trafficCount: null,
        gmv: null,
        orders: null,
        trafficShare: Number(traffic.value.toFixed(4)),
        gmvShare: gmvShare ? Number(gmvShare.value.toFixed(4)) : null,
        gpm: gpm ? Number(gpm.value.toFixed(2)) : null,
        native: true,
        source: "buyin_compass_live_screen_dom"
      });
      cursor += 4;
    }
  }
  if (!rows.length) return null;
  const result = finalizeChannels(rows);
  result.source = "buyin_compass_live_screen_dom";
  result.sourceLabel = "巨量百应直播大屏·专业版 · 流量分析";
  result.nativeFields = ["trafficShare", "gmvShare", "gpm"];
  return result;
}

function extractBuyinPayload(payload) {
  const metrics = {};
  const channels = [];
  const splitRows = [];
  walkObjects(payload, record => {
    for (const [field, aliases] of Object.entries(METRIC_ALIASES)) {
      if (metrics[field] != null) continue;
      const value = firstAliasValue(record, aliases);
      if (value !== null) metrics[field] = value;
    }
    const dimension = dimensionLabel(record);
    if (dimension) {
      const candidate = {
        ...dimension,
        trafficCount: firstAliasValue(record, CHANNEL_FIELD_ALIASES.trafficCount),
        gmv: firstAliasValue(record, CHANNEL_FIELD_ALIASES.gmv),
        orders: firstAliasValue(record, CHANNEL_FIELD_ALIASES.orders),
        gpm: firstAliasValue(record, CHANNEL_FIELD_ALIASES.gpm),
        trafficShare: firstAliasValue(record, CHANNEL_FIELD_ALIASES.trafficShare),
        gmvShare: firstAliasValue(record, CHANNEL_FIELD_ALIASES.gmvShare),
        source: "buyin_live_board_network"
      };
      if (
        candidate.trafficCount != null ||
        candidate.gmv != null ||
        candidate.orders != null ||
        candidate.gpm != null ||
        candidate.trafficShare != null ||
        candidate.gmvShare != null
      ) {
        splitRows.push(candidate);
      }
    }
  });
  if (metrics.netGmv != null) {
    metrics.gmv = metrics.netGmv;
    metrics.gmvScope = "net";
  } else if (metrics.gmv != null) {
    metrics.gmvScope = "buyin_reported";
  }
  if (metrics.netOrders != null) {
    metrics.orders = metrics.netOrders;
    metrics.ordersScope = "net";
  }
  if (metrics.netRoi != null) {
    metrics.roi = metrics.netRoi;
    metrics.roiScope = "net";
  }
  return {
    metrics,
    channels: splitRows.length ? finalizeChannels(splitRows) : null
  };
}

async function inspectPage(page) {
  return page.evaluate(() => {
    const visible = element => {
      if (!(element instanceof Element)) return false;
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const style = window.getComputedStyle(element);
      return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0;
    };
    const compact = value => String(value || "").replace(/\s+/g, " ").trim();
    const htmlTables = Array.from(document.querySelectorAll("table"))
      .filter(visible)
      .slice(0, 20)
      .map(table => Array.from(table.querySelectorAll("tr"))
        .filter(visible)
        .slice(0, 100)
        .map(row => Array.from(row.querySelectorAll("th,td"))
          .map(cell => compact(cell.innerText || cell.textContent))
          .filter(Boolean)));
    const compassTables = Array.from(document.querySelectorAll(".table--NcyJM"))
      .filter(visible)
      .slice(0, 20)
      .map(table => {
        const header = Array.from(
          table.querySelector(".header--dSjw0")?.children || []
        ).map(cell => compact(cell.innerText || cell.textContent)).filter(Boolean);
        const rows = Array.from(table.querySelectorAll(".row--Grqkh"))
          .filter(visible)
          .map(row => Array.from(row.querySelectorAll(".cell--DpUW8"))
            .map(cell => compact(cell.innerText || cell.textContent))
            .filter(Boolean));
        return [header, ...rows].filter(row => row.length);
      });
    const fragments = [];
    for (const element of document.querySelectorAll(
      "[data-testid], [class*='metric'], [class*='stat'], [class*='card'], section, article, div"
    )) {
      if (!visible(element)) continue;
      const text = compact(element.innerText || element.textContent);
      if (!text || text.length > 260) continue;
      const rect = element.getBoundingClientRect();
      fragments.push({ text, area: rect.width * rect.height });
    }
    fragments.sort((left, right) => left.area - right.area);
    return {
      url: location.href,
      title: document.title,
      lines: String(document.body?.innerText || "")
        .split(/\r?\n/)
        .map(compact)
        .filter(Boolean)
        .slice(0, 4000),
      fragments: fragments.slice(0, 900),
      tables: [...htmlTables, ...compassTables],
      bodyText: String(document.body?.innerText || "").slice(0, 80000)
    };
  });
}

function loginRequired(snapshot) {
  const url = String(snapshot?.url || "").toLowerCase();
  const text = String(snapshot?.bodyText || "");
  return (
    /\/(login|passport|account\/login|roles-select)(?:[/?#]|$)/i.test(url) ||
    /扫码登录|请登录|登录巨量百应|账号登录|选择登录角色/.test(text)
  );
}

function isBuyinTargetPage(snapshot, rawUrl = "") {
  try {
    const url = new URL(rawUrl || snapshot?.url || "");
    const hostname = url.hostname.toLowerCase();
    if (hostname === COMPASS_HOST) {
      return (
        url.pathname.startsWith("/screen/live/") &&
        /直播大屏|流量分析/.test(String(snapshot?.bodyText || ""))
      );
    }
    if (hostname !== TARGET_HOST) return false;
    if (TARGET_PATH_SIGNALS.some(signal => url.pathname.includes(signal))) return true;
  } catch (_) {
    return false;
  }
  const text = String(snapshot?.bodyText || "");
  const signals = TARGET_TEXT_SIGNALS.filter(signal => text.includes(signal)).length;
  return signals >= 2 && /流量占比|成交|直播/.test(text);
}

function parseLabelValue(text) {
  const compact = String(text || "").replace(/\s+/g, " ").trim();
  const match = compact.match(
    /^(.{2,30}?)\s*[:：]?\s*([¥￥]?-?\d[\d,]*(?:\.\d+)?\s*(?:%|万|亿|元|人|单|次)?)(?:\s|$)/
  );
  if (!match) return null;
  return {
    label: match[1].replace(/[：:]\s*$/, "").trim(),
    rawValue: match[2],
    evidence: compact.slice(0, 180)
  };
}

function extractMetricsFromSnapshot(snapshot, networkMetrics = {}) {
  const metrics = { ...networkMetrics };
  const matches = {};
  const sources = [
    ...(snapshot?.lines || []),
    ...(snapshot?.fragments || []).map(item => item.text || "")
  ];
  for (const [field, labels] of Object.entries(METRIC_LABELS)) {
    if (metrics[field] != null) continue;
    for (const source of sources) {
      const text = String(source || "").replace(/\s+/g, " ").trim();
      const label = labels.find(candidate => text.includes(candidate));
      if (!label) continue;
      const at = text.indexOf(label);
      const tail = text.slice(at + label.length).trim();
      const parsed = parseMetricNumber(tail);
      if (!parsed) continue;
      metrics[field] = Number(parsed.value.toFixed(6));
      if (field === "netGmv") {
        metrics.gmv = metrics[field];
        metrics.gmvScope = "net";
      } else if (field === "netOrders") {
        metrics.orders = metrics[field];
        metrics.ordersScope = "net";
      } else if (field === "netRoi") {
        metrics.roi = metrics[field];
        metrics.roiScope = "net";
      }
      matches[field] = {
        label,
        evidence: text.slice(0, 180),
        unit: parsed.unit,
        source: "buyin_live_board_dom"
      };
      break;
    }
  }
  return { metrics, matches };
}

function inferChannelColumn(header) {
  const text = String(header || "");
  if (/千次.*成交|GPM|千次观看/i.test(text)) return "gpm";
  if (/成交.*占比|金额占比|GMV.*占比/i.test(text)) return "gmvShare";
  if (/流量.*占比|人数占比|观看.*占比/i.test(text)) return "trafficShare";
  if (/成交金额|支付金额|GMV/i.test(text)) return "gmv";
  if (/观看.*人数|流量人数|人数|UV/i.test(text)) return "trafficCount";
  return "";
}

function extractChannelsFromSnapshot(snapshot) {
  const compassChannels = extractCompassChannels(snapshot);
  if (compassChannels?.items?.length) return compassChannels;
  const rows = [];
  for (const table of snapshot?.tables || []) {
    if (!Array.isArray(table) || table.length < 2) continue;
    let headerIndex = -1;
    const columns = {};
    for (let index = 0; index < Math.min(5, table.length); index += 1) {
      const candidate = {};
      table[index].forEach((cell, cellIndex) => {
        const field = inferChannelColumn(cell);
        if (field && candidate[field] == null) candidate[field] = cellIndex;
      });
      if (
        candidate.trafficShare != null ||
        candidate.gmvShare != null ||
        candidate.gpm != null
      ) {
        headerIndex = index;
        Object.assign(columns, candidate);
        break;
      }
    }
    if (headerIndex < 0) continue;
    for (const cells of table.slice(headerIndex + 1)) {
      const label = String(cells[0] || "").trim();
      if (!label || /合计|总计/.test(label)) continue;
      const item = {
        key: label,
        label,
        trafficCount: null,
        gmv: null,
        orders: null,
        gpm: null,
        trafficShare: null,
        gmvShare: null,
        source: "buyin_live_board_dom"
      };
      for (const [field, cellIndex] of Object.entries(columns)) {
        if (cellIndex >= cells.length) continue;
        const parsed = parseMetricNumber(cells[cellIndex]);
        if (parsed) item[field] = Number(parsed.value.toFixed(4));
      }
      if (
        item.trafficShare != null ||
        item.gmvShare != null ||
        item.gpm != null
      ) {
        rows.push(item);
      }
    }
  }
  return rows.length ? finalizeChannels(rows) : null;
}

function extractExtras(snapshot) {
  const seen = new Set();
  const extras = [];
  const sources = [
    ...(snapshot?.lines || []),
    ...(snapshot?.fragments || []).map(item => item.text || "")
  ];
  for (const source of sources) {
    const pair = parseLabelValue(source);
    if (!pair) continue;
    if (!/率|占比|人数|金额|成交|观看|点击|曝光|停留|互动|退款|订单|消耗|ROI|GPM|成本|客单|粉丝|转化|流量/.test(pair.label)) {
      continue;
    }
    const parsed = parseMetricNumber(pair.rawValue);
    if (!parsed) continue;
    const marker = `${pair.label}|${parsed.value}|${parsed.unit}`;
    if (seen.has(marker)) continue;
    seen.add(marker);
    extras.push({
      label: pair.label,
      value: Number(parsed.value.toFixed(6)),
      unit: parsed.unit,
      source: "buyin_live_board_dom",
      evidence: pair.evidence
    });
    if (extras.length >= 80) break;
  }
  return extras;
}

function extractAudienceSummary(snapshot) {
  const lines = (snapshot?.lines || [])
    .map(line => String(line || "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
  for (let index = 0; index < lines.length; index += 1) {
    if (!/实时看播用户画像|全场累计用户画像/.test(lines[index])) continue;
    for (let offset = 1; offset <= 4 && index + offset < lines.length; offset += 1) {
      const candidate = lines[index + offset];
      if (/居多|女性|男性/.test(candidate) && candidate.length <= 160) {
        return candidate;
      }
    }
  }
  return "";
}

const REGION_LABELS = new Set([
  "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
  "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
  "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
  "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
  "华东", "华南", "华北", "华中", "西南", "西北", "东北"
]);

function audienceHeaderScope(line) {
  const text = String(line || "").replace(/\s+/g, "");
  if (/近?1分钟.*看播.*画像|实时看播用户画像/.test(text)) {
    return { key: "realtimeViewer", label: "近1分钟看播用户" };
  }
  if (/近?5分钟.*(购买|成交).*画像|近期购买用户画像/.test(text)) {
    return { key: "recentBuyer", label: "近5分钟购买用户" };
  }
  if (/全场.*购买.*画像|购买用户画像|成交用户画像/.test(text)) {
    return { key: "fullBuyer", label: "全场购买用户" };
  }
  if (/全场.*(看播|观看|累计).*画像|全场累计用户画像/.test(text)) {
    return { key: "fullViewer", label: "全场看播用户" };
  }
  return null;
}

function percentageNearLabel(line, label) {
  const text = String(line || "");
  const at = text.indexOf(label);
  if (at < 0) return null;
  const before = text.slice(0, at);
  const after = text.slice(at + label.length);
  const afterMatch = after.match(/(\d+(?:\.\d+)?)\s*%/);
  const beforeMatches = Array.from(before.matchAll(/(\d+(?:\.\d+)?)\s*%/g));
  const beforeMatch = beforeMatches[beforeMatches.length - 1];
  const raw = afterMatch?.[1] || beforeMatch?.[1];
  return raw == null ? null : Number(raw);
}

function addDistributionItem(distribution, seen, label, value) {
  const cleanLabel = String(label || "").replace(/\s+/g, "").trim();
  if (!cleanLabel || !Number.isFinite(value)) return;
  const key = `${cleanLabel}|${value}`;
  if (seen.has(key)) return;
  seen.add(key);
  distribution.push({
    label: cleanLabel,
    value: Number(value.toFixed(4))
  });
}

function extractProfileDimension(block, kind) {
  const distribution = [];
  const seen = new Set();
  for (const line of block) {
    const text = String(line || "").replace(/\s+/g, " ").trim();
    if (!text) continue;
    if (kind === "gender") {
      for (const label of ["女性", "男性"]) {
        const value = percentageNearLabel(text, label);
        if (value != null) addDistributionItem(distribution, seen, label, value);
      }
    } else if (kind === "age") {
      const matches = Array.from(
        text.matchAll(/(\d{1,2}\s*[-~至]\s*\d{1,2}\s*岁|\d{1,2}\s*岁以下|\d{1,2}\s*岁以上)/g)
      );
      for (const match of matches) {
        const label = match[0].replace(/\s+/g, "");
        const value = percentageNearLabel(text, match[0]);
        if (value != null) addDistributionItem(distribution, seen, label, value);
      }
    } else if (kind === "region") {
      for (const label of REGION_LABELS) {
        if (!text.includes(label)) continue;
        const value = percentageNearLabel(text, label);
        if (value != null) addDistributionItem(distribution, seen, label, value);
      }
    }
  }
  distribution.sort((left, right) => right.value - left.value);
  return {
    top: distribution[0]?.label || "",
    distribution: distribution.slice(0, 12)
  };
}

function extractAudienceProfiles(snapshot) {
  const lines = (snapshot?.lines || [])
    .map(line => String(line || "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
  const headers = [];
  lines.forEach((line, index) => {
    const scope = audienceHeaderScope(line);
    if (scope) headers.push({ index, ...scope });
  });
  const profiles = {};
  headers.forEach((header, headerIndex) => {
    const end = headers[headerIndex + 1]?.index ?? Math.min(lines.length, header.index + 36);
    const block = lines.slice(header.index, end);
    const joined = block.join(" ");
    const unavailableReason = /人数过少/.test(joined)
      ? "百应直播大屏提示当前人数过少，暂无法展示画像"
      : /无法查看用户画像|暂无足够数据|数据不足/.test(joined)
        ? "百应直播大屏提示当前暂无法展示用户画像"
        : "";
    const gender = extractProfileDimension(block, "gender");
    const age = extractProfileDimension(block, "age");
    const region = extractProfileDimension(block, "region");
    if (!gender.top) {
      const match = joined.match(/(女性|男性)居多/);
      if (match) gender.top = match[1];
    }
    if (!age.top) {
      const match = joined.match(/(\d{1,2}\s*[-~至]\s*\d{1,2}\s*岁|\d{1,2}\s*岁以下|\d{1,2}\s*岁以上)居多/);
      if (match) age.top = match[1].replace(/\s+/g, "");
    }
    if (!region.top) {
      region.top = Array.from(REGION_LABELS).find(label => joined.includes(`${label}居多`)) || "";
    }
    if (!region.top) {
      const candidates = Array.from(joined.matchAll(/([\u4e00-\u9fa5]{2,8})居多/g))
        .map(match => match[1])
        .filter(value => !/女性|男性|用户|人群|年龄|城市|省份|地区/.test(value));
      region.top = candidates.find(value => REGION_LABELS.has(value)) || "";
    }
    const available = Boolean(unavailableReason === "" && (gender.top || age.top || region.top));
    const summaryParts = [];
    if (gender.top) summaryParts.push(`${gender.top}居多`);
    if (age.top) summaryParts.push(`${age.top}居多`);
    if (region.top) summaryParts.push(`${region.top}居多`);
    profiles[header.key] = {
      available,
      label: header.label,
      gender,
      age,
      region,
      summary: unavailableReason || summaryParts.join("、"),
      unavailableReason,
      source: "buyin_compass_live_screen_dom",
      sourceLabel: "巨量百应直播大屏·专业版 · 用户画像",
      evidence: block.slice(0, 8)
    };
  });
  if (!headers.length) {
    const unavailableReason = lines.find(line =>
      /无法查看用户画像|在线人数过少|人数过少|暂无足够数据|数据不足/.test(line)
    );
    if (unavailableReason) {
      const unavailableMessage = /人数过少/.test(unavailableReason)
        ? "百应直播大屏提示当前人数过少，暂无法展示画像"
        : "百应直播大屏提示当前暂无法展示用户画像";
      for (const [key, label] of Object.entries({
        realtimeViewer: "近1分钟看播用户",
        recentBuyer: "近5分钟购买用户",
        fullViewer: "全场看播用户",
        fullBuyer: "全场购买用户"
      })) {
        profiles[key] = {
          available: false,
          label,
          gender: { top: "", distribution: [] },
          age: { top: "", distribution: [] },
          region: { top: "", distribution: [] },
          summary: unavailableMessage,
          unavailableReason: unavailableMessage,
          source: "buyin_compass_live_screen_dom",
          sourceLabel: "巨量百应直播大屏·专业版 · 用户画像",
          evidence: [unavailableReason]
        };
      }
    }
  }
  return profiles;
}

function installNetworkCapture(page) {
  let metrics = {};
  let channels = null;
  let metricsUpdatedAt = 0;
  let channelsUpdatedAt = 0;
  const pending = [];
  page.on("response", response => {
    const url = response.url();
    const contentType = String(response.headers()["content-type"] || "");
    if (!contentType.includes("json")) return;
    if (!/buyin\.jinritemai\.com|jinritemai\.com/i.test(url)) return;
    pending.push(
      response.text()
        .then(body => {
          if (!body || body.length > 6000000) return;
          if (!/(gmv|watch|traffic|flow|order|amount|room|stat|compass|live)/i.test(body)) return;
          const extracted = extractBuyinPayload(JSON.parse(body));
          if (Object.keys(extracted.metrics).length) {
            metrics = { ...metrics, ...extracted.metrics };
            metricsUpdatedAt = Date.now();
          }
          if (extracted.channels?.items?.length) {
            channels = extracted.channels;
            channelsUpdatedAt = Date.now();
          }
        })
        .catch(() => {})
    );
  });
  return {
    async pending() {
      await Promise.allSettled(pending.splice(0));
    },
    metrics: () => Date.now() - metricsUpdatedAt <= 120000 ? { ...metrics } : {},
    channels: () => Date.now() - channelsUpdatedAt <= 120000 ? channels : null,
    reset() {
      metrics = {};
      channels = null;
      metricsUpdatedAt = 0;
      channelsUpdatedAt = 0;
      pending.length = 0;
    }
  };
}

async function scrapePage(page) {
  const snapshot = await inspectPage(page);
  const network = capture ? capture.metrics() : {};
  await (capture ? capture.pending() : Promise.resolve());
  const networkChannels = capture ? capture.channels() : null;
  const { metrics, matches } = extractMetricsFromSnapshot(snapshot, network);
  const domChannels = extractChannelsFromSnapshot(snapshot);
  const channels = domChannels?.items?.length
    ? domChannels
    : networkChannels;
  const extras = extractExtras(snapshot);
  const audienceProfiles = extractAudienceProfiles(snapshot);
  const hasAudience = Object.values(audienceProfiles).some(profile => profile?.available);
  const audienceSummary = (
    audienceProfiles.realtimeViewer?.summary
    || audienceProfiles.fullViewer?.summary
    || Object.values(audienceProfiles).find(profile => profile?.unavailableReason)?.unavailableReason
    || extractAudienceSummary(snapshot)
  );
  const audienceDebugLines = (snapshot?.lines || []).filter(line =>
    /画像|男性|女性|岁|地域|城市|省份|地区|人数过少|数据不足/.test(String(line || ""))
  ).slice(0, 80);
  const login = loginRequired(snapshot);
  const target = isBuyinTargetPage(snapshot, snapshot.url);
  const hasCore = CORE_METRICS.some(key => metrics[key] != null);
  const status = login
    ? "login_required"
    : !target
      ? "page_mismatch"
      : hasCore || channels?.items?.length || extras.length || hasAudience
        ? "ok"
        : "no_metrics";
  let roomId = "";
  try {
    roomId = String(new URL(snapshot.url).searchParams.get("live_room_id") || "").trim();
  } catch (_) {}
  return {
    status,
    live: status === "ok",
    syncedAt: nowIso(),
    source: "puppeteer-core_buyin_live",
    sourceLabel: new URL(snapshot.url).hostname === COMPASS_HOST
      ? "巨量百应直播大屏·专业版 · 无头 Chrome 抓取"
      : "巨量百应直播中控台 · 无头 Chrome 抓取",
    pageUrl: safePageUrl(snapshot.url),
    pageTitle: String(snapshot.title || "").slice(0, 180),
    room: roomId ? { id: roomId } : null,
    metrics,
    metricMatches: matches,
    missingMetrics: CORE_METRICS.filter(key => metrics[key] == null),
    channels: channels || null,
    extras,
    audienceSummary,
    audienceProfiles,
    audienceDebugLines,
    capturedFieldCount:
      Object.keys(metrics).length
      + (channels?.items?.length || 0)
      + extras.length
      + Object.values(audienceProfiles).filter(profile => profile?.available).length,
    gmvScope: String(metrics.gmvScope || ""),
    ordersScope: String(metrics.ordersScope || ""),
    roiScope: String(metrics.roiScope || ""),
    error:
      status === "login_required"
        ? "巨量百应登录已过期，请运行 login-buyin.bat 重新登录"
        : status === "page_mismatch"
          ? "当前页面不是巨量百应直播中控台，请重新登录并保存正确页面"
          : status === "no_metrics"
            ? "百应页面已打开，但本轮未识别到可核验的数值"
            : ""
  };
}

function writeState(config, value) {
  lastState = {
    ...value,
    heartbeatAt: nowIso(),
    pid: process.pid,
    intervalSeconds: Number(config.intervalSeconds) || 10
  };
  writeJsonAtomic(STATE_PATH, lastState);
}

function audienceProfileSignature(profiles) {
  return crypto
    .createHash("sha256")
    .update(JSON.stringify(profiles || {}))
    .digest("hex");
}

function persistAudienceHistory(
  result,
  capturedAt = new Date(),
  filePath = AUDIENCE_HISTORY_PATH
) {
  const profiles = result?.audienceProfiles;
  if (!profiles || typeof profiles !== "object" || !Object.keys(profiles).length) {
    return false;
  }
  const roomId = String(
    result?.room?.id
    || (() => {
      try {
        return new URL(result?.pageUrl || "").searchParams.get("live_room_id") || "";
      } catch (_) {
        return "";
      }
    })()
  ).trim();
  if (!roomId) return false;
  const history = readJson(filePath, {});
  const items = Array.isArray(history?.items) ? history.items.slice() : [];
  const nowMs = capturedAt.getTime();
  const signature = audienceProfileSignature(profiles);
  const latest = items[items.length - 1];
  if (
    latest &&
    String(latest.roomId || "") === roomId &&
    latest.signature === signature &&
    nowMs - Number(latest.t || 0) < 4 * 60 * 1000
  ) {
    return false;
  }
  const compactProfiles = Object.fromEntries(
    Object.entries(profiles).map(([key, profile]) => [
      key,
      {
        available: Boolean(profile?.available),
        label: String(profile?.label || ""),
        gender: profile?.gender || { top: "", distribution: [] },
        age: profile?.age || { top: "", distribution: [] },
        region: profile?.region || { top: "", distribution: [] },
        summary: String(profile?.summary || ""),
        unavailableReason: String(profile?.unavailableReason || ""),
        source: "buyin_compass_live_screen_dom"
      }
    ])
  );
  items.push({
    t: nowMs,
    capturedAt: capturedAt.toISOString(),
    roomId,
    profiles: compactProfiles,
    signature,
    source: "buyin_compass_live_screen_dom",
    sourceLabel: "巨量百应直播大屏·专业版 · 用户画像快照"
  });
  const cutoff = nowMs - 14 * 24 * 60 * 60 * 1000;
  const recent = items
    .filter(item => Number(item?.t || 0) >= cutoff)
    .slice(-5000);
  writeJsonAtomic(filePath, {
    version: 1,
    updatedAt: capturedAt.toISOString(),
    retentionDays: 14,
    items: recent
  });
  return true;
}

function startHeartbeat(config) {
  heartbeatConfig = config;
  if (heartbeatTimer) return;
  heartbeatTimer = setInterval(() => {
    if (!heartbeatConfig || !lastState) return;
    try {
      writeState(heartbeatConfig, { ...lastState, heartbeatOnly: true });
    } catch (error) {
      log(`百应采集心跳写入失败: ${error.message}`);
    }
  }, HEARTBEAT_INTERVAL_MS);
}

function stopHeartbeat() {
  if (!heartbeatTimer) return;
  clearInterval(heartbeatTimer);
  heartbeatTimer = null;
}

function readRefreshRequest() {
  const request = readJson(REFRESH_REQUEST_PATH, null);
  return request?.requestId ? request : null;
}

function clearRefreshRequest(requestId) {
  const current = readJson(REFRESH_REQUEST_PATH, null);
  if (!current || current.requestId !== requestId) return false;
  try {
    fs.unlinkSync(REFRESH_REQUEST_PATH);
  } catch (error) {
    if (error?.code !== "ENOENT") return false;
  }
  return true;
}

function captureRequestFields(request, status) {
  if (!request) return {};
  return {
    captureRequestId: request.requestId,
    captureRequestedAt: request.requestedAt,
    captureStatus: status
  };
}

async function persistBrowserSession(page) {
  const cookies = await page.cookies();
  const storage = await page.evaluate(() => {
    const copy = storageArea => {
      const result = {};
      for (let index = 0; index < storageArea.length; index += 1) {
        const key = storageArea.key(index);
        if (key) result[key] = storageArea.getItem(key);
      }
      return result;
    };
    return {
      localStorage: copy(window.localStorage),
      sessionStorage: copy(window.sessionStorage)
    };
  });
  writeJsonAtomic(SESSION_STATE_PATH, {
    capturedAt: nowIso(),
    origin: new URL(page.url()).origin,
    cookies,
    storage
  });
}

async function enableBuyinPhoneLogin(page) {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const state = await page.evaluate(() => {
      const visibleInputs = Array.from(document.querySelectorAll("input"))
        .filter(input => {
          const rect = input.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        })
        .map(input => String(input.getAttribute("placeholder") || ""));
      if (
        visibleInputs.includes("手机号码") &&
        visibleInputs.includes("验证码")
      ) {
        return "phone_form";
      }
      const toggle = document.querySelector(".login-switcher--qrPhone");
      if (toggle) {
        toggle.click();
        return "switched";
      }
      return String(document.body?.innerText || "").includes("扫码登录")
        ? "waiting"
        : "unknown";
    }).catch(() => "unknown");
    if (state === "phone_form") return true;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return false;
}

function isCompassScreenUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    return (
      url.hostname.toLowerCase() === COMPASS_HOST &&
      url.pathname.startsWith("/screen/live/")
    );
  } catch (_) {
    return false;
  }
}

function extractLiveScreenRoomId(state) {
  if (!state || typeof state !== "object") return "";
  const status = String(state.status || "").toLowerCase();
  if (state.live !== true || state.stale === true) return "";
  if (status && !["ok", "partial", "stale"].includes(status)) return "";
  const roomId = String(state?.room?.id || "").trim();
  return roomId && roomId !== "0" ? roomId : "";
}

function compassScreenUrlForRoom(rawUrl, roomId) {
  if (!isCompassScreenUrl(rawUrl)) return "";
  const targetRoom = String(roomId || "").trim();
  if (!targetRoom || targetRoom === "0") return "";
  try {
    const url = new URL(rawUrl);
    const currentRoom = String(url.searchParams.get("live_room_id") || "").trim();
    if (currentRoom === targetRoom) return "";
    url.searchParams.set("live_room_id", targetRoom);
    return url.href;
  } catch (_) {
    return "";
  }
}

async function currentDiscoveredRoomId(config) {
  const server = String(config.serverUrl || DEFAULT_SERVER_URL).replace(/\/+$/, "");
  try {
    const response = await fetch(`${server}/api/live/screen`, {
      signal: AbortSignal.timeout(8000)
    });
    if (response.ok) {
      const payload = await response.json();
      const roomId = extractLiveScreenRoomId(payload);
      if (roomId) return roomId;
    }
  } catch (_) {
    // 服务端接口失败时继续读取采集器状态文件。
  }
  return extractLiveScreenRoomId(readJson(LIVE_SCREEN_STATE_PATH, {}));
}

async function syncCompassRoom(page, config) {
  if (!isCompassScreenUrl(page.url())) return false;
  const roomId = await currentDiscoveredRoomId(config);
  const targetUrl = compassScreenUrlForRoom(page.url(), roomId);
  if (!targetUrl) return false;
  if (capture) capture.reset();
  await page.goto(targetUrl, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  config.pageUrl = safePageUrl(page.url());
  writeJsonAtomic(CONFIG_PATH, {
    ...readJson(CONFIG_PATH, {}),
    pageUrl: config.pageUrl,
    screenRoomSyncedAt: nowIso()
  });
  log(`百应直播大屏已切换至当前直播 room=${roomId}`);
  return true;
}

async function openCompassScreenFromControl(browser, controlPage, config) {
  await controlPage.waitForFunction(
    () => {
      const text = String(document.body?.innerText || "");
      return text.includes("直播大屏") && text.includes("直播中");
    },
    { timeout: 30000 }
  ).catch(() => {});
  await new Promise(resolve => setTimeout(resolve, 5000));
  const before = new Set((await browser.pages()).map(page => page.url()));
  const marked = await controlPage.evaluate(() => {
    const visible = element => {
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };
    const target = Array.from(document.querySelectorAll("div,button,a,[role='button']"))
      .find(element =>
        visible(element) &&
        String(element.innerText || element.textContent || "").trim() === "直播大屏"
      );
    if (!target) return false;
    const clickable = target.closest("button,a,[role='button']") || target;
    clickable.setAttribute("data-buyin-open-live-screen", "1");
    return true;
  }).catch(() => false);
  if (!marked) return null;
  try {
    await controlPage.click('[data-buyin-open-live-screen="1"]');
  } catch (_) {
    return null;
  }
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const screenPage = (await browser.pages()).find(page =>
      isCompassScreenUrl(page.url()) &&
      !before.has(page.url())
    );
    if (screenPage) {
      await screenPage.waitForFunction(
        () => /流量分析|千次观看成交金额|直播间成交金额/.test(
          String(document.body?.innerText || "")
        ),
        { timeout: 30000 }
      ).catch(() => {});
      const screenUrl = new URL(screenPage.url());
      if (screenUrl.searchParams.get("live_room_id") === "0") {
        const discoveredRoomId = await currentDiscoveredRoomId(config);
        if (discoveredRoomId) {
          screenUrl.searchParams.set("live_room_id", discoveredRoomId);
          await screenPage.goto(screenUrl.href, {
            waitUntil: "domcontentloaded",
            timeout: 60000
          });
          await screenPage.waitForFunction(
            () => /流量分析|千次观看成交金额|直播间成交金额/.test(
              String(document.body?.innerText || "")
            ),
            { timeout: 30000 }
          ).catch(() => {});
          log(`百应直播大屏 room_id=0，已按当前直播场次修正 room=${discoveredRoomId}`);
        }
      }
      return screenPage;
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  return null;
}

async function ensureCompassFlowAnalysis(page) {
  if (!isCompassScreenUrl(page.url())) return false;
  const ready = await page.evaluate(() => {
    const text = String(document.body?.innerText || "");
    return (
      text.includes("渠道名称") &&
      text.includes("成交金额占比") &&
      text.includes("渠道千次观看成交")
    );
  }).catch(() => false);
  if (ready) return true;
  const marked = await page.evaluate(() => {
    const visible = element => {
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };
    const target = Array.from(document.querySelectorAll("div,button,[role='tab']"))
      .find(element =>
        visible(element) &&
        String(element.innerText || element.textContent || "").trim() === "流量分析"
      );
    if (!target) return false;
    target.setAttribute("data-buyin-flow-analysis", "1");
    return true;
  }).catch(() => false);
  if (!marked) return false;
  await page.click('[data-buyin-flow-analysis="1"]').catch(() => {});
  await page.waitForFunction(() => {
    const text = String(document.body?.innerText || "");
    return (
      text.includes("渠道名称") &&
      text.includes("成交金额占比") &&
      text.includes("渠道千次观看成交")
    );
  }, { timeout: 20000 }).catch(() => {});
  return page.evaluate(() => String(document.body?.innerText || "").includes("渠道名称"))
    .catch(() => false);
}

async function restoreBrowserSession(page, targetUrl) {
  const session = readJson(SESSION_STATE_PATH, null);
  if (
    session?.origin &&
    session.origin === new URL(targetUrl).origin &&
    Array.isArray(session.cookies)
  ) {
    for (const cookie of session.cookies) {
      try {
        await page.setCookie(cookie);
      } catch (_) {}
    }
  }
  await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (session?.storage && session.origin === new URL(page.url()).origin) {
    try {
      await page.evaluate(value => {
        for (const [key, item] of Object.entries(value.localStorage || {})) {
          window.localStorage.setItem(key, item);
        }
        for (const [key, item] of Object.entries(value.sessionStorage || {})) {
          window.sessionStorage.setItem(key, item);
        }
      }, session.storage);
      await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    } catch (_) {}
  }
}

async function waitForLoginCollectorRelease(maxSeconds = 30) {
  const deadline = Date.now() + maxSeconds * 1000;
  while (Date.now() < deadline) {
    const owner = readJson(LOCK_PATH, null);
    if (!owner || !pidIsRunning(owner.pid)) return;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  const owner = readJson(LOCK_PATH, null);
  if (owner && pidIsRunning(owner.pid)) {
    throw new Error(`百应后台采集器 PID=${owner.pid} 未退出，请稍后重试`);
  }
}

async function runLogin(config) {
  writeJsonAtomic(PAUSE_PATH, {
    mode: "login",
    pid: process.pid,
    startedAt: nowIso()
  });
  log("正在停止百应后台采集器，准备打开官方登录入口");
  await waitForLoginCollectorRelease();
  const lock = acquireLock();
  if (!lock.acquired) {
    throw new Error(`百应采集器仍由 PID=${lock.owner?.pid || "-"} 占用`);
  }
  const puppeteer = await loadPuppeteer();
  log("正在启动独立可见浏览器");
  const browser = await launchBrowser(puppeteer, config, false);
  const initialPages = await browser.pages();
  const page = initialPages[0] || await browser.newPage();
  for (const extraPage of initialPages.slice(1)) {
    await extraPage.close().catch(() => {});
  }
  activePage = page;
  log(`正在打开巨量百应官方登录页: ${config.loginUrl || LOGIN_URL}`);
  await page.goto(config.loginUrl || LOGIN_URL, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForFunction(() => {
    const text = String(document.body?.innerText || "");
    return text.includes("扫码登录") || Array.from(document.querySelectorAll("input"))
      .some(input => {
        const rect = input.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });
  }, { timeout: 20000 }).catch(() => {});
  const phoneLoginEnabled = await enableBuyinPhoneLogin(page);
  const initial = await inspectPage(page);
  const inputCount = await page.$$eval("input", inputs => inputs.filter(input => {
    const rect = input.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }).length).catch(() => 0);
  log(
    `登录页已加载：${initial.title || "无标题"}；` +
    (phoneLoginEnabled
      ? "已切换到抖音手机号登录，请输入手机号和验证码。"
      : `可输入框 ${inputCount} 个，请人工选择手机号登录。`) +
    "不要关闭浏览器。"
  );
  log(`可直接尝试的控制台地址: ${CONTROL_URL}`);
  const deadline = Date.now() + 20 * 60 * 1000;
  let lastHintAt = 0;
  let nextControlAttemptAt = 0;
  while (Date.now() < deadline) {
    const pages = await browser.pages();
    for (const current of pages) {
      let snapshot = null;
      try {
        snapshot = await inspectPage(current);
      } catch (_) {
        continue;
      }
      if (
        /\/mpa\/account\/login(?:[/?#]|$)/i.test(current.url()) &&
        !String(snapshot.bodyText || "").includes("发送验证码")
      ) {
        await enableBuyinPhoneLogin(current);
      }
      let currentPath = "";
      try {
        const parsed = new URL(current.url());
        currentPath = parsed.pathname;
        if (
          Date.now() >= nextControlAttemptAt &&
          parsed.hostname.toLowerCase() === TARGET_HOST &&
          /^\/dashboard\/?$/i.test(currentPath) &&
          !loginRequired(snapshot)
        ) {
          nextControlAttemptAt = Date.now() + 15000;
          log("检测到百应工作台首页，自动打开直播中控台");
          await current.goto(CONTROL_URL, {
            waitUntil: "domcontentloaded",
            timeout: 60000
          });
          continue;
        }
      } catch (_) {}
      if (!isBuyinTargetPage(snapshot, current.url())) continue;
      const result = await scrapePage(current);
      if (!result.live) {
        if (Date.now() - lastHintAt > 12000) {
          lastHintAt = Date.now();
          log("已进入百应但尚未识别到直播指标，请打开当前场次的直播中控台并等待页面加载。");
        }
        continue;
      }
      const pageUrl = safePageUrl(current.url());
      const liveControlPage = pages.find(candidate => {
        try {
          const parsed = new URL(candidate.url());
          return (
            parsed.hostname.toLowerCase() === TARGET_HOST &&
            parsed.pathname.includes("/dashboard/live/control")
          );
        } catch (_) {
          return false;
        }
      });
      writeJsonAtomic(CONFIG_PATH, {
        ...readJson(CONFIG_PATH, {}),
        enabled: true,
        loginUrl: config.loginUrl || LOGIN_URL,
        pageUrl,
        controlPageUrl: liveControlPage
          ? safePageUrl(liveControlPage.url())
          : CONTROL_URL,
        executablePath: resolveBrowser(config),
        userDataDir: config.userDataDir,
        lastLoginAt: nowIso()
      });
      await persistBrowserSession(current);
      writeState(config, {
        ...result,
        status: "login_saved",
        sourceLabel: "巨量百应直播中控台 · 登录与采集验证成功"
      });
      log(`百应直播中控台已保存: ${pageUrl}`);
      log(
        `验证到 ${Object.keys(result.metrics).length} 个指标、` +
        `${result.channels?.items?.length || 0} 个渠道、${result.extras.length} 个补充字段`
      );
      await new Promise(resolve => setTimeout(resolve, 3000));
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  throw new Error("20 分钟内未检测到巨量百应直播中控台及可核验数值");
}

let capture = null;

async function runAgent(config) {
  if (!config.pageUrl) {
    while (true) {
      writeState(config, {
        status: "config_required",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core_buyin_live",
        sourceLabel: "巨量百应直播中控台 · 等待登录",
        metrics: {},
        missingMetrics: CORE_METRICS,
        channels: null,
        extras: [],
        error: "尚未登录巨量百应直播中控台，请运行 login-buyin.bat"
      });
      log("百应直播中控台尚未登录，等待配置");
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
  const puppeteer = await loadPuppeteer();
  const browser = await launchBrowser(puppeteer, config, config.headless !== false);
  let page = await browser.newPage();
  activePage = page;
  const startupUrl = config.controlPageUrl || config.pageUrl;
  await restoreBrowserSession(page, startupUrl);
  if (!isCompassScreenUrl(page.url())) {
    log("百应页面不是直播大屏专业版，正在从直播中控台自动打开");
    const compassPage = await openCompassScreenFromControl(browser, page, config);
    if (compassPage) {
      await page.close().catch(() => {});
      page = compassPage;
      activePage = page;
      const screenUrl = safePageUrl(page.url());
      config.pageUrl = screenUrl;
      config.controlPageUrl = CONTROL_URL;
      writeJsonAtomic(CONFIG_PATH, {
        ...readJson(CONFIG_PATH, {}),
        pageUrl: screenUrl,
        controlPageUrl: CONTROL_URL,
        screenCapturedAt: nowIso()
      });
      log(`已自动进入百应直播大屏专业版: ${screenUrl}`);
    } else {
      await restoreBrowserSession(page, config.pageUrl);
    }
  }
  capture = installNetworkCapture(page);
  await syncCompassRoom(page, config);
  await ensureCompassFlowAnalysis(page);
  log(`百应采集器已启动 page=${safePageUrl(config.pageUrl)}`);
  let lastPersistAt = 0;
  while (true) {
    const startedAt = Date.now();
    const refreshRequest = readRefreshRequest();
    let result;
    try {
      if (page.isClosed()) throw new Error("百应直播中控台页面已关闭");
      if (isCompassScreenUrl(page.url())) {
        await syncCompassRoom(page, config);
        await ensureCompassFlowAnalysis(page);
      }
      result = await scrapePage(page);
      if (!result.live && !result.extras.length && !result.channels?.items?.length) {
        await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
        await new Promise(resolve => setTimeout(resolve, 2500));
        capture.reset();
        result = await scrapePage(page);
      }
      result.browser = {
        executablePath: resolveBrowser(config),
        profile: resolveUserDataDir(config.userDataDir),
        headless: config.headless !== false
      };
      writeState(config, {
        ...result,
        ...captureRequestFields(refreshRequest, result.status)
      });
      persistAudienceHistory(result);
      if (result.live && Date.now() >= lastPersistAt) {
        await persistBrowserSession(page);
        lastPersistAt = Date.now() + 60000;
      }
      log(
        `百应抓取 ${result.status} 指标=${Object.keys(result.metrics).length} ` +
        `渠道=${result.channels?.items?.length || 0} 补充=${result.extras.length}`
      );
    } catch (error) {
      result = {
        status: "error",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core_buyin_live",
        sourceLabel: "巨量百应直播中控台 · 抓取失败",
        metrics: {},
        missingMetrics: CORE_METRICS,
        channels: null,
        extras: [],
        error: String(error.message || error),
        ...captureRequestFields(refreshRequest, "error")
      };
      writeState(config, result);
      log(`百应抓取失败: ${error.message}`);
      if (/Target closed|Session closed|Browser closed|页面已关闭|Protocol error|detached Frame|Execution context was destroyed/i.test(String(error.message || ""))) {
        throw error;
      }
    }
    if (refreshRequest) clearRefreshRequest(refreshRequest.requestId);
    const interval = Math.max(5000, Number(config.intervalSeconds || 10) * 1000);
    await new Promise(resolve =>
      setTimeout(resolve, Math.max(500, interval - (Date.now() - startedAt)))
    );
  }
}

async function main() {
  ensureDataDir();
  const config = loadConfig();
  const loginMode = process.argv.includes("--login");
  if (!loginMode) {
    const lock = acquireLock();
    if (!lock.acquired) {
      log(`百应采集器已在运行 PID=${lock.owner?.pid || "-"}`);
      return;
    }
  }
  registerCleanup();
  startHeartbeat(config);
  try {
    if (loginMode) {
      await runLogin(config);
      return;
    }
    await runAgent(config);
  } finally {
    try {
      fs.unlinkSync(PAUSE_PATH);
    } catch (error) {
      if (error?.code !== "ENOENT") log(`清理百应登录暂停标记失败: ${error.message}`);
    }
    await closeBrowser();
    stopHeartbeat();
    releaseLock();
  }
}

if (require.main === module) {
  main().catch(error => {
    const config = loadConfig();
    writeState(config, {
      status: "crashed",
      live: false,
      syncedAt: nowIso(),
      source: "puppeteer-core_buyin_live",
      sourceLabel: "巨量百应直播中控台 · 采集器异常",
      metrics: {},
      missingMetrics: CORE_METRICS,
      channels: null,
      extras: [],
      error: String(error.stack || error.message || error)
    });
    console.error(error);
    process.exitCode = 1;
  });
}

module.exports = {
  AUDIENCE_HISTORY_PATH,
  CONFIG_PATH,
  CONTROL_URL,
  CORE_METRICS,
  DEFAULT_CONFIG,
  LOCK_PATH,
  LOGIN_URL,
  REFRESH_REQUEST_PATH,
  STATE_PATH,
  clearRefreshRequest,
  enableBuyinPhoneLogin,
  ensureCompassFlowAnalysis,
  extractLiveScreenRoomId,
  extractBuyinPayload,
  extractChannelsFromSnapshot,
  extractCompassChannels,
  extractMetricsFromSnapshot,
  extractAudienceSummary,
  extractAudienceProfiles,
  finalizeChannels,
  compassScreenUrlForRoom,
  isCompassScreenUrl,
  isBuyinTargetPage,
  loginRequired,
  mergeConfig,
  parseMetricNumber,
  persistAudienceHistory,
  readRefreshRequest
};
