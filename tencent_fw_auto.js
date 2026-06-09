const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox']
  });
  const page = await browser.newPage({ 
    viewport: { width: 1280, height: 900 }
  });
  
  // 直接跳转到防火墙设置页面（用户已登录，浏览器cookie应该还生效）
  console.log('正在打开防火墙设置页面...');
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await page.waitForTimeout(5000);
  
  const url = page.url();
  const title = await page.title();
  console.log(`Title: ${title}, URL: ${url.substring(0,80)}`);
  
  // 如果跳转到登录页，说明cookie失效
  if (url.includes('login') || title.includes('登录')) {
    console.log('需要登录...');
    
    // 填账号密码
    await page.goto('https://cloud.tencent.com/login?s_url=https%3A%2F%2Fconsole.cloud.tencent.com%2F', { 
      waitUntil: 'domcontentloaded', timeout: 30000 
    });
    await page.waitForTimeout(3000);
    
    // 点击邮箱登录
    try {
      await page.locator('text=邮箱登录').first().click();
      await page.waitForTimeout(1000);
    } catch(e) {}
    
    // 填账号
    const inputs = page.locator('input');
    await inputs.nth(0).fill('13818912672').catch(() => {});
    await inputs.nth(1).fill('hj711201').catch(() => {});
    await page.locator('button:has-text("登录")').first().click();
    console.log('登录中...');
    
    // 等待可能出现的验证码或跳转
    await page.waitForTimeout(15000);
    
    // 再跳转到防火墙
    console.log('跳转到防火墙...');
    await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
      waitUntil: 'domcontentloaded', timeout: 30000 
    });
    await page.waitForTimeout(8000);
  }
  
  console.log('当前页面:', await page.title());
  console.log('URL:', page.url().substring(0,80));
  
  // 获取页面文本
  const bodyText = await page.locator('html').textContent().catch(() => '');
  console.log('页面内容片段:', bodyText.substring(0,600));
  
  // 查找"添加规则"按钮
  const addSelectors = [
    'text=添加规则',
    'button:has-text("添加")',
    'span:has-text("添加")',
    '.lighthouse-security-rule-add',
    '[class*="add"]:visible',
    '.addfirewall',
    '#addRule',
    '[data-v-*] span:has-text("添加")'
  ];
  
  for (const sel of addSelectors) {
    try {
      const el = page.locator(sel).first();
      const vis = await el.isVisible({ timeout: 2000 }).catch(() => false);
      console.log(`选择器 "${sel}": visible=${vis}`);
      if (vis) {
        await el.click();
        console.log(`点击了 "${sel}"`);
        break;
      }
    } catch(e) {
      console.log(`选择器 "${sel}": 错误 ${e.message.substring(0,50)}`);
    }
  }
  
  await page.waitForTimeout(3000);
  
  // 现在找弹出框里的端口输入框
  const allInputs = await page.locator('input[placeholder*="端口"], input[placeholder*="port"], .el-input__inner, input').all();
  console.log(`\n找到 ${allInputs.length} 个input`);
  
  for (let i = 0; i < Math.min(allInputs.length, 10); i++) {
    try {
      const ph = await allInputs[i].getAttribute('placeholder').catch(() => '');
      const val = await allInputs[i].inputValue().catch(() => '');
      console.log(`  Input[${i}]: placeholder="${ph}", value="${val}"`);
    } catch(e) {
      console.log(`  Input[${i}]: error ${e.message.substring(0,40)}`);
    }
  }
  
  // 直接点击第二个或者尝试填充443
  // 通常第一个input是端口
  if (allInputs.length > 0) {
    await allInputs[0].fill('443').catch(() => {});
    console.log('已填入端口443');
  }
  
  // 找确定按钮
  const confirmBtns = ['text=确定', 'button:has-text("确定")', 'span:has-text("确定")', 'button:has-text("确认")'];
  let clickedConfirm = false;
  for (const sel of confirmBtns) {
    try {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 1000 }).catch(() => false)) {
        await el.click();
        console.log(`点击了 "${sel}"`);
        clickedConfirm = true;
        break;
      }
    } catch(e) {}
  }
  
  if (!clickedConfirm) {
    // 可能含有确定文字的按钮
    const allBtns = await page.locator('button').all();
    console.log(`\n总共 ${allBtns.length} 个button`);
    for (let i = 0; i < allBtns.length; i++) {
      try {
        const txt = await allBtns[i].textContent().catch(() => '');
        if (txt.includes('确定') || txt.includes('确认')) {
          console.log(`Button[${i}]: "${txt.substring(0,30)}" -> clicking`);
          await allBtns[i].click();
          break;
        }
      } catch(e) {}
    }
  }
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'fw_result.png', fullPage: false });
  
  console.log('\n截图保存: fw_result.png');
  await browser.close();
  console.log('完成!');
})();
