const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36'
  });

  await page.goto('https://world-clim-extractor.streamlit.app/', {
    waitUntil: 'load',
    timeout: 60000
  });

  // Zadrži se 10 sekundi kao pravi korisnik
  await page.waitForTimeout(10000);

  await browser.close();
})();
