/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;

// Check dataset matching and deleting Pages:
describe('When I go to the dataset options page', function () {
  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should delete a single file', function () {
    browser.get('/app/#/data');
    $$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
    var rows = element.all(by.repeater('f in dataset.importfiles'));
    expect(rows.count()).toBe(2);
  });

  //Mapping
  it('should edit mappings', function () {
    var rows = element.all(by.repeater('f in dataset.importfiles'));
    expect(rows.count()).toBe(2);
    $$('#data-mapping-0').first().click();
    expect($('.page_title').getText()).toContain('Data Mapping & Validation');
  });

  it('should have more than one mapped value', function () {
    //Need this?
    // $('[ng-change="setAllInventoryTypes()"]').element(by.cssContainingText('option', 'Tax Lot')).click();
    var cusRow = element.all(by.repeater('tcm in valids')).filter(function (rows) {
      expect(rows.length).not.toBeLessThan(1);
      return rows.$('[ng-model="tcm.suggestion_table_name"]').getText().then(function (label) {
        // expect(label).toEqual('Tax Lot');
        return;
      });
    });
  });

  it('should go to mapping Validation for taxlots', function () {
    var rowC = element.all(by.repeater('result in row.data_quality_results'));
    $$('[ng-click="get_mapped_buildings()"]').first().click();
    browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')), 30000);
    expect($('[heading="View by Property"]').isPresent()).toBe(true);
    expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
    var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter(function (elm) {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
    $$('[ng-click="open_data_quality_modal()"]').first().click();
    browser.wait(EC.presenceOf($('.modal-title')), 30000);
    expect(rowC.count()).toBe(49);
    // expect($('.modal-body.ng-scope').getText()).toContain('No warnings/errors');
    $$('[ng-click="close()"]').first().click();
    expect($('.modal-body.ng-scope').isPresent()).toBe(false);
    $$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();
  });

  it('should go to data page and select properties', function () {
    $$('#data-mapping-1').first().click();
    expect($('.page_title').getText()).toContain('Data Mapping & Validation');
  });

  it('should have more than one mapped value for properties', function () {
    //Need this?
    // $('[ng-change="setAllInventoryTypes()"]').element(by.cssContainingText('option', 'Tax Lot')).click();
    var cusRow = element.all(by.repeater('tcm in valids')).filter(function (rows) {
      expect(rows.length).not.toBeLessThan(1);
      return rows.$('[ng-model="tcm.suggestion_table_name"]').getText().then(function (label) {
        // expect(label).toEqual('Tax Lot');
        return;
      });
    });
  });

  it('should go to mapping Validation for properties', function () {
    $$('[ng-click="get_mapped_buildings()"]').first().click();
    $$('[ng-click="backToMapping()"]').first().click();
    $$('[ng-click="get_mapped_buildings()"]').first().click();
    browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')), 30000);
    expect($('[heading="View by Property"]').isPresent()).toBe(true);
    expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
    var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter(function (elm) {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
    $$('[ng-click="open_data_quality_modal()"]').first().click();
    browser.wait(EC.presenceOf($('.modal-title')), 30000);
    expect($('.modal-body.ng-scope').getText()).toContain('File Name:');
    var rows1 = element.all(by.repeater('row in dataQualityResults'));
    var rowC = element.all(by.repeater('result in row.data_quality_results'));
    expect(rowC.count()).toBe(64);
    $('[ng-show="importFileId"]').click();
    $$('[ng-click="close()"]').first().click();
    expect($('.modal-body.ng-scope').isPresent()).toBe(false);
  });

  it('should test mapping filters', function () {
    $$('[ng-model="colFilter.term"]').first().sendKeys('>12');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('>=12');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('<12');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('<=12');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('==2264');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('!=2264');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('>=1 <3000');
    $$('[ng-model="colFilter.term"]').first().clear();
    $$('[ng-model="colFilter.term"]').first().sendKeys('<1 =>3000');
    $('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').click();
  });
});
