"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, "data");
const CONFIG_PATH = path.join(DATA_DIR, "live-screen.json");
const STATE_PATH = path.join(DATA_DIR, "live-screen-metrics.json");
const SESSION_STATE_PATH = path.join(DATA_DIR, "live-screen-session.json");
const AGENT_LOCK_PATH = path.join(DATA_DIR, "live-screen-agent.lock");
const TAKEOVER_PATH = path.join(DATA_DIR, "live-screen-takeover.json");
const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";
const SCREEN_HEARTBEAT_INTERVAL_MS = 5000;
const LOGIN_URL = "https://business.oceanengine.com/ebp/account-manage/ecp/bidding/universe/account?ebpid=1855365007750474&uuid=6f018086-b594-462c-8733-5c8f75c443a1";
const TRADE_METRIC_KEYS = ["spend", "gmv", "orders", "orderCost", "roi"];
const BEHAVIOR_METRIC_KEYS = ["watchCount", "productClicks", "peakOnline", "gpm", "online"];
const METRIC_KEYS = [...TRADE_METRIC_KEYS, ...BEHAVIOR_METRIC_KEYS];
const BROWSER_LAUNCH_ARGS = [
  // Edge 155 on Windows can crash its GPU subprocess in headless mode.
  "--no-sandbox",
  "--disable-gpu",
  "--disable-gpu-sandbox",
  "--disable-background-timer-throttling",
  "--disable-backgrounding-occluded-windows",
  "--disable-renderer-backgrounding",
  "--disable-features=CalculateNativeWinOcclusion",
  "--no-first-run",
  "--no-default-browser-check",
  "--lang=zh-CN"
];
const SENSITIVE_QUERY_KEY = /(token|session|cookie|auth|secret|sign|api[_-]?key)/i;
const PROFILE_LOCK_FILES = [
  "SingletonLock",
  "SingletonSocket",
  "SingletonCookie",
  "DevToolsActivePort",
  "DevToolsActivePort-*",
  "lockfile"
];
const LIVE_SCREEN_METRIC_SIGNALS = [
  "累计观看",
  "商品点击",
  "峰值",
  "GPM",
  "消耗",
  "成交"
];
let activeAgentLockPath = "";
let activeBrowser = null;
let activePage = null;
let activeProfileDir = "";
let stateHeartbeatTimer = null;
let heartbeatConfig = null;
let lastPublishedState = null;
let heartbeatTickCount = 0;
let cleanupHandlersRegistered = false;
let shutdownInProgress = false;
let takeoverTimer = null;
const FLOW_LABELS = {
  "千川PC": "live_pc_qian_chuan",
  "千川 PC": "live_pc_qian_chuan",
  "随心推": "live_xiao_dian_qian_chuan",
  "直播推荐": "homepage_hot",
  "推荐Feed": "homepage_hot",
  "搜索": "general_search",
  "短视频引流": "video_to_live",
  "短视频及图文引流": "video_to_live",
  "关注": "homepage_follow",
  "同城": "homepage_fresh",
  "直播广场": "live_merge",
  "抖音商城": "douyin_shopping_center",
  "商城": "douyin_shopping_center",
  "头条西瓜": "touxi_saas",
  "其他": "ecom_other"
};

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
    spend: {
      labels: ["整体消耗(元)", "整体消耗", "千川消耗", "广告消耗", "投放消耗", "今日消耗", "消耗金额", "消耗"],
      selector: ""
    },
    gmv: {
      labels: ["净成交金额(元)", "净成交金额", "用户实际支付金额", "成交金额", "支付金额", "成交额", "GMV"],
      selector: ""
    },
    orders: {
      labels: ["整体成交订单数", "成交订单数", "支付订单数", "成交订单", "订单量", "订单数"],
      selector: ""
    },
    orderCost: {
      labels: ["整体成交订单成本(元)", "整体成交订单成本", "成交订单成本", "支付订单成本", "订单成本"],
      selector: ""
    },
    roi: {
      labels: ["净成交ROI", "整体支付ROI", "支付ROI", "整体ROI", "ROI"],
      selector: ""
    },
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
      labels: ["整体GPM(元)", "千川投放GPM", "整体GPM", "GPM(元)", "GPM", "千次观看成交金额", "千次观看成交"],
      selector: ""
    },
    exposure: {
      labels: ["直播间整体曝光次数", "整体曝光次数", "直播间曝光人数", "累计曝光人数", "曝光人数", "曝光量", "曝光"],
      selector: ""
    },
    online: {
      labels: ["当前在线人数", "实时在线人数", "在线人数"],
      selector: ""
    },
    watchOneMinute: {
      labels: ["观看满1分钟人数", "观看满 1 分钟人数", "1分钟观看人数"],
      selector: ""
    },
    comments: {
      labels: ["累计评论次数", "评论次数", "累计评论", "评论数"],
      selector: ""
    },
    follows: {
      labels: ["新增关注人数", "新增关注", "关注人数"],
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

function pidIsRunning(pid) {
  const parsed = Number(pid);
  if (!Number.isInteger(parsed) || parsed <= 0) return false;
  try {
    process.kill(parsed, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

function terminateProcessTree(pid) {
  const parsed = Number(pid);
  if (!Number.isInteger(parsed) || parsed <= 0 || parsed === process.pid) return;
  if (process.platform === "win32") {
    const result = spawnSync(
      "taskkill.exe",
      ["/PID", String(parsed), "/T", "/F"],
      { windowsHide: true, encoding: "utf8", timeout: 15000 }
    );
    if (result.status !== 0 && pidIsRunning(parsed)) {
      log(`接管登录时结束旧采集器失败 PID=${parsed}: ${String(result.stderr || "").trim()}`);
    }
    return;
  }
  try {
    process.kill(parsed, "SIGTERM");
  } catch (error) {
    if (error?.code !== "ESRCH") throw error;
  }
}

function readAgentLock(lockPath = AGENT_LOCK_PATH) {
  try {
    const payload = JSON.parse(fs.readFileSync(lockPath, "utf8"));
    return payload && typeof payload === "object" ? payload : null;
  } catch (_) {
    return null;
  }
}

function releaseAgentLock(lockPath = activeAgentLockPath) {
  if (!lockPath) return;
  const lock = readAgentLock(lockPath);
  if (lock && Number(lock.pid) !== process.pid && pidIsRunning(lock.pid)) return;
  try {
    fs.unlinkSync(lockPath);
  } catch (error) {
    if (error?.code !== "ENOENT") log(`清理采集器锁失败: ${error.message}`);
  }
  if (activeAgentLockPath === lockPath) activeAgentLockPath = "";
}

function registerAgentCleanup() {
  if (cleanupHandlersRegistered) return;
  cleanupHandlersRegistered = true;
  const cleanup = () => releaseAgentLock();
  process.once("exit", cleanup);
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    process.once(signal, () => {
      if (shutdownInProgress) return;
      shutdownInProgress = true;
      void (async () => {
        if (activePage && lastPublishedState?.live) {
          await persistBrowserSession(activePage);
        }
        await closeActiveBrowser();
        if (activeProfileDir) {
          cleanupBrowserProfileState(activeProfileDir, { terminateOrphans: true });
        }
        stopStateHeartbeat();
        cleanup();
        process.exit(0);
      })();
    });
  }
}

function startTakeoverWatcher() {
  if (takeoverTimer) return;
  takeoverTimer = setInterval(() => {
    if (shutdownInProgress) return;
    const request = readJson(TAKEOVER_PATH, {});
    if (!request?.pid || Number(request.pid) === process.pid) return;
    shutdownInProgress = true;
    log(`收到登录模式接管请求 PID=${request.pid}，正在释放浏览器与单实例锁`);
    void (async () => {
      try {
        if (activePage && lastPublishedState?.live) {
          await persistBrowserSession(activePage);
        }
        await closeActiveBrowser();
        if (activeProfileDir) {
          cleanupBrowserProfileState(activeProfileDir, { terminateOrphans: true });
        }
        stopStateHeartbeat();
        releaseAgentLock();
      } finally {
        process.exit(0);
      }
    })();
  }, 500);
}

async function closeActiveBrowser() {
  const browser = activeBrowser;
  activeBrowser = null;
  activePage = null;
  if (!browser) return;
  let timer = null;
  try {
    await Promise.race([
      browser.close(),
      new Promise(resolve => {
        timer = setTimeout(resolve, 8000);
      })
    ]);
  } catch (_) {
    // The watchdog will terminate any browser child that outlives a crashed agent.
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function acquireAgentLock(options = {}) {
  const lockPath = options.lockPath || AGENT_LOCK_PATH;
  const mode = options.mode || "agent";
  fs.mkdirSync(path.dirname(lockPath), { recursive: true });
  const payload = {
    pid: process.pid,
    mode,
    startedAt: nowIso(),
    userDataDir: options.userDataDir || ""
  };

  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const fd = fs.openSync(lockPath, "wx");
      fs.writeFileSync(fd, JSON.stringify(payload, null, 2), "utf8");
      fs.closeSync(fd);
      activeAgentLockPath = lockPath;
      registerAgentCleanup();
      return { acquired: true, ...payload };
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      const existing = readAgentLock(lockPath);
      if (existing && pidIsRunning(existing.pid)) {
        return { acquired: false, owner: existing };
      }
      try {
        fs.unlinkSync(lockPath);
      } catch (unlinkError) {
        if (unlinkError?.code !== "ENOENT") throw unlinkError;
      }
    }
  }
  return { acquired: false, owner: readAgentLock(lockPath) };
}

function stopProfileBrowsers(userDataDir) {
  if (process.platform !== "win32") return;
  const script = [
    "$profile=$env:QIANCHUAN_PROFILE_PATH;",
    "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR Name='chrome.exe'\" -ErrorAction SilentlyContinue |",
    "Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profile) } |",
    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
  ].join(" ");
  const result = spawnSync(
    "powershell.exe",
    ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
    {
      env: { ...process.env, QIANCHUAN_PROFILE_PATH: userDataDir },
      windowsHide: true,
      timeout: 12000
    }
  );
  if (result.error) log(`清理占用 chrome-profile 的浏览器失败: ${result.error.message}`);
}

function cleanupBrowserProfileState(userDataDir, options = {}) {
  const terminateOrphans = options.terminateOrphans === true;
  if (terminateOrphans) stopProfileBrowsers(userDataDir);
  const directories = [userDataDir, path.join(userDataDir, "Default")];
  const removed = [];
  for (const directory of directories) {
    if (!fs.existsSync(directory)) continue;
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const matched = PROFILE_LOCK_FILES.some(pattern =>
        pattern.endsWith("*")
          ? entry.name.startsWith(pattern.slice(0, -1))
          : entry.name === pattern
      );
      if (!matched) continue;
      const target = path.join(directory, entry.name);
      try {
        fs.rmSync(target, { force: true, recursive: entry.isDirectory() });
        removed.push(target);
      } catch (error) {
        log(`清理浏览器残留锁失败 ${target}: ${error.message}`);
      }
    }
  }
  if (removed.length) log(`已清理浏览器残留锁 ${removed.length} 个`);
  return removed;
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

async function persistBrowserSession(page) {
  if (!page || page.isClosed()) return;
  try {
    const cookies = await page.cookies(
      "https://business.oceanengine.com",
      "https://qianchuan.jinritemai.com"
    );
    const storage = await page.evaluate(() => {
      const read = source => Object.fromEntries(
        Array.from({ length: source.length }, (_, index) => {
          const key = source.key(index);
          return [key, source.getItem(key)];
        })
      );
      return {
        origin: location.origin,
        localStorage: read(localStorage),
        sessionStorage: read(sessionStorage)
      };
    });
    writeJsonAtomic(SESSION_STATE_PATH, {
      schema: 1,
      savedAt: nowIso(),
      cookies,
      storage
    });
  } catch (error) {
    log(`保存自动登录状态失败: ${error.message}`);
  }
}

async function restoreBrowserSession(page, targetUrl) {
  const saved = readJson(SESSION_STATE_PATH, {});
  if (Array.isArray(saved.cookies) && saved.cookies.length) {
    try {
      await page.setCookie(...saved.cookies);
      log(`已恢复自动登录 Cookie ${saved.cookies.length} 项`);
    } catch (error) {
      log(`恢复自动登录 Cookie 失败: ${error.message}`);
    }
  }
  await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  const persisted = saved.storage;
  if (persisted?.origin) {
    try {
      if (page.url().startsWith(persisted.origin)) {
        await page.evaluate(value => {
          for (const [key, item] of Object.entries(value.localStorage || {})) {
            localStorage.setItem(key, String(item));
          }
          for (const [key, item] of Object.entries(value.sessionStorage || {})) {
            sessionStorage.setItem(key, String(item));
          }
        }, persisted);
        await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
        log("已恢复自动登录页面存储");
      }
    } catch (error) {
      log(`恢复自动登录页面存储失败: ${error.message}`);
    }
  }
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
    const parsed = new URL(rawUrl);
    if (parsed.hostname.toLowerCase() !== "qianchuan.jinritemai.com") {
      return false;
    }
    // The current EBP live-room entry signs in on business.oceanengine.com and
    // then SSOs to this board-next page. board-next is the live-screen target,
    // not a legacy uni-prom page, as long as it carries a concrete roomId.
    if (roomIdFromUrl(parsed.href)) {
      return false;
    }
    return true;
  } catch (_) {
    return true;
  }
}

function isConfiguredLiveScreenUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const hostname = parsed.hostname.toLowerCase();
    const roomId = roomIdFromUrl(parsed.href);
    if (
      hostname === "qianchuan.jinritemai.com" &&
      (parsed.pathname === "/board-next" || parsed.pathname.endsWith("/board-next")) &&
      roomId
    ) {
      return true;
    }
    return hostname === "business.oceanengine.com" &&
      (
        parsed.pathname.endsWith("/data-analysis/live-analysis/detail") ||
        parsed.pathname.endsWith("/data-analysis/live-analysis/list")
      );
  } catch (_) {
    return false;
  }
}

function liveScreenMetricSignalCount(snapshot) {
  const bodyText = String(snapshot?.bodyText || "");
  return LIVE_SCREEN_METRIC_SIGNALS.filter(label => bodyText.includes(label)).length;
}

function hasLiveScreenEvidence(snapshot, rawUrl = "") {
  const pageUrl = rawUrl || snapshot?.url || "";
  if (/^\d{8,}$/.test(roomIdFromUrl(pageUrl))) return true;
  return liveScreenMetricSignalCount(snapshot) >= 2;
}

function isLiveScreenPage(snapshot, rawUrl = "") {
  const pageUrl = rawUrl || snapshot?.url || "";
  return isConfiguredLiveScreenUrl(pageUrl) && hasLiveScreenEvidence(snapshot, pageUrl);
}

function isLoginCompletePage(snapshot, rawUrl = "") {
  const pageUrl = rawUrl || snapshot?.url || "";
  if (!isConfiguredLiveScreenUrl(pageUrl)) return false;
  if (roomIdFromUrl(pageUrl)) return true;
  try {
    const parsed = new URL(pageUrl);
    return parsed.hostname === "business.oceanengine.com" &&
      parsed.pathname.endsWith("/data-analysis/live-analysis/detail") &&
      liveScreenMetricSignalCount(snapshot) >= 2;
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

function metricCandidates(snapshot, definition, metricKey = "") {
  const labels = (definition?.labels || []).map(item => String(item).trim()).filter(Boolean);
  const candidates = [];
  const countLike = new Set([
    "spend",
    "gmv",
    "orders",
    "orderCost",
    "watchCount",
    "productClicks",
    "peakOnline",
    "exposure",
    "online",
    "watchOneMinute",
    "comments",
    "follows"
  ]);
  const hasLabelBoundary = (text, labelAt, label) => {
    const after = String(text).slice(labelAt + label.length).trimStart();
    if (!after) return true;
    if (/^[0-9:：¥￥,.\-+]/.test(after)) return true;
    return label.length > 4 || !/[\u3400-\u9fff]/.test(after[0]);
  };
  for (const label of labels) {
    const lowerLabel = label.toLowerCase();
    (snapshot.lines || []).forEach((line, index) => {
      const lowerLine = String(line).toLowerCase();
      if (!lowerLine.includes(lowerLabel)) return;
      const labelAt = lowerLine.indexOf(lowerLabel);
      if (!hasLabelBoundary(line, labelAt, label)) return;
      const after = String(line).slice(labelAt + label.length);
      const before = String(line).slice(0, labelAt);
      const afterValue = parseMetricNumber(after);
      const beforeValue = parseMetricNumber(before);
      if (afterValue !== null) {
        candidates.push({ value: afterValue, score: 100, evidence: line });
      } else if (!countLike.has(metricKey) && beforeValue !== null) {
        candidates.push({ value: beforeValue, score: 86, evidence: line });
      } else if (line.trim().length <= label.length + 8) {
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
      const labelAt = lowerText.indexOf(lowerLabel);
      if (!hasLabelBoundary(fragment.text, labelAt, label)) return;
      const after = String(fragment.text).slice(labelAt + label.length);
      const before = String(fragment.text).slice(0, labelAt);
      const afterValue = parseMetricNumber(after);
      const beforeValue = parseMetricNumber(before);
      if (afterValue !== null) {
        candidates.push({ value: afterValue, score: 94, evidence: fragment.text });
      } else if (!countLike.has(metricKey) && beforeValue !== null) {
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
      candidates = metricCandidates(snapshot, definition, key);
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

function extractFlows(snapshot) {
  const items = new Map();
  const sources = [
    ...(snapshot.lines || []),
    ...(snapshot.fragments || []).map(fragment => fragment.text || "")
  ];
  for (const raw of sources) {
    const text = String(raw || "").replace(/\s+/g, " ").trim();
    if (!text || text.length > 160) continue;
    for (const [label, key] of Object.entries(FLOW_LABELS)) {
      if (!text.includes(label)) continue;
      const labelAt = text.indexOf(label);
      const after = text.slice(labelAt + label.length);
      const before = text.slice(0, labelAt);
      const percentMatch = after.match(/(\d+(?:\.\d+)?)\s*%/);
      const beforePercentMatch = before.match(/(\d+(?:\.\d+)?)\s*%\s*$/);
      const value = percentMatch
        ? Number(percentMatch[1])
        : beforePercentMatch
          ? Number(beforePercentMatch[1])
          : parseMetricNumber(after);
      if (!Number.isFinite(value) || value <= 0) continue;
      const item = {
        key,
        label,
        value: Number(value.toFixed(4)),
        unit: percentMatch || beforePercentMatch ? "percent" : "count",
        evidence: text.slice(0, 180)
      };
      const previous = items.get(key);
      if (!previous || item.unit === "percent" || item.value > previous.value) {
        items.set(key, item);
      }
    }
  }
  return {
    items: Array.from(items.values()),
    source: "screen_text"
  };
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

function replaceRoomIdInUrl(rawUrl, roomId) {
  try {
    const parsed = new URL(rawUrl);
    if (parsed.searchParams.has("live_room_id")) {
      parsed.searchParams.set("live_room_id", roomId);
    } else {
      parsed.searchParams.set("roomId", roomId);
    }
    return safePageUrl(parsed.href);
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
  const payload = {
    ...value,
    heartbeatAt: nowIso(),
    pid: process.pid,
    accountId: config.accountId || "fashion",
    intervalSeconds: Number(config.intervalSeconds) || 10
  };
  lastPublishedState = payload;
  writeJsonAtomic(statePathFor(config), payload);
}

function startStateHeartbeat(config) {
  heartbeatConfig = config;
  if (stateHeartbeatTimer) return;
  stateHeartbeatTimer = setInterval(() => {
    if (!heartbeatConfig || !lastPublishedState) return;
    try {
      writeState(heartbeatConfig, {
        ...lastPublishedState,
        heartbeatOnly: true
      });
      heartbeatTickCount += 1;
      if (heartbeatTickCount === 1) log("采集器心跳保活已启动");
    } catch (error) {
      log(`采集器心跳写入失败: ${error.message}`);
    }
  }, SCREEN_HEARTBEAT_INTERVAL_MS);
}

function stopStateHeartbeat() {
  if (!stateHeartbeatTimer) return;
  clearInterval(stateHeartbeatTimer);
  stateHeartbeatTimer = null;
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
  activeProfileDir = userDataDir;
  fs.mkdirSync(userDataDir, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath,
    headless: headless ? "new" : false,
    userDataDir,
    defaultViewport: config.viewport,
    args: BROWSER_LAUNCH_ARGS
  });
  activeBrowser = browser;
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
  return /(^|\/)(login|check_login)|passport/.test(url) ||
    /扫码登录|登录千川|请登录|立即登录/.test(text);
}

async function clickEbPDetailTab(page, suffix, name) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await page.evaluate((tabSuffix, tabName) => {
        const byDataE2E = Array.from(document.querySelectorAll("[data-e2e]"))
          .find(candidate => String(candidate.getAttribute("data-e2e") || "").endsWith(tabSuffix));
        const element = byDataE2E || Array.from(
          document.querySelectorAll('[role="tab"], button, [class*="tab"]')
        ).find(candidate => {
          const text = String(candidate.textContent || "").replace(/\s+/g, "").trim();
          return text === String(tabName || "").replace(/\s+/g, "");
        });
        if (!element) return false;
        element.click();
        return true;
      }, suffix, name);
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
    return (
      text.includes("直播间详情") ||
      text.includes("直播详情") ||
      text.includes("直播分析")
    ) &&
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

function buildLiveBoardUrl(room) {
  const boardUrl = new URL("https://qianchuan.jinritemai.com/board-next");
  boardUrl.searchParams.set("live_room_id", room.roomId);
  boardUrl.searchParams.set("aavid", room.advertiserId);
  boardUrl.searchParams.set("fromModule", "uni_promotion_v2");
  if (room.anchorId) boardUrl.searchParams.set("anchorId", room.anchorId);
  return boardUrl.href;
}

function buildLiveBoardEntryUrl(room) {
  const boardUrl = buildLiveBoardUrl(room);
  const loginUrl = new URL("https://business.oceanengine.com/check_login");
  loginUrl.searchParams.set("from", boardUrl);
  const entryUrl = new URL("https://e.jinritemai.com/account/api/access/logout");
  entryUrl.searchParams.set("passport", "false");
  entryUrl.searchParams.set("next", loginUrl.href);
  return entryUrl.href;
}

function buildLoginPageUrl(targetUrl) {
  const loginUrl = new URL("https://business.oceanengine.com/login");
  loginUrl.searchParams.set("from", targetUrl);
  loginUrl.searchParams.set("sso", "1");
  loginUrl.searchParams.set("ssoDomain", "sso.oceanengine.com");
  return loginUrl.href;
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

async function recoverLiveBoardSession(page, config) {
  const room = await discoverLiveRoomFromServer(config);
  if (!room.roomId) return null;
  await page.goto(buildLiveBoardEntryUrl(room), {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await new Promise(resolve => setTimeout(resolve, 3500));
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
    const clicked = await clickEbPDetailTab(page, tab.suffix, tab.name);
    if (clicked) {
      await new Promise(resolve => setTimeout(resolve, tab.name === "直播数据" ? 5000 : 3500));
    }
    const snapshot = await inspectPage(page, config);
    snapshots.push(snapshot);
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
  const flows = extractFlows(aggregate);
  const missingTradeMetrics = TRADE_METRIC_KEYS.filter(key => extracted.metrics[key] == null);
  const missingBehaviorMetrics = BEHAVIOR_METRIC_KEYS.filter(key => extracted.metrics[key] == null);
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
    tradeMetrics: Object.fromEntries(
      TRADE_METRIC_KEYS
        .filter(key => extracted.metrics[key] != null)
        .map(key => [key, extracted.metrics[key]])
    ),
    missingTradeMetrics,
    behaviorMetrics: Object.fromEntries(
      BEHAVIOR_METRIC_KEYS
        .filter(key => extracted.metrics[key] != null)
        .map(key => [key, extracted.metrics[key]])
    ),
    missingBehaviorMetrics,
    flows: flows.items,
    tabs: tabs.map(tab => tab.name),
    error: status === "login_required"
      ? "登录已过期，正在使用持久化登录态自动恢复；持续失败再运行 login-live-screen.bat"
      : status === "no_metrics"
        ? "EBP 直播详情已打开，但未识别到大屏指标"
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
  const flows = extractFlows(snapshot);
  const missingTradeMetrics = TRADE_METRIC_KEYS.filter(key => extracted.metrics[key] == null);
  const missingBehaviorMetrics = BEHAVIOR_METRIC_KEYS.filter(key => extracted.metrics[key] == null);
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
    tradeMetrics: Object.fromEntries(
      TRADE_METRIC_KEYS
        .filter(key => extracted.metrics[key] != null)
        .map(key => [key, extracted.metrics[key]])
    ),
    missingTradeMetrics,
    behaviorMetrics: Object.fromEntries(
      BEHAVIOR_METRIC_KEYS
        .filter(key => extracted.metrics[key] != null)
        .map(key => [key, extracted.metrics[key]])
    ),
    missingBehaviorMetrics,
    flows: flows.items,
    error: status === "login_required"
      ? "登录已过期，正在使用持久化登录态自动恢复；持续失败再运行 login-live-screen.bat"
      : status === "no_metrics"
        ? "页面已打开，但未识别到大屏指标，请检查 data/live-screen.json 的 labels 或 selector"
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
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}${body ? ` ${body.slice(0, 240)}` : ""}`);
  }
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
  let latestStreamUrl = "";
  let publishing = false;
  const publish = async (streamUrl, force = false) => {
    const roomId = String(getRoomId() || "");
    if (!/^\d{8,}$/.test(roomId) || !streamUrl) return;
    const now = Date.now();
    // Re-register periodically so a server restart does not lose the short-lived stream URL.
    if (!force && streamUrl === lastUrl && now - lastSentAt < 30000) return;
    if (publishing) return;
    publishing = true;
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
      let host = "";
      try {
        host = new URL(streamUrl).hostname;
      } catch (_) {
        host = "invalid-url";
      }
      log(`直播画面流同步失败 host=${host}: ${error.message}`);
    } finally {
      publishing = false;
    }
  };
  page.on("response", response => {
    const url = response.url();
    if (/\.flv(?:\?|$)/i.test(url)) {
      latestStreamUrl = url;
      publish(url).catch(() => {});
      return;
    }
    const contentType = String(response.headers()["content-type"] || "");
    if (!contentType.includes("json")) return;
    response.text()
      .then(body => {
        if (!body.includes("room_stream_flv_pull_url")) return;
        const streamUrl = findStreamUrl(JSON.parse(body));
        if (streamUrl) {
          latestStreamUrl = streamUrl;
          return publish(streamUrl);
        }
      })
      .catch(() => {});
  });
  const streamHeartbeat = setInterval(() => {
    if (latestStreamUrl) publish(latestStreamUrl, true).catch(() => {});
  }, 20000);
  page.once("close", () => clearInterval(streamHeartbeat));
}

async function runLogin(config) {
  const puppeteer = await loadPuppeteer();
  const launched = await launchBrowser(puppeteer, config, false);
  const page = await launched.browser.newPage();
  activePage = page;
  const loginUrl = config.loginUrl || LOGIN_URL;
  let initialLoginUrl = loginUrl;
  try {
    const room = await discoverLiveRoomFromServer(config);
    if (room.roomId) {
      initialLoginUrl = buildLoginPageUrl(buildLiveBoardUrl(room));
      log(`已定位当前直播场次 room=${room.roomId}，直接打开该场次登录页`);
    }
  } catch (error) {
    log(`当前直播场次预定位失败，使用 EBP 登录入口: ${error.message}`);
  }
  await restoreBrowserSession(page, initialLoginUrl);
  log("已打开千川登录页。登录成功后会直接回到当前直播大屏并自动验证指标。");
  const deadline = Date.now() + 20 * 60 * 1000;
  let savedCandidateUrl = "";
  let nextAutomaticBoardAt = 0;
  while (Date.now() < deadline) {
    const pages = await launched.browser.pages();
    for (const current of pages) {
      const currentUrl = current.url();
      let pageSnapshot = null;
      try {
        pageSnapshot = await inspectPage(current, config);
      } catch (_) {
        continue;
      }
      const bodyText = String(pageSnapshot?.bodyText || "");
      if (
        Date.now() >= nextAutomaticBoardAt &&
        /^business\.oceanengine\.com$/i.test(new URL(currentUrl).hostname) &&
        !loginRequired({ bodyText, url: currentUrl })
      ) {
        nextAutomaticBoardAt = Date.now() + 15000;
        try {
          const room = await discoverLiveRoomFromServer(config);
          if (room.roomId) {
            log(`EBP 登录完成，自动进入当前直播大屏 room=${room.roomId}`);
            await current.goto(buildLiveBoardEntryUrl(room), {
              waitUntil: "domcontentloaded",
              timeout: 60000
            });
            continue;
          }
        } catch (error) {
          log(`EBP 登录后自动进入直播大屏失败: ${error.message}`);
        }
      }
      if (!isLoginCompletePage({ bodyText, url: currentUrl }, currentUrl)) continue;
      const targetType = new URL(currentUrl).hostname === "qianchuan.jinritemai.com"
        ? "qianchuan_board_next"
        : "ebp_live_detail";
      const safeUrl = safePageUrl(currentUrl);
      if (savedCandidateUrl !== safeUrl) {
        const nextConfig = {
          ...readJson(CONFIG_PATH, {}),
          enabled: true,
          loginUrl,
          pageUrl: safeUrl,
          executablePath: config.executablePath || launched.executablePath,
          userDataDir: config.userDataDir
        };
        writeJsonAtomic(CONFIG_PATH, nextConfig);
        writeState(config, {
          status: "login_saved",
          live: false,
          syncedAt: nowIso(),
          source: "puppeteer-core",
          sourceLabel: "直播大屏地址已保存，正在验证指标",
          pageUrl: safeUrl,
          room: { id: roomIdFromUrl(currentUrl) || "" },
          loginTargetType: targetType,
          metrics: {},
          missingMetrics: METRIC_KEYS,
          error: ""
        });
        savedCandidateUrl = safeUrl;
        log(`已保存直播大屏地址，开始验证页面指标: ${safeUrl}`);
      }

      let verification = null;
      try {
        verification = await scrape(current, config);
      } catch (error) {
        log(`直播大屏指标验证失败，继续保持登录窗口: ${error.message}`);
      }
      if (!verification || !Object.keys(verification.metrics || {}).length) {
        log("已识别直播大屏地址，但指标尚未加载；浏览器保持打开，继续等待。");
        continue;
      }

      writeState(config, {
        ...verification,
        status: verification.missingMetrics?.length ? "partial" : "ok",
        sourceLabel: "直播大屏登录与指标均验证成功",
        loginTargetType: targetType,
        error: ""
      });
      await persistBrowserSession(current);
      log(
        `登录与指标验证成功：${Object.keys(verification.metrics).join(", ")}。` +
        "浏览器将在 10 秒后自动关闭，以交给后台无头采集器；这不是程序闪退。"
      );
      for (let remaining = 10; remaining > 0; remaining -= 1) {
        log(`后台采集接管倒计时 ${remaining}s`);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      await closeActiveBrowser();
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  await closeActiveBrowser();
  throw new Error("20 分钟内未检测到直播大屏：地址需包含 roomId，或页面出现累计观看/商品点击/峰值/GPM/消耗/成交中的至少 2 项");
}

async function prepareAutomaticLiveBoard(config) {
  const room = await discoverLiveRoomFromServer(config);
  if (!room.roomId) return null;
  const storedConfig = readJson(CONFIG_PATH, {});
  let pageUrl = "";
  if (
    storedConfig.pageUrl &&
    new URL(storedConfig.pageUrl).hostname === "qianchuan.jinritemai.com"
  ) {
    pageUrl = replaceRoomIdInUrl(storedConfig.pageUrl, room.roomId);
  } else if (
    storedConfig.pageUrl &&
    new URL(storedConfig.pageUrl).hostname === "business.oceanengine.com" &&
    new URL(storedConfig.pageUrl).pathname.endsWith("/data-analysis/live-analysis/detail")
  ) {
    pageUrl = replaceRoomIdInUrl(storedConfig.pageUrl, room.roomId);
  } else {
    pageUrl = buildLiveBoardEntryUrl(room);
  }
  if (!pageUrl) return null;
  const nextConfig = {
    ...storedConfig,
    enabled: true,
    autoLogin: true,
    pageUrl,
    autoPreparedAt: nowIso()
  };
  writeJsonAtomic(CONFIG_PATH, nextConfig);
  log(`开机自动恢复直播大屏 room=${room.roomId}`);
  return nextConfig;
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
    log("缺少直播大屏地址，正在使用持久化 EBP 登录态自动恢复");
    while (true) {
      const refreshed = loadConfig();
      if (refreshed.enabled && refreshed.pageUrl) return runAgent(refreshed);
      try {
        const prepared = await prepareAutomaticLiveBoard(refreshed);
        if (prepared?.pageUrl) return runAgent(prepared);
      } catch (error) {
        log(`开机自动恢复暂不可用: ${error.message}`);
      }
      writeState(config, {
        status: "config_required",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "正在自动恢复直播大屏",
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: "正在使用已保存的 EBP 登录态自动恢复；如持续失败，再运行 login-live-screen.bat"
      });
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
  if (isLegacyQianchuanUrl(config.pageUrl)) {
    const storedConfig = readJson(CONFIG_PATH, {});
    writeJsonAtomic(CONFIG_PATH, {
      ...storedConfig,
      pageUrl: "",
      legacyPageUrlClearedAt: nowIso()
    });
    config.pageUrl = "";
    log("检测到无 roomId 的旧版页面，已清空 pageUrl 并准备自动恢复当前直播场次");
    while (true) {
      const refreshed = loadConfig();
      if (refreshed.enabled && isConfiguredLiveScreenUrl(refreshed.pageUrl)) {
        return runAgent(refreshed);
      }
      writeState(config, {
        status: "login_required",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "登录已过期，请重新登录",
        pageUrl: "",
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: "旧版地址已清空，正在自动恢复当前直播大屏；持续失败再运行 login-live-screen.bat"
      });
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
  if (!isConfiguredLiveScreenUrl(config.pageUrl)) {
    const storedConfig = readJson(CONFIG_PATH, {});
    writeJsonAtomic(CONFIG_PATH, { ...storedConfig, pageUrl: "" });
    config.pageUrl = "";
    log("已清除误存的 EBP 首页地址，等待重新登录直播大屏");
    while (true) {
      const refreshed = loadConfig();
      if (refreshed.enabled && isConfiguredLiveScreenUrl(refreshed.pageUrl)) {
        return runAgent(refreshed);
      }
      writeState(config, {
        status: "login_required",
        live: false,
        syncedAt: nowIso(),
        source: "puppeteer-core",
        sourceLabel: "登录已过期，请重新登录",
        pageUrl: "",
        metrics: {},
        missingMetrics: METRIC_KEYS,
        error: "保存的页面不是直播大屏，正在自动恢复当前直播场次；持续失败再运行 login-live-screen.bat"
      });
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }

  writeState(config, {
    status: "starting",
    live: false,
    syncedAt: nowIso(),
    source: "puppeteer-core",
    sourceLabel: "千川直播大屏 · 正在启动",
    pageUrl: safePageUrl(config.pageUrl),
    metrics: {},
    missingMetrics: METRIC_KEYS,
    error: ""
  });
  const puppeteer = await loadPuppeteer();
  const launched = await launchBrowser(puppeteer, config, config.headless !== false);
  const page = await launched.browser.newPage();
  activePage = page;
  let currentRoomId = roomIdFromUrl(config.pageUrl);
  installStreamCapture(page, config, () => currentRoomId || roomIdFromUrl(page.url()));
  await restoreBrowserSession(page, config.pageUrl);
  log(`采集器已启动 browser=${launched.executablePath} profile=${launched.userDataDir}`);

  let nextNavigationAt = 0;
  let nextRoomDiscoveryAt = 0;
  const previousState = readJson(STATE_PATH, {});
  let lastUsableState = previousState?.live && previousState?.metrics
    ? previousState
    : null;
  let cycleCount = 0;
  let peakRoomId = "";
  let observedPeak = 0;
  let observedPeakAt = "";
  let nextSsoRecoveryAt = 0;
  let nextSessionPersistAt = 0;
  let lastLiveMetricSignature = "";
  let liveMetricsUnchangedSince = 0;
  let lastPageRefreshAt = Date.now();
  while (true) {
    const startedAt = Date.now();
    try {
      if (page.isClosed()) throw new Error("页面已关闭");
      const configuredUrl = new URL(config.pageUrl);
      if (
        (
          configuredUrl.hostname === "qianchuan.jinritemai.com" ||
          (
            configuredUrl.hostname === "business.oceanengine.com" &&
            configuredUrl.pathname.endsWith("/data-analysis/live-analysis/detail")
          )
        ) &&
        Date.now() >= nextRoomDiscoveryAt
      ) {
        try {
          const currentRoom = await discoverLiveRoomFromServer(config);
          if (currentRoom.roomId && currentRoom.roomId !== currentRoomId) {
            const targetUrl = replaceRoomIdInUrl(config.pageUrl, currentRoom.roomId);
            if (targetUrl) {
              log(`发现当前直播场次 ${currentRoom.roomId}，切换到该场次`);
              await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
              config.pageUrl = targetUrl;
              currentRoomId = currentRoom.roomId;
              nextNavigationAt = 0;
            }
          }
        } catch (error) {
          log(`当前直播场次发现失败，继续使用保存的场次: ${error.message}`);
        }
        nextRoomDiscoveryAt = Date.now() + 120000;
      }
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
      let result = await scrape(page, config);
      if (
        result.status === "login_required" &&
        Date.now() >= nextSsoRecoveryAt
      ) {
        nextSsoRecoveryAt = Date.now() + 120000;
        try {
          const recoveredRoom = await recoverLiveBoardSession(page, config);
          if (recoveredRoom?.roomId) {
            currentRoomId = recoveredRoom.roomId;
            result = await scrape(page, config);
            log(
              `登录页跳转已触发 EBP 单点恢复 room=${currentRoomId} status=${result.status}`
            );
          }
        } catch (error) {
          log(`EBP 单点恢复失败: ${error.message}`);
        }
      }
      result.room = { ...(result.room || {}), id: currentRoomId || result.room?.id || "" };
      const liveMetricSignature = result.live
        ? METRIC_KEYS.map(key => String(result.metrics?.[key] ?? "")).join("|")
        : "";
      if (liveMetricSignature && liveMetricSignature === lastLiveMetricSignature) {
        if (!liveMetricsUnchangedSince) liveMetricsUnchangedSince = Date.now();
        result.metricUnchangedSeconds = Math.max(
          0,
          Math.round((Date.now() - liveMetricsUnchangedSince) / 1000)
        );
        if (
          result.metricUnchangedSeconds >= 300 &&
          Date.now() - lastPageRefreshAt >= 300000
        ) {
          log(
            `直播指标连续 ${result.metricUnchangedSeconds}s 未变化，自动刷新大屏页面`
          );
          lastPageRefreshAt = Date.now();
          liveMetricsUnchangedSince = Date.now();
          await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
          await new Promise(resolve => setTimeout(resolve, 3000));
        }
      } else {
        lastLiveMetricSignature = liveMetricSignature;
        liveMetricsUnchangedSince = liveMetricSignature ? Date.now() : 0;
      }
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
        result.behaviorMetrics = Object.fromEntries(
          BEHAVIOR_METRIC_KEYS
            .filter(key => result.metrics[key] != null)
            .map(key => [key, result.metrics[key]])
        );
        result.missingBehaviorMetrics = BEHAVIOR_METRIC_KEYS.filter(
          key => result.metrics[key] == null
        );
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
        if (Date.now() >= nextSessionPersistAt) {
          await persistBrowserSession(page);
          nextSessionPersistAt = Date.now() + 60000;
        }
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
  const loginMode = process.argv.includes("--login");
  const userDataDir = path.resolve(ROOT, config.userDataDir || "data/chrome-profile");
  let lock = acquireAgentLock({ mode: loginMode ? "login" : "agent", userDataDir });
  if (!lock.acquired && loginMode) {
    const owner = lock.owner || {};
    log(`登录模式立即接管采集器 PID=${owner.pid || "-"}`);
    writeJsonAtomic(TAKEOVER_PATH, {
      pid: process.pid,
      targetPid: Number(owner.pid) || null,
      requestedAt: nowIso()
    });
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline && pidIsRunning(owner.pid)) {
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (pidIsRunning(owner.pid)) {
      terminateProcessTree(owner.pid);
      const forceDeadline = Date.now() + 5000;
      while (Date.now() < forceDeadline && pidIsRunning(owner.pid)) {
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }
    if (pidIsRunning(owner.pid)) {
      throw new Error(`旧采集器 PID=${owner.pid} 无法退出，登录页未能打开`);
    }
    lock = acquireAgentLock({ mode: "login", userDataDir });
    try {
      fs.unlinkSync(TAKEOVER_PATH);
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
  }
  if (!lock.acquired) {
    const owner = lock.owner || {};
    log(`采集器已在运行，拒绝启动第二个实例 PID=${owner.pid || "-"} mode=${owner.mode || "-"}`);
    return;
  }
  try {
    cleanupBrowserProfileState(userDataDir, { terminateOrphans: true });
    startStateHeartbeat(config);
    startTakeoverWatcher();
    if (loginMode) {
      await runLogin(config);
      return;
    }
    await runAgent(config);
  } finally {
    if (takeoverTimer) {
      clearInterval(takeoverTimer);
      takeoverTimer = null;
    }
    try {
      fs.unlinkSync(TAKEOVER_PATH);
    } catch (error) {
      if (error?.code !== "ENOENT") log(`清理登录接管请求失败: ${error.message}`);
    }
    await closeActiveBrowser();
    cleanupBrowserProfileState(userDataDir, { terminateOrphans: true });
    stopStateHeartbeat();
    releaseAgentLock();
  }
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
  AGENT_LOCK_PATH,
  BROWSER_LAUNCH_ARGS,
  DEFAULT_CONFIG,
  LOGIN_URL,
  acquireAgentLock,
  buildLiveBoardUrl,
  buildLoginPageUrl,
  cleanupBrowserProfileState,
  extractMetrics,
  extractFlows,
  findStreamUrl,
  hasLiveScreenEvidence,
  inspectPage,
  isConfiguredLiveScreenUrl,
  isLegacyQianchuanUrl,
  isLoginCompletePage,
  isLiveScreenPage,
  liveScreenMetricSignalCount,
  loginRequired,
  mergeConfig,
  parseMetricNumber,
  pidIsRunning,
  readAgentLock,
  releaseAgentLock,
  replaceRoomIdInUrl,
  roomIdFromUrl,
  safePageUrl
};
