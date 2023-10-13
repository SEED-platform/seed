/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// test Data Quality, Sharing, Reports, delete function and other misc items after data is loaded
const EC = protractor.ExpectedConditions;

describe('When I go to the dataset options page', () => {
  it('should reset sync', () => {
    browser.ignoreSynchronization = false;
  });

  // Pairing
  it('should change cycle and refresh', () => {
    browser.get('/app/#/data');
    $$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
    $$('#data-pairing-0').first().click();
    element(by.cssContainingText('[ng-model="cycle.selected_cycle"] option', '2016 Calendar Year')).click();
  });

  it('should edit pairing', () => {
    element(by.cssContainingText('[ng-model="cycle.selected_cycle"] option', browser.params.testOrg.cycle)).click();
    expect($('.page_title').getText()).toContain('Pair Properties to Tax Lots');

    $('[ng-model="showPaired"]').element(by.cssContainingText('option', 'Show Paired')).click();
    element(by.cssContainingText('[ng-change="inventoryTypeChanged()"] option', 'Tax Lot')).click();

    $('[ng-model="showPaired"]').element(by.cssContainingText('option', 'Show Unpaired')).click();
    element(by.cssContainingText('[ng-change="inventoryTypeChanged()"] option', 'Property')).click();

    $('[ng-model="showPaired"]').element(by.cssContainingText('option', 'All')).click();

    expect($('.pairing-text-left').getText()).toContain('Showing 19 Properties');
    expect($('.pairing-text-right').getText()).toContain('Showing 11 Tax Lots');

    $$('[ng-click="leftSortData(col.name)"]').first().click().click();
    $$('[ng-click="rightSortData(col.name)"]').first().click().click();
  }, 60000);

  it('should test filters and sort on left and right table', () => {
    const leftRows = element.all(by.repeater('row in newLeftData'));
    const rightRows = element.all(by.repeater('row in rightData'));
    expect(leftRows.count()).toBe(19);
    $$('[ng-model="col.searchText"]').first().click().sendKeys('elm');
    expect(leftRows.count()).toBe(3);
    $$('[ng-model="col.searchText"]').get(4).click().sendKeys('33');
    expect(rightRows.count()).toBe(5);
    $$('[ng-model="col.searchText"]').first().clear();
    $$('[ng-model="col.searchText"]').get(4).clear();
  });

  it('should edit drag pairs', () => {
    // var dragElement = $$('.pairing-data-row.grab-pairing-left').first();
    const dragElement = element.all(by.repeater('row in newLeftData')).first();
    const dropElement = $$('.pairing-data-row-indent').first();
    const lastDropElement = $$('.pairing-data-row-indent').last();
    // console.log('drag: ', dragElement);
    // console.log('drop: ', dropElement);

    // drag doesn't work on chrome....so use click functionality
    dragElement.click();
    browser.sleep(200);
    dropElement.click();
    browser.sleep(200);
    lastDropElement.click();
    browser.sleep(200);
  });

  it('should edit delete pairings', () => {
    $$('.unpair-child')
      .count()
      .then((count) => {
        for (let index = 0; index < count; index++) {
          // console.log('index: ', index, count)
          const option = $$('.unpair-child').first();
          option.click();
          browser.sleep(200);
        }
      });

    expect($$('.unpair-child').count()).toBeLessThan(1);
  }, 60000);

  it('should edit change pair view', () => {
    browser.sleep(2000);
    element(by.cssContainingText('[ng-change="inventoryTypeChanged()"] option', 'Tax Lot')).click();
    // browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')),30000);
    expect($('.page_title').getText()).toContain('Pair Tax Lots to Properties');
    expect($('.pairing-text-right').getText()).toContain('Showing 19 Properties (19 unpaired)');
    expect($('.pairing-text-left').getText()).toContain('Showing 11 Tax Lots (11 unpaired)');
    browser.sleep(2000);
  });

  it('should edit drag pairs', () => {
    // var dragElement = $$('.pairing-data-row.grab-pairing-left').first();
    const dragElement = element.all(by.repeater('row in newLeftData')).first();
    const dropElement = $$('.pairing-data-row-indent').first();
    const lastDropElement = $$('.pairing-data-row-indent').last();
    // console.log('drag: ', dragElement);
    // console.log('drop: ', dropElement);

    // drag doesn't work on chrome....so use click functionality
    dragElement.click();
    browser.sleep(200);
    dropElement.click();
    browser.sleep(200);
    lastDropElement.click();
    browser.sleep(200);

    expect($('.pairing-text-right').getText()).toContain('Showing 19 Properties (17 unpaired)');
    expect($('.pairing-text-left').getText()).toContain('Showing 11 Tax Lots (10 unpaired)');
    browser.sleep(2000);
  });

  it('should delete pairings the other way', () => {
    $$('.unpair-child')
      .count()
      .then((count) => {
        for (let index = 0; index < count; index++) {
          // console.log('index: ', index, count)
          const option = $$('.unpair-child').first();
          option.click();
          browser.sleep(200);
        }
      });

    expect($$('.unpair-child').count()).toBeLessThan(1);
  }, 60000);

  it('should pair so we can delete pairs later in inventory page', () => {
    const dragElement = element.all(by.repeater('row in newLeftData')).get(2);
    const dropElement = $$('.pairing-data-row-indent').get(2);
    const lastDropElement = $$('.pairing-data-row-indent').last();

    dragElement.click();
    browser.sleep(200);
    dropElement.click();
    browser.sleep(200);
    lastDropElement.click();
    browser.sleep(200);
  });
});
