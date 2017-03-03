// check inventory pages after import and delete test dataset
var EC = protractor.ExpectedConditions;
// Check inventory Page:
describe('When I go to the taxlot page', function () {
	it('should change to our test cycle', function () {
		browser.ignoreSynchronization = false;
		browser.get("/app/#/taxlots");
	});
});


// Delete created dataset:
// describe('When I go to the dataset page', function () {
//     it('should delete dataset', function () {
//     // click dataset 
//     });
// });
