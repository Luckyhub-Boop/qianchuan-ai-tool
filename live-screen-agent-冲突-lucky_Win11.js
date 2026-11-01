"use strict";

const fs = require("node:fs");
const path = require("node:path");

const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, "data");
const CONFIG_PATH = path.join(DATA_DIR, "live-screen.json");
const STATE_PATH = path.join(DATA_DIR, "live-screen-metrics.json");
const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";
const LOGIN_URL = "https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1";
const METRIC_KEYS = ["watchCount", "productClicks", "peakOnline", "gpm"];
const SENSITIVE_QUERY_KEY = /(token|session|cookie|auth|secret|sign|api[_-]?key)/i;

const DEFAULT_CONFIG = {
  enabled: true,
  loginUrl: LOGIN_URL,
  pageUrl: "",
  accountId: "fashion",
  intervalSeconds: 10,
  headless: true,
  executablePath: "",
  userDataDir: "data/chrome-profile",
  serverUrl: DEFAULT_SERVER_URL,
  viewport: { width: 1600, height: 1000, deviceScaleFactor: 1 },
  captureStream: true,
  metrics: {
    watchCount: {
      labels: ["直播间整体观看人数", "累计观看人数", "累计观看", "观看人数", "观看数"],
      selector: ""
    },
    productClicks: {
      labels: ["商品点击次数", "商品点击", "点击次数"],
      selector: ""
    },
    peakOnline: {
      labels: ["峰值在线人数", "最高在线人数", "峰值在线", "最高在线"],
      selector: ""
    },
    gpm: {
      labels: ["千川投放GPM", "整体GPM(元)", "整体GPM", "GPM", "千次观看成交金额", "千次观看成交"],
      selector: ""
    },
    spend: {
      labels: ["整体消耗", "广告消耗", "实时消耗", "消耗"],
      selector: ""
    },
    gmv: {
      labels: ["整体成交金额", "累计成交金额", "直播间成交金额", "成交金额"],
      excludeLabels: ["GPM", "千次观看"],
      selector: ""
    },
    orders: {
      labels: ["整体成交订单数", "整体成单数", "成交订单数", "成交订单", "成交单量"],
      excludeLabels: ["成本", "率"],
      selector: ""
    },
    orderCost: {
      labels: ["整体成交订单成本", "成交订单成本", "订单成本", "转化成本"],
      selector: ""
    },
    roi: {
      labels: ["整体支付ROI", "整体ROI", "支付ROI", "ROI"],
      selector: ""
    },
    online: {
      labels: ["当前在线人数", "实时在线人数", "在线人数"],
      selector: ""
    },
    watchOneMinute: {
      labels: ["观看满1分钟人数", "观看满 1 分钟人数", "1分钟观看人数"],
      selector: ""
    }
  }
};

function nowIso() {
  return new Date().toISOString();
}

function log(message) {
  const line = `[${nowIso()}] ${message}`;
  console.log(line);
}

function ensureDataDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (_) {
    return fallback;
  }
}

function writeJsonAtomic(filePath, value) {
  ensureDataDir();
  const tempPath = `${filePath}.${process.pid}.tmp`;
  fs.writeFileSync(tempPath, JSON.stringify(value, null, 2), "utf8");
  fs.renameSync(tempPath, filePath);
}

function mergeConfig(base, override) {
  const result = { ...base, ...(override || {}) };
  result.metrics = { ...base.metrics };
  for (const [key, value] of Object.entries((override || {}).metrics || {})) {
    result.metrics[key] = { ...(base.metrics[key] || {}), ...(value || {}) };
  }
  result.viewport = { ...base.viewport, ...((override || {}).viewport || {}) };
  return result;
}

function loadConfig() {
  const override = readJson(CONFIG_PATH, {});
  const config = mergeConfig(DEFAULT_CONFIG, override);
  if (process.env.QIANCHUAN_PORT && !override.serverUrl) {
    config.serverUrl = `http://127.0.0.1:${process.env.QIANCHUAN_PORT}`;
  }
  return config;
}

function safePageUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const safeParams = new URLSearchParams();
    for (const [key, value] of parsed.searchParams.entries()) {
      if (!SENSITIVE_QUERY_KEY.test(key)) safeParams.append(key, value);
    }
    const query = safeParams.toString();
    return `${parsed.origin}${parsed.pathname}${query ? `?${query}` : ""}`;
  } catch (_) {
    return "";
  }
}

function isLegacyQianchuanUrl(rawUrl) {
  try {
    return new URL(rawUrl).hostname.toLowerCase() === "qianchuan.jinritemai.com";
  } catch (_) {
    return false;
  }
}

function parseMetricNumber(rawValue) {
  const text = String(rawValue || "")
    .replace(/[,，\s]/g, "")
    .replace(/[¥￥]/g, "");
  const match = text.match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;
  let value = Number(match[0]);
  if (!Number.isFinite(value)) return null;
  const tail = text.slice((match.index || 0) + match[0].length);
  const unit = tail.match(/^(亿|万|w|W|k|K|千|百|%)/);
  if (unit) {
    const symbol = unit[1];
    if (symbol === "亿") value *= 100000000;
    else if (symbol === "万" || symbol === "w" || symbol === "W") value *= 10000;
    else if (symbol === "千" || symbol === "k" || symbol === "K") value *= 1000;
    else if (symbol === "百") value *= 100;
    else if (symbol === "%") value /= 100;
  }
  return Number(value.toFixed(6));
}

function metricCandidates(snapshot, definition) {
  const labels = (definition?.labels || []).map(item => String(item).trim()).filter(Boolean);
  const excluded = (definition?.excludeLabels || [])
    .map(item => String(item).trim().toLowerCase())
    .filter(Boolean);
  const candidates = [];
  for (const label of labels) {
    const lowerLabel = label.toLowerCase();
    (snapshot.lines || []).forEach((line, index) => {
      const lowerLine = String(line).toLowerCase();
      if (!lowerLine.includes(lowerLabel)) return;
      if (excluded.some(item => lowerLine.includes(item))) return;
      const labelAt = lowerLine.indexOf(lowerLabel);
      const after = String(line).slice(labelAt + label.length);
      const before = String(line).slice(0, labelAt);
      const afterValue = parseMetricNumber(after);
      const beforeValue = parseMetricNumber(before);
      if (afterValue !== null) {
        candidates.push({ value: afterValue, score: 100, evidence: line });
      } else if (beforeValue !== null) {
        candidates.push({ value: beforeValue, score: 86, evidence: line });
      } else {
        for (let offset = 1; offset <= 3; offset += 1) {
          const nearby = parseMetricNumber(snapshot.lines[index + offset]);
          if (nearby !== null) {
            candidates.push({
              value: nearby,
              score: 80 - offset * 8,
              evidence: `${line} / ${snapshot.lines[index + offset]}`
            });
            break;
          }
        }
      }
    });
    (snapshot.fragments || []).forEach(fragment => {
      const lowerText = String(fragment.text || "").toLowerCase();
      if (!lowerText.includes(lowerLabel)) return;
      if (excluded.some(item => lowerText.includes(item))) return;
      const labelAt = lowerText.indexOf(lowerLabel);
      const after = String(fragment.text).slice(labelAt + label.length);
      const before = String(fragment.text).slice(0, labelAt);
      const afterValue = parseMetricNumber(after);
      const beforeValue = parseMetricNumber(before);
      if (afterValue !== null) {
        candidates.push({ value: afterValue, score: 94, evidence: fragment.text });
      } else if (beforeValue !== null) {
        candidates.push({ value: beforeValue, score: 82, evidence: fragment.text });
      }
    });
  }
  candidates.sort((left, right) => right.score - left.score);
  return candidates;
}

function extractMetrics(snapshot, metricConfig) {
  const metrics = {};
  const matches = {};
  const missing = [];
  for (const key of Object.keys(metricConfig || {})) {
    const definition = metricConfig[key] || {};
    let candidates = [];
    if (definition.selector) {
      const selected = (snapshot.selected || {})[key];
      const selectedValue = parseMetricNumber(selected);
      if (selectedValue !== null) {
        candidates = [{ value: selectedValue, score: 120, evidence: String(selected) }];
      }
    }
    if (!candidates.length) {
      candidates = metricCandidates(snapshot, definition);
    }
    if (candidates.length) {
      metrics[key] = candidates[0].value;
      matches[key] = {
        evidence: String(candidates[0].evidence || "").slice(0, 220),
        confidence: candidates[0].score
      };
    } else if (METRIC_KEYS.includes(key)) {
      missing.push(key);
    }
  }
  return { metrics, matches, missing };
}

function roomIdFromUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const value = parsed.searchParams.get("live_room_id")
      || parsed.searchParams.get("roomId")
      || parsed.searchParams.get("roomid")
      || "";
    return /^\d{8,}$/.test(value) ? value : "";
  } catch (_) {
    return "";
  }
}

function browserCandidates(config) {
  return [
    config.executablePath,
    process.env.QIANCHUAN_BROWSER_PATH || "",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
}

function resolveBrowser(config) {
  for (const candidate of browserCandidates(config)) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error("未找到 Chrome / Edge。请在 data/live-screen.json 配置 executablePath。");
}

function statePathFor(config) {
  return STATE_PATH;
}

function writeState(config, value) {
  writeJsonAtomic(statePathFor(config), {
    heartbeatAt: nowIso(),
    pid: process.pid,
    accountId: config.accountId || "fashion",
    intervalSeconds: Number(config.intervalSeconds) || 10,
    ...value
  });
}

async function loadPuppeteer() {
  try {
    return require("puppeteer-core");
  } catch (_) {
    throw new Error("缺少 puppeteer-core，请先执行 npm install");
  }
}

async function launchBrowser(puppeteer, config, headless) {
  const executablePath = resolveBrowser(config);
  const userDataDir = path.resolve(ROOT, config.userDataDir || "data/chrome-profile");
  fs.mkdirSync(userDataDir, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath,
    headless: headless ? "new" : false,
    userDataDir,
    defaultViewport: config.viewport,
    args: [
      "--disable-background-timer-throttling",
      "--disable-backgrounding-occluded-windows",
      "--disable-renderer-backgrounding",
      "--disable-features=CalculateNativeWinOcclusion",
      "--no-first-run",
      "--no-default-browser-check",
      "--lang=zh-CN"
    ]
  });
  return { browser, executablePath, userDataDir };
}

async function inspectPage(page, config) {
  return page.evaluate(metricConfig => {
    const styleOf = element => window.getComputedStyle(element);
    const visible = element => {
      if (!(element instanceof Element)) return false;
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const style = styleOf(element);
      return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0;
    };
    const lines = String(document.body?.innerText || "")
      .replace(/\r/g, "")
      .split("\n")
      .map(line => line.trim())
      .filter(Boolean);
    const fragments = [];
    const selected = {};
    for (const [key, definition] of Object.entries(metricConfig || {})) {
      if (definition?.selector) {
        const element = document.querySelector(definition.selector);
        if (element && visible(element)) {
          selected[key] = String(element.textContent || "").trim();
        }
      }
    }
    const elements = document.querySelectorAll(
      "[data-testid], [class*='metric'], [class*='stat'], [class*='card'], section, article, div"
    );
    for (const element of elements) {
      if (!visible(element)) continue;
      const text = String(element.innerText || "").replace(/\s+/g, " ").trim();
      if (!text || text.length > 240) continue;
      const rect = element.getBoundingClientRect();
      fragments.push({ text, area: rect.width * rect.height });
    }
    fragments.sort((left, right) => left.area - right.area);
    return {
      url: location.href,
      title: document.title,
      lines,
      fragments: fragments.slice(0, 1200),
      selected,
      bodyText: String(document.body?.innerText || "").slice(0, 50000)
    };
  }, config.metrics || {});
}

function loginRequired(snapshot) {
  const url = String(snapshot.url || "").toLowerCase();
  const text = String(snapshot.bodyText || "");
  return /(^|\/)login|passport/.test(url) ||
    /扫码登录|登录千川|请登录|立即登录/.test(text);
}

async function clickEbPDetailTab(page, suffix) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await page.evaluate(value => {
        const element = Array.from(document.querySelectorAll("[data-e2e]"))
          .find(candidate => String(candidate.getAttribute("data-e2e") || "").endsWith(value));
        if (!element) return false;
        element.click();
        return true;
      }, suffix);
    } catch (error) {
      if (!/detached Frame|Execution context was destroyed/i.test(String(error.message))) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
  }
  return false;
}

async function waitForEbPDetailReady(page) {
  await page.waitForFunction(() => {
    const text = String(document.body?.innerText || "");
    return text.includes("直播间详情") &&
      Boolean(document.querySelector('[data-e2e*="promotionDataOverview"]'));
  }, { timeout: 60000 });
  await new Promise(resolve => setTimeout(resolve, 6000));
}

async function resolveEbPLiveRoom(page) {
  await page.waitForFunction(() => {
    const text = String(document.body?.innerText || "");
    return text.includes("直播分析") && /ID:\s*\d{8,}/.test(text);
  }, { timeout: 45000 });
  return page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("tr"))
      .map(row => String(row.innerText || "").trim())
      .filter(text => text.includes("直播中") && /ID:\s*\d{8,}/.test(text));
    const row = rows[0] || "";
    const ids = Array.from(row.matchAll(/ID:\s*(\d{8,})/g))
      .map(match => match[1]);
    return {
      status: row ? "直播中" : "",
      roomId: ids[0] || "",
      anchorId: ids[1] || ""
    };
  });
}

async function discoverLiveRoomFromServer(config) {
  const server = String(config.serverUrl || DEFAULT_SERVER_URL).replace(/\/+$/, "");
  const response = await fetch(
    `${server}/api/live/discover?account=${encodeURIComponent(config.accountId || "fashion")}`,
    { signal: AbortSignal.timeout(20000) }
  );
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = await response.json();
  const room = payload.room || {};
  return {
    status: payload.live ? "直播中" : "",
    roomId: String(payload.roomId || room.room_id || room.roomId || ""),
    anchorId: String(room.anchor_id || ""),
    advertiserId: String(payload.advertiserId || ""),
    source: payload.sourceLabel || "千川今日直播间 Open API"
  };
}

function buildLiveBoardEntryUrl(room) {
  const boardUrl = new URL("https://qianchuan.jinritemai.com/board-next");
  boardUrl.searchParams.set("live_room_id", room.roomId);
  boardUrl.searchParams.set("aavid", room.advertiserId);
  boardUrl.searchParams.set("fromModule", "uni_promotion_v2");
  if (room.anchorId) boardUrl.searchParams.set("anchorId", room.anchorId);
  const loginUrl = new URL("https://business.oceanengine.com/check_login");
  loginUrl.searchParams.set("from", boardUrl.href);
  const entryUrl = new URL("https://e.jinritemai.com/account/api/access/logout");
  entryUrl.searchParams.set("passport", "false");
  entryUrl.searchParams.set("next", loginUrl.href);
  return entryUrl.href;
}

async function navigateEbPListToLiveBoard(page, config) {
  const listUrl = new URL(page.url());
  if (!listUrl.pathname.endsWith("/data-analysis/live-analysis/list")) {
    return null;
  }
  let room = await resolveEbPLiveRoom(page);
  if (!room.roomId) {
    try {
      room = await discoverLiveRoomFromServer(config);
    } catch (error) {
      room = {
        status: "",
        roomId: "",
        error: String(error.message || error)
      };
    }
  }
  if (!room.roomId) return null;
  if (!room.advertiserId) {
    room.advertiserId = "1744479430946824";
  }
  await page.goto(buildLiveBoardEntryUrl(room), {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForFunction(() => {
    const text = String(document.body?.innerText || "");
    return text.includes("直播大屏") && text.includes("直播中");
  }, { timeout: 45000 });
  return room;
}

async function scrapeEbPDetail(page, config) {
  const tabs = [
    { name: "直播数据", suffix: "_LIVE_DATA" },
    { name: "流量表现", suffix: "_TRAFFIC_PERFORMANCE" },
    { name: "直播间投放", suffix: "_LIVE_PROMOTION" }
  ];
  const snapshots = [];
  await waitForEbPDetailReady(page);
  for (const tab of tabs) {
    const clicked = await clickEbPDetailTab(page, tab.suffix);
    if (clicked) {
      await new Promise(resolve => setTimeout(resolve, tab.name === "直播数据" ? 5000 : 3500));
    }
    snapshots.push(await inspectPage(page, config));
  }
  const last = snapshots[snapshots.length - 1] || {
    url: page.url(),
    title: "",
    lines: [],
    fragments: [],
    selected: {},
    bodyText: ""
  };
  const aggregate = {
    url: last.url,
    title: last.title,
    lines: snapshots.flatMap(snapshot => snapshot.lines || []),
    fragments: snapshots.flatMap(snapshot => snapshot.fragments || []),
    selected: Object.assign({}, ...snapshots.map(snapshot => snapshot.selected || {})),
    bodyText: snapshots.map(snapshot => snapshot.bodyText || "").join("\n")
  };
  const extracted = extractMetrics(aggregate, config.metrics);
  const roomId = roomIdFromUrl(aggregate.url);
  let status = "ok";
  if (loginRequired(aggregate)) status = "login_required";
  else if (extracted.missing.length === METRIC_KEYS.length) status = "no_metrics";
  else if (extracted.missing.length) status = "partial";
  return {
    status,
    live: status === "ok" || status === "partial",
    syncedAt: nowIso(),
    source: "puppeteer-core",
    sourceLabel: "千川 EBP 直播详情 · 无头 Chrome 抓取",
    pageUrl: safePageUrl(aggregate.url || config.pageUrl),
    pageTitle: String(aggregate.title || "").slice(0, 160),
    room: roomId ? { id: roomId } : {},
    metrics: extracted.metrics,
    matches: extracted.matches,
    missingMetrics: extracted.missing,
    tabs: tabs.map(tab => tab.name),
    error: status === "login_required"
      ? "独立 chrome-profile 登录态无效，请执行 login-live-screen.bat"
      : status === "no_metrics"
        ? "EBP 直播详情已打开，但未识别到观看/点击/峰值/GPM"
        : ""
  };
}

async function scrape(page, config) {
  try {
    const currentUrl = new URL(page.url());
    if (
      currentUrl.hostname === "business.oceanengine.com" &&
      currentUrl.pathname.endsWith("/data-analysis/live-analysis/detail")
    ) {
      return await scrapeEbPDetail(page, config);
    }
  } catch (_) {}
  const snapshot = await inspectPage(page, config);
  const extracted = extractMetrics(snapshot, config.metrics);
  const roomId = roomIdFromUrl(snapshot.url);
  let status = "ok";
  if (loginRequired(snapshot)) status = "login_required";
  else if (extracted.missing.length === METRIC_KEYS.length) status = "no_metrics";
  else if (extracted.missing.length) status = "partial";
  return {
    status,
    live: status === "ok" || status === "partial",
    syncedAt: nowIso(),
    source: "puppeteer-core",
    sourceLabel: "千川直播大屏 · 无头 Chrome 抓取",
    pageUrl: safePageUrl(snapshot.url || config.pageUrl),
    pageTitle: String(snapshot.title || "").slice(0, 160),
    room: roomId ? { id: roomId } : {},
    metrics: extracted.metrics,
    matches: extracted.matches,
    missingMetrics: extracted.missing,
    error: status === "login_required"
      ? "独立 chrome-profile 登录态无效，请执行 login-live-screen.bat"
      : status === "no_metrics"
        ? "页面已打开，但未识别到观看/点击/峰值/GPM，请检查 data/live-screen.json 的 labels 或 selector"
        : ""
  };
}

async function postJson(url, payload, timeoutMs = 5000) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(timeoutMs)
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json().catch(() => ({ ok: true }));
}

function findStreamUrl(value, seen = new Set()) {
  if (!value || typeof value !== "object" || seen.has(value)) return "";
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findStreamUrl(item, seen);
      if (found) return found;
    }
    return "";
  }
  for (const [key, item] of Object.entries(value)) {
    if (key.toLowerCase() === "room_stream_flv_pull_url") {
      const candidate = typeof item === "string"
        ? item
        : item?.Value || item?.value || item?.Url || item?.url || "";
      if (/^https?:\/\/.+\.flv(?:\?|$)/i.test(candidate)) return candidate;
    }
  }
  for (const item of Object.values(value)) {
    const found = findStreamUrl(item, seen);
    if (found) return found;
  }
  return "";
}

function installStreamCapture(page, config, getRoomId) {
  if (!config.captureStream) return;
  let lastUrl = "";
  let lastSentAt = 0;
  const publish = async streamUrl => {
    const roomId = String(getRoomId() || "");
    if (!/^\d{8,}$/.test(roomId) || !streamUrl) return;
    const now = Date.now();
    if (streamUrl === lastUrl && now - lastSentAt < 120000) return;
    lastUrl = streamUrl;
    lastSentAt = now;
    try {
      await postJson(`${String(config.serverUrl || DEFAULT_SERVER_URL).replace(/\/+$/, "")}/api/live/stream`, {
        roomId,
        url: streamUrl,
        type: "flv",
        source: "qianchuan-headless"
      });
      log(`已同步直播画面流 room=${roomId}`);
    } catch (error) {
      log(`直播画面流同步失败: ${error.message}`);
    }
  };
  page.on("response", response => {
    const url = response.url();
    if (/\.flv(?:\?|$)/i.test(url)) {
      publish(url).catch(() => {});
      return;
    }
    const contentType = String(response.headers()["content-type"] || "");
    if (!contentType.includes("json")) return;
    response.text()
      .then(body => {
        if (!body.includes("room_stream_flv_pull_url")) return;
        const streamUrl = findStreamUrl(JSON.parse(body));
        if (streamUrl) return publish(streamUrl);
      })
      .catch(() => {});
  });
}

async function runLogin(config) {
  const puppeteer = await loadPuppeteer();
  const launched = await launchBrowser(puppeteer, config, false);
  const page = await launched.browser.newPage();
  const loginUrl = config.loginUrl || LOGIN_URL;
  await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  log("已打开新版千川 EBP。请完成登录并进入直播大屏；检测到 live_room_id 或大屏指标后会自动保存登录态和地址。");
  const deadline = Date.now() + 20 * 60 * 1000;
  while (Date.now() < deadline) {
    const pages = await launched.browser.pages();
    for (const current of pages) {
      const currentUrl = current.url();
      let pageSnapshot = null;
      if (!/^\d{8,}$/.test(roomIdFromUrl(currentUrl))) {
        try {
          pageSnapshot = await inspectPage(current, config);
        } catch (_) {
          continue;
        }
      }
      const bodyText = String(pageSnapshot?.bodyText || "");
      const liveScreenSignals = ["累计观看", "商品点击", "峰值在线", "GPM"]
        .filter(label => bodyText.includes(label)).length;
      const hasRoomId = /^\d{8,}$/.test(roomIdFromUrl(currentUrl));
      if (!hasRoomId && liveScreenSignals < 2) continue;
      const nextConfig = {
        ...readJson(CONFIG_PATH, {}),
        enabled: true,
        loginUrl,
        pageUrl: safePageUrl(currentUrl),
        executablePath: config.executablePath || launched.executablePath,
        userDataDir: config.userDataDir
      };
      writeJsonAtomic(CONFIG_PATH, nextConfig);
      writeState(config, {
        status: "login_saved",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "直播大屏登录态已保存",
        pageUrl: nextConfig.pageUrl,
        room: { id: roomIdFromUrl(currentUrl) || "" },
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: ""
      });
      log(`已保存直播大屏地址: ${nextConfig.pageUrl}`);
      await new Promise(resolve => setTimeout(resolve, 8000));
      await launched.browser.close();
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  await launched.browser.close();
  throw new Error("20 分钟内未检测到直播大屏：地址需包含 live_room_id，或页面出现累计观看/商品点击/峰值在线/GPM");
}

async function runAgent(config) {
  if (!config.enabled) {
    log("直播大屏采集已停用");
    while (true) {
      const refreshed = loadConfig();
      if (refreshed.enabled) return runAgent(refreshed);
      writeState(config, {
        status: "disabled",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "直播大屏双通道已停用",
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: ""
      });
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
  if (!config.pageUrl) {
    log("缺少直播大屏地址，等待 login-live-screen.bat 完成首次登录");
    while (true) {
      const refreshed = loadConfig();
      if (refreshed.enabled && refreshed.pageUrl) return runAgent(refreshed);
      writeState(config, {
        status: "config_required",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "等待配置直播大屏",
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: "首次使用请运行 login-live-screen.bat，登录并打开直播大屏"
      });
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
  if (isLegacyQianchuanUrl(config.pageUrl)) {
    log("检测到旧版千川直播地址，等待重新登录新版 EBP");
    while (true) {
      const refreshed = loadConfig();
      if (refreshed.enabled && refreshed.pageUrl && !isLegacyQianchuanUrl(refreshed.pageUrl)) {
        return runAgent(refreshed);
      }
      writeState(config, {
        status: "config_required",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "旧版直播地址已停用",
        pageUrl: config.pageUrl,
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: "旧版千川直播地址已停用，请运行 login-live-screen.bat 重新进入新版直播大屏"
      });
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }

  const puppeteer = await loadPuppeteer();
  const launched = await launchBrowser(puppeteer, config, config.headless !== false);
  const page = await launched.browser.newPage();
  let currentRoomId = roomIdFromUrl(config.pageUrl);
  installStreamCapture(page, config, () => currentRoomId || roomIdFromUrl(page.url()));
  await page.goto(config.pageUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  log(`采集器已启动 browser=${launched.executablePath} profile=${launched.userDataDir}`);

  let nextNavigationAt = 0;
  const previousState = readJson(STATE_PATH, {});
  let lastUsableState = previousState?.live && previousState?.metrics
    ? previousState
    : null;
  let cycleCount = 0;
  let peakRoomId = "";
  let observedPeak = 0;
  let observedPeakAt = "";
  while (true) {
    const startedAt = Date.now();
    try {
      if (page.isClosed()) throw new Error("页面已关闭");
      const configuredUrl = new URL(config.pageUrl);
      if (
        configuredUrl.pathname.endsWith("/data-analysis/live-analysis/list") &&
        page.url().includes("/data-analysis/live-analysis/list")
      ) {
        const room = await navigateEbPListToLiveBoard(page, config);
        if (room?.roomId) currentRoomId = room.roomId;
      } else if (
        configuredUrl.pathname.endsWith("/data-analysis/live-analysis/list") &&
        cycleCount > 0 &&
        cycleCount % 6 === 0
      ) {
        await page.goto(config.pageUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
        const room = await navigateEbPListToLiveBoard(page, config);
        if (room?.roomId) currentRoomId = room.roomId;
      }
      if (Date.now() >= nextNavigationAt) {
        const currentUrl = page.url();
        if (!currentUrl || currentUrl === "about:blank") {
          await page.goto(config.pageUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
        }
      }
      currentRoomId = roomIdFromUrl(page.url()) || currentRoomId;
      const result = await scrape(page, config);
      result.room = { ...(result.room || {}), id: currentRoomId || result.room?.id || "" };
      const resultRoomId = String(result.room.id || currentRoomId || "");
      if (resultRoomId !== peakRoomId) {
        peakRoomId = resultRoomId;
        observedPeak = 0;
        observedPeakAt = "";
      }
      const online = Number(result.metrics?.online);
      if (Number.isFinite(online) && online > observedPeak) {
        observedPeak = online;
        observedPeakAt = nowIso();
      }
      if (result.metrics && result.metrics.peakOnline == null && observedPeak > 0) {
        result.metrics.peakOnline = observedPeak;
        result.matches = {
          ...(result.matches || {}),
          peakOnline: {
            evidence: `实时在线人数最高观测 ${observedPeak}`,
            confidence: 60,
            source: "observed_since_capture"
          }
        };
        result.peakOnlineSource = "observed_since_capture";
        result.peakObservedAt = observedPeakAt;
        result.missingMetrics = METRIC_KEYS.filter(
          key => result.metrics[key] == null
        );
        if (!result.missingMetrics.length && result.status === "partial") {
          result.status = "ok";
        }
      }
      result.browser = {
        executablePath: launched.executablePath,
        profile: launched.userDataDir,
        headless: config.headless !== false
      };
      if (result.status === "login_required") nextNavigationAt = Date.now() + 60000;
      if (result.status === "no_metrics") nextNavigationAt = Date.now() + 30000;
      if (Object.keys(result.metrics || {}).length) {
        lastUsableState = result;
        writeState(config, result);
      } else if (lastUsableState) {
        writeState(config, {
          ...lastUsableState,
          status: "stale",
          staleWarning: "EBP 本轮未返回完整指标，保留上一次有效值"
        });
      } else {
        writeState(config, result);
      }
      log(
        `抓取 ${result.status} room=${currentRoomId || "-"} ` +
        `missing=${result.missingMetrics.join(",") || "-"}`
      );
      cycleCount += 1;
    } catch (error) {
      const errorMessage = String(error.message || error);
      if (/detached Frame|Execution context was destroyed/i.test(errorMessage)) {
        try {
          await page.goto(config.pageUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
        } catch (_) {}
      }
      if (lastUsableState) {
        log("本轮未取得新指标，保留上一次有效采集值");
        writeState(config, {
          ...lastUsableState,
          status: "stale",
          staleWarning: errorMessage
        });
      } else {
        writeState(config, {
          status: "error",
          live: false,
          syncedAt: nowIso(),
          source: "puppeteer-core",
          sourceLabel: "千川直播大屏 · 无头 Chrome 抓取",
          pageUrl: safePageUrl((() => { try { return page.url(); } catch (_) { return config.pageUrl; } })()),
          room: currentRoomId ? { id: currentRoomId } : {},
          metrics: {},
          missingMetrics: METRIC_KEYS,
          error: errorMessage
        });
      }
      log(`抓取失败: ${error.message}`);
      if (/Target closed|Session closed|Browser closed|页面已关闭|Protocol error/.test(String(error.message))) {
        throw error;
      }
    }
    const interval = Math.max(3000, Number(config.intervalSeconds || 10) * 1000);
    const remaining = Math.max(500, interval - (Date.now() - startedAt));
    await new Promise(resolve => setTimeout(resolve, remaining));
  }
}

async function main() {
  ensureDataDir();
  const config = loadConfig();
  if (process.argv.includes("--login")) {
    await runLogin(config);
    return;
  }
  await runAgent(config);
}

if (require.main === module) {
  main().catch(error => {
    const config = loadConfig();
    writeState(config, {
      status: "crashed",
      live: false,
      syncedAt: nowIso(),
      source: "puppeteer-core",
      sourceLabel: "千川直播大屏 · 无头 Chrome 抓取",
      metrics: {},
      missingMetrics: METRIC_KEYS,
      error: String(error.stack || error.message || error)
    });
    console.error(error);
    process.exitCode = 1;
  });
}

module.exports = {
  DEFAULT_CONFIG,
  LOGIN_URL,
  extractMetrics,
  findStreamUrl,
  inspectPage,
  isLegacyQianchuanUrl,
  mergeConfig,
  parseMetricNumber,
  roomIdFromUrl,
  safePageUrl
};
