/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// Login

const EC = protractor.ExpectedConditions;

// Login
describe('When I visit the login page', () => {
  // manually
  it('should set sync', () => {
    browser.ignoreSynchronization = true;
  });

  it('should see login', () => {
    browser.get('/');
    element(by.id('id_email')).sendKeys(browser.params.login.user);
    element(by.id('id_password')).sendKeys(browser.params.login.password);
    element(by.className('btn btn-primary')).click();
  });

  // manually
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should see title', () => {
    $$('.fa.fa-cloud-upload').first().click();
    $('[ng-click="cancel()"]').click();
    browser.get('/app/#/about');
    expect(browser.getTitle()).toContain('SEED Platform');
  });
});
