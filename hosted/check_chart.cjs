// Requires playwright-core and installed Google Chrome. Pass the explorer URL as the first argument.
const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

async function check() {
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    for (const width of [1200, 375]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(process.argv[2]);
      const lines = page.locator('#annualTrends polyline');
      await lines.first().waitFor();
      assert.equal(await lines.count(), 7);
      assert.ok(await page.locator('#annual table').isVisible());
      for (const line of await lines.all()) {
        const style = await line.evaluate(node => {
          const rect = node.ownerSVGElement.getBoundingClientRect();
          const color = getComputedStyle(document.querySelector('#legend .' + node.getAttribute('class'))).backgroundColor;
          return { stroke: getComputedStyle(node).stroke, color,
            left: node.getBoundingClientRect().left - rect.left,
            right: rect.right - node.getBoundingClientRect().right,
            count: node.points.length };
        });
        assert.equal(style.stroke, style.color);
        assert.ok(Math.abs(style.left) < 1 && Math.abs(style.right) < 1);
        assert.equal(style.count, await page.locator('#annual thead th').count() - 1);
      }
      const first = page.locator('#annualLegend input[value="1"]');
      await first.uncheck();
      assert.equal(await lines.count(), 6);
      await first.check();
      await page.locator('#annualLegend input[value="total"]').check();
      assert.equal(await lines.count(), 8);
      await page.locator('#annual tbody button').first().click();
      assert.match(await page.locator('#selection').innerText(), /Parameter change/);
      console.log(width + 'px: table, drill-down, simultaneous series, colors and plot edges passed');
      await page.close();
    }
  } finally {
    await browser.close();
  }
}
check().catch(error => { console.error(error); process.exitCode = 1; });
