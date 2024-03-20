/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// test Data Quality, labels, delete function and other misc items after data is loaded
const EC = protractor.ExpectedConditions;

describe('When I do miscellaneous things', () => {
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  // Data Quality
  it('should see my organizations', () => {
    browser.get('/app/#/accounts');
    const rows = element.all(by.repeater('org in orgs_I_own'));
    expect(rows.count()).not.toBeLessThan(1);
  });

  it('should go to parent organization', () => {
    const myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent)).element(by.xpath('..')).$('.account_org.right');
    expect(myNewOrg.isPresent()).toBe(true);
    browser.actions().mouseMove(myNewOrg).perform();
    myNewOrg.$$('a').first().click();
  });

  it('should select Data Quality tab', () => {
    const myOptions = element
      .all(by.css('a'))
      .filter((elm) => elm.getText().then((label) => label === 'Data Quality'))
      .first();
    myOptions.click();
    expect($('.table_list_container').isPresent()).toBe(true);
  });

  it('should select and edit one rule, click save settings', () => {
    const rowCount = element.all(by.repeater('rule in ruleGroup'));
    expect(rowCount.count()).toBe(1);

    $$('[ng-model="rule.min"]')
      .first()
      .click()
      .clear()
      .then(() => {
        $$('[ng-model="rule.min"]').first().sendKeys('0');
      });
    $$('[ng-click="create_new_rule()"]').first().click();
    expect(rowCount.count()).toBe(2);

    $$('[ng-click="save_settings()"]').first().click();
    browser.wait(EC.presenceOf($('.fa-check')), 5000);
    browser.driver.navigate().refresh();
  }, 60000);

  it('should refresh and change a rule', () => {
    const rowCount = element.all(by.repeater('rule in ruleGroup'));
    expect(rowCount.count()).toBe(1);

    $$('[ng-click="selectAll()"]').first().click();
    browser.sleep(1000);
    $$('[ng-click="selectAll()"]').first().click();
    $$('[ng-model="rule.field"]').first().click();
    $$('[label="Campus"]').first().click();
    $$('[ng-model="rule.data_type"]').first().click();
    $('[label="Year"]').click();

    $$('[ng-model="rule.severity"]').first().click();
    $('[value="warning"]').click();

    $$('[ng-model="rule.units"]').first().click();
    $('[label="square feet"]').click();

    $$('[ng-click="rule.rule_type = 1; rule.enabled = !rule.enabled"]').first().click().click();

    $$('[ng-click="save_settings()"]').first().click();
    browser.wait(EC.presenceOf($('.fa-check')), 5000);
    browser.driver.navigate().refresh();
  }, 60000);

  it('should create new label and associate with rule', () => {
    // no rule should have a label
    expect($('.form-control.label.label-primary').isPresent()).toBe(false);

    // create label but select not created one
    $$('[ng-click="create_label(rule, $index)"]').first().click();
    $('[ng-click="cancel()"]').click();
    $$('[ng-click="create_label(rule, $index)"]').first().click();
    expect($('.modal-title').isPresent()).toBe(true);
    $('#labelName').sendKeys('ruleLabel');
    $('[name="newLabelForm"]').$('#btnSelectLabel').click();
    $$('[ng-click="new_label.label = label.label; new_label.color = label.color"]').first().click();
    $$('.btn.btn-primary').first().click();
    $('#labelName').sendKeys('ruleLabel');
    $('#labelName').sendKeys('2');
    $('[name="newLabelForm"]').$('#btnSelectLabel').click();
    $$('[ng-click="new_label.label = label.label; new_label.color = label.color"]').get(1).click();
    $$('.btn-default.action_link').get(2).click();

    // check label was attached after save and refresh
    $$('[ng-click="save_settings()"]').first().click();
    browser.driver.navigate().refresh();
  }, 60000);

  it('should reset all rules and add labels', () => {
    $$('[ng-click="restore_defaults()"]').first().click();
    const rowCount = element.all(by.repeater('rule in ruleGroup'));
    expect(rowCount.count()).toBe(21);
    $$('[ng-click="reset_all_rules()"]').first().click();
    expect(rowCount.count()).toBe(20);
  });

  it('should add labels to previous rules', () => {
    $('[ui-sref="organization_data_quality({organization_id: org.id, inventory_type: \'taxlots\'})"]').click();
    $$('[ng-click="create_label(rule, $index)"]').first().click();
    $$('.btn.btn-sm.btn-default.action_link').get(2).click();

    $$('[label="Text"]').get(1).click();

    $$('[ng-repeat="field in sortedRuleGroups()"]').get(1).$('[ng-model="rule.text_match"]').sendKeys('1234');
    $$('[ng-click="create_label(rule, $index)"]').first().click();
    $$('.btn-default.action_link').get(3).click();
    $$('[ng-click="save_settings()"]').first().click();
    browser.driver.navigate().refresh();
  }, 60000);

  it('should refresh and rules are correctly saved', () => {
    expect(element.all(by.repeater('rule in ruleGroup')).first().$('.form-control.label.label-primary').isPresent()).toBe(true);
    $$('[ng-click="remove_label(rule)"]').first().click();
    expect(element.all(by.repeater('rule in ruleGroup')).first().$('.form-control.label.label-primary').isPresent()).toBe(false);
    $$('[ng-click="save_settings()"]').first().click();
    browser.driver.navigate().refresh();
  }, 60000);

  it('should refresh again and check rules', () => {
    expect(element.all(by.repeater('rule in ruleGroup')).first().$('.form-control.label.label-primary').isPresent()).toBe(false);
    $$('[ng-click="create_label(rule, $index)"]').first().click();
    $$('.btn.btn-sm.btn-default.action_link').get(2).click();
    $$('[ng-click="save_settings()"]').first().click();
  });

  it('should go to labels page and check that new label was created with new rule', () => {
    const myOptions2 = element
      .all(by.css('a'))
      .filter((elm) => elm.getText().then((label) => label === 'Labels'))
      .first();
    myOptions2.click();
    expect($('b').getText()).toContain('Existing Labels');

    const labelRowCount = element.all(by.repeater('label in labels'));
    expect(labelRowCount.count()).toBe(15);
  });

  // Check data quality on inventory page
  it('should select first item and test data quality modal and presence of rows', () => {
    $('#sidebar-inventory').click();
    $('[ng-change="update_cycle(cycle.selected_cycle)"]').element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();

    $$('.ui-grid-menu-button').first().click();
    const myOptions = element
      .all(by.repeater('item in menuItems'))
      .filter((elm) => elm.getText().then((label) =>
      // expect(label).toBe('fake');
        label === '  Clear all filters'))
      .first();
    myOptions.click();

    $$('[ng-click="toggleMenu($event)"]').first().click();
    $$('[ng-click="itemAction($event, title)"]').first().click();

    $$('[ng-click="selectButtonClick(row, $event)"]').first().click();
    $('#btnInventoryActions').click();
    $$('[ng-click="run_data_quality_check()"]').click();
    expect($('.modal-title').getText()).toContain('Data Quality Results');
    const rowCount = element.all(by.repeater('result in row.data_quality_results'));

    expect(rowCount.count()).toBe(0);
    $$('[ng-click="close()"]').click();
  });

  it('should go to taxlots and and test the same', () => {
    // run on taxlots
    $('[ui-sref="inventory_list({inventory_type: \'taxlots\'})"]').click();

    $$('[ng-click="toggleMenu($event)"]').first().click();
    $$('[ng-click="itemAction($event, title)"]').first().click();

    $$('[ng-click="selectButtonClick(row, $event)"]').first().click();
    $$('[ng-click="selectButtonClick(row, $event)"]').get(1).click();
    $$('[ng-click="selectButtonClick(row, $event)"]').get(2).click();
    $('#btnInventoryActions').click();
    $$('[ng-click="run_data_quality_check()"]').click();
    expect($('.modal-title').getText()).toContain('Data Quality Results');
    const rowCount3 = element.all(by.repeater('result in row.data_quality_results'));

    expect(rowCount3.count()).toBe(5);
    $$('[ng-click="c.toggle_sort()"]').first().click();
    browser.sleep(500);
    $$('[ng-change="search.filter_search()"]').first().sendKeys('1234');
    browser.sleep(500);
    $$('[ng-change="search.filter_search()"]').first().clear();
    browser.sleep(500);
    $$('[ng-click="c.toggle_sort()"]').first().click();
    browser.sleep(500);
    $$('[ng-click="c.toggle_sort()"]').get(2).click();
    browser.sleep(500);
    $$('[ng-change="search.filter_search()"]').get(2).sendKeys('1234');
    browser.sleep(500);
    $$('[ng-change="search.filter_search()"]').get(2).clear();
    browser.sleep(500);
    $$('[ng-click="c.toggle_sort()"]').get(2).click().click();
    browser.sleep(500);
    $$('[ng-click="close()"]').click();
  }, 60000);

  it('should test labels were applied correctly', () => {
    const rows = $('.left.ui-grid-render-container-left.ui-grid-render-container').all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows'));

    // check labels -
    $('[ng-click="clear_labels()"]').click();
    $('#tags-input').click();
    $$('.suggestion-item.selected').first().click();

    expect(rows.count()).toBe(3);
    $('[uib-btn-radio="\'and\'"]').click();
    $('#tags-input').click();
    $$('.suggestion-item.selected').first().click();

    expect(rows.count()).toBe(2);
    $('[uib-btn-radio="\'or\'"]').click();
    expect(rows.count()).toBe(3);
    $('[ng-click="clear_labels()"]').click();
    expect(rows.count()).toBe(11);
  });

  it('should test delete and export modals', () => {
    // select rows and delete
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $('[ng-click="delete_inventory()"]').click();
    $('[ng-click="close()"]').click();

    $('#btnInventoryActions').click();
    $('[ng-click="open_update_labels_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();

    // reselect rows and export
    $$('[ng-click="selectButtonClick(row, $event)"]').first().click();
    $$('[ng-click="selectButtonClick(row, $event)"]').get(1).click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_export_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_export_modal()"]').click();
    $('#fileName').sendKeys('someFileName');
    $('[ng-click="export_selected()"]').click();
  });

  it('should test pin and move', () => {
    $('[ui-sref="inventory_list({inventory_type: \'properties\'})"]').click();
    $$('.ui-grid-icon-angle-down').get(4).click();
    $$('.ui-grid-icon-left-open').first().click();
    $$('.ui-grid-icon-angle-down').get(4).click();
    $$('.ui-grid-icon-left-open').first().click();

    $$('.ui-grid-icon-angle-down').first().click();
    var myOptions = element
      .all(by.repeater('item in menuItems'))
      .filter((elm) => elm.getText().then((label) =>
      // expect(label).toBe('fake');
        label === '  Unpin'))
      .first();
    myOptions.click();

    $$('.ui-grid-icon-angle-down').first().click();
    var myOptions = element
      .all(by.repeater('item in menuItems'))
      .filter((elm) => elm.getText().then((label) =>
      // expect(label).toBe('fake');
        label === '  Hide Column'))
      .first();
    myOptions.click();
  }, 45000);

  it('should test export modals properties', () => {
    // reselect rows and export
    $$('[ng-click="selectButtonClick(row, $event)"]').first().click();
    $$('[ng-click="selectButtonClick(row, $event)"]').get(1).click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_export_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_export_modal()"]').click();
    $('#fileName').sendKeys('someFileName');
    $('[ng-click="export_selected()"]').click();

    // select rows and delete
    $$('[ng-click="headerButtonClick($event)"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $('[ng-click="delete_inventory()"]').click();
    $('[ng-click="close()"]').click();
  });

  it('should test delete TL and properties', () => {
    // select rows and delete
    $$('[ng-if="grid.options.enableSelectAll"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $('[ng-click="delete_inventory()"]').click();
    $('[ng-click="close()"]').click();

    // taxlots
    $('[ui-sref="inventory_list({inventory_type: \'taxlots\'})"]').click();
    $$('[ng-if="grid.options.enableSelectAll"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $$('[ng-click="cancel()"]').first().click();
    $('#btnInventoryActions').click();
    $('[ng-click="open_delete_modal()"]').click();
    $('[ng-click="delete_inventory()"]').click();
    $('[ng-click="close()"]').click();
  }, 45000);

  // Delete
  it('should check edit and delete stuff for files', () => {
    browser.get('/app/#/data');
    $$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
    const rows = element.all(by.repeater('f in dataset.importfiles'));
    // click and cancel
    $$('.delete_link').get(1).click();
    $$('[ng-click="cancel()"]').first().click();
    expect(rows.count()).toBe(2);
    // click and delete
    $$('.delete_link').get(1).click();
    $$('[ng-click="delete_file()"]').first().click();
    expect(rows.count()).toBe(1);
    // open upload modal
    $$('[ng-click="open_data_upload_modal()"]').get(1).click();
    $('[ng-click="cancel()"].btn-default').click();

    $$('[ui-sref="dataset_list"]').first().click();
  });

  it('should check edit and delete stuff for datasets', () => {
    $$('[ng-click="open_data_upload_modal()"]').get(1).click();
    $('[ng-click="cancel()"].btn-default').click();
    browser.sleep(1000);
    $('[ng-click="edit_dataset_name(d)"]').click();
    $('[ng-click="cancel_edit_name(d)"]').click();
    browser.sleep(2000);
    $('[ng-click="edit_dataset_name(d)"]').click();
    $('#editDatasetName').sendKeys('2');
    $('[ng-click="save_dataset_name(d)"]').click();
    browser.sleep(2000);

    $$('[ng-click="confirm_delete(d)"]').first().click();
    $$('[ng-click="delete_dataset()"]').first().click();
    rows = element.all(by.repeater('d in datasets'));
    expect(rows.count()).toBe(0);
  });
});
