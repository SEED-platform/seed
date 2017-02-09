// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;
// Check inventory Page:
describe('When I go to the inventory page', function () {
	it('should change to our test cycle', function () {
		browser.ignoreSynchronization = false;
		browser.get("/app/#/properties");
		$('[ng-change="update_cycle(cycle.selected_cycle)"]').element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();

		var rows = $('.left.ui-grid-render-container-left.ui-grid-render-container')
					.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows'));

		rows.count().then(function (count) {
			$('.item-count.ng-binding').getText().then(function (label) {
				expect(label).toContain(count);
			})
		})
	});

	it('should filter', function () {
		var rows = $('.left.ui-grid-render-container-left.ui-grid-render-container')
					.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows'));

		rows.first().getText().then(function (label) {
			$$('[ng-model="colFilter.term"]').first().sendKeys(label);
		});
		//after filter
		expect(rows.count()).not.toBeLessThan(1);

		//clear by clicking the 'x' -> child of sibling of text input
		$$('[ng-model="colFilter.term"]').first().element(by.xpath('..')).$('[ui-grid-one-bind-aria-label="aria.removeFilter"]').click();
		expect($$('[ng-model="colFilter.term"]').first().getAttribute('value')).toEqual('');
		$$('[ng-model="colFilter.term"]').first().sendKeys('this is something long and fake to get nothing to filter');
		expect(rows.count()).toBeLessThan(1);
		$$('[ng-model="colFilter.term"]').first().element(by.xpath('..')).$('[ui-grid-one-bind-aria-label="aria.removeFilter"]').click();
	});

	it('should filter semi colon and expand', function () {
		var jurisTL = $$('[role="columnheader"]').filter(function(elm) {
			return elm.getText().then(function (label) {
				return label.includes('Jurisdiction Tax Lot ID');
			});
		}).first();
		jurisTL.$$('[ng-model="colFilter.term"]').first().sendKeys(';');
	});

	it('should go to info pages', function () {
		$$('[ng-click="treeButtonClick(row, $event)"]').first().click();
		$$('.ui-grid-icon-info-circled').first().click();
		expect(browser.getCurrentUrl()).toContain("/app/#/properties");
		expect($('.page_title').getText()).toEqual('Property Detail');
		$('a.page_action.ng-binding').click();


		// add more about info mages here: TODO
		// repeater: historical_item in historical_items should be 0
		// edit, save, should be 1
		// add label
		// after you go back, look for your edit
		// filter by label (should only have 1 row)
		// clear labels


		// re expand
		$$('[ng-click="treeButtonClick(row, $event)"]').first().click();
		
		$$('.ui-grid-icon-info-circled').get(2).click();
		expect(browser.getCurrentUrl()).toContain("/app/#/taxlots");
		expect($('.page_title').getText()).toEqual('Tax Lot Detail');
		$('a.page_action.ng-binding').click();
		expect(browser.getCurrentUrl()).toContain("/app/#/taxlots");
	});

	it('should change columns', function () {
		browser.get("/app/#/properties");
		$('#list-settings').click();
		$('[ng-if="grid.options.enableSelectAll"]').click().click();
		$$('[ng-class="{\'ui-grid-row-selected\': row.isSelected}"]').first().click();
		$('#inventory-list').click();
		var cols = $('.ui-grid-render-container.ui-grid-render-container-body').all(by.repeater('col in colContainer.renderedColumns'));
		expect(cols.count()).toBe(1);
	});

	//TODO reports?

	//Taxlots
});


// Delete created dataset:
// describe('When I go to the dataset page', function () {
//     it('should delete dataset', function () {
//     // click dataset 
//     });
// });
