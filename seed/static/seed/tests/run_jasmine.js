/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * run_jasmine.js: runs the jasmine JS test runner
 */
const isPortReachable = require('is-port-reachable');
const puppeteer = require('puppeteer');

(async () => {
  // Launch a headless browser
  const browser = await puppeteer.launch({ headless: 'shell' });
  const page = await browser.newPage();

  // Navigate to the Jasmine SpecRunner
  if (await isPortReachable(80)) {
    await page.goto('http://localhost:80/angular_js_tests/');
  } else if (await isPortReachable(8000)) {
    await page.goto('http://localhost:8000/angular_js_tests/');
  } else {
    console.error('SEED is not running - unable to run Jasmine tests');
    process.exit(1);
  }

  // Wait for Jasmine to finish running the tests
  await page.waitForFunction('window.jasmine.getEnv().currentRunner().queue.running === false');

  // Extract the test results
  const result = await page.evaluate(() => {
    const results = window.jasmine.getEnv().currentRunner().results();
    return {
      passed: results.failedCount === 0,
      failedCount: results.failedCount,
      passedCount: results.passedCount,
      totalCount: results.totalCount
    };
  });

  console.log(`Total tests: ${result.totalCount}`);
  console.log(`Passed tests: ${result.passedCount}`);
  console.log(`Failed tests: ${result.failedCount}`);

  await browser.close();

  if (result.passed) {
    console.log('All tests passed!');
    process.exit(0);
  } else {
    console.log('Some tests failed.');
    process.exit(1);
  }
})();
