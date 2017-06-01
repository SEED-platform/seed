// test Data Quality, Sharing, Reports, delete function and other misc items after data is loaded
var EC = protractor.ExpectedConditions;


describe('When I go to the dataset options page', function () {

	it ('should reset sync', function () {
		browser.ignoreSynchronization = false;
	});

	//Pairing
	it('should edit pairing', function () {
		$$('#data-pairing-0').first().click()
		expect($('.page_title').getText()).toContain('Pair Properties to Tax Lots');
		element(by.cssContainingText('[ng-model="cycle.selected_cycle"] option', browser.params.testOrg.cycle)).click();
		browser.sleep(2000);

		// Gotta figure this out, remote has 1 unpaired.
		expect($('.pairing-text-left').getText()).toContain('Showing 19 Properties');
		expect($('.pairing-text-right').getText()).toContain('Showing 11 Tax Lots');
	});

	it('should edit delete pairings', function () {
		$$('.unpair-child').count().then( function (count) {
			for (var index = 0; index < count; index++) {
				// console.log('index: ', index, count)
				var option = $$('.unpair-child').first();
				option.click();
				browser.sleep(200);
			};
		});

		expect($$('.unpair-child').count()).toBeLessThan(1);
	}, 60000);

	it('should edit change pair view', function () {
		browser.sleep(2000);
		element(by.cssContainingText('[ng-change="inventoryTypeChanged()"] option', "Tax Lot")).click();
		// browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')),30000);
		expect($('.page_title').getText()).toContain('Pair Tax Lots to Properties');
		expect($('.pairing-text-right').getText()).toContain('Showing 19 Properties (19 unpaired)');
		expect($('.pairing-text-left').getText()).toContain('Showing 11 Tax Lots (11 unpaired)');
		browser.sleep(2000);
	});

	it('should edit drag pairs', function () {
		// var dragElement = $$('.pairing-data-row.grab-pairing-left').first();
		var dragElement = element.all(by.repeater('row in newLeftData')).first();
		var dropElement = $$('.pairing-data-row-indent').first();
		var lastDropElement = $$('.pairing-data-row-indent').last();
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

});