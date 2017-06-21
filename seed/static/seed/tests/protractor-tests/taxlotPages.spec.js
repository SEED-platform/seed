/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;
// Check inventory Page:
describe('When I go to the taxlot page', function () {
  // manually
  it('should reset sync', function () {
    browser.ignoreSynchronization = false;
  });

  it('should change to our test cycle', function () {
    browser.get('/app/#/taxlots');
    $('[ng-change="update_cycle(cycle.selected_cycle)"]').element(by.cssContainingText('option', "Default 2016 Calendar Year")).click();
    $('[ng-change="update_cycle(cycle.selected_cycle)"]').element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();

    var rows = $('.left.ui-grid-render-container-left.ui-grid-render-container')
      .all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows'));

    rows.count().then(function (count) {
      $('.item-count.ng-binding').getText().then(function (label) {
        expect(label).toContain(count);
      });
    });
  });

  //Not sure we need this one:
  // it('should filter semi colon and expand', function () {
  // 	var jurisTL = $$('[role="columnheader"]').filter(function(elm) {
  // 		return elm.getText().then(function (label) {
  // 			return label.includes('Associated TaxLot IDs');
  // 		});
  // 	}).first();
  // 	jurisTL.$$('[ng-model="colFilter.term"]').first().sendKeys(';');
  // });

  it('should filter', function () {
    // browser.executeScript("arguments[0].scrollIntoView();", elm.getWebElement());
    var rows = $('.left.ui-grid-render-container-left.ui-grid-render-container')
      .all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows'));

    rows.first().getText().then(function (label) {
      $$('[ng-model="colFilter.term"]').first().sendKeys(label);
    });
    //after filter
    expect(rows.count()).toBe(1);

    //clear by clicking the 'x' -> child of sibling of text input
    $$('[ng-model="colFilter.term"]').first().element(by.xpath('..')).$('[ui-grid-one-bind-aria-label="aria.removeFilter"]').click();
    expect($$('[ng-model="colFilter.term"]').first().getAttribute('value')).toEqual('');
    $$('[ng-model="colFilter.term"]').first().sendKeys('this is something long and fake to get nothing to filter');
    expect(rows.count()).toBeLessThan(1);
    $$('[ng-model="colFilter.term"]').first().element(by.xpath('..')).$('[ui-grid-one-bind-aria-label="aria.removeFilter"]').click();
  });

  it('should go to info pages', function () {
    $$('[ng-click="treeButtonClick(row, $event)"]').first().click();
    $$('.ui-grid-icon-info-circled').first().click();
    expect(browser.getCurrentUrl()).toContain('/app/#/taxlots');
    expect($('.page_title').getText()).toEqual('Tax Lot Detail');

    //make change
    $('[ng-click="on_edit()"]').click();
    var firstInput = $$('#edit_attribute_id').first();
    firstInput.sendKeys('protractor unique stuff');
    $('[ng-click="on_save()"]').click();

    // now historical items
    var historicalItems = element.all(by.repeater('historical_item in historical_items'));
    expect(historicalItems.count()).not.toBeLessThan(1);

    var labels = element.all(by.repeater('label in labels'));
    expect(labels.count()).toBeLessThan(1);
  });

  it('should go to settings in info pages', function () {
    $('#settings').click();
    $('[ng-if="grid.options.enableSelectAll"]').click().click();
    $$('[ng-class="{\'ui-grid-row-selected\': row.isSelected}"]').first().click();
    $('#item_title').click();
    var rows = element.all(by.repeater('field in columns'));
    expect(rows.count()).toBe(1);
  });

  it('should go to settings reset', function () {
    $('#settings').click();
    $$('.ui-grid-menu-button').first().click();
    $$('[ng-click="itemAction($event, title)"]').first().click();
    $('#item_title').click();
    var rows = element.all(by.repeater('field in columns'));
    expect(rows.count()).not.toBeLessThan(2);
  });


  it('should go to info pages and add remove label', function () {
    // add label
    $('[ng-click="open_update_labels_modal(inventory.id, inventory_type)"]').click();
    $('.modal-title').getText().then(function (label) {
      expect(label).toContain('Labels');
    });
    $$('[ng-model="label.is_checked_add"]').first().click();
    $('[ng-click="done()"]').click();

    var labels = element.all(by.repeater('label in labels'));
    expect(labels.count()).not.toBeLessThan(1);

    //remove label
    $('[ng-click="open_update_labels_modal(inventory.id, inventory_type)"]').click();
    $$('[ng-click="toggle_remove(label)"]').first().click();
    $('[ng-click="done()"]').click();
    var labels = element.all(by.repeater('label in labels'));
    expect(labels.count()).toBeLessThan(1);

    $('a.page_action.ng-binding').click();

  });

  it('should get property info from linked taxlots', function () {
    // re expand
    $$('[ng-click="treeButtonClick(row, $event)"]').first().click();

    $$('.ui-grid-icon-info-circled').get(2).click();
    expect(browser.getCurrentUrl()).toContain('/app/#/properties');
    expect($('.page_title').getText()).toEqual('Property Detail');
    $('a.page_action.ng-binding').click();
    expect(browser.getCurrentUrl()).toContain('/app/#/properties');
  });

  it('should change columns', function () {
    browser.get('/app/#/taxlots');
    $('#list-settings').click();
    $('[ng-if="grid.options.enableSelectAll"]').click().click();
    $$('[ng-class="{\'ui-grid-row-selected\': row.isSelected}"]').first().click();
    $('#inventory-list').click();
    var cols = $('.ui-grid-render-container.ui-grid-render-container-body').all(by.repeater('col in colContainer.renderedColumns'));
    expect(cols.count()).toBe(1);
    $('#list-settings').click();
    $('[ng-click="toggleMenu()"]').click();
    $$('[ng-click="itemAction($event, title)"]').get(1).click();
    $('[ng-click="toggleMenu()"]').click();
    $$('[ng-click="itemAction($event, title)"]').first().click();
    $('[ng-change="saveShowSharedBuildings()"]').click();
    $('#inventory-list').click();
    var cols = $('.ui-grid-render-container.ui-grid-render-container-body').all(by.repeater('col in colContainer.renderedColumns'));
    expect(cols.count()).not.toBeLessThan(2);
    browser.driver.navigate().refresh();
  }, 45000);
});

