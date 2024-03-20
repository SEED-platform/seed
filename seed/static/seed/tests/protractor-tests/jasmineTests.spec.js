/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// run jasmine tests

const EC = protractor.ExpectedConditions;

// Older Jasmine unit tests:
describe('When I go to jasmine tests', () => {
  it('should reset sync', () => {
    browser.ignoreSynchronization = true;
  });
  it('should run jasmine unit tests and pass', () => {
    browser.get('/angular_js_tests/');
    const passingBar = $('.passingAlert.bar');
    return browser
      .wait(EC.presenceOf(passingBar), 30000)
      .then(() => $('.passingAlert.bar')
        .getText()
        .then((resultText) => {
          console.log(resultText);
        }))
      .catch(() => $('.resultsMenu.bar')
        .getText()
        .then((resultText) => {
          console.error(resultText);
          return $('html')
            .getText()
            .then((htmlText) => {
              console.log('========== Begin angular_js_tests output ==========');
              console.error(htmlText);
              console.log('========== End angular_js_tests output ==========');
              fail(resultText);
            });
        }));
  }, 60000);
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });
});
