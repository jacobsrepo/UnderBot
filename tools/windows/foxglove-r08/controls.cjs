const { chromium } = require('../Underbot-Website/node_modules/playwright');
(async()=>{const b=await chromium.connectOverCDP('http://127.0.0.1:9223');const p=b.contexts()[0].pages().find(p=>p.url().includes('/app.html')); console.log(await p.locator('button').evaluateAll(es=>es.map(e=>({text:e.innerText,label:e.getAttribute('aria-label'),title:e.getAttribute('title')})))); await b.close()})()
