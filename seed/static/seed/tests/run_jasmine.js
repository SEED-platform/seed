/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * run_jasmine.js: runs the jasmine JS test runner
 */
(function () {
  const jasmineEnv = jasmine.getEnv();
  jasmineEnv.updateInterval = 1000;

  const htmlReporter = new jasmine.HtmlReporter();

  jasmineEnv.addReporter(htmlReporter);

  jasmineEnv.specFilter = (spec) => htmlReporter.specFilter(spec);

  const currentWindowOnload = window.onload;

  window.onload = function () {
    if (currentWindowOnload) {
      currentWindowOnload();
    }
    execJasmine();
  };
  function execJasmine() {
    jasmineEnv.execute();
  }
}());
