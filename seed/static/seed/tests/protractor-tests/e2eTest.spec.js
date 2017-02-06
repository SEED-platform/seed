//main e2e Protractor test

// Helpers
var hasClass = function (element, cls) {
    return element.getAttribute('class').then(function (classes) {
        return classes.split(' ').indexOf(cls) !== -1;
    });
};

var EC = protractor.ExpectedConditions;

// Login
describe('When I visit the login page', function () {
    it('should see login', function () {
        browser.ignoreSynchronization = true; //login isn't angular based
        browser.get("/");
        element(by.id('id_email')).sendKeys(browser.params.login.user);
        element(by.id('id_password')).sendKeys(browser.params.login.password);
        element(by.className('btn btn-primary')).click();
    });
    it('should see title', function () {
        // browser.get("/app");
        // browser.ignoreSynchronization = false;
        expect(browser.getTitle()).toContain('SEED Platform');
    });
});


// Older Jasmine tests:
 describe('When I go to jamine tests', function () {
     it('should run jasmine unit tests and pass', function () {
        browser.get("/app/angular_js_tests");
        var passingBar = $('.passingAlert.bar');
        browser.wait(EC.presenceOf(passingBar), 5000);
        expect($('.passingAlert.bar').isPresent()).toBe(true);
     });
 });

 // Admin page:
 describe('When I go to admin page', function () {
     it('should create new test org', function () {
        browser.ignoreSynchronization = false;
        browser.get("/app/#/profile/admin");
        $('#org_name').sendKeys(browser.params.testOrg.parent);
        $('#user_emails').element(by.cssContainingText('option', browser.params.login.user)).click();
        $('[ng-click="org_form.add(org)"]').click();

        //  browser.wait(function() {
        //     var myNewOrg;
        //     return element.all(by.repeater('org in org_user.organizations')).then(function(rows) {
        //         expect(rows.length).not.toBeLessThan(1);
        //         for(var i=0;i<rows.length;i++){
        //             rows[i].all(by.tagName('td')).then(function(inner) {
        //                 for(var j=0;j<inner.length;j++){
        //                     inner[j].getText().then(function(text) {
        //                         if (text.includes(browser.params.testOrg.parent)) {
        //                             myNewOrg = inner;
        //                         }
        //                     });
        //                     if(myNewOrg) break;
        //                 }
        //             });
        //             if(myNewOrg) break;
        //         }
        //     });
        // }, 2000).then(function(){
        //     expect(myNewOrg.isPresent()).toBe(true);
        // });

        var myNewOrg = element.all(by.repeater('org in org_user.organizations')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.getText().then(function (label) {
                return label.includes(browser.params.testOrg.parent);
            });
        }).first();
        expect(myNewOrg.isPresent()).toBe(true);

     });
    it('should create new user for test org', function () {
        $('#first_name').sendKeys('Test');
        $('#last_name').sendKeys('Testy');
        $('#user_email').sendKeys('testy@test.com');
        $('[ng-model="user.organization"]').element(by.cssContainingText('option', browser.params.testOrg.parent)).click();
        $('[ng-click="user_form.add(user)"]').click();

        $('[ng-model="org_user.organization"]').element(by.cssContainingText('option', browser.params.testOrg.parent)).click();
        var myNewUser = element.all(by.repeater('user in org_user.users')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.getText().then(function (label) {
                return label.includes('testy@test.com');
            });
        }).first();
        expect(myNewUser.isPresent()).toBe(true);
    });

    it('should delete new user for test org', function () {
        $('[ng-model="org_user.organization"]').element(by.cssContainingText('option', browser.params.testOrg.parent)).click();
        var myNewUser = element.all(by.repeater('user in org_user.users')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.getText().then(function (label) {
                return label.includes('testy@test.com');
            });
        }).first();
        myNewUser.$('button').click();
        browser.sleep(100);
        expect(myNewUser.isPresent()).toBe(false);
    });
 });


// Accounts page
describe('When I visit the accounts page', function () {
    it('should see my organizations', function () {
        browser.ignoreSynchronization = false;
        browser.get("/app/#/accounts");

        var rows = element.all(by.repeater('org in orgs_I_own'));
        expect(rows.count()).not.toBeLessThan(1);
    });
    it('should find and create new sub org', function () {
        var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
            .element(by.xpath('..')).element(by.xpath('..'));
        expect(myNewOrg.isPresent()).toBe(true);

        browser.actions().mouseMove(myNewOrg.$('[ng-show="org.is_parent"]').$('.sub_head.sub_org.right')).perform();
        myNewOrg.$('.sub_head.sub_org.right').$('a').click(); 
        $('[id="createOrganizationName"]').sendKeys(browser.params.testOrg.child);
        $('[id="createOrganizationInvite"]').sendKeys(browser.params.login.user);
        $('.btn.btn-primary').click();
        
        var myNewSub = element(by.cssContainingText('.account_org.left', browser.params.testOrg.child))
            .element(by.xpath('..'));
        
        // expect(myNewSub.count() > 0);
        expect(myNewSub.isPresent()).toBe(true);
        browser.actions().mouseMove(myNewSub.$('.account_org.right')).perform();
        myNewSub.$('.account_org.right a').click();
    });
    it('should change the sub org name', function () {
        $('input').clear().then(function() {
            $('input').sendKeys(browser.params.testOrg.childRename);
            $('[ng-click="save_settings()"]').click();
            expect($('.page_title').getText()).toEqual(browser.params.testOrg.childRename);
        });
    });
    it('should go back to orgranizations', function () {
        $('[ui-sref="organizations"]').click();
        expect($('.page_title').getText()).toEqual('Organizations');
    });
});
describe('When I visit the the parent org', function () {
    it('should go to parent organization', function () {
        var myNewOrg = element(by.cssContainingText('.account_org.parent_org', browser.params.testOrg.parent))
            .element(by.xpath('..')).$('.account_org.right');
        
        expect(myNewOrg.isPresent()).toBe(true);

        browser.actions().mouseMove(myNewOrg).perform();
        myNewOrg.$('a').click();
        var myOptions = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Cycles';
            });
        }).first();
        myOptions.click();
        expect($('.table_list_container').isPresent()).toBe(true);
    });
    it('should create new cycle', function () {
        $('[ng-model="new_cycle.name"]').sendKeys(browser.params.testOrg.cycle);
        $('[ng-model="new_cycle.start"]').sendKeys('01-01-2017');
        $('[ng-model="new_cycle.end"]').sendKeys('12-31-2017');
        $('#btnCreateCycle').click();
        
        var myNewCycle = element.all(by.repeater('cycle in cycles')).filter(function(sub) {
            return sub.element(by.tagName('td')).$('[ng-show="!rowform.$visible"]').getText().then(function(label) { 
                return label == browser.params.testOrg.cycle;
            });
        }).first();
        expect(myNewCycle.element(by.tagName('td')).$('[ng-show="!rowform.$visible"]').getText()).toEqual(browser.params.testOrg.cycle);
    });
    it('should create new label', function () {
        var myOptions = element.all(by.css('a')).filter(function (elm) {
            return elm.getText().then(function(label) { 
                return label == 'Labels';
            });
        }).first();
        myOptions.click();
        
        $('input').sendKeys('fake label');
        $('.input-group-btn.dropdown').click();
        element(by.cssContainingText('.dropdown-menu.pull-right', 'orange')).click();
        $('#btnCreateLabel').click();
        var myNewLabel = element(by.cssContainingText('[editable-text="label.name"]', 'fake label'))
            .element(by.xpath('..')).element(by.xpath('..'));

        expect(myNewLabel.isPresent()).toBe(true);
        myNewLabel.$('[ng-click="deleteLabel(label, $index)"]').click();
        browser.sleep(300);
        $('.btn.btn-primary.ng-binding').click();
        expect(myNewLabel.isPresent()).toBe(false);
    });
});

// Select my new sub org
describe('When I click the orgs button', function () {
    it('should be able to switch to my org', function () {
        browser.get("/app/#/data");
        $('#btnUserOrgs').click();
        element(by.cssContainingText('[ng-click="set_user_org(org)"]', browser.params.testOrg.parent)).click();
        expect($('#btnUserOrgs').getText()).toEqual(browser.params.testOrg.parent)
    });
});

// // Data Set page
describe('When I visit the data set page', function () {
    it('should be able to create a new data set', function () {

        $('[ui-sref="dataset_list"]').click();
        browser.sleep(500);
        $('input').sendKeys('my fake dataset');
        $('[ng-click="create_dataset(dataset.name)"]').click();
        // selectDropdownbyText(element, browser.params.testOrg.cycle);
        element(by.cssContainingText('option', browser.params.testOrg.cycle)).click();
        // $('[buttontext="Upload a Spreadsheet"]').$('.qq-uploader').click();

        var path = require('path');
        // Select image
        var fileToUpload = '../../../../tests/data/portfolio-manager-sample.csv'
        var absolutePath = path.resolve(__dirname, fileToUpload);

        element(by.xpath('//input[@type="file"]')).sendKeys(absolutePath);
        var passingBar = $('.alert.alert-success');
        browser.ignoreSynchronization = true; //not angular based
        browser.wait(EC.presenceOf(passingBar), 120000);
        expect($('.alert.alert-success').isPresent()).toBe(true);
        expect($('[ng-click="goto_data_mapping()"]').isPresent()).toBe(true);
    });
    it('should take me to the mapping page', function () {
        $('[ng-click="goto_data_mapping()"]').click(); 
        browser.wait(EC.presenceOf($('.table_list_container.mapping')),5000);       
        expect($('.page_title').getText()).toContain('Data Mapping & Validation');
    });
    it('should have more than one mapped value and change prop/tl', function () {
        var cusRow = element.all(by.repeater('tcm in valids')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.element(by.tagName('strong')).getText().then(function (label) {
                return label == "Address 1"
            })
        }).first();
        cusRow.element(by.cssContainingText('option', 'Tax Lot')).click();
        $('[ng-click="remap_buildings()"]').click();
    });
    it('should go to mapping Validation', function () {
        browser.ignoreSynchronization = true;
        browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')),120000);       
        expect($('[heading="View by Property"]').isPresent()).toBe(true);
        expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
        var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).map(function (elm) {
            return elm;
        });
        expect(rows.length).not.toBeLessThan(1);
        browser.ignoreSynchronization = false;
    });

    it('should save mappings', function () {
        $('#save-mapping').click();
        browser.sleep(5000);
        $('#confirm-mapping').click();
    });
});


 // Check inventory Page:
 describe('When I go to the inventory page', function () {
    it('should ', function () {
    // click inventory
    });
 });


 // Delete created dataset:
 describe('When I go to the dataset page', function () {
    it('should delete dataset', function () {
    // click dataset 
    });
 });

 // Admin page last:
 describe('When I go to admin page', function () {
    it('should delete new test org', function () {
        browser.ignoreSynchronization = false;
        browser.get("/app/#/profile/admin");
        var myNewOrg = element.all(by.repeater('org in org_user.organizations')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.getText().then(function (label) {
                return label.includes(browser.params.testOrg.parent);
            });
        }).first();
        expect(myNewOrg.isPresent()).toBe(true);

        myNewOrg.$('[ng-click="confirm_inventory_delete(org)"]').click();
        browser.wait(EC.alertIsPresent(), 10000, "Remove inventory Alert is not present");
        browser.switchTo().alert().accept();
        // expect(myNewOrg.$('[ng-click="confirm_inventory_delete(org)"]').isDisabled()).toBe(true);

        browser.wait(EC.presenceOf(myNewOrg.$('[ng-click="confirm_inventory_delete(org)"]')), 120000);
        myNewOrg.$('[ng-click="confirm_org_delete(org)"]').click();
        browser.wait(EC.alertIsPresent(), 10000, "Remove org Alert is not present";
        browser.switchTo().alert().accept();
        // accept again
        browser.wait(EC.alertIsPresent(), 10000, "Second remove org Alert is not present");
        browser.switchTo().alert().accept();
        browser.sleep(5000)
        expect(myNewOrg.isPresent()).toBe(false);
    });
 });
