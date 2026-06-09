const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  // Step 1: Login
  console.log('=== LOGIN ===');
  await page.goto('https://cloud.tencent.com/login?s_url=https%3A%2F%2Fconsole.cloud.tencent.com%2F', { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await page.waitForTimeout(3000);
  console.log('Title:', await page.title());
  
  // Fill email login
  try {
    const emailTab = page.locator('text=邮箱登录');
    if (await emailTab.isVisible({ timeout: 2000 })) {
      await emailTab.click();
      await page.waitForTimeout(1000);
    }
  } catch(e) {}
  
  const inputs = page.locator('input');
  const count = await inputs.count();
  console.log(`Inputs: ${count}`);
  
  if (count >= 2) {
    await inputs.nth(0).fill('13818912672');
    await inputs.nth(1).fill('hj711201');
    await page.locator('button:has-text("登录")').first().click();
    console.log('Login clicked');
    await page.waitForTimeout(5000);
  }
  
  // Wait for login to complete
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(3000);
    const url = page.url();
    console.log(`URL after ${i+1}s:`, url.substring(0,100));
    if (url.includes('console.cloud.tencent.com') && !url.includes('login')) {
      console.log('LOGGED IN!');
      break;
    }
  }
  
  // Step 2: Navigate to firewall
  console.log('\n=== FIREWALL ===');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'networkidle', timeout: 60000 
  });
  await page.waitForTimeout(5000);
  console.log('Title:', await page.title());
  
  // Get page text
  const text = await page.locator('body').textContent();
  console.log('Page text (first 500):', text.substring(0, 500));
  
  // Button check
  const btnText = await page.locator('button').allTextContents();
  console.log('Buttons:', btnText.join(' | '));
  
  // Try different approaches to find add button
  const addSelectors = [
    'text=添加规则',
    'button:has-text("添加")',
    'span:has-text("添加")',
    '.add-rule',
    '[class*="add"]',
    '[class*="rule"]'
  ];
  
  for (const sel of addSelectors) {
    const vis = await page.locator(sel).first().isVisible().catch(() => false);
    console.log(`Selector "${sel}": visible=${vis}`);
  }
  
  await page.screenshot({ path: 'fw_page.png', fullPage: false });
  console.log('\nScreenshot saved');
  
  await browser.close();
  console.log('DONE');
})();
