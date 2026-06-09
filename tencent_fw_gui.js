const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ 
    headless: false,
    channel: undefined
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('正在打开腾讯云控制台，请在弹出的浏览器窗口中登录...');
  
  // 跳转到防火墙设置页面
  await page.goto('https://console.cloud.tencent.com/lighthouse/instance/security?instanceId=lhins-3nmd98is', { 
    waitUntil: 'domcontentloaded',
    timeout: 30000 
  });
  
  console.log('页面已打开，请手动登录(邮箱:13818912672 / 密码:hj711201)');
  console.log('登录后，添加规则: 端口443, 协议TCP, 来源0.0.0.0/0');
  console.log('完成后关闭浏览器窗口即可');
  
  // 等待用户操作并关闭
  await page.waitForTimeout(120000);
  
  console.log('超时关闭');
  await browser.close();
})();
