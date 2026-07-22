/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * run_jasmine.mjs: runs the jasmine JS test runner
 */
import isPortReachable from 'is-port-reachable';
import puppeteer from 'puppeteer';

// Launch a headless browser
const browser = await puppeteer.launch({
  channel: 'chrome',
  headless: 'shell'
});
const page = await browser.newPage();

// Navigate to the Jasmine SpecRunner
if (await isPortReachable(80, { host: '127.0.0.1' })) {
  await page.goto('http://localhost:80/angular_js_tests/');
} else if (await isPortReachable(8000, { host: '127.0.0.1' })) {
  await page.goto('http://localhost:8000/angular_js_tests/');
} else {
  console.error('SEED is not running - unable to run Jasmine tests');
  process.exit(1);
}

// Wait for Jasmine to finish running the tests by checking for completion indicator in DOM
await page.waitForFunction(() => {
  const summary = document.querySelector('.jasmine-alert');
  return summary && summary.textContent.includes('specs,');
});

// Extract the test results from the Jasmine HTML reporter DOM
const result = await page.evaluate(() => {
  const summary = document.querySelector('.jasmine-alert');

  if (!summary) {
    return {
      passed: false,
      failedCount: 0,
      passedCount: 0,
      pendingCount: 0,
      totalCount: 0
    };
  }

  // Parse summary text like "15 specs, 2 failures, 3 pending"
  const summaryText = summary.textContent;
  const specsMatch = summaryText.match(/(\d+)\s+spec/);
  const failuresMatch = summaryText.match(/(\d+)\s+failure/);
  const pendingMatch = summaryText.match(/(\d+)\s+pending/);

  const totalCount = specsMatch ? parseInt(specsMatch[1], 10) : 0;
  const failedCount = failuresMatch ? parseInt(failuresMatch[1], 10) : 0;
  const pendingCount = pendingMatch ? parseInt(pendingMatch[1], 10) : 0;
  const passedCount = totalCount - failedCount - pendingCount;

  return {
    passed: failedCount === 0,
    failedCount,
    passedCount,
    pendingCount,
    totalCount
  };
});

console.log(`Total tests: ${result.totalCount}`);
console.log(`Passed tests: ${result.passedCount}`);
console.log(`Failed tests: ${result.failedCount}`);
if (result.pendingCount > 0) {
  console.log(`Pending tests: ${result.pendingCount}`);
}

await browser.close();

if (result.passed) {
  console.log('All tests passed!');
  process.exit(0);
} else {
  console.log('Some tests failed.');
  process.exit(1);
}
