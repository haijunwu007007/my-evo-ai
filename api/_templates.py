"""
AUTO-EVO-AI V0.1 — HTML 页面模板
将原有 Python 路由文件中的大段 HTML 抽取至此。
"""

# ── QR 码页面模板（使用 $URL$ 占位符替换局域网地址）──
QR_PAGE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>扫码访问</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui;text-align:center;padding:40px 20px;background:#0f0f1a;color:#e2e8f0;}
h1{font-size:20px;color:#6366f1;}.box{background:#1a1a2e;border-radius:16px;padding:30px;margin:20px auto;max-width:360px;}
.info{font-size:13px;color:#9ca3af;margin:16px 0;}
code{background:#2d2d44;padding:6px 12px;border-radius:6px;font-size:13px;color:#06b6d4;word-break:break-all;}
.btn{display:inline-block;margin:12px 6px;padding:10px 24px;border-radius:10px;text-decoration:none;font-size:14px;border:none;cursor:pointer;font-family:inherit;}
.btn-p{background:#6366f1;color:#fff;}.btn-g{background:#10b981;color:#fff;}
input{width:100%;padding:10px;border:1px solid #334;border-radius:8px;background:#16213e;color:#e2e8f0;font-size:14px;box-sizing:border-box;font-family:inherit;}
.tun-box{display:none;background:#0a1f14;border-radius:12px;padding:16px;margin:12px 0;border:1px solid #10b981;}</style></head><body>
<div class="box">
<h1>&#x1F4F1; 扫码访问</h1>
<img src="https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=$URL$" alt="QR" id="qr-img">
<p class="info">同一WiFi扫码，或贴外网地址&#x2193;</p>
<code id="url-display">$URL$</code>
<hr style="border:none;border-top:1px solid #334;margin:20px 0;">
<p style="font-size:14px;color:#9ca3af;">&#x1F310; 外网访问（粘贴隧道地址）：</p>
<input id="tun-in" type="text" placeholder="粘贴 https://xxx.trycloudflare.com ...">
<button class="btn btn-g" style="margin-top:8px;width:100%;" onclick="doTun()">生成外网二维码</button>
<div id="tun-box" class="tun-box"></div>
<div style="margin-top:20px;">
<a class="btn btn-p" href="/dashboard">电脑上打开</a>
</div>
<div class="info">AUTO-EVO-AI V0.1</div>
</div>
<script>
function doTun(){
    var u = document.getElementById('tun-in').value.trim();
    if(!u){alert('请粘贴隧道地址');return;}
    if(!u.startsWith('http')) u='https://'+u;
    if(u.indexOf('/dashboard')<0) u+='/dashboard';
    document.getElementById('tun-box').style.display='block';
    document.getElementById('tun-box').innerHTML='<img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data='+encodeURIComponent(u)+'" style="width:200px;height:200px;border-radius:12px;border:2px solid #10b981;"><p style="font-size:12px;color:#9ca3af;margin-top:8px;">手机任意网络扫码可用</p><code>'+u+'</code>';
}
</script>
</body></html>"""


# ── 部署指南页面 ──
DEPLOY_GUIDE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>云部署指南</title>
<style>body{font-family:system-ui;max-width:700px;margin:40px auto;padding:20px;line-height:1.8}
h1{color:#6366f1}code{background:#f4f4f5;padding:2px 6px;border-radius:4px;font-size:13px}
.s{margin:16px 0;padding:16px;background:#fafafa;border-radius:10px;border-left:4px solid #6366f1}
.step{font-weight:700;color:#6366f1}
.qr{text-align:center;margin:16px 0}.s1{border-color:#10b981;background:#f0fdf4}.s2{border-color:#6366f1;background:#eef2ff}.s3{border-color:#f59e0b;background:#fffbeb}.s4{border-color:#06b6d4;background:#ecfeff}</style></head><body>
<h1>&#x2601;&#xFE0F; AUTO-EVO-AI 云部署指南</h1>
<p>让手机/电脑随时随地访问本系统：</p>

<div class="s" style="border-left:4px solid #10b981;background:#0a1f14;">
<span class="step" style="color:#10b981;">&#x1F4F1; 扫码即用（小白首选）</span><br>
<p style="font-size:14px;color:#9ca3af;">手机连接同一WiFi，扫下方二维码直接打开：</p>
<div class="qr"><img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=http://192.168.1.3:8765/dashboard" style="width:220px;height:220px;border-radius:12px;border:2px solid #334;"></div>
<code style="display:block;text-align:center;">http://192.168.1.3:8765/dashboard</code>
<p style="font-size:12px;color:#666;text-align:center;">&#x26A0;&#xFE0F; 手机和电脑必须在同一WiFi下</p>
</div>

<div class="s" style="border-left:4px solid #06b6d4;background:#0a1a25;">
<span class="step" style="color:#06b6d4;">&#x1F310; 外网访问（通过Cloudflare Tunnel）</span><br>
<p style="font-size:13px;color:#9ca3af;">在电脑终端运行以下命令：</p>
<code style="display:block;text-align:center;margin:8px 0;">cloudflared tunnel --url http://127.0.0.1:8765</code>
<p style="font-size:12px;color:#9ca3af;">终端会出现 <span style="color:#06b6d4;">https://xxxx.trycloudflare.com</span> 地址<br>
将它粘贴到 <a href="http://127.0.0.1:8765/api/qr" style="color:#6366f1;">二维码生成页</a> 即可生成外网二维码。</p>
</div>

<div class="s" style="border-left:4px solid #6366f1;background:#111827;">
<span class="step" style="color:#6366f1;">&#x2B50; Cloudflare Tunnel 安装</span><br>
1. 打开终端（Windows键&#x2192;输入 cmd 回车）<br>
2. 执行 <code>winget install Cloudflare.cloudflared</code><br>
3. 执行 <code>cloudflared tunnel --url http://127.0.0.1:8765</code><br>
4. 复制终端输出的 https://xxxx.trycloudflare.com 地址<br>
5. <a href="http://127.0.0.1:8765/api/qr" style="color:#6366f1;">点此生成二维码</a>，手机扫码即用<br>
<span style="font-size:12px;color:#666;">无需云服务器、无需公网IP、免费。</span>
</div>

<div class="s" style="border-left:4px solid #f59e0b;background:#1a150a;">
<span class="step" style="color:#f59e0b;">方案二：Docker 云服务器</span><br>
<code>docker build -t auto-evo-ai D:/AUTO-EVO-AI-V0.1</code><br>
<code>docker run -d -p 8765:8765 auto-evo-ai</code><br>
需要一台云服务器（阿里云/腾讯云/AWS 最低配即可）</div>
<div class="s" style="border-left:4px solid #ec4899;background:#1a0820;">
<span class="step" style="color:#ec4899;">方案三：内网穿透 ngrok</span><br>
<code>ngrok http 8765</code><br>
快速调试用，免费版有域名随机变化限制</div>
<p style="text-align:center;color:#9ca3af;font-size:13px;">部署后把外网地址粘贴到 <a href="http://127.0.0.1:8765/api/qr" style="color:#6366f1;">二维码生成页</a>，手机扫码即用。</p>
</body></html>"""


# ── 使用说明书页面 ──
GUIDE_PAGE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>使用说明书</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui;background:#0f0f1a;color:#e2e8f0;padding:0;line-height:1.6}
h1{font-size:22px;color:#6366f1;margin-bottom:20px}
h2{font-size:17px;color:#e2e8f0;margin:30px 0 12px;display:flex;align-items:center;gap:8px}
h3{font-size:14px;color:#06b6d4;margin:16px 0 8px}
p{font-size:14px;color:#9ca3af;margin:8px 0}
code{background:#2d2d44;padding:2px 6px;border-radius:4px;font-size:13px;color:#06b6d4}
.step-box{background:#1a1a2e;border-radius:12px;padding:20px;margin:16px 0;border-left:4px solid #6366f1}
.step-box.g{border-left-color:#10b981}
.step-box.b{border-left-color:#06b6d4}
.step-box.y{border-left-color:#f59e0b}
.step{display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:28px;height:28px;text-align:center;line-height:28px;font-size:14px;font-weight:700;margin-right:8px}
.btn{display:inline-block;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;margin:8px 4px}
.btn-p{background:#6366f1;color:#fff;border:none;cursor:pointer}
.btn-g{background:#10b981;color:#fff}
.btn-s{background:#2d2d44;color:#e2e8f0}
img{max-width:100%;border-radius:10px;margin:8px 0}
.flag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600}
.flag-g{background:rgba(16,185,129,0.15);color:#10b981}
.flag-y{background:rgba(245,158,11,0.15);color:#f59e0b}
.flag-r{background:rgba(239,68,68,0.15);color:#ef4444}
.warn{background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:10px 14px;margin:8px 0;font-size:13px;color:#f59e0b}
</style></head><body style="max-width:680px;margin:0 auto;padding:20px;">

<h1>&#x1F4D6; AUTO-EVO-AI 使用说明书</h1>
<p>小白也能看懂，5分钟上手。</p>

<h2>&#x1F4E5; 一、下载与解压</h2>
<div class="step-box g">
<p>收到的是一个 zip 压缩包：</p>
<p style="background:#2d2d44;padding:12px;border-radius:8px;text-align:center;font-size:15px;color:#e2e8f0;">
&#x1F4E6; AUTO-EVO-AI-V0.1.zip（约5MB）</p>
<p>右键 &#x2192; <strong>解压到当前文件夹</strong> &#x2192; 得到一个文件夹。</p>
<p style="color:#666;font-size:12px;">&#x26A0;&#xFE0F; 不要双击zip直接打开，要右键"解压"出来。</p></div>

<h2>&#x1F680; 二、本地启动（电脑上用）</h2>
<div class="step-box g">
<p><span class="step">1</span>打开解压后的文件夹</p>
<p><span class="step">2</span><strong>双击</strong> <code>&#x4E00;&#x952E;&#x542F;&#x52A8;.bat</code>（图标是齿轮&#x2699;&#xFE0F;）</p>
<p><span class="step">3</span>耐心等 5-10 秒</p>
<p><span class="step">4</span>浏览器会自动打开 Dashboard 界面 &#x2193;</p>
<div style="background:#2d2d44;border-radius:8px;padding:16px;text-align:center;margin:12px 0;">
<div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">&#x1F446; 浏览器会自动打开这个画面</div>
<div style="background:#0f0f1a;border:1px solid #334;border-radius:8px;padding:20px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
<span style="font-size:13px;color:#e2e8f0;">&#x1F9E0; 主编排器</span>
<span style="font-size:11px;color:#6366f1;">V0.1</span></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">&#x1F9E0; 协调中心</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">&#x2699;&#xFE0F; 配置中心</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">&#x23F0; 调度器</div>
<div style="background:#1a1a2e;padding:10px;border-radius:8px;font-size:11px;color:#9ca3af;">&#x26A1; 事件引擎</div></div>
<div style="margin-top:10px;font-size:10px;color:#10b981;">&#x2705; AUTO-EVO-AI V0.1 运行中</div></div></div>
<p style="font-size:13px;color:#10b981;">&#x2705; 系统已在电脑上启动完毕！点左侧菜单开始使用。</p></div>

<h2>&#x1F4F1; 三、手机访问（同一WiFi）</h2>
<div class="step-box b">
<p>电脑启动后，手机也能用：</p>
<p><span class="step">1</span>手机连上<strong>同一个 WiFi</strong></p>
<p><span class="step">2</span>在电脑浏览器上打开 <a href="/api/qr" style="color:#6366f1;">扫码页面</a></p>
<p><span class="step">3</span>用手机微信/浏览器扫二维码</p>
<p><span class="step">4</span>手机浏览器直接打开系统 &#x2192; 随意操作</p>
<div class="warn">&#x26A0;&#xFE0F; 某些公司/公共WiFi会阻止设备互访，如无法连接请切换到家里的WiFi。</div></div>

<h2>&#x1F310; 四、远程访问（任何地方）</h2>
<div class="step-box b">
<p>想让手机<strong>在外面</strong>也能用？很简单：</p>
<p><span class="step">1</span>在电脑文件夹里找到 <code>&#x542F;&#x52A8;&#x5916;&#x7F51;&#x8BBF;&#x95EE;.bat</code>，<strong>双击</strong></p>
<p><span class="step">2</span>会弹出两个窗口：</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;">
<div style="background:#2d2d44;border-radius:6px;padding:10px;font-size:11px;color:#9ca3af;">&#x2699;&#xFE0F; API服务窗口<br><span style="color:#10b981;">（最小化不用管）</span></div>
<div style="background:#2d2d44;border-radius:6px;padding:10px;font-size:11px;color:#9ca3af;">&#x1F310; 隧道窗口<br><span style="color:#f59e0b;">（等它出现地址）</span></div></div>
<p><span class="step">3</span>等待 10-30 秒，隧道窗口里会出现一行文字：</p>
<code style="display:block;text-align:center;padding:10px;margin:8px 0;font-size:12px;background:#0f0f1a;">
https://xxxx.trycloudflare.com</code>
<p><span class="step">4</span>复制这行地址，粘贴到刚才的<a href="/api/qr" style="color:#6366f1;">扫码页面</a></p>
<p><span class="step">5</span>点"生成外网二维码" &#x2192; 手机扫码即可</p>
<p><span class="step">6</span><strong>【推荐】</strong>手机浏览器点"分享"&#x2192;"添加到主屏幕"，就像App一样用</p></div>

<h2>&#x2753; 五、常见问题</h2>
<div class="step-box y">
<p><strong>Q: 双击 .bat 文件没反应？</strong><br>
A: 右键 &#x2192; "以管理员身份运行"。或者先装 Python：<a href="https://www.python.org/downloads/" style="color:#06b6d4;" target="_blank">python.org/downloads</a> 下载安装（勾选"Add to PATH"）。</p>
<p style="margin-top:12px;"><strong>Q: 手机扫码打不开？</strong><br>
A: 检查手机和电脑是否连接<strong>同一个WiFi</strong>。如果是公司网络，换家里WiFi再试。</p>
<p style="margin-top:12px;"><strong>Q: "外网访问"的隧道窗口等了很久没出现地址？</strong><br>
A: 确保电脑能访问外网。有些公司网络会屏蔽 cloudflared，这时只能用同一WiFi方案。</p>
<p style="margin-top:12px;"><strong>Q: 按钮点了没反应？</strong><br>
A: 确保地址栏是 <code>http://127.0.0.1:8765/dashboard</code>，不是 8080 端口。</p>
<p style="margin-top:12px;"><strong>Q: 怎么关掉系统？</strong><br>
A: 直接关掉黑色的命令行窗口就行，或者重启电脑。</p></div>

<div style="text-align:center;margin:30px 0 20px;padding:20px;border-top:1px solid #334;">
<p style="font-size:12px;color:#666;">AUTO-EVO-AI V0.1 &#x2014; 有问题找开发者</p>
<p><a href="/api/qr" class="btn btn-p">&#x1F4F1; 扫码访问页面</a> <a href="/dashboard" class="btn btn-s">&#x1F4CA; 回 Dashboard</a></p></div>
</body></html>"""
