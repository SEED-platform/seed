//admin delete test orgs

var EC = protractor.ExpectedConditions;


// Admin page last:
describe('When I go to admin page', function () {
    it('should delete new test org inventory', function () {
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

        browser.wait(EC.alertIsPresent(), 2000, "Remove inventory Alert is not present");
        browser.switchTo().alert().accept();
        browser.sleep(1000);
        // expect(myNewOrg.$('[ng-click="confirm_inventory_delete(org)"]').isDisabled()).toBe(true);
    });

    it('should delete new test sub org', function () {
        browser.ignoreSynchronization = false;
        // browser.get("/app/#/profile/admin");
        var myNewSubOrg = element.all(by.repeater('org in org_user.organizations')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.getText().then(function (label) {
                return label.includes(browser.params.testOrg.childRename);
            });
        }).first();
        expect(myNewSubOrg.isPresent()).toBe(true);

        browser.wait(EC.presenceOf(myNewSubOrg.$('[ng-click="confirm_inventory_delete(org)"]')), 120000);
        myNewSubOrg.$('[ng-click="confirm_org_delete(org)"]').click();
        browser.wait(EC.alertIsPresent(), 2000, "Remove org Alert is not present");
        browser.switchTo().alert().accept();

        // accept again
        browser.wait(EC.alertIsPresent(), 2000, "Second remove org Alert is not present");
        browser.switchTo().alert().accept();

        browser.wait(EC.not(EC.presenceOf(myNewSubOrg.$('.progress-bar.progress-bar-danger'))), 15000);
        expect(myNewSubOrg.isPresent()).toBe(false);
    }, 30000);

    it('should delete new test org', function () {
        browser.ignoreSynchronization = false;
        // browser.get("/app/#/profile/admin");
        var myNewOrg = element.all(by.repeater('org in org_user.organizations')).filter(function (rows) {
            expect(rows.length).not.toBeLessThan(1);
            return rows.getText().then(function (label) {
                return label.includes(browser.params.testOrg.parent);
            });
        }).first();
        expect(myNewOrg.isPresent()).toBe(true);

        browser.wait(EC.presenceOf(myNewOrg.$('[ng-click="confirm_inventory_delete(org)"]')), 120000);
        myNewOrg.$('[ng-click="confirm_org_delete(org)"]').click();
        browser.wait(EC.alertIsPresent(), 2000, "Remove org Alert is not present");
        browser.switchTo().alert().accept();

        // accept again
        browser.wait(EC.alertIsPresent(), 2000, "Second remove org Alert is not present");
        browser.switchTo().alert().accept();

        browser.wait(EC.not(EC.presenceOf(myNewOrg.$('.progress-bar.progress-bar-danger'))), 15000);
        expect(myNewOrg.isPresent()).toBe(false);
    }, 30000);
});
