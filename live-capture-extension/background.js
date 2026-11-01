const DEFAULT_SERVER = "http://127.0.0.1:8765";
let lastStream = { url: "", roomId: "", sentAt: 0 };

const allowedStreamUrl = value => {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    return ["http:", "https:"].includes(url.protocol) &&
      (host === "douyincdn.com" || host.endsWith(".douyincdn.com") ||
       host === "byteimg.com" || host.endsWith(".byteimg.com"));
  } catch (_) {
    return false;
  }
};

const getServer = async () => {
  const stored = await chrome.storage.local.get({ serverUrl: DEFAULT_SERVER });
  return String(stored.serverUrl || DEFAULT_SERVER).replace(/\/+$/, "");
};

const post = async (path, payload) => {
  const server = await getServer();
  const response = await fetch(`${server}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {})
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json().catch(() => ({ ok: true }));
};

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || !["stream", "heartbeat"].includes(message.type)) return false;
  if (message.type === "heartbeat") {
    post("/api/live/stream/heartbeat", { roomId: String(message.roomId || "").trim() })
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ ok: false, error: String(error.message || error) }));
    return true;
  }
  const roomId = String(message.roomId || "").trim();
  const url = String(message.url || "").trim();
  if (!/^\d{8,}$/.test(roomId) || !allowedStreamUrl(url)) {
    sendResponse({ ok: false, error: "invalid_stream_payload" });
    return false;
  }
  const now = Date.now();
  if (lastStream.url === url && lastStream.roomId === roomId && now - lastStream.sentAt < 120000) {
    sendResponse({ ok: true, cached: true });
    return false;
  }
  post("/api/live/stream", { roomId, url, type: "flv", source: "qianchuan-board" })
    .then(result => {
      if (result.ok) lastStream = { url, roomId, sentAt: now };
      sendResponse(result);
    })
    .catch(error => sendResponse({ ok: false, error: String(error.message || error) }));
  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  post("/api/live/stream/heartbeat", {}).catch(() => {});
});
