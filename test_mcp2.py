import json, urllib.request

MCP_URL = "https://open.oceanengine.com/qianchuan/mcp?API_KEY=40b38db60d924afb27792f358cb88d75128612f7"

# 先看 qianchuan_report_live_get_v1 的参数要求
req = urllib.request.Request(MCP_URL,
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}).encode(),
    headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
for t in data.get("result",{}).get("tools",[]):
    if t["name"] == "qianchuan_report_live_get_v1":
        print("=== qianchuan_report_live_get_v1 参数 ===")
        print(json.dumps(t.get("inputSchema",{}), indent=2, ensure_ascii=False))
