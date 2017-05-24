// test Data Quality, Sharing, Reports, delete function and other misc items after data is loaded
var EC = protractor.ExpectedConditions;


describe('When I do miscellaneous things', function () {

	it ('should reset sync', function () {
		browser.ignoreSynchronization = false;
	});

	//Data Quality
	it('should see my organizations', function () {
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
	});    

	it('should select and edit one rule, click save settings', function () {
		var rowCount = element.all(by.repeater('rule in ruleGroup'));
		expect(rowCount.count()).toBe(1);

		$$('[ng-model="rule.min"]').first().click().clear().then(function(){
			$$('[ng-model="rule.min"]').first().sendKeys('0');
		});
		$$('[ng-click="create_new_rule()"]').first().click();         
		expect(rowCount.count()).toBe(2);
			
		$$('[ng-click="save_settings()"]').first().click();  
		browser.wait(EC.presenceOf($('.fa-check')),10000);
		browser.driver.navigate().refresh();
		expect(rowCount.count()).toBe(1);

		$$('[ng-model="rule.data_type"]').first().click();
		$('[label="Number"]').click();

		$$('[ng-click="change_required(rule)"]').first().click();

		$$('[ng-model="rule.severity"]').first().click();
		$('[value="warning"]').click();

		$$('[ng-model="rule.units"]').first().click();
		$('[label="square feet"]').click();

		$$('[ng-click="rule.rule_type = 1; rule.enabled = !rule.enabled"]').first().click().click();
		
		$$('[ng-click="save_settings()"]').first().click();  
		browser.wait(EC.presenceOf($('.fa-check')),10000);
		browser.driver.navigate().refresh();
	});    

	it('should create new label and associate with rule', function () {
		//no rule should have a label
		expect($('.form-control.label.label-primary').isPresent()).toBe(false);

		//create label but select not created one
		$$('[ng-click="create_label(rule, $index)"]').first().click();
		expect($('.modal-title').isPresent()).toBe(true);
		$('#labelName').sendKeys('ruleLabel');
		$$('.btn.btn-primary').first().click();
		$$('.btn-default.action_link').get(1).click();

		//check label was attached after save and refresh
		$$('[ng-click="save_settings()"]').first().click();
		browser.driver.navigate().refresh();
	});

	it('should reset all rules and add labels', function () {
		$$('[ng-click="restore_defaults()"]').first().click();
		var rowCount = element.all(by.repeater('rule in ruleGroup'));
		expect(rowCount.count()).toBe(21);
		$$('[ng-click="reset_all_rules()"]').first().click();
		expect(rowCount.count()).toBe(20);

		$('[ui-sref="organization_data_quality({organization_id: org.id, inventory_type: \'taxlots\'})"]').click();
		$$('[ng-click="create_label(rule, $index)"]').first().click();
		$$('.btn.btn-sm.btn-default.action_link').first().click();

		$$('[label="Text"]').get(1).click();

		$$('[ng-repeat="field in sortedRuleGroups()"]').get(1).$('[ng-model="rule.text_match"]').sendKeys("1235");
		$$('[ng-click="create_label(rule, $index)"]').first().click();
		$$('.btn-default.action_link').get(2).click();
		$$('[ng-click="save_settings()"]').first().click();
		browser.driver.navigate().refresh();
		expect(element.all(by.repeater('rule in ruleGroup')).first().$('.form-control.label.label-primary').isPresent()).toBe(true);
		$$('[ng-click="removeLabelFromRule(rule)"]').first().click();
		expect(element.all(by.repeater('rule in ruleGroup')).first().$('.form-control.label.label-primary').isPresent()).toBe(false);
		$$('[ng-click="save_settings()"]').first().click();
		browser.driver.navigate().refresh();
		expect(element.all(by.repeater('rule in ruleGroup')).first().$('.form-control.label.label-primary').isPresent()).toBe(false);
		$$('[ng-click="create_label(rule, $index)"]').first().click();
		$$('.btn.btn-sm.btn-default.action_link').first().click();
		$$('[ng-click="save_settings()"]').first().click();
	});    

	it('should go to labels page and check that new label was created with new rule', function () {
		var myOptions2 = element.all(by.css('a')).filter(function (elm) {
			return elm.getText().then(function(label) { 
				return label == 'Labels';
			});
		}).first();
		myOptions2.click();
		expect($('b').getText()).toContain('Existing Labels');

		var labelRowCount = element.all(by.repeater('label in labels'));
		expect(labelRowCount.count()).toBe(15);
	});

	// Check data quality on inventory page
	it('should select first item and test data quality modal and presence of rows', function () {
		$('#sidebar-inventory').click();
		$$('[ng-click="selectButtonClick(row, $event)"]').first().click();
		$('#btnInventoryActions').click();
		$$('[ng-click="run_data_quality_check()"]').click();
		expect($('.modal-title').getText()).toContain('Data Quality Results');
		var rowCount2 = element.all(by.repeater('result in row.data_quality_results'));
		expect(rowCount2.count()).toBe(2);
		$$('[ng-click="close()"]').click();

		$('[ng-class="{\'ui-grid-all-selected\': grid.selection.selectAll}"]').click();
		$('#btnInventoryActions').click();
		$$('[ng-click="run_data_quality_check()"]').click();
		expect($('.modal-title').getText()).toContain('Data Quality Results');
		var rowCount2 = element.all(by.repeater('result in row.data_quality_results'));
		expect(rowCount2.count()).toBe(15);
		$$('[ng-click="close()"]').click();

		//check labels - 
		$('[ui-sref="inventory_list({inventory_type: \'taxlots\'})"]').click();
		$('#tagsInput').click();
		$$('.suggestion-item.selected').first().click();
		var rows = $('.left.ui-grid-render-container-left.ui-grid-render-container')
				.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows'));
		expect(rows.count()).toBe(11);
		$('[ng-click="clear_labels()"]').click();
		$$('.suggestion-item.selected').get(1).click();
		expect(rows.count()).toBe(10);
		$('[uib-btn-radio="\'or\'"]').click();
		expect(rows.count()).toBe(11);
		$('[ng-click="clear_labels()"]').click();
		expect(rows.count()).toBe(11);

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

		$('[ng-click="open_data_upload_modal(d)"]').click();
		$('[ng-click="cancel()"].btn-default').click();
		browser.sleep(1000);
		$('[ng-click="edit_dataset_name(d)"]').click();
		$('[ng-click="cancel_edit_name(d)"]').click();
		browser.sleep(2000);
		$('[ng-click="edit_dataset_name(d)"]').click();
		$('#editDatasetName').sendKeys('2');
		$('[ng-click="save_dataset_name(d)"]').click();
		browser.sleep(2000);

		$$('[ng-click="confirm_delete(d)"]').first().click();
		$$('[ng-click="delete_dataset()"]').first().click();
		rows = element.all(by.repeater('d in datasets'));
		expect(rows.count()).toBe(0);
	});

});