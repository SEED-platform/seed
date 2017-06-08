/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;

// Check dataset matching and deleting Pages:
describe('When I go to the matching page', function () {

  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should delete a single file', function () {
    browser.get('/app/#/data');
    $$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
    var rows = element.all(by.repeater('f in dataset.importfiles'));
    expect(rows.count()).toBe(2);
  });

  //Matching
  it('should go to matching and have rows', function () {
    $$('#data-matching-0').first().click();
    expect($('.page_title').getText()).toContain('Data Matching');
    expect($('.table_footer').getText()).toContain('4 unmatched');
    element(by.cssContainingText('#selected-cycle', browser.params.testOrg.cycle)).click();
    $('#showHideFilterSelect').element(by.cssContainingText('option', 'Show Matched')).click();
    var rows = element.all(by.repeater('i in inventory'));
    expect(rows.count()).not.toBeLessThan(1);
  });

  it('should unmatch stuffs', function () {
    $$('[ui-sref="matching_detail({importfile_id: import_file.id, inventory_type: inventory_type, state_id: i.id})"]').first().click();
    rows = element.all(by.repeater('state in available_matches'));
    expect(rows.count()).not.toBeLessThan(1);
    $('[ng-change="unmatch()"]').click();
    browser.wait(EC.presenceOf($('.message')), 10000);
    $('[ui-sref="matching_list({importfile_id: import_file.id, inventory_type: inventory_type})"]').click();
    expect($('.table_footer').getText()).toContain('5 unmatched');
    $('#showHideFilterSelect').element(by.cssContainingText('option', 'Show Unmatched')).click();
  });

  it('should match matches', function () {
    $$('[ui-sref="matching_detail({importfile_id: import_file.id, inventory_type: inventory_type, state_id: i.id})"]').first().click();
    $$('[ng-change="checkbox_match(state)"]').first().click();
    browser.wait(EC.presenceOf($('.message')), 10000);
    $('[ui-sref="matching_list({importfile_id: import_file.id, inventory_type: inventory_type})"]').click();
    $('#showHideFilterSelect').element(by.cssContainingText('option', 'Show All')).click();
    expect($('.table_footer').getText()).toContain('4 unmatched');
  });
  
  it('should filter matches', function () {
    $$('[ui-sref="matching_detail({importfile_id: import_file.id, inventory_type: inventory_type, state_id: i.id})"]').first().click();
    $$('[ng-model="col.searchText"]').get(4).click().sendKeys('elm');
    expect(rows.count()).toBe(3);
    $$('[ng-model="col.searchText"]').get(9).click().sendKeys('148');
    expect(rows.count()).toBe(1);
    $$('[ng-model="col.searchText"]').get(4).click().clear();
    $$('[ng-model="col.searchText"]').get(9).click().clear();
    expect(rows.count()).toBe(17);
    $$('[ng-click="sortData(col.name)"]').get(4).click();
    browser.wait(EC.presenceOf($('.arrow-up')), 10000);
    
    var rowText = element.all(by.repeater('state in available_matches')).get(0);
    expect(rowText.getText()).toContain('11 Ninth Street Rust 24651456');
    $$('[ng-click="sortData(col.name)"]').get(4).click();
    browser.wait(EC.presenceOf($('.arrow-down')), 10000);
    expect(rowText.getText()).toContain('94000 Wellington Blvd Rust 23810533');
    $('[ui-sref="matching_list({importfile_id: import_file.id, inventory_type: inventory_type})"]').click();
  });


  it('should unmatch from front page', function () {
    $$('[ng-change="unmatch(i)"]').first().click();
    expect($('.table_footer').getText()).toContain('5 unmatched');
    $$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();
  });

});
