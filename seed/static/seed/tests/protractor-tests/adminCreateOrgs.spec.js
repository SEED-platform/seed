// create test orgs 
var EC = protractor.ExpectedConditions;
// Admin page:
describe('When I go to admin page', function () {

    // manually
    it ('should reset sync', function () {
        browser.ignoreSynchronization = true;
    });


     it('should test admin pages', function () {
        browser.get("/app/#/api/swagger");
        browser.sleep(5000);
        expect(browser.getTitle()).toContain('SEED Platform');
        browser.get("/app/#/contact");
        browser.sleep(5000);
        expect(browser.getTitle()).toContain('SEED Platform');
        browser.get("/app/#/profile/security");
        browser.sleep(5000);
        expect(browser.getTitle()).toContain('SEED Platform');
        browser.get("/app/#/profile/developer");
        browser.sleep(5000);
        expect(browser.getTitle()).toContain('SEED Platform');
    });


    // manually
    it ('should reset sync', function () {
        browser.ignoreSynchronization = false;
    });

        
     it('should test adding profile name', function () {
        browser.get("/app/#/profile");
        $('#first-name-text').clear().then(function(){
            $('#first-name-text').sendKeys("ME");                  
        });
        $('#last-name-text').clear().then(function(){
            $('#last-name-text').sendKeys("NotYou");                  
        });
        $('#update_profile').click();
        browser.wait(EC.presenceOf($('.fa-check')),10000);
        $('#first-name-text').clear().then(function(){
            $('#first-name-text').sendKeys("ME");                  
        });
        $('[ng-click="reset_form()"]').click();
    });


     it('should create new test org', function () {
        browser.get("/app/#/profile/admin");
        // browser.sleep(5000);
        $('#org_name').sendKeys(browser.params.testOrg.parent);
        $$('#user_emails').first().element(by.cssContainingText('option', browser.params.login.user)).click();
        $('[ng-click="org_form.add(org)"]').click();

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
        $$('#user_email').first().sendKeys('testy@test.com');
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
