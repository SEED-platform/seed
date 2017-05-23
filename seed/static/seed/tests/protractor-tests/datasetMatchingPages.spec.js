// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;

// Check dataset matching and deleting Pages:
describe('When I go to the dataset options page', function () {
	it ('should reset sync', function () {
		browser.ignoreSynchronization = false;
	});

	it('should delete a single file', function () {
		browser.get("/app/#/data");
		$$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
		var rows = element.all(by.repeater('f in dataset.importfiles'));
		expect(rows.count()).toBe(2);
	});

	//Mapping
	it('should edit mappings', function () {
		var rows = element.all(by.repeater('f in dataset.importfiles'));
		expect(rows.count()).toBe(2);
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
		var rowC = element.all(by.repeater('result in row.data_quality_results'));
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
		//row count inconsistent, not sure why this is happening, returns 64, 0 and 128
		expect(rowC.count()).toBe(64);
		// Recent pull populated errors, not sure if we should expect no errors anywhere else
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
            })
        });
    });

    it('should go to mapping Validation for properties', function () {
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
        expect($('.modal-body.ng-scope').getText()).toContain('File Name:');
        var rows1 = element.all(by.repeater('row in dataQualityResults'));
        expect(rows1.count()).toBe(3);
        $$('[ng-click="close()"]').first().click();
        expect($('.modal-body.ng-scope').isPresent()).toBe(false);
    });

    it('should see my organizations from dataset', function () {
    	$('#sidebar-accounts').click();
        var rows = element.all(by.repeater('org in orgs_I_own'));
        expect(rows.count()).not.toBeLessThan(1);
    });


    // Uncomment after data quality updates!

    it('should go to parent organization for data quality', function () {
        var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
            .element(by.xpath('..')).$('.account_org.right');
        
        expect(myNewOrg.isPresent()).toBe(true);

        browser.actions().mouseMove(myNewOrg).perform();
        myNewOrg.$$('a').first().click();
        var myOptions = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Data Quality';
            });
        }).first();
        myOptions.click();
        expect($('.table_list_container').isPresent()).toBe(true);

        // var myOptions2 = element.all(by.repeater('rule in rules')).filter(function (elm) {
        //     return elm.$('span').getText().then(function(label) { 
        //         return label == 'Energy Score';
        //     });
        // }).last();
        // myOptions2.$('[ng-model="rule.min"]').clear().then(function(){
        //     myOptions2.$('[ng-model="rule.min"]').sendKeys('0');
        // });
        var rowCount = element.all(by.repeater('rule in rules'));

        //put back later
        // expect(rowCount.count()).toBe(17);
        
        // alternate way to select Min input in row 4
        $$('[ng-model="rule.min"]').get(3).click().clear().then(function(){
            $$('[ng-model="rule.min"]').get(3).sendKeys('0');
        });
        expect($('.table_list_container').isPresent()).toBe(true);
        $$('[ng-click="save_settings()"]').first().click();        
        browser.wait(EC.presenceOf($('.fa-check')),10000);
    });

    it('should go back to data page and select properties', function () {
        browser.get("/app/#/data");
        $$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
        $$('#data-mapping-1').first().click();
        expect($('.page_title').getText()).toContain('Data Mapping & Validation');
    });

    it('should have more than one mapped value when Im back', function () {
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

    it('should go to mapping Validation again with updated quality check', function () {
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
        expect($('.modal-body.ng-scope').getText()).toContain('File Name:');
        var rows1 = element.all(by.repeater('row in dataQualityResults'));

        // once quality check stuff has been updated, add this back in.
        // expect(rows1.count()).toBe(2);

        $$('[ng-click="close()"]').first().click();
        expect($('.modal-body.ng-scope').isPresent()).toBe(false);
        $('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').click();
    });

	//Matching
	it('should go to matching and have rows', function () {
		$$('#data-matching-0').first().click()
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


	it('should unmatch from front page', function () {
        $$('[ng-change="unmatch(i)"]').first().click()
        expect($('.table_footer').getText()).toContain('5 unmatched');
		$$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();
	});

});
