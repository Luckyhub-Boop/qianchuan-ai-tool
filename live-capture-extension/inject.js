(() => {
  const MARK = "__qianchuanLiveCaptureInstalled";
  if (window[MARK]) return;
  window[MARK] = true;

  const SIGNAL = "qianchuan-live-capture";
  const FIELD = "room_stream_flv_pull_url";
  let lastSentUrl = "";
  let lastSentAt = 0;

  const getRoomId = () => {
    try {
      const value = new URL(location.href).searchParams.get("live_room_id") || "";
      return /^\d{8,}$/.test(value) ? value : "";
    } catch (_) {
      return "";
    }
  };

  const streamValue = value => {
    if (typeof value === "string") return value;
    if (value && typeof value === "object") {
      for (const key of ["Value", "value", "Url", "url"]) {
        if (typeof value[key] === "string") return value[key];
      }
    }
    return "";
  };

  const findStreamUrl = (value, seen = new Set()) => {
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
      if (key.toLowerCase() === FIELD) {
        const found = streamValue(item);
        if (/^https?:\/\//i.test(found)) return found;
      }
    }
    for (const item of Object.values(value)) {
      const found = findStreamUrl(item, seen);
      if (found) return found;
    }
    return "";
  };

  const publish = url => {
    if (!url || !/^https?:\/\//i.test(url)) return;
    const roomId = getRoomId();
    if (!roomId) return;
    const now = Date.now();
    if (url === lastSentUrl && now - lastSentAt < 120000) return;
    lastSentUrl = url;
    lastSentAt = now;
    window.postMessage({ source: SIGNAL, type: "stream", roomId, url }, location.origin);
  };

  const publishIfStreamUrl = value => {
    try {
      const candidate = new URL(String(value || ""), location.href);
      const host = candidate.hostname.toLowerCase();
      const cdnHost = host === "douyincdn.com" || host.endsWith(".douyincdn.com") ||
        host === "byteimg.com" || host.endsWith(".byteimg.com");
      if (cdnHost && /\.flv$/i.test(candidate.pathname)) publish(candidate.href);
    } catch (_) {}
  };

  const inspectText = text => {
    if (!text || !text.includes(FIELD)) return;
    try {
      publish(findStreamUrl(JSON.parse(text)));
    } catch (_) {}
  };

  const originalFetch = window.fetch;
  if (typeof originalFetch === "function") {
    window.fetch = async function (...args) {
      const requestUrl = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      publishIfStreamUrl(requestUrl);
      const response = await originalFetch.apply(this, args);
      try {
        if (requestUrl.startsWith(location.origin)) {
          response.clone().text().then(inspectText).catch(() => {});
        }
      } catch (_) {}
      return response;
    };
  }

  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    publishIfStreamUrl(url);
    this.addEventListener("load", () => {
      try {
        const requestUrl = String(url || "");
        if (!requestUrl.startsWith(location.origin) && !requestUrl.startsWith("/")) return;
        const contentType = this.getResponseHeader("content-type") || "";
        if (!contentType.includes("json")) return;
        inspectText(this.responseText);
      } catch (_) {}
    });
    return originalOpen.call(this, method, url, ...rest);
  };

  if (typeof PerformanceObserver === "function") {
    try {
      const observer = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) publishIfStreamUrl(entry.name);
      });
      observer.observe({ type: "resource", buffered: true });
    } catch (_) {}
  }
})();
