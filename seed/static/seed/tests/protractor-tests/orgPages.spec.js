/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// test new orgs and sub orgs
var EC = protractor.ExpectedConditions;
// Accounts page
describe('When I visit the accounts page', function () {
  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });
  it('should see my organizations', function () {
    browser.get('/app/#/accounts');

    var rows = element.all(by.repeater('org in orgs_I_own'));
    expect(rows.count()).not.toBeLessThan(1);
  });
  it('should find and create new sub org', function () {
    var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
      .element(by.xpath('..')).element(by.xpath('..'));
    expect(myNewOrg.isPresent()).toBe(true);

    browser.actions().mouseMove(myNewOrg.$('[ng-show="org.is_parent"]').$('.sub_head.sub_org.right')).perform();
    myNewOrg.$('.sub_head.sub_org.right').$$('a').first().click();
    $('[id="createOrganizationName"]').sendKeys(browser.params.testOrg.child);
    $('[id="createOrganizationInvite"]').sendKeys(browser.params.login.user);
    $('.btn.btn-primary').click();

    var myNewSub = element(by.cssContainingText('.account_org.left', browser.params.testOrg.child))
      .element(by.xpath('..'));

    // expect(myNewSub.count() > 0);
    expect(myNewSub.isPresent()).toBe(true);
    browser.actions().mouseMove(myNewSub.$('.account_org.right')).perform();
    myNewSub.$$('.account_org.right a').first().click();
  });
  it('should change the sub org name', function () {
    $('input').clear().then(function () {
      $('input').sendKeys(browser.params.testOrg.childRename);
      $$('[ng-click="save_settings()"]').first().click();
      expect($('.page_title').getText()).toEqual(browser.params.testOrg.childRename);
    });
  });
  it('should go back to orgranizations', function () {
    $('[ui-sref="organizations"]').click();
    expect($('.page_title').getText()).toEqual('Organizations');
  });
});
describe('When I visit the the parent org', function () {
  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });
  it('should go to parent organization', function () {
    var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
      .element(by.xpath('..')).$('.account_org.right');

    expect(myNewOrg.isPresent()).toBe(true);

    browser.actions().mouseMove(myNewOrg).perform();
    myNewOrg.$$('a').first().click();
    var myOptions = element.all(by.css('a')).filter(function (elm) {
      return elm.getText().then(function (label) {
        return label == 'Cycles';
      });
    }).first();
    myOptions.click();
    expect($('.table_list_container').isPresent()).toBe(true);
  });
  it('should create new cycle', function () {
    $('[ng-model="new_cycle.name"]').sendKeys('faketest121212');
    $('[ng-model="new_cycle.start"]').sendKeys('01-01-2017');
    $('[ng-model="new_cycle.end"]').sendKeys('12-31-2017');
    $('#btnCreateCycle').click();
    $('[ng-click="openStartDatePicker($event)"]').click();
    $('[ng-click="openEndDatePicker($event)"]').click();
    $('[ng-click="openStartDatePicker($event)"]').click();
    $('[ng-click="openEndDatePicker($event)"]').click();
  });

  it('should edit created cycle', function () {
    $$('.btn-default.btn-rowform').last().click();
    var editCycle = $$('.editable-wrap.editable-text').first();
    editCycle.$('.ng-not-empty').clear().then(function () {
      editCycle.$('.ng-empty').sendKeys(browser.params.testOrg.cycle);
    });

    $$('.btn-primary.btn-rowform').last().click();
    var myNewCycle = element.all(by.repeater('cycle in cycles')).filter(function (sub) {
      return sub.all(by.tagName('td')).first().$('[ng-show="!rowform.$visible"]').getText().then(function (label) {
        return label == browser.params.testOrg.cycle;
      });
    }).first();
    expect(myNewCycle.all(by.tagName('td')).first().$('[ng-show="!rowform.$visible"]').getText()).toEqual(browser.params.testOrg.cycle);
  });

  it('should create new label', function () {
    var myOptions = element.all(by.css('a')).filter(function (elm) {
      return elm.getText().then(function (label) {
        return label == 'Labels';
      });
    }).first();
    myOptions.click();

    $$('input').first().sendKeys('fake label');
    $('.input-group-btn.dropdown').click();
    element(by.cssContainingText('.dropdown-menu.pull-right', 'orange')).click();
    $('#btnCreateLabel').click();
    var myNewLabel = element(by.cssContainingText('[editable-text="label.name"]', 'fake label'))
      .element(by.xpath('..')).element(by.xpath('..'));

    expect(myNewLabel.isPresent()).toBe(true);
    
    myNewLabel.$('[ng-click="deleteLabel(label, $index)"]').click();
    browser.sleep(1000);
    $('[data-ng-click="modalOptions.cancel()"]').click();

    myNewLabel.$('[ng-click="rowform.$show()"]').click();
    myNewLabel.$('[ng-click="rowform.$cancel()"]').click();
    myNewLabel.$('[ng-click="rowform.$show()"]').click();
    $('[ng-keypress="onEditLabelNameKeypress($event, rowform)"]').clear();
    myNewLabel.$('.btn.btn-primary.btn-rowform').click();
    $('[ng-keypress="onEditLabelNameKeypress($event, rowform)"]').sendKeys('Call');
    myNewLabel.$('.btn.btn-primary.btn-rowform').click();
    $('[ng-keypress="onEditLabelNameKeypress($event, rowform)"]').clear();
    $('[ng-keypress="onEditLabelNameKeypress($event, rowform)"]').sendKeys('fake label');
    element(by.cssContainingText('[name="color"]', 'blue')).click();
    myNewLabel.$('.btn.btn-primary.btn-rowform').click();

    myNewLabel.$('[ng-click="deleteLabel(label, $index)"]').click();
    browser.sleep(1000);
    $('.btn.btn-primary.ng-binding').click();
    expect(myNewLabel.isPresent()).toBe(false);
  }, 60000);

  // manually
  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should create new members', function () {
    var myOptions = element.all(by.css('a')).filter(function (elm) {
      return elm.getText().then(function (label) {
        return label == 'Members';
      });
    }).first();
    myOptions.click();

    $('[ng-click="new_member_modal()"]').click();
    $('[ng-click="cancel()"]').click();
    $('[ng-click="new_member_modal()"]').click();
    $('[ng-model="user.first_name"]').sendKeys('fake');
    $('[ng-model="user.last_name"]').sendKeys('stuff');
    $('[ng-model="user.email"]').sendKeys('something@test.com');
    element(by.cssContainingText('[ng-model="user.role"]', 'Owner')).click();
    $('.btn.btn-primary').click();

    $('[placeholder="member name"]').sendKeys('stuff');
    $('[placeholder="member name"]').clear();
    element(by.cssContainingText('[ng-model="u.role"]', 'viewer')).click();
    $$('[ng-click="remove_member(u)"]').first().click();
  });

  it('should create other sub org', function () {
    $('[ui-sref="organization_sub_orgs({organization_id: org.id})"]').click();
    $('[ng-click="create_sub_organization_modal()"]').click();
    $('[ng-click="cancel()"]').click();
    $('[ng-click="create_sub_organization_modal()"]').click();
    $('#createOrganizationName').sendKeys('protractor yet another fake sub org');
    $('#createOrganizationInvite').sendKeys(browser.params.login.user);
    $('[type="submit"]').click();
    var rows = element.all(by.repeater('sub_org in org.sub_orgs'));
    expect(rows.count()).toBe(2);
  });

  it('should select Data Quality tab and delete all default rules for properties', function () {
    var myOptions = element.all(by.css('a')).filter(function (elm) {
      return elm.getText().then(function (label) {
        return label == 'Data Quality';
      });
    }).first();
    myOptions.click();
    expect($('.table_list_container').isPresent()).toBe(true);

    var rowCheck = element.all(by.repeater('rule in ruleGroup'));
    expect(rowCheck.count()).not.toBeLessThan(1);

    var delRules = $$('[ng-click="delete_rule(rule, $index)"]').filter(function (elm) {
      return true;
    }).click();

    expect(rowCheck.count()).toBeLessThan(1);
  }, 120000);


  it('should create 1 data quality rule for properties', function () {
    $('[ng-click="create_new_rule()"]').click();
    $$('[ng-model="rule.field"]').first().click();
    $('[label="Postal Code (Property)"]').click();
    // element(by.cssContainingText('[ng-model="rule.field"]', 'PM Property ID')).click();
    $$('[ng-click="change_not_null(rule)"]').first().click();
    $$('[ng-click="save_settings()"]').first().click();
    //should show checkmark
    expect($$('[ng-click="save_settings()"]').first().$('i.ng-hide').isPresent()).toBe(false);

  });

  it('should select Data Quality tab and delete all default rules for taxlots', function () {
    $('[ui-sref="organization_data_quality({organization_id: org.id, inventory_type: \'taxlots\'})"]').click();
    expect($('.table_list_container').isPresent()).toBe(true);

    var rowCheck = element.all(by.repeater('rule in ruleGroup'));
    expect(rowCheck.count()).not.toBeLessThan(1);

    var delRules = $$('[ng-click="delete_rule(rule, $index)"]').filter(function (elm) {
      return true;
    }).click();

    expect(rowCheck.count()).toBeLessThan(1);
  });

  it('should create 1 data quality rule for taxlots', function () {
    $('[ng-click="create_new_rule()"]').click();
    $$('[ng-model="rule.field"]').first().click();
    $('[label="Address Line 1 (Tax Lot)"]').click();
    // element(by.cssContainingText('[ng-model="rule.field"]', 'Address Line 1 (Tax Lot)')).click();
    $$('[ng-click="change_not_null(rule)"]').first().click();
    $$('[ng-click="save_settings()"]').first().click();
    //should show checkmark
    expect($$('[ng-click="save_settings()"]').first().$('i.ng-hide').isPresent()).toBe(false);

  });

  // sharing page...what else can we test here?
  it('should go to parent organization and select Sharing', function () {
    var myOptions3 = element.all(by.css('a')).filter(function (elm) {
      return elm.getText().then(function (label) {
        return label == 'Sharing';
      });
    }).first();
    myOptions3.click();
    expect($('.table_list_container').isPresent()).toBe(true);
    $$('[ng-model="controls.public_select_all"]').first().click();
    $$('[ng-change="select_all_clicked(\'internal\')"]').first().click();
    var rowCheck = element.all(by.repeater('field in fields'));
    expect(rowCheck.count()).not.toBeLessThan(1);
    $$('[ng-model="filter_params.title"]').first().click().sendKeys('this is some fake stuff to test filter');
    expect(rowCheck.count()).toBe(0);
    $$('[ng-model="filter_params.title"]').first().click().clear();
    expect(rowCheck.count()).not.toBeLessThan(1);
    $$('[ng-click="save_settings()"]').first().click();
    browser.wait(EC.presenceOf($('.fa-check')), 10000);
  }, 60000);

});

