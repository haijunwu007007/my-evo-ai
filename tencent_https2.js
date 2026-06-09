const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--no-sandbox']
  });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  
  console.log('正在打开腾讯云控制台...');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded',
    timeout: 60000 
  });
  console.log('页面加载完成');
  await page.waitForTimeout(5000);
  
  // Save screenshot
  await page.screenshot({ path: 'tencent_login.png', fullPage: false });
  console.log('截图已保存: tencent_login.png');
  console.log('当前URL:', page.url());
  
  // Try email login
  try {
    const emailTab = page.locator('text=邮箱登录');
    if (await emailTab.isVisible({ timeout: 3000 })) {
      await emailTab.click();
      console.log('点击邮箱登录');
      await page.waitForTimeout(2000);
    }
  } catch(e) { console.log('已有登录或无邮箱标签'); }
  
  // Fill credentials
  try {
    const inputs = page.locator('input[type="text"], input[type="password"]');
    const count = await inputs.count();
    console.log(`输入框数量: ${count}`);
    if (count >= 2) {
      await inputs.nth(0).fill('13818912672');
      await inputs.nth(1).fill('hj711201');
      console.log('已填写账号密码');
    }
  } catch(e) { console.log('填写失败:', e.message); }
  
  // Click login button
  try {
    await page.locator('button:has-text("登录")').first().click({ timeout: 3000 });
    console.log('已点击登录');
    await page.waitForTimeout(15000);
  } catch(e) { console.log('登录按钮点击失败:', e.message); }
  
  // Check if CAPTCHA
  await page.screenshot({ path: 'tencent_after_login.png', fullPage: false });
  
  // Wait for login to complete (manual CAPTCHA if needed)
  console.log('等待登录完成...如果遇到验证码请在浏览器中手动完成');
  for (let i = 0; i < 12; i++) {
    await page.waitForTimeout(10000);
    if (!page.url().includes('passport')) {
      console.log('登录成功!');
      break;
    }
    console.log(`等待中...${i+1}/12`);
  }
  
  // Navigate to firewall
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded',
    timeout: 30000 
  });
  await page.waitForTimeout(3000);
  
  // Add rule
  try {
    const addBtn = page.locator('button:has-text("添加规则"), span:has-text("添加规则")').first();
    await addBtn.click({ timeout: 5000 });
    console.log('已点击添加规则');
    await page.waitForTimeout(2000);
  } catch(e) { console.log('添加规则按钮点击失败:', e.message); }
  
  // Fill port
  try {
    await page.locator('input').first().fill('443');
    console.log('已填端口443');
  } catch(e) { console.log('填写端口失败'); }
  
  // Confirm
  try {
    await page.locator('button:has-text("确定"), span:has-text("确定")').first().click({ timeout: 3000 });
    console.log('已确认添加!');
    await page.waitForTimeout(2000);
  } catch(e) { console.log('确认按钮点击失败:', e.message); }
  
  await page.screenshot({ path: 'tencent_fw_result.png', fullPage: false });
  console.log('最终截图已保存');
  
  await page.waitForTimeout(5000);
  await browser.close();
  console.log('完成');
})();
