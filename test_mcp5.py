import json, urllib.request

MCP_URL = "https://open.oceanengine.com/qianchuan/mcp?API_KEY=40b38db60d924afb27792f358cb88d75128612f7"

# 拉完整字段列表
req = urllib.request.Request(MCP_URL,
    data=json.dumps({
        "jsonrpc":"2.0","id":2,"method":"tools/call",
        "params":{"name":"get_tool_response_field_desc","arguments":{"tool_name":"qianchuan_report_live_get_v1"}}
    }).encode(),
    headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
text = data["result"]["content"][0]["text"]
fields = json.loads(text)
props = fields.get("properties",{}).get("data",{}).get("properties",{})

print("=== 所有字段名 ===")
for name, desc in props.items():
    d = desc.get("description","")
    if any(k in d for k in ["消耗","成交","订单","观看","GMV","GMV","金额","roi","ROI"]):
        print(f"{name}: {d}")
