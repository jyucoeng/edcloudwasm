#!/usr/bin/env python3
"""给 dist 副本里的 _worker.js 打补丁：非 WebSocket 的 GET 请求返回一个说明页。

原版 worker 的 fetch 只认 WebSocket 升级和 application/grpc，其余一律 404，
所以浏览器打开域名看到的是空白 404。这里把 404 分支换成 HTML 落地页（只改
部署副本，不动仓库）。
"""
import sys

MARK = "/* __LANDING_PATCH__ */"

LANDING_FN = MARK + r"""
function _landingPage(env) {
    var host = (env && env.HOST) || 'ed.dora.cc.cd';
    var uuid = (env && env.UUID) || '-';
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>edcloudwasm · 服务运行中</title><style>' +
    ':root{color-scheme:dark}*{box-sizing:border-box}' +
    'body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;' +
    'background:radial-gradient(1200px 600px at 50% -10%,#1b2b4b 0%,#0b0f17 60%);' +
    'color:#e6edf3;font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",sans-serif}' +
    '.card{width:min(680px,92vw);padding:34px 32px 26px;border-radius:18px;background:#111823cc;' +
    'border:1px solid #ffffff14;box-shadow:0 24px 70px #0008;backdrop-filter:blur(10px)}' +
    'h1{margin:0 0 6px;font-size:21px;letter-spacing:.3px}' +
    '.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#22c55e;margin-right:8px;' +
    'box-shadow:0 0 0 4px #22c55e2e;animation:p 2s infinite}@keyframes p{50%{opacity:.45}}' +
    '.sub{color:#93a3b8;font-size:13px;margin:0 0 22px}' +
    'table{width:100%;border-collapse:collapse;font-size:14px}' +
    'td{padding:9px 0;border-bottom:1px dashed #ffffff10;vertical-align:top}' +
    'td:first-child{color:#8b9bb4;width:104px;white-space:nowrap}' +
    'code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#8ee0b0;word-break:break-all}' +
    '.tip{margin-top:18px;padding:12px 14px;border-radius:10px;background:#f59e0b14;' +
    'border:1px solid #f59e0b33;color:#f3c98b;font-size:13px}' +
    'footer{margin-top:16px;color:#5b6b82;font-size:12px;text-align:center}' +
    '</style></head><body><div class="card">' +
    '<h1><span class="dot"></span>edcloudwasm</h1>' +
    '<p class="sub">反向代理节点正在运行 / proxy worker is up</p>' +
    '<table>' +
    '<tr><td>地址</td><td><code>' + host + '</code></td></tr>' +
    '<tr><td>端口</td><td><code>443</code>（TLS 开启）</td></tr>' +
    '<tr><td>传输</td><td><code>WebSocket</code>，路径任意</td></tr>' +
    '<tr><td>UUID</td><td><code>' + uuid + '</code></td></tr>' +
    '</table>' +
    '<div class="tip">这个域名不是网页站，只响应 WebSocket 握手。' +
    '你在客户端里填上面这些参数即可；直接打开其他路径返回 404 是设计如此。</div>' +
    '<footer>Cloudflare Pages · edcloudwasm</footer>' +
    '</div></body></html>';
}
"""

OLD_404 = "        return new Response(null, {status: 404});"
NEW_404 = (
    "        if (request.method === 'GET' && !request.headers.get('Upgrade') && env && env.ASSETS) {\n"
    "            const _assetRes = await env.ASSETS.fetch(request);\n"
    "            if (_assetRes.status !== 404) return _assetRes;\n"
    "        }\n"
    "        if (request.method === 'GET' && !request.headers.get('Upgrade') &&\n"
    "            ((new URL(request.url).pathname === '/') ||\n"
    "             ((request.headers.get('accept') || '').indexOf('text/html') >= 0))) {\n"
    "            return new Response(_landingPage(env), {status: 200, headers: {\n"
    "                'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store'}});\n"
    "        }\n"
    "        return new Response(null, {status: 404});"
)


def main(path):
    src = open(path, encoding="utf-8").read()
    if MARK in src:
        print("landing patch: already applied")
        return 0
    if src.count(OLD_404) != 1:
        print("landing patch: FAILED, 404 branch count = %d" % src.count(OLD_404))
        return 1
    idx = src.index("export default {")
    out = src[:idx] + LANDING_FN + "\n" + src[idx:].replace(OLD_404, NEW_404, 1)
    open(path, "w", encoding="utf-8").write(out)
    print("landing patch: applied (%d -> %d bytes)" % (len(src), len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/eddist/_worker.js"))
