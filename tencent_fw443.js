const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: undefined });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.setDefaultTimeout(15000);

  // 1. 登录腾讯云
  console.log('LOGIN: navigating...');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'login_page.png' });

  // 尝试切换到邮箱登录
  try {
    const emailTab = page.locator('text=邮箱登录');
    if (await emailTab.isVisible({timeout: 3000})) {
      await emailTab.click();
      await page.waitForTimeout(1000);
    }
  } catch(e) { console.log('no email tab'); }

  await page.screenshot({ path: 'after_email_tab.png' });

  // 填账号
  const inputs = page.locator('input');
  const count = await inputs.count();
  console.log('INPUTS:', count);
  
  // 找账号和密码输入框
  let accountFilled = false;
  let passwordFilled = false;
  for (let i = 0; i < count && i < 6; i++) {
    const inp = inputs.nth(i);
    const placeholder = await inp.getAttribute('placeholder') || '';
    const type = await inp.getAttribute('type') || '';
    console.log(`INPUT[${i}]: type=${type} placeholder=${placeholder}`);
  }

  await page.fill('input[type="text"]', '13818912672');
  await page.fill('input[type="password"]', 'hj711201');
  await page.waitForTimeout(500);

  // 点击登录按钮
  try {
    await page.click('button:has-text("登录")');
    console.log('LOGIN: clicked login button');
  } catch(e) {
    // try other selectors
    try {
      await page.click('button:has-text("登录")');
    } catch(e2) {
      console.log('LOGIN: button click error:', e2.message);
    }
  }
  
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'after_login.png' });

  // 2. 检查是否登录成功 - 跳转到防火墙设置
  const url = page.url();
  console.log('CURRENT URL:', url);

  // 直接跳转到防火墙页面
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'firewall_page.png' });
  console.log('FW URL:', page.url());

  // 3. 添加443端口规则
  try {
    await page.click('text=添加规则');
    console.log('FW: clicked add rule');
    await page.waitForTimeout(2000);

    // 填端口
    const fwInputs = page.locator('input[placeholder*="端口"]');
    if (await fwInputs.count() > 0) {
      await fwInputs.first().fill('443');
      console.log('FW: filled port 443');
    } else {
      // try broader search
      const allInputs = page.locator('input');
      const ac = await allInputs.count();
      console.log('FW INPUTS:', ac);
    }
    await page.screenshot({ path: 'fw_filled.png' });

    // 点击确定
    await page.click('text=确定');
    console.log('FW: clicked confirm');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'fw_done.png' });
    console.log('FW: DONE');
  } catch(e) {
    console.log('FW ERROR:', e.message);
    await page.screenshot({ path: 'fw_error.png' });
  }

  await browser.close();
  console.log('ALL DONE');
})();
