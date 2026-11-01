import json, urllib.request

MCP_URL = "https://open.oceanengine.com/qianchuan/mcp?API_KEY=40b38db60d924afb27792f358cb88d75128612f7"

req = urllib.request.Request(MCP_URL,
    data=json.dumps({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{
            "name":"qianchuan_report_live_get_v1",
            "arguments":{
                "advertiser_id": 1744479430946824,
                "aweme_id": 7637818476896437305,
                "start_time": "2026-10-21 00:00:00",
                "end_time": "2026-10-21 23:59:59",
                "fields": ["stat_cost", "live_pay_order_gmv_alias", "live_pay_order_count_alias", "total_live_watch_cnt", "live_watch_one_minute_count"]
            }
        }
    }).encode(),
    headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
print("=== 返回结果 ===")
print(json.dumps(data.get("result",{}).get("structuredContent",{}), indent=2, ensure_ascii=False))
