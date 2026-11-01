import json, urllib.request

MCP_URL = "https://open.oceanengine.com/qianchuan/mcp?API_KEY=40b38db60d924afb27792f358cb88d75128612f7"

# 调用 tools/list 看看有哪些工具
req = urllib.request.Request(MCP_URL,
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}).encode(),
    headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
print("=== 工具列表 ===")
for t in data.get("result",{}).get("tools",[]):
    print(f"- {t['name']}")
