const { chromium } = require('../Underbot-Website/node_modules/playwright');
(async () => {
 const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
 for (const context of browser.contexts()) for (const page of context.pages()) {
  console.log('PAGE', page.url());
  console.log((await page.locator('body').innerText()).slice(0,13000));
  await page.screenshot({path: __dirname + '/foxglove-r08.png'});
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
