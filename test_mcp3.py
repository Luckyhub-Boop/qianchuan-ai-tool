import json, urllib.request

MCP_URL = "https://open.oceanengine.com/qianchuan/mcp?API_KEY=40b38db60d924afb27792f358cb88d75128612f7"

# 调用 get_tool_response_field_desc 看看直播报表有哪些字段
req = urllib.request.Request(MCP_URL,
    data=json.dumps({
        "jsonrpc":"2.0","id":2,"method":"tools/call",
        "params":{"name":"get_tool_response_field_desc","arguments":{"tool_name":"qianchuan_report_live_get_v1"}}
    }).encode(),
    headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
print("=== 直播报表字段列表 ===")
print(json.dumps(data.get("result",{}), indent=2, ensure_ascii=False)[:2000])
