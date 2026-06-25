#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原神 国服米游社 自动签到
- 多账号：COOKIE 用 # 或换行分隔
- 通知：Server酱 Turbo（SCT_KEY），推送到微信
环境变量：
  COOKIE   必填，米游社 Cookie（多个用 # 分隔）
  SCT_KEY  选填，Server酱 Turbo 的 SENDKEY
"""

import os
import time
import random
import string
import hashlib

import requests

# ============ 配置（接口/版本会变，失效时改这里）============
# 国服原神现用 luna 新接口（/event/luna/...），act_id 见签到页 URL
ACT_ID = "e202311201442471"  # 国服原神签到活动 ID
LANG = "zh-cn"
APP_VERSION = "2.71.1"       # 米游社 App 版本号，DS 校验需要时随官方更新
DS_SALT = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"  # web 端 DS salt（如失效需更新）

ROLE_URL = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"
INFO_URL = "https://api-takumi.mihoyo.com/event/luna/info"
HOME_URL = "https://api-takumi.mihoyo.com/event/luna/home"
SIGN_URL = "https://api-takumi.mihoyo.com/event/luna/sign"

REFERER = ("https://act.mihoyo.com/bbs/event/signin/hk4e/index.html"
           "?bbs_auth_required=true&act_id=" + ACT_ID)


def get_ds() -> str:
    """计算 web 端 DS 动态签名 (t,r,md5)。"""
    t = str(int(time.time()))
    r = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    c = hashlib.md5(f"salt={DS_SALT}&t={t}&r={r}".encode()).hexdigest()
    return f"{t},{r},{c}"


def build_headers(cookie: str) -> dict:
    return {
        "Cookie": cookie,
        "DS": get_ds(),
        "x-rpc-app_version": APP_VERSION,
        "x-rpc-client_type": "5",
        "x-rpc-platform": "4",
        "x-rpc-channel": "appstore",
        "x-rpc-device_id": "".join(random.choices(string.hexdigits.lower(), k=32)),
        "User-Agent": (f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                       f"AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/{APP_VERSION}"),
        "Referer": REFERER,
        "Origin": "https://act.mihoyo.com",
        "Accept": "application/json, text/plain, */*",
    }


class SignError(Exception):
    pass


def get_roles(cookie: str) -> list:
    """获取该 Cookie 下的原神角色列表。"""
    r = requests.get(ROLE_URL, headers=build_headers(cookie), timeout=20).json()
    if r.get("retcode") != 0:
        raise SignError(f"获取角色失败: {r.get('message')} (retcode={r.get('retcode')})")
    roles = (r.get("data") or {}).get("list") or []
    if not roles:
        raise SignError("该账号下没有原神角色，请确认 Cookie 是国服账号")
    return roles


def sign_one_role(cookie: str, role: dict) -> str:
    """对单个角色签到，返回结果文本。"""
    region = role["region"]
    uid = role["game_uid"]
    nickname = role.get("nickname", uid)
    headers = build_headers(cookie)

    # 已签天数信息
    info = requests.get(
        INFO_URL, params={"lang": LANG, "act_id": ACT_ID, "region": region, "uid": uid},
        headers=headers, timeout=20,
    ).json()
    if info.get("retcode") != 0:
        return (f"❌ {nickname}({uid}) 查询签到信息失败: {info.get('message')} "
                f"(retcode={info.get('retcode')})")
    data = info.get("data") or {}
    if data.get("is_sign"):
        total = data.get("total_sign_day", "?")
        return f"➖ {nickname}({uid}) 今天已签过，本月累计 {total} 天"

    # 执行签到
    resp = requests.post(
        SIGN_URL,
        json={"act_id": ACT_ID, "region": region, "uid": uid, "lang": LANG},
        headers=headers, timeout=20,
    ).json()
    retcode = resp.get("retcode")
    rdata = resp.get("data") or {}

    if retcode == 0 and not rdata.get("risk_code"):
        total = (data.get("total_sign_day") or 0) + 1
        return f"✅ {nickname}({uid}) 签到成功，本月累计 {total} 天"
    if retcode == -5003:
        return f"➖ {nickname}({uid}) 今天已签过"
    if rdata.get("risk_code") or rdata.get("gt"):
        return f"⚠️ {nickname}({uid}) 触发了验证码(geetest)，本次签到被拦截，需人工或打码"
    return f"❌ {nickname}({uid}) 签到失败: {resp.get('message')} (retcode={retcode})"


def run_account(cookie: str, idx: int) -> str:
    head = f"【账号{idx}】"
    try:
        roles = get_roles(cookie)
        lines = [sign_one_role(cookie, role) for role in roles]
        return head + "\n" + "\n".join(lines)
    except SignError as e:
        return f"{head}\n❌ {e}"
    except Exception as e:  # noqa: BLE001
        return f"{head}\n❌ 异常: {e}"


def notify(title: str, content: str):
    key = os.environ.get("SCT_KEY", "").strip()
    if not key:
        return
    try:
        requests.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data={"title": title, "desp": content},
            timeout=20,
        )
        print("已推送 Server酱 通知")
    except Exception as e:  # noqa: BLE001
        print(f"通知推送失败: {e}")


def main():
    raw = os.environ.get("COOKIE", "").strip()
    if not raw:
        print("未设置 COOKIE 环境变量")
        raise SystemExit(1)

    cookies = [c.strip() for c in raw.replace("\n", "#").split("#") if c.strip()]
    results = []
    for i, ck in enumerate(cookies, 1):
        res = run_account(ck, i)
        print(res)
        results.append(res)
        time.sleep(random.uniform(2, 5))  # 账号间随机间隔，降低风控

    summary = "\n\n".join(results)
    notify("原神签到结果", summary)


if __name__ == "__main__":
    main()
