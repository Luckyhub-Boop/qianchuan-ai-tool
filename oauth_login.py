from __future__ import annotations

import argparse
import html
import json
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from getpass import getpass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import server


def prompt_value(label: str, current: str = "", *, secret: bool = False) -> str:
    suffix = "（直接回车保留现有值）" if current else ""
    prompt = f"{label}{suffix}: "
    value = getpass(prompt) if secret else input(prompt)
    value = value.strip()
    if value:
        return value
    if current:
        return current
    raise RuntimeError(f"{label}不能为空")


def ensure_config(force_setup: bool = False) -> dict[str, Any]:
    config = server.load_oauth_config()
    missing = server.oauth_config_errors(config)
    if not force_setup and not missing:
        return config

    print("\n首次使用需要填写巨量开放平台应用参数。")
    print("这些值来自 open.oceanengine.com 的开发者应用；App Secret 只保存在本机。")
    if missing:
        print("当前缺失：" + " ".join(missing))
    config["appId"] = prompt_value("App ID", config.get("appId", ""))
    config["appSecret"] = prompt_value(
        "App Secret",
        config.get("appSecret", ""),
        secret=True,
    )
    config["redirectUri"] = prompt_value(
        "已登记的回调地址 redirect_uri",
        config.get("redirectUri", ""),
    )
    if not config.get("scope"):
        scope = input(
            "Scope（可选，应用后台已勾选权限时可留空）: "
        ).strip()
        config["scope"] = scope
    errors = server.oauth_config_errors(config)
    if errors:
        raise RuntimeError("".join(errors))
    server.save_oauth_config(config)
    print(f"OAuth 配置已安全写入：{server.OAUTH_CONFIG_PATH}")
    return server.load_oauth_config()


class CallbackCapture:
    def __init__(self, expected_state: str, callback_path: str) -> None:
        self.expected_state = expected_state
        self.callback_path = callback_path or "/"
        self.auth_code = ""
        self.error = ""
        self.received_state = ""
        self.event = threading.Event()


def callback_handler(capture: CallbackCapture) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != capture.callback_path:
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(parsed.query)
            capture.received_state = (query.get("state") or [""])[0]
            capture.auth_code = (
                query.get("auth_code") or query.get("code") or [""]
            )[0]
            capture.error = (
                query.get("error_description")
                or query.get("error")
                or [""]
            )[0]
            state_ok = secrets.compare_digest(
                str(capture.received_state),
                str(capture.expected_state),
            )
            if not state_ok and not capture.error:
                capture.error = "OAuth state 校验失败，已拒绝本次授权回调。"
            ok = bool(capture.auth_code) and not capture.error
            message = (
                "授权成功，可以关闭此页面并回到命令窗口。"
                if ok
                else f"授权失败：{html.escape(capture.error or '未收到 auth_code')}"
            )
            page = f"""<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<title>千川 OAuth 授权</title>
<body style="font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#f4f7f6;padding:48px">
<main style="max-width:680px;margin:auto;background:white;border-radius:16px;padding:32px;box-shadow:0 12px 40px #1232">
<h1 style="color:{'#087a57' if ok else '#b42318'}">{'授权成功' if ok else '授权失败'}</h1>
<p>{message}</p>
<p style="color:#667085">可回到命令窗口，程序会自动换取并保存 Access Token。</p>
</main></body></html>"""
            body = page.encode("utf-8")
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            capture.event.set()

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return Handler


def can_use_local_callback(redirect_uri: str) -> tuple[bool, dict[str, Any]]:
    parsed = urllib.parse.urlparse(redirect_uri)
    host = (parsed.hostname or "").lower()
    is_local = parsed.scheme == "http" and host in {
        "127.0.0.1",
        "localhost",
        "::1",
    }
    return is_local, {
        "host": host,
        "port": parsed.port or 80,
        "path": parsed.path or "/",
    }


def auth_code_from_user_input(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if "://" in value:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(value).query)
        return (
            query.get("auth_code")
            or query.get("code")
            or [""]
        )[0].strip()
    return value


def wait_for_local_callback(
    authorize_url: str,
    redirect_uri: str,
    state: str,
    timeout_seconds: int,
) -> str:
    local, callback = can_use_local_callback(redirect_uri)
    if not local:
        print("回调地址不是本机 HTTP 地址，改为浏览器授权后粘贴回调 URL 或 auth_code。")
        print(f"\n授权链接：\n{authorize_url}\n")
        webbrowser.open(authorize_url)
        return auth_code_from_user_input(
            input("请粘贴浏览器地址栏的完整回调 URL，或只粘贴 auth_code: ")
        )

    capture = CallbackCapture(state, str(callback["path"]))
    try:
        httpd = ThreadingHTTPServer(
            ("127.0.0.1", int(callback["port"])),
            callback_handler(capture),
        )
    except OSError as exc:
        print(f"本机回调端口无法监听：{exc}")
        print(f"\n授权链接：\n{authorize_url}\n")
        webbrowser.open(authorize_url)
        return auth_code_from_user_input(
            input("请粘贴浏览器地址栏的完整回调 URL，或只粘贴 auth_code: ")
        )

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"本机 OAuth 回调监听已启动：http://127.0.0.1:{callback['port']}{callback['path']}")
    print(f"\n授权链接：\n{authorize_url}\n")
    opened = webbrowser.open(authorize_url)
    if not opened:
        print("浏览器未能自动打开，请手动复制上面的授权链接。")
    print(f"等待授权回调，最长 {timeout_seconds} 秒……")
    try:
        capture.event.wait(timeout=timeout_seconds)
    finally:
        httpd.shutdown()
        httpd.server_close()
    if capture.error:
        raise RuntimeError(capture.error)
    if not capture.auth_code:
        raise RuntimeError("等待 OAuth 授权回调超时")
    return capture.auth_code


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "未返回"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return f"{number:,.0f}"
    return f"{number:,.{digits}f}"


def probe_open_api() -> None:
    print("\n正在验证新 Token、今日直播间和素材上传时间……")
    config = server.load_config()
    token, token_info, credential_errors = server.resolve_access_token(config)
    if not token:
        raise RuntimeError(
            credential_errors[0]["message"]
            if credential_errors
            else "未取得 Access Token"
        )
    client = server.QianchuanClient(config, token)
    accounts = config.get("accounts") or []
    if not accounts:
        raise RuntimeError("qianchuan.config.json 中没有广告主账户")
    account = accounts[0]
    advertiser_id = str(account.get("advertiserId") or account.get("qianchuanId") or "")
    aweme_ids = [
        str(item.get("id"))
        for item in account.get("awemeAccounts") or []
        if item.get("id")
    ] or [str(item) for item in account.get("awemeIds") or [] if item]
    today = server.date.today().isoformat()
    live_room: dict[str, Any] | None = None
    api_errors: list[str] = []
    for aweme_id in aweme_ids:
        try:
            rooms = client.fetch_live_rooms(advertiser_id, aweme_id, today)
            live_room = next(
                (
                    room
                    for room in rooms
                    if str(room.get("room_status") or "").upper() == "LIVING"
                ),
                None,
            )
            if live_room:
                break
        except server.QianchuanAPIError as exc:
            api_errors.append(f"{aweme_id}: {exc}")

    print("\n一、今日直播间 Open API")
    if live_room:
        api_metrics = {
            "消耗": client._live_money(live_room.get("stat_cost")),
            "成交": client._live_money(
                live_room.get("live_pay_order_gmv_alias")
                or live_room.get("luban_live_pay_order_gmv")
            ),
            "订单": server.to_number(
                live_room.get("live_pay_order_count_alias")
                or live_room.get("luban_live_pay_order_count")
            )
            or 0,
            "ROI": server.to_number(
                live_room.get("live_pay_order_gmv_roi")
                or live_room.get("ad_live_prepay_and_pay_order_gmv_roi")
            ),
            "累计观看": server.to_number(live_room.get("total_live_watch_cnt")) or 0,
            "商品点击": server.to_number(
                live_room.get("live_click_product_count_alias")
            )
            or 0,
            "观看满1分钟": server.to_number(
                live_room.get("live_watch_one_minute_count")
            )
            or 0,
            "评论": server.to_number(live_room.get("total_live_comment_cnt")) or 0,
        }
        print(f"roomId: {live_room.get('room_id')}  状态: {live_room.get('room_status')}")
        for label, value in api_metrics.items():
            print(f"  {label}: {fmt(value)}")
    else:
        print("未发现 room_status=LIVING 的直播间。")
        for error in api_errors:
            print(f"  {error}")

    screen_payload: dict[str, Any] = {}
    try:
        screen_payload = server.load_json(server.LIVE_SCREEN_STATE_PATH, {})
    except ValueError as exc:
        print(f"读取无头大屏状态失败：{exc}")
    screen_metrics = (
        screen_payload.get("metrics")
        if isinstance(screen_payload.get("metrics"), dict)
        else {}
    )
    print("\n二、与当前无头大屏抓取对比")
    print(f"无头大屏状态: {screen_payload.get('status') or '未获取'}")
    for label, key in (
        ("消耗", "spend"),
        ("成交", "gmv"),
        ("订单", "orders"),
        ("ROI", "roi"),
        ("累计观看", "watchCount"),
        ("商品点击", "productClicks"),
        ("曝光", "exposure"),
        ("GPM", "gpm"),
        ("实时在线", "online"),
    ):
        api_value = None
        if live_room:
            api_value = {
                "spend": client._live_money(live_room.get("stat_cost")),
                "gmv": client._live_money(
                    live_room.get("live_pay_order_gmv_alias")
                    or live_room.get("luban_live_pay_order_gmv")
                ),
                "orders": server.to_number(
                    live_room.get("live_pay_order_count_alias")
                    or live_room.get("luban_live_pay_order_count")
                ),
                "roi": server.to_number(live_room.get("live_pay_order_gmv_roi")),
                "watchCount": server.to_number(live_room.get("total_live_watch_cnt")),
                "productClicks": server.to_number(
                    live_room.get("live_click_product_count_alias")
                ),
                "exposure": None,
                "gpm": None,
                "online": None,
            }.get(key)
        print(
            f"  {label}: Open API {fmt(api_value)} | 大屏 {fmt(screen_metrics.get(key))}"
        )

    print("\n三、千川素材库上传时间")
    videos, meta = client.fetch_qianchuan_video_library(
        advertiser_id,
        with_meta=True,
    )
    print(
        f"来源: {meta.get('source')}  "
        f"总数: {fmt(meta.get('sourceTotal'), 0)}  "
        f"本次取得: {fmt(meta.get('uniqueCount'), 0)}  "
        f"含上传时间: {fmt(meta.get('uploadTimeCount'), 0)}"
    )
    newest = sorted(
        (item for item in videos if item.get("uploadedAt") != "未获取"),
        key=lambda item: str(item.get("uploadedAt")),
        reverse=True,
    )[:5]
    for item in newest:
        print(
            f"  {item['id']}  {item['uploadedAt']}  "
            f"{item.get('name', '')[:60]}"
        )
    print(f"\nToken 到期时间: {token_info.get('expiresAt') or '接口未返回'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="巨量千川 OAuth 授权助手")
    parser.add_argument("--setup", action="store_true", help="重新填写应用参数")
    parser.add_argument("--manual", action="store_true", help="不启动本机回调监听")
    parser.add_argument("--skip-probe", action="store_true", help="授权后不执行接口验证")
    parser.add_argument("--timeout", type=int, default=600, help="等待回调的秒数")
    args = parser.parse_args()

    try:
        config = ensure_config(force_setup=args.setup)
        state = secrets.token_urlsafe(24)
        authorize_url = server.build_oauth_authorize_url(config, state)
        if args.manual:
            print(f"\n授权链接：\n{authorize_url}\n")
            webbrowser.open(authorize_url)
            auth_code = auth_code_from_user_input(
                input("请粘贴完整回调 URL 或 auth_code: ")
            )
        else:
            auth_code = wait_for_local_callback(
                authorize_url,
                str(config.get("redirectUri") or ""),
                state,
                max(30, args.timeout),
            )
        if not auth_code:
            raise RuntimeError("未取得 auth_code")
        print("\n正在使用 auth_code 换取 Access Token……")
        token_record = server.exchange_oauth_code(config, auth_code)
        server.atomic_write_secret_json(server.TOKEN_FILE_PATH, token_record)
        print(f"Access Token 已安全写入：{server.TOKEN_FILE_PATH}")
        print(f"Refresh Token: {'已取得' if token_record.get('refreshToken') else '未返回'}")
        print(f"Access Token 到期: {token_record.get('expiresAt') or '接口未返回'}")
        if not args.skip_probe:
            probe_open_api()
        print("\nOAuth 授权与接口验证完成。")
        return 0
    except KeyboardInterrupt:
        print("\n已取消授权。")
        return 130
    except Exception as exc:
        print(f"\n授权失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
