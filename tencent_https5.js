const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  // Login
  console.log('=== LOGIN ===');
  await page.goto('https://cloud.tencent.com/login?s_url=https%3A%2F%2Fconsole.cloud.tencent.com%2F', { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await page.waitForTimeout(3000);
  
  await page.locator('text=邮箱登录').first().click().catch(() => {});
  await page.waitForTimeout(1000);
  
  const inputs = page.locator('input');
  await inputs.nth(0).fill('13818912672').catch(() => {});
  await inputs.nth(1).fill('hj711201').catch(() => {});
  await page.locator('button:has-text("登录")').first().click();
  console.log('Login clicked');
  
  // Wait for login
  for (let i = 0; i < 12; i++) {
    await page.waitForTimeout(5000);
    const url = page.url();
    if (url.includes('console.cloud.tencent.com') && !url.includes('login') && !url.includes('passport')) {
      console.log('LOGGED IN!', url.substring(0,80));
      break;
    }
    console.log(`Waiting login... ${i+1}/12`);
  }
  
  // Firewall page - use domcontentloaded
  console.log('\n=== FIREWALL ===');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await page.waitForTimeout(8000);
  console.log('Title:', await page.title());
  
  // Get all clickable text
  const bodyText = await page.locator('body').textContent();
  const addMatch = bodyText.match(/.{0,100}添加.{0,100}/);
  console.log('"添加" context:', addMatch ? addMatch[0] : 'NOT FOUND');
  
  // Try clicking the add button by text
  const addBtn = page.locator('text=添加规则').first();
  const addVisible = await addBtn.isVisible().catch(() => false);
  console.log('Add rule visible:', addVisible);
  
  if (addVisible) {
    await addBtn.click();
    console.log('Clicked add rule');
    await page.waitForTimeout(3000);
  } else {
    // Try clicking button by text content
    const allBtns = page.locator('button');
    const btnCount = await allBtns.count();
    console.log(`Total buttons: ${btnCount}`);
    for (let i = 0; i < btnCount; i++) {
      const txt = await allBtns.nth(i).textContent();
      if (txt.includes('添加') || txt.includes('新建')) {
        console.log(`Found add button[${i}]: "${txt.substring(0,30)}"`);
        await allBtns.nth(i).click();
        await page.waitForTimeout(3000);
        break;
      }
    }
  }
  
  await page.screenshot({ path: 'fw_after_add.png', fullPage: false });
  
  // Check for dialog and fill port
  const dialogInputs = page.locator('input');
  const diCount = await dialogInputs.count();
  console.log(`Dialog inputs: ${diCount}`);
  for (let i = 0; i < diCount; i++) {
    const ph = await dialogInputs.nth(i).getAttribute('placeholder').catch(() => '');
    console.log(`  Input[${i}]: placeholder="${ph}"`);
  }
  
  if (diCount > 0) {
    await dialogInputs.first().fill('443').catch(() => {});
    console.log('Filled port 443');
  }
  
  // Confirm
  await page.locator('button:has-text("确定")').first().click().catch(() => {
    console.log('Confirm button not found');
  });
  await page.waitForTimeout(2000);
  
  await page.screenshot({ path: 'fw_final.png', fullPage: false });
  console.log('Done!');
  
  await browser.close();
})();
