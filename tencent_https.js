const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ 
    headless: false,
    channel: undefined,
    args: ['--no-sandbox']
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  console.log('Step 1: 登录腾讯云...');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'networkidle',
    timeout: 30000 
  });
  
  await page.waitForTimeout(3000);
  
  // Check if already logged in, or need to login
  const loginBtn = await page.locator('button:has-text("登录")');
  if (await loginBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('Step 2: 切换到邮箱登录...');
    const emailTab = page.locator('text=邮箱登录');
    if (await emailTab.isVisible().catch(() => false)) {
      await emailTab.click();
      await page.waitForTimeout(1000);
    }
    
    // Fill credentials
    const inputs = page.locator('input[type="text"], input[type="password"]');
    const count = await inputs.count();
    console.log(`Found ${count} inputs`);
    if (count >= 2) {
      await inputs.nth(0).fill('13818912672');
      await inputs.nth(1).fill('hj711201');
      console.log('Credentials filled');
    }
    
    // Click login
    await page.locator('button:has-text("登录")').click();
    console.log('Login clicked, waiting...');
    await page.waitForTimeout(10000);
  }
  
  // Take screenshot to see where we are
  await page.screenshot({ path: 'tencent_login.png', fullPage: false });
  console.log('Screenshot saved as tencent_login.png');
  
  // Check current URL
  console.log('Current URL:', page.url());
  
  // If there's a CAPTCHA, wait for user to solve it
  const captcha = page.locator('#captcha, .captcha, iframe[src*="captcha"]');
  if (await captcha.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('CAPTCHA detected! Waiting for manual solving (60s)...');
    await page.waitForTimeout(60000);
  }
  
  // Navigate to firewall page
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'networkidle',
    timeout: 30000 
  });
  await page.waitForTimeout(3000);
  
  // Click "添加规则" button
  const addBtn = page.locator('button:has-text("添加规则"), span:has-text("添加规则")');
  if (await addBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
    await addBtn.click();
    await page.waitForTimeout(2000);
    console.log('Add rule button clicked');
  }
  
  // Fill port field
  const portInput = page.locator('input[placeholder*="端口"], input[placeholder*="Port"]');
  if (await portInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    await portInput.fill('443');
  }
  
  // Click confirm
  const confirmBtn = page.locator('button:has-text("确定"), span:has-text("确定")');
  if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await confirmBtn.click();
    await page.waitForTimeout(2000);
    console.log('Port 443 added!');
  }
  
  await page.screenshot({ path: 'tencent_fw_result.png', fullPage: false });
  console.log('Final screenshot saved');
  
  await browser.close();
})();
