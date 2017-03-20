// create test orgs 
var EC = protractor.ExpectedConditions;
// Admin page:
describe('When I go to admin page', function () {
     it('should create new test org', function () {
        browser.ignoreSynchronization = false;
        browser.get("/app/#/profile/admin");
        $('#org_name').sendKeys(browser.params.testOrg.parent);
        $$('#user_emails').first().element(by.cssContainingText('option', browser.params.login.user)).click();
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

