# 千川 OAuth Open API 接入说明

## 1. 先区分两种凭证

- 千川 MCP API Key：只用于 MCP 网关当前开放的 11 个工具，不能生成 OAuth 授权链接。
- OAuth 应用：巨量开放平台开发者应用，需要 App ID、App Secret 和已登记的回调地址，用于直接调用千川 Open API。

## 2. 一键授权

1. 登录 `https://open.oceanengine.com/`，进入开发者应用管理。
2. 确认应用状态正常，并已申请项目需要的千川报表、直播和素材接口权限。
3. 在应用的“回调地址”中登记一个完整地址。
4. 双击项目根目录的 `oauth-login.bat`。
5. 首次运行按提示填写 App ID、App Secret 和已登记回调地址。App Secret 输入时不显示。
6. 浏览器打开千川授权页后，登录并确认授权。
7. 程序使用回调中的一次性 `auth_code` 换取 Access Token 和 Refresh Token，并写入 `data/qianchuan-token.json`。

推荐回调地址：

```text
http://127.0.0.1:8767/oauth/callback
```

该地址必须是应用后台已登记的地址。使用它时，授权完成后本机助手会自动接收回调，不需要手工复制代码。

如果应用只登记了远程回调，也可以继续使用 `oauth-login.bat`：浏览器完成授权后，把浏览器地址栏中的完整回调 URL 粘贴到命令窗口。

## 3. 敏感文件

- `data/qianchuan-oauth.json`：App ID、App Secret、回调地址和可选 scope。
- `data/qianchuan-token.json`：Access Token、Refresh Token、到期时间和 scope。

两个文件都已加入 `.gitignore`，不要发送到群聊、提交到仓库或截图公开。

Access Token 到期前 5 分钟，后端会使用 Refresh Token 自动刷新。刷新成功后原子覆盖原有 Token 文件。

## 4. 授权诊断

服务启动后可访问：

```text
http://127.0.0.1:8765/api/oauth/status
```

状态接口只返回是否配置了 App ID、Secret、回调地址、Access Token、Refresh Token 和到期时间，不返回凭证内容。

## 5. 实时直播对账

当前直播间发现接口：

```text
/open_api/v1.0/qianchuan/today_live/room/get/
```

项目对比接口：

```text
http://127.0.0.1:8765/api/live/compare?account=fashion
```

该接口逐项展示今日直播间 Open API 与无头大屏抓取值。2026-10-25 实测结果为：

- Open API 正确返回当前 `roomId=7700373751996746532` 和 `LIVING` 状态。
- 当前全域推广账户的消耗、成交、订单、累计观看和商品点击字段均返回 0。
- 同一时刻无头大屏返回真实非零经营指标。

因此当前账户不能使用今日直播间 Open API 替代大屏的实时经营数据。直播间 ID 发现可以继续使用 Open API。

## 6. 素材上传时间

素材上传时间接口：

```text
GET /open_api/v1.0/qianchuan/video/get/
```

核心字段：

- `material_id`：素材 ID，用于与计划素材库关联。
- `create_time`：官方定义为素材上传时间。
- `filename`、`duration`、`poster_url`：素材元数据。

项目每 3 分钟同步素材库，按 `material_id` 合并上传时间。2026-10-25 实测：

- 视频素材库总数 1,854。
- 1,854 条均返回 `create_time`。
- 5 个计划合并去重后为 1,885 条素材。
- 1,829 条匹配到真实上传时间。
- 51 条历史视频已不在当前视频库，另有 5 条直播间画面；这 56 条保持“未获取”，不做推算。

曝光量 `< 60`、订单 `< 2` 且上传超过 40 天的素材会被标红。上传时间未获取时只提示“待核对上传时间”。

## 7. 相关接口

- 授权页：`https://open.oceanengine.com/audit/oauth.html`
- 换取 Access Token：`POST https://ad.oceanengine.com/open_api/oauth2/access_token/`
- 刷新 Token：`POST https://ad.oceanengine.com/open_api/oauth2/refresh_token/`
- 今日直播间：`GET /open_api/v1.0/qianchuan/today_live/room/get/`
- 素材库视频：`GET /open_api/v1.0/qianchuan/video/get/`
