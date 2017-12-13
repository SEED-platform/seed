/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// run jasmine tests

var EC = protractor.ExpectedConditions;


// Older Jasmine unit tests:
describe('When I go to jasmine tests', function () {
  it('should reset sync', function () {
    browser.ignoreSynchronization = true;
  });
  it('should run jasmine unit tests and pass', function () {
    browser.get('/angular_js_tests');
    var passingBar = $('.passingAlert.bar');
    browser.wait(EC.presenceOf(passingBar), 30000);
    expect($('.passingAlert.bar').isPresent()).toBe(true);
  }, 60000);
  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });
});
