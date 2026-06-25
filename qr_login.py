#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫码登录 → 自动获取米游社 Cookie（不依赖浏览器）

用法：
  pip install requests qrcode pillow
  python qr_login.py

流程：运行后弹出二维码 → 用【米游社 App】扫一扫 → 手机上确认登录
      → 脚本自动换出 Cookie 并打印 → 复制粘贴到 GitHub 的 COOKIE Secret。

⚠️ 输出的 Cookie = 账号钥匙，只填进 GitHub Secrets，别发任何人。
"""

import time
import json
import uuid
import random
import string
import hashlib
import os
import sys

import requests

SALT = "JwYDpKvLj6MrMqqYU6jTKF17KNO2PXoS"  # passport web DS 盐（失效时更新）
APP_ID = "bll8iq97cem8"                     # 米游社 bbs
PASSPORT = "https://passport-api.mihoyo.com/account/ma-cn-passport/web"
DEVICE = uuid.uuid4().hex


def ds(body: str = "", query: str = "") -> str:
    t = str(int(time.time()))
    r = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    c = hashlib.md5(f"salt={SALT}&t={t}&r={r}&b={body}&q={query}".encode()).hexdigest()
    return f"{t},{r},{c}"


def headers(body: str = "") -> dict:
    return {
        "x-rpc-app_id": APP_ID,
        "x-rpc-device_id": DEVICE,
        "x-rpc-client_type": "2",
        "DS": ds(body=body),
        "Content-Type": "application/json",
        "User-Agent": "okhttp/4.9.3",
    }


def create_qr():
    body = "{}"
    r = requests.post(f"{PASSPORT}/createQRLogin", data=body,
                      headers=headers(body), timeout=20).json()
    if r.get("retcode") != 0:
        raise SystemExit(f"取二维码失败: {r.get('message')} ({r.get('retcode')})")
    return r["data"]["url"], r["data"]["ticket"]


def show_qr(url: str):
    import qrcode
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    # 主：存成图片并自动弹开，用米游社 App 扫这张图
    saved = False
    try:
        img = qr.make_image()
        path = os.path.abspath("login_qr.png")
        img.save(path)
        print(f"二维码已生成: {path}")
        if sys.platform == "win32":
            os.startfile(path)  # 自动弹开图片
            print("（已自动打开图片，用米游社 App 扫它）")
        saved = True
    except Exception as e:  # noqa: BLE001
        print(f"图片生成失败: {e}")
    # 备用：终端打印（GBK 控制台可能不支持方块字符，崩了忽略）
    try:
        qr.print_ascii(invert=True)
    except Exception:
        if not saved:
            print("终端无法显示二维码，且图片生成失败，请检查 pillow 是否安装")


def poll(ticket: str) -> dict:
    print("\n请用【米游社 App】扫描上面的二维码，并在手机上确认登录...")
    body = json.dumps({"ticket": ticket}, separators=(",", ":"))
    last = None
    for _ in range(150):  # ~5 分钟
        r = requests.post(f"{PASSPORT}/queryQRLoginStatus", data=body,
                          headers=headers(body), timeout=20).json()
        if r.get("retcode") != 0:
            raise SystemExit(f"二维码已失效: {r.get('message')} ({r.get('retcode')})，请重跑脚本")
        data = r["data"]
        st = data.get("status")
        if st != last:
            print({"Created": "  · 等待扫描...",
                   "Scanned": "  · 已扫描，请在手机上点【确认登录】",
                   "Confirmed": "  · 已确认 ✅"}.get(st, f"  · {st}"))
            last = st
        if st == "Confirmed":
            return data
        time.sleep(2)
    raise SystemExit("超时未确认，请重跑脚本")


def get_cookie_token(stoken, aid, mid):
    ck = f"stuid={aid};stoken={stoken};mid={mid}"
    r = requests.get(
        "https://api-takumi.mihoyo.com/auth/api/getCookieAccountInfoBySToken",
        params={"stoken": stoken, "uid": aid},
        headers={"Cookie": ck, "x-rpc-app_id": APP_ID}, timeout=20).json()
    if r.get("retcode") == 0 and r.get("data"):
        return r["data"].get("cookie_token")
    return None


def get_ltoken(stoken, aid, mid):
    ck = f"stuid={aid};stoken={stoken};mid={mid}"
    r = requests.get(
        "https://passport-api.mihoyo.com/account/auth/api/getLTokenBySToken",
        headers={"Cookie": ck, "x-rpc-app_id": APP_ID, "DS": ds()}, timeout=20).json()
    if r.get("retcode") == 0 and r.get("data"):
        return r["data"].get("ltoken")
    return None


def main():
    url, ticket = create_qr()
    show_qr(url)
    data = poll(ticket)

    ui = data.get("user_info") or {}
    aid, mid = ui.get("aid"), ui.get("mid")
    tokens = [t.get("token") for t in (data.get("tokens") or []) if t.get("token")]

    # 自动识别哪个 token 是 stoken（能换出 cookie_token 的就是）
    stoken = cookie_token = None
    for t in tokens:
        ct = get_cookie_token(t, aid, mid)
        if ct:
            stoken, cookie_token = t, ct
            break

    if not cookie_token:
        print("\n⚠️ 没能换出 cookie_token，诊断信息（发给协助者）：")
        print("  user_info keys:", list(ui.keys()))
        print("  token_types:", [t.get("token_type") for t in (data.get("tokens") or [])])
        sys.exit(1)

    ltoken = get_ltoken(stoken, aid, mid)

    parts = [f"account_id={aid}", f"cookie_token={cookie_token}",
             f"ltuid={aid}", f"stuid={aid}", f"mid={mid}", f"stoken={stoken}"]
    if ltoken:
        parts += [f"ltoken={ltoken}", f"ltuid={aid}"]

    cookie_str = ";".join(parts)
    print("\n========== 复制下面这一整行 → 粘贴到 GitHub 的 COOKIE Secret ==========\n")
    print(cookie_str)
    print("\n========== 复制到上面这行结束 ==========")
    print("\n⚠️ 这串 = 账号钥匙，只填进 GitHub Secrets，别发给任何人。")


if __name__ == "__main__":
    main()
