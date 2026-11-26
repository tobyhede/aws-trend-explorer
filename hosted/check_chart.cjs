// Requires playwright-core and installed Google Chrome. Pass the explorer URL as the first argument.
const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

async function check() {
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    for (const width of [1200, 375]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(process.argv[2]);
      const panels = page.locator('#annualTrends .panel');
      await panels.first().waitFor();
      assert.equal(await panels.count(), 7);
      assert.ok(await page.locator('#annual table').isVisible());
      const years = await page.locator('#annual thead th').count() - 1;
      for (const panel of await panels.all()) {
        assert.equal(await panel.locator('polyline').evaluate(node => node.points.length), years);
        assert.equal(await panel.locator('circle').count(), years);
      }
      // Each panel's end label is the last column of the matching table row.
      const endLabels = () => page.locator('#annualTrends text.end').allTextContents();
      const lastColumn = async () => (await page.locator('#annual tbody tr td:last-child').allTextContents()).slice(0, 7);
      assert.deepEqual(await endLabels(), await lastColumn());
      const unfiltered = await endLabels();
      await page.locator('#service').selectOption('aws-lambda');
      assert.notDeepEqual(await endLabels(), unfiltered);
      assert.deepEqual(await endLabels(), await lastColumn());
      await page.locator('#clear').click();
      await page.waitForFunction(expected => [...document.querySelectorAll('#annualTrends text.end')].map(t => t.textContent).join() === expected, unfiltered.join());

      const first = page.locator('#annualLegend input[value="1"]');
      await first.uncheck();
      assert.equal(await panels.count(), 6);
      await first.check();
      await page.locator('#annualLegend input[value="total"]').check();
      assert.equal(await panels.count(), 8);

      const point = page.locator('#annualTrends rect.hit[data-series="1"]').first();
      await point.hover();
      assert.match(await page.locator('.tip').innerText(), /Parameter change/);
      await point.click();
      assert.match(await page.locator('#selection').innerText(), /Parameter change/);
      assert.equal(await page.locator('#annualTrends circle.selected').count(), 1);

      await page.locator('#monthly rect.seg').first().hover();
      assert.equal(await page.locator('.tip div').count(), 8);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'page scrolls sideways');
      console.log(width + 'px: panels, filters, series picker, tooltips, drill-down and page width passed');
      await page.close();
    }
  } finally {
    await browser.close();
  }
}
check().catch(error => { console.error(error); process.exitCode = 1; });
