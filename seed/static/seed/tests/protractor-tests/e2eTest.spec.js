//main e2e Protractor test

// Helpers
var hasClass = function (element, cls) {
    return element.getAttribute('class').then(function (classes) {
        return classes.split(' ').indexOf(cls) !== -1;
    });
};

var selectDropdownbyText = function ( element, optionSelect ) {
    element.all(by.tagName('option')).filter(function(org) {
        return org.getText().then(function(label) { 
            return label == optionSelect;
        });
    }).first().click();
};

// This is the name of the org we're working on. i.e. first parent we find
var globalOrg;
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
        expect(browser.getTitle()).toEqual('SEED Platform™');
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
        // browser.get("/app/#/profile/admin");
     });
 });


// Accounts page
// describe('When I visit the accounts page', function () {
//     it('should see my organizations', function () {
//         browser.ignoreSynchronization = false;
//         browser.get("/app/#/accounts");

//         var orgsAreThere = $('.section_content_container').$('.section_content').$('.table_list_container');

    //     browser.wait(EC.presenceOf(orgsAreThere), 5000);
    //     var rows = element.all(by.repeater('org in orgs_I_own')).map(function (elm) {
    //         return elm;
    //     });
    //     expect(rows.length).not.toBeLessThan(1);
    // });
    // it('should find and create new sub org', function () {
    //     var myDiv = element.all(by.css('[ng-show="org.is_parent"]')).filter(function (elm) {
//             return elm.isDisplayed().then(function (isDisplayed) {
//                 return isDisplayed;
//             });
//         }).first();

//         // This is the name of the org we're working on. i.e. first parent we find
//         myDiv.element(by.xpath('..')).$('.account_org.parent_org').getText().then(function(text) {
//             globalOrg = text;
//         });

//         browser.actions().mouseMove(myDiv.$('.sub_head.sub_org.right')).perform();
//         myDiv.$('.sub_head.sub_org.right').$('a').click(); 
//         $('[id="createOrganizationName"]').sendKeys('test sub org');
//         $('[id="createOrganizationInvite"]').sendKeys(browser.params.login.user);
//         $('.btn.btn-primary').click();
//         var myNewSub = element.all(by.repeater('sub_org in org.sub_orgs')).filter(function(sub) {
//             return sub.$('.account_org.left').getText().then(function(label) { 
//                 return label == 'test sub org';
//             });
//         });
        // // expect(myNewSub.count() > 0);
        // var rows = element.all(myNewSub).map(function (elm) {
        //     return elm;
        // });
        // expect(rows.length).not.toBeLessThan(1);
//         browser.actions().mouseMove(myNewSub.get(0).$('.account_org.right')).perform();
//         myNewSub.get(0).$('.account_org.right a').click();
//     });
//     it('should change the sub org name', function () {
//         $('input').clear().then(function() {
//             $('input').sendKeys('Another test sub name');
//         });
//         $('[ng-click="save_settings()"]').click();
//         expect($('.page_title').getText()).toEqual('Another test sub name');
//     });
//     it('should go back to orgranizations', function () {
//         $('[ui-sref="organizations"]').click();
//         expect($('.page_title').getText()).toEqual('Organizations');
//     });
// });
// describe('When I visit the the parent org', function () {
//     it('should go to parent organization', function () {
//         var myDiv = element.all(by.css('[ng-show="org.is_parent"]')).filter(function (elm) {
//             return elm.isDisplayed().then(function (isDisplayed) {
//                 return isDisplayed;
//             });
//         }).first().element(by.xpath('..')).$('.account_org.right');
//         browser.actions().mouseMove(myDiv).perform();
//         myDiv.$('a').click();
//         var myOptions = element.all(by.css('a')).filter(function (elm) {
//             return elm.getText().then(function(label) { 
//                 return label == 'Cycles';
//             });
//         }).first();
//         myOptions.click();
//         expect($('.table_list_container').isPresent()).toBe(true);
//     });
//     it('should create new cycle', function () {
//         $('[ng-model="new_cycle.name"]').sendKeys('protractor test cycle 2017');
//         $('[ng-model="new_cycle.start"]').sendKeys('01-01-2017');
//         $('[ng-model="new_cycle.end"]').sendKeys('12-31-2017');
//         $('#btnCreateCycle').click();
        
//         var myNewCycle = element.all(by.repeater('cycle in cycles')).filter(function(sub) {
//             return sub.element(by.tagName('td')).$('[ng-show="!rowform.$visible"]').getText().then(function(label) { 
//                 return label == 'protractor test cycle 2017';
//             });
//         }).first();
//         expect(myNewCycle.element(by.tagName('td')).$('[ng-show="!rowform.$visible"]').getText()).toEqual('protractor test cycle 2017');
//     });
//  //TODO add other settings from parent
// });

// // Select my new sub org
// describe('When I click the orgs button', function () {
//     it('should be able to switch to my org', function () {
//         browser.get("/app/#/data");
//         $('#btnUserOrgs').click();
//         var myOrg = element.all(by.repeater('org in menu.user.organizations')).filter(function(org) {
//             return org.$('a.ng-binding').getText().then(function(label) {
//                 return label == globalOrg;
//             });
//         }).first().$('a.ng-binding').click();
//         expect($('#btnUserOrgs').getText()).toEqual(globalOrg)
//     });
// });

// Data Set page
describe('When I visit the data set page', function () {
    it('should be able to create a new data set', function () {
        
        //temp
        browser.get("/app/#/data");
        browser.sleep(2000);

        $('[ui-sref="dataset_list"]').click();
        browser.sleep(500);
        $('input').sendKeys('my fake dataset');
        $('[ng-click="create_dataset(dataset.name)"]').click();
        // selectDropdownbyText(element, "protractor test cycle 2017");
        element(by.cssContainingText('option', 'protractor test cycle 2017')).click();
        // $('[buttontext="Upload a Spreadsheet"]').$('.qq-uploader').click();

        var path = require('path');
        // Select image
        var fileToUpload = '../../../../tests/data/portfolio-manager-sample.csv'
        var absolutePath = path.resolve(__dirname, fileToUpload);

        element(by.xpath('//input[@type="file"]')).sendKeys(absolutePath);
        var passingBar = $('.alert.alert-success');
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
        browser.wait(EC.presenceOf($('.inventory-list-tab-container.ng-scope')),120000);       
        expect($('[heading="View by Property"]').isPresent()).toBe(true);
        expect($('[heading="View by Tax Lot"]').isPresent()).toBe(true);
        var rows = element.all(by.repeater('(rowRenderIndex, row) in rowContainer.renderedRows')).map(function (elm) {
            return elm;
        });
        expect(rows.length).not.toBeLessThan(1);
    });

    it('should save mappings', function () {
        $('#save-mapping').click();
        browser.sleep(500);
        $('#confirm-mapping').click();
    });
});

 // Admin page last:
 describe('When I go to admin page', function () {
     it('should delete new test org', function () {
        // browser.get("/app/#/profile/admin");
     });
 });


// describe('And I have a project', function () {
//     it('should have a project', function () {
//         Project.objects.create(
//             name="my project",
//             super_organization_id=world.org.id,
//             owner=world.user
//         )
//     });
// });


// describe('And I have a dataset', function () {
//     it('should and_i_have_a_dataset', function () {
//         ImportRecord.objects.create(
//             name='dataset 1',
//             super_organization=world.org,
//             owner=world.user
//         )
//     });
// });


// describe('When I visit the dataset page', function () {
//     it('should when_i_visit_the_dataset_page', function () {
//         browser.get("/app" + "#/data");
//     });
// });


// describe('And I delete a dataset', function () {
//     it('should and_i_delete_a_dataset', function () {
//         delete_icon = browser.find_by_css('.delete_link')
//         delete_icon.click()
//         alert = browser.get_alert()
//         alert.accept()
//     });
// });


// describe('Then I should see no datasets', function () {
//     it('should then_i_should_see_no_datasets', function () {
//         number_of_datasets = len(browser.find_by_css('.import_row'))
//         number_of_datasets = len(browser.find_by_css('.import_row'))
//         number_of_datasets = len(browser.find_by_css('.import_row'))
//         assert number_of_datasets == 0
//     });
// });
