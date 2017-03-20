//Login

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

