//main e2e Protractor test

describe('I visit the login page', function () {
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



// describe('I should see that the tests passed', function () {
//     it('should run jasmine unit tests and pass', function () {
//         browser.get("/app/angular_js_tests");
//         time.sleep(2)
//         try:
//             assert browser.is_element_present_by_css(".passingAlert.bar")
//         except:
//             time.sleep(50)
//             assert len(browser.find_by_css(".passingAlert.bar")) > 0
//     });
// });


describe('When I visit the accounts page', function () {
    it('should see my organizations', function () {
        browser.get("/app/#/accounts");

        var EC = protractor.ExpectedConditions;
        var orgsAreThere = $('.section_content_container').$('.section_content').$('.table_list_container');

        browser.wait(EC.presenceOf(orgsAreThere), 5000);
        expect($('.section_content_container').$('.section_content').$('.table_list_container').isPresent()).toBe(true);
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
