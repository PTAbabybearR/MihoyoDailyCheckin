# 原神 国服自动签到

米游社（国服）原神每日签到，跑在 **GitHub Actions** 上定时执行，结果通过 **Server酱** 推送到微信。

## 工作原理

每天定时调用米游社签到接口（`api-takumi.mihoyo.com`），自动领取每日签到奖励，并把结果推送到你的微信。

> ⚠️ **关于验证码**：国服米游社签到接口会**随机触发 geetest 极验验证码**。大多数情况下脚本能正常签到，但偶尔会被拦截，此时通知里会显示「触发了验证码」。这是国服自动签到的固有限制，不是脚本 bug。如果频繁被拦，再考虑接入打码服务。

## 一、获取米游社 Cookie

### 方法 A：扫码登录（推荐，不依赖浏览器）

```bash
pip install requests qrcode pillow
python qr_login.py
```

运行后会弹出二维码图片 → 用 **米游社 App** 扫一扫 → 手机上确认登录 → 脚本自动换出整段 Cookie 并打印，复制粘贴到 GitHub 的 `COOKIE` Secret 即可。失效后重跑一次即可。

### 方法 B：从浏览器读取（Edge/Chrome 新版加密可能读不到）

前提：浏览器里登录了 mihoyo.com。

```bash
pip install browser_cookie3
python get_cookie.py
```

> Edge/Chrome 新版对 Cookie 做了 App-Bound 加密，常常读取失败；读不到就用方法 A。

### 方法 C：开发者工具手动抓（兜底）

1. 电脑浏览器打开并登录 <https://user.mihoyo.com/>（或米游社 <https://bbs.mihoyo.com/>）。
2. 打开签到页 <https://act.mihoyo.com/bbs/event/signin/hk4e/index.html?bbs_auth_required=true&act_id=e202311201442471>。
3. 按 `F12` 打开开发者工具 → `Network`（网络）面板，**勾选「禁用缓存」**，刷新页面，并点 `Fetch/XHR` 只看接口。
4. 随便点一个发往 `api-takumi.mihoyo.com` 的请求 → `Headers` → 找到请求头里的 `Cookie`，**整段复制**。
   - 必须包含 `cookie_token`/`account_id` 或 `ltoken`/`ltuid`/`stoken` 等字段。
5. 多个账号：把每个账号的 Cookie 用 `#` 连接成一行，例如 `cookieA#cookieB`。

## 二、获取 Server酱 SENDKEY

1. 打开 <https://sct.ftqq.com/> 用微信扫码登录。
2. 复制 **SENDKEY**（形如 `SCTxxxxxxxxxxxx`）。
3. 在 Server酱后台「消息通道」里绑定微信，确保能收到推送。

## 三、部署到 GitHub Actions

1. 把本项目推到你自己的 GitHub 仓库（建议设为 **Private**，Cookie 不外泄）。
2. 仓库 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`，添加：
   - `COOKIE`：上面拿到的米游社 Cookie。
   - `SCT_KEY`：Server酱 SENDKEY（不想要通知可不填）。
3. 仓库 → `Actions` → 选中 `Genshin Daily Check-in` → `Run workflow` 手动触发一次，验证能跑通。
4. 之后每天北京时间 ~8:30 自动执行（GitHub cron 有延迟，属正常）。

## 四、本地测试

```bash
pip install -r requirements.txt

# PowerShell
$env:COOKIE="你的Cookie"; $env:SCT_KEY="你的SENDKEY"; python sign.py

# bash
COOKIE="你的Cookie" SCT_KEY="你的SENDKEY" python sign.py
```

## 维护说明

接口、`APP_VERSION`、`DS_SALT`、`ACT_ID` 都可能随官方更新而失效，对应常量集中在 [sign.py](sign.py) 顶部，失效时改那里即可。
