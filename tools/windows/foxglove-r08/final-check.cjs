const { chromium } = require('../Underbot-Website/node_modules/playwright');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
 const page=browser.contexts()[0].pages().find(p=>p.url().includes('/app.html'));
 await page.getByRole('tab',{name:'Problems',exact:true}).click();
 await page.getByText('No problems found',{exact:true}).waitFor({timeout:10000});
 console.log('PASS: Foxglove reports no problems. Navigation simulation connected.');
 await page.getByRole('button',{name:'Hide left sidebar'}).click();
 await page.screenshot({path:__dirname+'/foxglove-r08-ready.png'});
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
