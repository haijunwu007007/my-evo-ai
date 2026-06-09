const { firefox } = require('playwright');
(async () => {
  const browser = await firefox.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  console.log('Starting Firefox automation...');
  
  // 1. 直接去轻量应用服务器防火墙页面
  const fwUrl = 'https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is';
  await page.goto(fwUrl, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(e => {
    console.log('Goto error:', e.message.substring(0, 60));
  });
  await page.waitForTimeout(5000);
  
  const title = await page.title();
  const url = page.url();
  console.log(`Title: "${title}"`);
  console.log(`URL: ${url.substring(0,80)}`);
  
  // 如果跳转到登录页，尝试登录
  if (url.includes('login') || title.includes('登录')) {
    console.log('Login page detected. Trying email login...');
    
    // 填邮箱登录
    await page.fill('input[type="text"]', '13818912672').catch(() => {});
    await page.waitForTimeout(500);
    await page.fill('input[type="password"]', 'hj711201').catch(() => {});
    await page.waitForTimeout(500);
    
    // 点击登录
    const loginBtns = page.locator('button');
    const btnCount = await loginBtns.count();
    for (let i = 0; i < btnCount; i++) {
      const txt = await loginBtns.nth(i).textContent().catch(() => '');
      if (txt.includes('登录')) {
        await loginBtns.nth(i).click();
        console.log('Clicked login');
        break;
      }
    }
    
    // 等登录（含验证码可能需要等待）
    await page.waitForTimeout(15000);
    
    // 再跳转到防火墙
    await page.goto(fwUrl, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(8000);
  }
  
  const title2 = await page.title();
  const url2 = page.url();
  console.log(`After login - Title: "${title2}", URL: ${url2.substring(0,80)}`);
  
  // 获取页面文本找"添加规则"
  const html = await page.locator('html').textContent().catch(() => '');
  const addIdx = html.indexOf('添加规则');
  const addIdx2 = html.indexOf('添加防火墙规则');
  console.log(`Found "添加规则" at: ${addIdx}`);
  console.log(`Found "添加防火墙规则" at: ${addIdx2}`);
  
  if (addIdx >= 0) {
    console.log('Context:', html.substring(Math.max(0,addIdx-30), addIdx+80));
  }
  
  // 截图看看
  await page.screenshot({ path: 'fw_page_firefox.png', fullPage: false });
  
  await browser.close();
  console.log('DONE');
})();
