/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// create test orgs
const EC = protractor.ExpectedConditions;
// Admin page:
describe('When I go to admin page', () => {
  // manually
  it('should reset sync', () => {
    browser.ignoreSynchronization = true;
  });

  it('should test admin pages', () => {
    browser.get('/app/#/api/swagger');
    browser.wait(EC.presenceOf($('.logo')), 10000);
    browser.sleep(5000);
    expect(browser.getTitle()).toContain('SEED Platform');
    browser.get('/app/#/contact');
    browser.wait(EC.presenceOf($('.logo')), 10000);
    // browser.sleep(5000);
    expect(browser.getTitle()).toContain('SEED Platform');
  });

  // manually
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should test developer pages', () => {
    browser.get('/app/#/profile/developer');
    browser.wait(EC.presenceOf($('.logo')), 20000);
    // browser.sleep(5000);
    expect(browser.getTitle()).toContain('SEED Platform');
    $('[ng-click="generate_api_key()"]').click();
    browser.wait(EC.presenceOf($('.fa-check')), 10000);
  });

  it('should test pw change', () => {
    browser.get('/app/#/profile/security');
    browser.wait(EC.presenceOf($('.logo')), 10000);
    // browser.sleep(5000);
    expect(browser.getTitle()).toContain('SEED Platform');
    $('#editCurrentPassword').sendKeys(browser.params.login.password);
    $('#editNewPassword').sendKeys('somethingFAKE!');
    $('#editConfirmNewPassword').sendKeys('somethingFAKE!');
    $('[ng-click="change_password()"]').click();
    browser.wait(EC.presenceOf($('.fa-check')), 10000);
  });

  it('should test adding profile name', () => {
    browser.get('/app/#/profile');
    $('#first-name-text')
      .clear()
      .then(() => {
        $('#first-name-text').sendKeys('ME');
      });
    $('#last-name-text')
      .clear()
      .then(() => {
        $('#last-name-text').sendKeys('NotYou');
      });
    $('#update_profile').click();
    browser.wait(EC.presenceOf($('.fa-check')), 10000);
    $('#first-name-text')
      .clear()
      .then(() => {
        $('#first-name-text').sendKeys('ME');
      });
    $('[ng-click="reset_form()"]').click();
  });

  it('should create new test org', () => {
    browser.get('/app/#/profile/admin');
    // browser.sleep(5000);
    $('#org_name').sendKeys(browser.params.testOrg.parent);
    $$('#user_emails').first().element(by.cssContainingText('option', browser.params.login.user)).click();
    $('[ng-click="org_form.add(org)"]').click();

    const myNewOrg = element
      .all(by.repeater('org in org_user.organizations'))
      .filter((rows) => {
        expect(rows.length).not.toBeLessThan(1);
        return rows.getText().then((label) => label.includes(browser.params.testOrg.parent));
      })
      .first();
    expect(myNewOrg.isPresent()).toBe(true);
  });

  it('should create new user for test org', () => {
    $('#first_name').sendKeys('Test');
    $('#last_name').sendKeys('Testy');
    $$('#user_email').first().sendKeys('testy@test.com');
    $('[ng-model="user.organization"]').element(by.cssContainingText('option', browser.params.testOrg.parent)).click();
    $('[ng-click="user_form.add(user)"]').click();

    $('[ng-model="org_user.organization"]').element(by.cssContainingText('option', browser.params.testOrg.parent)).click();
    const myNewUser = element
      .all(by.repeater('user in org_user.users'))
      .filter((rows) => {
        expect(rows.length).not.toBeLessThan(1);
        return rows.getText().then((label) => label.includes('testy@test.com'));
      })
      .first();
    expect(myNewUser.isPresent()).toBe(true);
  });

  it('should delete new user for test org', () => {
    $('[ng-model="org_user.organization"]').element(by.cssContainingText('option', browser.params.testOrg.parent)).click();
    const myNewUser = element
      .all(by.repeater('user in org_user.users'))
      .filter((rows) => {
        expect(rows.length).not.toBeLessThan(1);
        return rows.getText().then((label) => label.includes('testy@test.com'));
      })
      .first();
    myNewUser.$('button').click();
    browser.sleep(100);
    expect(myNewUser.isPresent()).toBe(false);
  });

  it('should add user again', () => {
    $$('#orgs').first().$$('option').first()
      .click();
    $$('#user_emails').first().$$('option').first()
      .click();
    $('[ng-click="org_user.add()"]').click();

    // check no column mappings
    $$('[ng-click="confirm_column_mappings_delete(org)"]').first().click();
    browser.wait(EC.alertIsPresent(), 2000, 'an alert');
    browser.switchTo().alert().accept();
  });

  it('should create new test org', () => {
    // browser.sleep(5000);
    $('#org_name').clear().sendKeys(browser.params.testOrg.parent);
    $$('#user_emails').first().element(by.cssContainingText('option', browser.params.login.user)).click();
    $('[ng-click="org_form.add(org)"]').click();
  });
});
