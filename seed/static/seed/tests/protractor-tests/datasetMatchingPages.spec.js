// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;

// Check dataset matching and deleting Pages:
describe('When I go to the dataset options page', function () {
	it('should delete a single file', function () {
		browser.get("/app/#/data");
		$$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
		var rows = element.all(by.repeater('f in dataset.importfiles'));
		expect(rows.count()).toBe(2);

	});

	//Mapping
	it('should edit mappings', function () {
		$$('#data-mapping-0').first().click()
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
			})
		});
	});

	it('should go to mapping Validation', function () {
		$$('[ng-click="get_mapped_buildings()"]').first().click();
		browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')),30000);
		expect($('[heading="View by Property"]').isPresent()).toBe(true);
		expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
		var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter(function (elm) {
			expect(elm.length).not.toBeLessThan(1);
			return elm;
		});
		$$('[ng-click="open_data_quality_modal()"]').first().click();
		browser.wait(EC.presenceOf($('.modal-title')),30000);
		// expect($('.modal-body.ng-scope').getText()).toContain('No warnings/errors');
		$$('[ng-click="close()"]').first().click();
		expect($('.modal-body.ng-scope').isPresent()).toBe(false);
	});

	//Matching
	it('should edit matching', function () {
		$$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();
		var rows = element.all(by.repeater('f in dataset.importfiles'));
		expect(rows.count()).toBe(2);
		$$('#data-matching-0').first().click()
	});

	it('should go to matching and have rows', function () {
		expect($('.page_title').getText()).toContain('Data Matching');
        expect($('.table_footer').getText()).toContain('4 unmatched');
		element(by.cssContainingText('#selected-cycle', browser.params.testOrg.cycle)).click();
        $('#showHideFilterSelect').element(by.cssContainingText('option', 'Show Matched')).click();
		var rows = element.all(by.repeater('i in inventory'));
		expect(rows.count()).not.toBeLessThan(1);
		$$('[ui-sref="matching_detail({importfile_id: import_file.id, inventory_type: inventory_type, state_id: i.id})"]').first().click();
		rows = element.all(by.repeater('state in available_matches'));
		expect(rows.count()).not.toBeLessThan(1);
        $('[ng-change="unmatch()"]').click();
        browser.wait(EC.presenceOf($('.message')),10000);
        $('[ui-sref="matching_list({importfile_id: import_file.id, inventory_type: inventory_type})"]').click();
        expect($('.table_footer').getText()).toContain('5 unmatched');
        $('#showHideFilterSelect').element(by.cssContainingText('option', 'Show Unmatched')).click();
		$$('[ui-sref="matching_detail({importfile_id: import_file.id, inventory_type: inventory_type, state_id: i.id})"]').first().click();
        $$('[ng-change="checkbox_match(state)"]').first().click();
        browser.wait(EC.presenceOf($('.message')),10000);
        $('[ui-sref="matching_list({importfile_id: import_file.id, inventory_type: inventory_type})"]').click();
        $('#showHideFilterSelect').element(by.cssContainingText('option', 'Show All')).click();
        expect($('.table_footer').getText()).toContain('4 unmatched');
	});

	//Pairing
	it('should edit pairing', function () {
		// should be later: $$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();

		//temp
		browser.get("/app/#/data");
		$('.import_name').click();
		// temp
		browser.wait( EC.presenceOf( $('.data_file_name'), 5000 ));
		$$('#data-pairing-0').first().click()
		expect($('.page_title').getText()).toContain('Pair Properties to Tax Lots');
		element(by.cssContainingText('[ng-model="cycle.selected_cycle"] option', browser.params.testOrg.cycle)).click();
		browser.sleep(2000);

		// Gotta figure this out, remote has 1 unpaired.
		expect($('.pairing-text-left').getText()).toContain('Showing 18 Properties');
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

		expect($('.pairing-text-right').getText()).toContain('Showing 18 Properties (18 unpaired)');
		expect($('.pairing-text-left').getText()).toContain('Showing 11 Tax Lots (11 unpaired)');

		browser.sleep(2000);
	});



	it('should edit drag pairs', function () {
		browser.ignoreSynchronization = true;
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

		expect($('.pairing-text-right').getText()).toContain('Showing 18 Properties (16 unpaired)');
		expect($('.pairing-text-left').getText()).toContain('Showing 11 Tax Lots (10 unpaired)');
		browser.sleep(2000);
	});

	//Delete
	it('should delete data stuffs', function () {
		browser.ignoreSynchronization = false;
		browser.get("/app/#/data");
		$$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
		$$('.delete_link').get(1).click();
		$$('[ng-click="delete_file()"]').click();
		var rows = element.all(by.repeater('f in dataset.importfiles'));
		expect(rows.count()).toBe(1);
		$$('[ui-sref="dataset_list"]').first().click();
		$$('[ng-click="confirm_delete(d)"]').first().click();
		$$('[ng-click="delete_dataset()"]').first().click();
		rows = element.all(by.repeater('d in datasets'));
		expect(rows.count()).toBe(0);
	});
});