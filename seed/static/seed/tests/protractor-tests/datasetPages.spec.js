/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// create and test new dataset with import
var EC = protractor.ExpectedConditions;

var path = require('path');
var remote = require('selenium-webdriver/remote');

// Data Set page
// Select my new sub org
describe('When I click the orgs button', function () {

  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should be able to switch to my org', function () {
    browser.get('/app/#/data');
    $('#btnUserOrgs').click();
    element(by.cssContainingText('[ng-click="set_user_org(org)"]', browser.params.testOrg.parent)).click();
    expect($('#btnUserOrgs').getText()).toEqual(browser.params.testOrg.parent);
  });
});

describe('When I visit the data set page', function () {

  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should be able to create a new data set', function () {
    $('[ui-sref="dataset_list"]').click();
    $$('input').first().sendKeys('my fake dataset');
    $('[ng-click="create_dataset(dataset.name)"]').click();
    // selectDropdownbyText(element, browser.params.testOrg.cycle);
    expect(element(by.cssContainingText('option', browser.params.testOrg.cycle)).isPresent()).toBe(true);
    element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();
    // $('[buttontext="Upload a Spreadsheet"]').$('.qq-uploader').click();
  });

  // manually
  it('should reset sync', function () {
    browser.ignoreSynchronization = true;
  });

  it('should be able to create a new data set async', function () {

    // for remote travis ci to grab files
    browser.setFileDetector(new remote.FileDetector());

    var fileToUpload = 'seed/tests/data/protractorProperties.xlsx';
    var absolutePath = path.resolve(fileToUpload);

    element.all(by.xpath('//input[@type="file"]')).first().sendKeys(absolutePath);
    browser.wait(EC.presenceOf($('.alert.alert-success')), 120000);
    expect($('.alert.alert-success').isPresent()).toBe(true);
    expect($('[ng-click="goto_data_mapping()"]').isPresent()).toBe(true);
  });

  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should take me to the mapping page', function () {
    $('[ng-click="goto_data_mapping()"]').click();
    browser.wait(EC.presenceOf($('.table_list_container.mapping')), 5000);
    expect($('.page_title').getText()).toContain('Data Mapping & Validation');
  });

  it('should have more than one mapped value', function () {
    var rows = element.all(by.repeater('tcm in valids')).filter(function (elm) {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
  });

  it('should go to mapping Validation', function () {
    $$('[ng-click="remap_buildings()"]').first().click();
    browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')), 120000);
    expect($('[heading="View by Property"]').isPresent()).toBe(true);
    expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
  });


  // manually
  it('should reset sync', function () {
    browser.ignoreSynchronization = true;
  });

  it('should go to mapping Validation async', function () {
    var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter(function (elm) {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
  });


  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should save mappings', function () {
    $('#save-mapping').click();
    browser.sleep(500);
    $('#confirm-mapping').click();
    browser.wait(EC.presenceOf($('.alert.alert-info.alert-dismissable')), 120000);
    expect($('.alert.alert-info.alert-dismissable').isPresent()).toBe(true);
    $$('[ng-click="goto_step(2)"]').first().click();
  });

  // manually
  it('should reset sync', function () {
    browser.ignoreSynchronization = true;
  });

  it('should be able to add tax lots file too', function () {

    element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();
    // $('[buttontext="Upload a Spreadsheet"]').$('.qq-uploader').click();

    // for remote travis ci to grab the files
    browser.setFileDetector(new remote.FileDetector());

    var fileToUpload = 'seed/tests/data/protractorTaxlots.xlsx';
    var absolutePath = path.resolve(fileToUpload);

    element.all(by.xpath('//input[@type="file"]')).first().sendKeys(absolutePath);
    var passingBar = $('.alert.alert-success');
    browser.wait(EC.presenceOf(passingBar), 120000);
    expect($('.alert.alert-success').isPresent()).toBe(true);
    expect($('[ng-click="goto_data_mapping()"]').isPresent()).toBe(true);
  });

  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should take me to the mapping page for taxlots', function () {
    $('[ng-click="goto_data_mapping()"]').click();
    browser.wait(EC.presenceOf($('.table_list_container.mapping')), 5000);
    expect($('.page_title').getText()).toContain('Data Mapping & Validation');
  });

  it('should have more than one mapped value and change all to taxlot', function () {
    $('[ng-change="setAllInventoryTypes()"]').element(by.cssContainingText('option', 'Property')).click();
    var cusRow = element.all(by.repeater('tcm in valids')).filter(function (rows) {
      expect(rows.length).not.toBeLessThan(1);
      return rows.$('[ng-model="tcm.suggestion_table_name"]').getText().then(function (label) {
        expect(label).toEqual('Property');
        return;
      });
    });
    $$('[ng-change="updateInventoryTypeDropdown(); change(tcm)"]').first().element(by.cssContainingText('option', 'Tax Lot')).click();
    $('#mapped-row-input-box-0').clear();
    $('#mapped-row-input-box-0').sendKeys('Address Line 1');
    $('#mapped-row-input-box-0').clear();
    $('#mapped-row-input-box-0').sendKeys('Jurisdiction Tax Lot Id');
    $$('[ng-click="remap_buildings()"]').first().click();
  });

  it('should reset sync', function () {
    browser.ignoreSynchronization = true;
  });

  it('should go to mapping Validation for taxlots', function () {
    browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')), 120000);
    expect($('[heading="View by Property"]').isPresent()).toBe(true);
    expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
    var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter(function (elm) {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
  });

  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should save mappings for taxlots', function () {
    $('#save-mapping').click();
    browser.sleep(500);
    $('#confirm-mapping').click();
    browser.wait(EC.presenceOf($('.alert.alert-success.alert-dismissable')), 120000);
    expect($('.alert.alert-success.alert-dismissable').isPresent()).toBe(true);
    $('[ng-click="view_my_properties()"]').click();
    expect(browser.getCurrentUrl()).toContain('/app/#/properties');
  });
});
