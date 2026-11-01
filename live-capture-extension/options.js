const input = document.querySelector("#serverUrl");
const status = document.querySelector("#status");
chrome.storage.local.get({ serverUrl: "http://127.0.0.1:8765" }).then(value => {
  input.value = value.serverUrl;
});
document.querySelector("#save").addEventListener("click", async () => {
  const serverUrl = input.value.trim().replace(/\/+$/, "");
  status.textContent = "正在测试…";
  try {
    const parsed = new URL(serverUrl);
    if (!["http:", "https:"].includes(parsed.protocol) || !["127.0.0.1", "localhost"].includes(parsed.hostname)) {
      throw new Error("仅支持本机地址");
    }
    await chrome.storage.local.set({ serverUrl });
    const response = await fetch(`${serverUrl}/api/live/stream/heartbeat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    status.textContent = "已连接";
  } catch (error) {
    status.textContent = `连接失败：${error.message}`;
  }
});
