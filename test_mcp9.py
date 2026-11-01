import json, urllib.request

MCP_URL = "https://open.oceanengine.com/qianchuan/mcp?API_KEY=40b38db60d924afb27792f358cb88d75128612f7"

# 先试试全域推广报表，确认 API 是通的
req = urllib.request.Request(MCP_URL,
    data=json.dumps({
        "jsonrpc":"2.0","id":4,"method":"tools/call",
        "params":{
            "name":"qianchuan_report_uni_promotion_get_v1",
            "arguments":{
                "advertiser_id": 1744479430946824,
                "start_time": "2026-10-21",
                "end_time": "2026-10-21",
                "fields": ["stat_cost", "total_pay_order_gmv_for_roi2", "total_pay_order_count_for_roi2"]
            }
        }
    }).encode(),
    headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
print("=== 全域推广报表返回 ===")
print(json.dumps(data.get("result",{}).get("structuredContent",{}), indent=2, ensure_ascii=False)[:1500])
