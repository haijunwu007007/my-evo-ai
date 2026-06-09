const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  console.log('1. 打开腾讯云...');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'step1.png', fullPage: false });
  console.log('URL:', page.url().substring(0, 80));
  
  // Check if redirected to login
  if (page.url().includes('passport') || page.url().includes('login')) {
    console.log('2. 检测到登录页面');
    // Try email login
    try {
      const emailTab = page.locator('text=邮箱登录');
      if (await emailTab.isVisible({ timeout: 2000 })) {
        await emailTab.click();
        await page.waitForTimeout(1000);
      }
    } catch(e) {}
    
    // Fill login form  
    const inputs = page.locator('input');
    const count = await inputs.count();
    console.log(`Inputs: ${count}`);
    
    if (count >= 2) {
      await inputs.nth(0).fill('13818912672');
      await inputs.nth(1).fill('hj711201');
      console.log('Credentials filled');
      
      await page.locator('button:has-text("登录")').first().click();
      console.log('Login clicked, waiting for CAPTCHA/redirect...');
      await page.waitForTimeout(8000);
      await page.screenshot({ path: 'step2_after_login.png', fullPage: false });
      
      // Check for CAPTCHA
      const body = await page.locator('body').textContent();
      if (body.includes('captcha') || body.includes('验证码') || body.includes('滑块')) {
        console.log('CAPTCHA detected!');
      } else if (page.url().includes('passport')) {
        console.log('Still on login page - CAPTCHA or error');
      } else {
        console.log('Login successful!');
      }
    }
  }
  
  // Try again if still on login
  if (page.url().includes('passport')) {
    console.log('3. Waiting more for CAPTCHA...');
    for (let i = 0; i < 6; i++) {
      await page.waitForTimeout(10000);
      if (!page.url().includes('passport')) {
        console.log('Logged in!');
        break;
      }
      console.log(`Waiting ${i+1}/6`);
    }
  }
  
  // Navigate to firewall
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded', timeout: 30000
  });
  await page.waitForTimeout(3000);
  
  // Read page to find "添加规则"
  const addBtnText = await page.locator('button, span, div').filter({ hasText: '添加规则' }).first().textContent().catch(() => '');
  console.log('Add rule text:', addBtnText.substring(0, 50));
  
  // Try clicking
  try {
    await page.locator('text=添加规则').first().click({ timeout: 3000 });
    console.log('Clicked add rule');
    await page.waitForTimeout(2000);
  } catch(e) { console.log('Add rule click failed'); }
  
  await page.screenshot({ path: 'step3.png', fullPage: false });
  
  // Look for dialog inputs and fill 443
  const allInputs = page.locator('input');
  const inputCount = await allInputs.count();
  console.log(`Total inputs: ${inputCount}`);
  
  // Try to submit
  try {
    await page.locator('text=确定').first().click({ timeout: 3000 });
    console.log('Confirmed');
  } catch(e) { console.log('Confirm failed'); }
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'step4.png', fullPage: false });
  console.log('Done');
  
  await browser.close();
})();
