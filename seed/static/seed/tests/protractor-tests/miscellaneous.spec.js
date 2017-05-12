// test Data Quality, Sharing, Reports, delete function and other misc items after data is loaded
var EC = protractor.ExpectedConditions;


describe('When I go to the dataset options page', function () {
	it('should delete a single file', function () {
		// browser.get("/app/#/data");
		$('#sidebar-data').click();
		$$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
		var rows = element.all(by.repeater('f in dataset.importfiles'));
		expect(rows.count()).toBe(2);
	});

	//Mapping for data quality initial check for rows
	it('should go to mappings', function () {
		$$('#data-mapping-1').first().click()
		expect($('.page_title').getText()).toContain('Data Mapping & Validation');
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
	});

	it('should open the data quality modal and check to have no errors', function () {		
		$$('[ng-click="open_data_quality_modal()"]').first().click();
		browser.wait(EC.presenceOf($('.modal-title')),30000);
		expect($('.modal-body.ng-scope').getText()).toContain('No warnings/errors');
		$$('[ng-click="close()"]').first().click();
		expect($('.modal-body.ng-scope').isPresent()).toBe(false);
	});

	//Data Quality
    it('should see my organizations', function () {
        browser.ignoreSynchronization = false;
        browser.get("/app/#/accounts");
        var rows = element.all(by.repeater('org in orgs_I_own'));
        expect(rows.count()).not.toBeLessThan(1);
    });

    it('should go to parent organization', function () {
        var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
            .element(by.xpath('..')).$('.account_org.right');
        expect(myNewOrg.isPresent()).toBe(true);
        browser.actions().mouseMove(myNewOrg).perform();
        myNewOrg.$$('a').first().click();
    });    

    it('should select Data Quality tab', function () {
        var myOptions = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Data Quality';
            });
        }).first();
        myOptions.click();
        expect($('.table_list_container').isPresent()).toBe(true);

        // test not working yet
        // var myOptions2 = element.all(by.repeater('rule in rules')).filter(function (elm) {
        //     return elm.$('span').getText().then(function(label) { 
        //         return label == 'Energy Score';
        //     });
        // }).last();
        // myOptions2.$('[ng-model="rule.min"]').clear().then(function(){
        //     myOptions2.$('[ng-model="rule.min"]').sendKeys('0');
        // });
    });    

    it('should select and edit one rule, click save settings', function () {
        var rowCount = element.all(by.repeater('rule in ruleGroup'));
        expect(rowCount.count()).toBe(20);
        // alternate way to select Min input in row 4
        $$('[ng-model="rule.min"]').get(3).click().clear().then(function(){
            $$('[ng-model="rule.min"]').get(3).sendKeys('0');
        });
        $$('[ng-click="create_new_rule()"]').first().click();         
        expect(rowCount.count()).toBe(21);

        //change in drop down clears minimum and maximum fields if field type changes

        //test required and not null checkbox

		$$('[ng-click="save_settings()"]').first().click();  
		browser.wait(EC.presenceOf($('.fa-check')),10000);
		     
	    //test new rule is enabled by default
	    //work on this, not working 
		// var box = $$('[ng-model="rule.enabled"]').get(9);
  //       expect(element(by.model('rule.enabled').get(9)).isSelected()).toBeTruthy();

  		// not working 
        // $$('[ng-model="rule.enabled"]').then(function(btn) {
        // 	expect(btn[9].attr('checked')).toBe('true');
        // });

    });    

    it('should go to labels page and check that new label was created with new rule', function () {
        var myOptions2 = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Labels';
            });
        }).first();
        myOptions2.click();
        
  		expect($('b').getText()).toContain('Existing Labels');

        var newLabel = element(by.cssContainingText('[editable-text="label.name"]', 'Invalid PM Property ID'))
        	.element(by.xpath('..')).element(by.xpath('..'));
        	//failing right now
        expect(newLabel.isPresent()).toBe(true);

        // not working yet
        // expect(newLabel.getText()).toContain('Invalid PM Property ID');

        var labelRowCount = element.all(by.repeater('label in labels'));
        expect(labelRowCount.count()).toBe(15);
    });

    it('should go back to Data Quality page and check row count on properties and taxlots tabs', function () {
        var rowCount = element.all(by.repeater('rule in ruleGroup'));
        var myOptions = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Data Quality';
            });
        }).first();
        myOptions.click();
        expect(rowCount.count()).toBe(21);
        expect($('.table_list_container').isPresent()).toBe(true);

        $$('[ng-model="rule.min"]').get(4).click().clear().then(function(){
            $$('[ng-model="rule.min"]').get(4).sendKeys('1');
        });
        $$('[ng-model="rule.min"]').get(4).click().clear().then(function(){
            $$('[ng-model="rule.min"]').get(4).sendKeys('1');
        });
        $$('[ng-model="rule.min"]').get(5).click().clear().then(function(){
            $$('[ng-model="rule.min"]').get(5).sendKeys('2');
        });
        $$('[ng-model="rule.min"]').get(5).click().clear().then(function(){
            $$('[ng-model="rule.min"]').get(5).sendKeys('2');
        });
        $$('[ng-click="save_settings()"]').first().click();
        

        expect($('.warning').isPresent()).toBe(true);
        $$('[ui-sref="organization_data_quality({organization_id: org.id, inventory_type: \'taxlots\'})"]').first().click();
        $$('[ui-sref="organization_data_quality({organization_id: org.id, inventory_type: \'properties\'})"]').first().click();
        // expect($$('[ng-model="rule.min"]').get(4).getText()).toContain('1');
        $$('[ng-click="create_new_rule()"]').click().click();
        expect(rowCount.count()).toBe(23);
    });

    it('should save settings and check delete row functionality', function () {
        expect($('h2').getText()).toContain('Data Quality');
    	var rowCount = element.all(by.repeater('rule in ruleGroup'));
        $$('[ng-click="save_settings()"]').first().click();        
        browser.wait(EC.presenceOf($('.fa-check')),10000);
        // not working
        // $('.warning').element(by.cssContainingText('option', 'PM Property ID')).click();
        // $$('[ng-model="rule.label"]').first().element(by.cssContainingText('option', 'Invalid PM Property ID')).click();
        $$('.btn-danger.btn-rowform').last().click();
        expect(rowCount.count()).toBe(22);
		$$('[ng-click="create_new_rule()"]').click();
		expect(rowCount.count()).toBe(23);  
		expect($('.warning').isPresent()).toBe(true);
	    $$('.btn-danger.btn-rowform').last().click();
	    expect(rowCount.count()).toBe(21);
		$$('[ui-sref="organization_data_quality({organization_id: org.id, inventory_type: \'taxlots\'})"]').first().click();
        expect(rowCount.count()).toBe(2);
    });

    it('should go to data page and select properties', function () {
        // should be later: $$('[ui-sref="dataset_detail({dataset_id: import_file.dataset.id})"]').first().click();

        //temp
        browser.get("/app/#/data");
        $$('[ui-sref="dataset_detail({dataset_id: d.id})"]').first().click();
        $$('#data-mapping-0').first().click();
        expect($('.page_title').getText()).toContain('Data Mapping & Validation');
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
    });

    it('should open the Data Quality Modal and check for presence of errors', function () {
        $$('[ng-click="open_data_quality_modal()"]').first().click();
        browser.wait(EC.presenceOf($('.modal-title')),30000);
        // expect($('.modal-body.ng-scope').getText()).toContain('File Name:');
        var rows1 = element.all(by.repeater('row in dataQualityResults'));

        // expect(rows1.count()).toBe(2);

        $$('[ng-click="close()"]').first().click();
        expect($('.modal-body.ng-scope').isPresent()).toBe(false);
    });

     // Organizations Data Sharing page
    it('should see my organizations from dataset again', function () {
        $('#sidebar-accounts').click();
        var rows = element.all(by.repeater('org in orgs_I_own'));
        expect(rows.count()).not.toBeLessThan(1);
    });

    it('should go to parent organization and select Sharing', function () {
        var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
            .element(by.xpath('..')).$('.account_org.right');
        expect(myNewOrg.isPresent()).toBe(true);
        browser.actions().mouseMove(myNewOrg).perform();
        myNewOrg.$$('a').first().click();
        var myOptions3 = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Sharing';
            });
        }).first();
        myOptions3.click();
    });

    it('should test filters on sharing page and click save button', function () {
        expect($('.table_list_container').isPresent()).toBe(true);
        $$('[ng-model="controls.public_select_all"]').first().click();
        var rowCheck = element.all(by.repeater('field in fields'));
        expect(rowCheck.count()).toBe(43); 
        $$('[ng-model="filter_params.title"]').first().click().sendKeys('Ad');
        expect(rowCheck.count()).toBe(4);
        $$('[ng-model="filter_params.title"]').first().click().clear();
        expect(rowCheck.count()).toBe(43); 
        $$('[ng-model="filter_params.title"]').first().click().sendKeys('This is some text to test the filter.');
        expect(rowCheck.count()).toBe(0);
        $$('[ng-click="save_settings()"]').first().click();
        browser.wait(EC.presenceOf($('.fa-check')),10000);
    });

	// Reports page from Inventory
    it('should see inventory page and test filtering/item counter', function () {
        $('#sidebar-inventory').click();
        expect($('.ui-grid-contents-wrapper').isPresent()).toBe(true);
        expect($('.page_title').getText()).toContain('Properties');
        $('.form-control.input-sm').element(by.cssContainingText('option', 'Protractor test cycle')).click();
        expect($('.item-count').getText()).toContain('18 Properties');
        $$('[ng-model="colFilter.term"]').first().click().sendKeys('2342').then();
        expect($('[ng-model="cycle.selected_cycle"]').getText()).toContain('Protractor test cycle');
        expect($('.item-count').getText()).toContain('1 Property');
        $$('[ng-model="colFilter.term"]').first().clear();
        expect($('.item-count').getText()).toContain('18 Properties');
        $$('[href="#/taxlots"]').click();
        expect($('.page_title').getText()).toContain('Tax Lots');
        expect($('.item-count').getText()).toContain('11 Tax Lots');
    });

    it('should go to reports page and test chart creation functionality', function () {
        $('#reports').click();
        expect($('.page_title').getText()).toContain('Inventory Reports');
        expect($('svg').isPresent()).toBe(true);
        $('.btn.btn-primary').click();
        browser.wait(EC.presenceOf($('#dimple-use-description-2017--0-99k-2017--')), 10000);
        browser.wait(EC.presenceOf($('#dimple-use-description-2017--500-599k-2017--')), 10000);
        browser.wait(EC.presenceOf($('.dimple-series-0')), 10000);
        expect($('.fa.fa-square').isPresent()).toBe(true);
        expect($('.fa.fa-circle').isPresent()).toBe(true);
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