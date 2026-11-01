(() => {
  const SIGNAL = "qianchuan-live-capture";
  const send = payload => {
    try {
      chrome.runtime.sendMessage(payload, () => void chrome.runtime.lastError);
    } catch (_) {}
  };
  window.addEventListener("message", event => {
    if (event.origin !== location.origin || !event.data || event.data.source !== SIGNAL) return;
    if (event.data.type !== "stream") return;
    send({
      type: "stream",
      roomId: event.data.roomId,
      url: event.data.url,
      pageUrl: location.href
    });
  });
  const heartbeat = () => {
    let roomId = "";
    try {
      const value = new URL(location.href).searchParams.get("live_room_id") || "";
      if (/^\d{8,}$/.test(value)) roomId = value;
    } catch (_) {}
    send({ type: "heartbeat", roomId, pageUrl: location.href });
  };
  heartbeat();
  setInterval(heartbeat, 20000);
})();
