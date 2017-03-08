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
        $('[ng-change="setAllInventoryTypes()"]').element(by.cssContainingText('option', 'Tax Lot')).click();
        var cusRow = element.all(by.repeater('tcm in valids')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.$('[ng-model="tcm.suggestion_table_name"]').getText().then(function (label) {
                expect(label).toEqual('Tax Lot');
                return;
            })
        });
    });

    it('should go to mapping Validation', function () {
        $$('[ng-click="get_mapped_buildings(true)"]').first().click();
        browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')),30000);       
        expect($('[heading="View by Property"]').isPresent()).toBe(true);
        expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
        var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).filter(function (elm) {
            expect(elm.length).not.toBeLessThan(1);
            return elm;
        });
        $$('[ng-click="open_cleansing_modal()"]').first().click();
        browser.wait(EC.presenceOf($('.modal-title')),30000);
        expect($('.modal-body.ng-scope').getText()).toContain('No warnings/errors');
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
		element(by.cssContainingText('#selected-cycle', browser.params.testOrg.cycle)).click();
		var rows = element.all(by.repeater('b in inventory'));
		expect(rows.count()).not.toBeLessThan(1);
		$$('[ui-sref="matching({importfile_id: importfile_id, inventory_type: \'taxlots\'})"]').first().click();
		rows = element.all(by.repeater('b in inventory'));
		expect(rows.count()).not.toBeLessThan(1);
		//Need more stuff here....
	});

	//Pairing
	it('should edit pairing', function () {
		$$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();
		$$('#data-pairing-0').first().click()
        expect($('.page_title').getText()).toContain('Pair Properties to Tax Lots');

	});

	//Delete
	it('should delete data stuffs', function () {
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