/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// create and test new dataset with import
const EC = protractor.ExpectedConditions;

const path = require('path');
const remote = require('selenium-webdriver/remote');

// Data Set page
// Select my new sub org
describe('When I click the orgs button', () => {
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should be able to switch to my org', () => {
    browser.get('/app/#/data');
    $('#btnUserOrgs').click();
    element(by.cssContainingText('[ng-click="set_user_org(org)"]', browser.params.testOrg.parent)).click();
    expect($('#btnUserOrgs').getText()).toEqual(browser.params.testOrg.parent);
  });
});

describe('When I visit the data set page', () => {
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should be able to create a new data set', () => {
    $('[ui-sref="dataset_list"]').click();
    $$('input').first().sendKeys('my fake dataset');
    $('[ng-click="create_dataset(dataset.name)"]').click();
    // selectDropdownbyText(element, browser.params.testOrg.cycle);
    expect(element(by.cssContainingText('option', browser.params.testOrg.cycle)).isPresent()).toBe(true);
    element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();
  });

  // manually
  it('should reset sync', () => {
    browser.ignoreSynchronization = true;
  });

  it('should be able to create a new data set async', () => {
    // for remote ci to grab files
    browser.setFileDetector(new remote.FileDetector());

    const fileToUpload = 'seed/data_importer/tests/data/example-data-properties.xlsx';
    const absolutePath = path.resolve(fileToUpload);

    element.all(by.xpath('//input[@type="file"]')).first().sendKeys(absolutePath);
    browser.wait(EC.presenceOf($('.alert.alert-success')), 120000);
    expect($('.alert.alert-success').isPresent()).toBe(true);
    expect($('[ng-click="goto_data_mapping()"]').isPresent()).toBe(true);
  });

  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should take me to the mapping page', () => {
    $('[ng-click="goto_data_mapping()"]').click();
    browser.wait(EC.presenceOf($('.table_list_container.mapping')), 5000);
    expect($('.page_title').getText()).toContain('Data Mapping & Validation');
  });

  it('should have more than one mapped value', () => {
    const rows = element.all(by.repeater('tcm in valids')).filter((elm) => {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
  });

  it('should go to mapping Validation', () => {
    $$('[ng-click="remap_buildings()"]').first().click();
    browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')), 120000);
    expect($('[heading="View by Property"]').isPresent()).toBe(true);
    expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
  });

  // manually
  it('should reset sync', () => {
    browser.ignoreSynchronization = true;
  });

  it('should go to mapping Validation async', () => {
    const rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter((elm) => {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
  });

  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should save mappings', () => {
    $('#save-mapping').click();
    browser.sleep(500);
    $('#confirm-mapping').click();
    browser.wait(EC.presenceOf($('.alert.alert-info.alert-dismissable')), 120000);
    expect($('.alert.alert-info.alert-dismissable').isPresent()).toBe(true);
    $$('[ng-click="goto_step(2)"]').first().click();
  });

  // manually
  it('should reset sync', () => {
    browser.ignoreSynchronization = true;
  });

  it('should be able to add tax lots file too', () => {
    element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();

    // for remote ci to grab the files
    browser.setFileDetector(new remote.FileDetector());

    const fileToUpload = 'seed/data_importer/tests/data/example-data-taxlots.xlsx';
    const absolutePath = path.resolve(fileToUpload);

    element.all(by.xpath('//input[@type="file"]')).first().sendKeys(absolutePath);
    const passingBar = $('.alert.alert-success');
    browser.wait(EC.presenceOf(passingBar), 120000);
    expect($('.alert.alert-success').isPresent()).toBe(true);
    expect($('[ng-click="goto_data_mapping()"]').isPresent()).toBe(true);
  });

  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should take me to the mapping page for taxlots', () => {
    $('[ng-click="goto_data_mapping()"]').click();
    browser.wait(EC.presenceOf($('.table_list_container.mapping')), 5000);
    expect($('.page_title').getText()).toContain('Data Mapping & Validation');
  });

  it('should have more than one mapped value and change all to taxlot', () => {
    $('[ng-change="setAllInventoryTypes()"]').element(by.cssContainingText('option', 'Property')).click();
    const cusRow = element.all(by.repeater('tcm in valids')).filter((rows) => {
      expect(rows.length).not.toBeLessThan(1);
      return rows
        .$('[ng-model="tcm.suggestion_table_name"]')
        .getText()
        .then((label) => {
          expect(label).toEqual('Property');
        });
    });
    $$('[ng-change="updateInventoryTypeDropdown(); change(tcm)"]').first().element(by.cssContainingText('option', 'Tax Lot')).click();
    $('#mapped-row-input-box-0').clear();
    $('#mapped-row-input-box-0').sendKeys('Address Line 1');
    $('#mapped-row-input-box-0').clear();
    $('#mapped-row-input-box-0').sendKeys('Jurisdiction Tax Lot ID');
    $$('[ng-click="remap_buildings()"]').first().click();
  });

  it('should reset sync', () => {
    browser.ignoreSynchronization = true;
  });

  it('should go to mapping Validation for taxlots', () => {
    browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')), 120000);
    expect($('[heading="View by Property"]').isPresent()).toBe(true);
    expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
    const rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter((elm) => {
      expect(elm.length).not.toBeLessThan(1);
      return elm;
    });
  });

  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  it('should save mappings for taxlots', () => {
    $('#save-mapping').click();
    browser.sleep(500);
    $('#confirm-mapping').click();
    browser.wait(EC.presenceOf($('.alert.alert-success.alert-dismissable')), 120000);
    expect($('.alert.alert-success.alert-dismissable').isPresent()).toBe(true);
    $('[ng-click="view_my_properties()"]').click();
    expect(browser.getCurrentUrl()).toContain('/app/#/properties');
  });
});
