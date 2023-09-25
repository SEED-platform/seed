/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * run_jasmine.js: runs the jasmine JS test runner
 */
(function () {
  var jasmineEnv = jasmine.getEnv();
  jasmineEnv.updateInterval = 1000;

  var htmlReporter = new jasmine.HtmlReporter();

  jasmineEnv.addReporter(htmlReporter);

  jasmineEnv.specFilter = function (spec) {
    return htmlReporter.specFilter(spec);
  };

  var currentWindowOnload = window.onload;

  window.onload = function () {
    if (currentWindowOnload) {
      currentWindowOnload();
    }
    execJasmine();
  };
  function execJasmine () {
    jasmineEnv.execute();
  }
})();
