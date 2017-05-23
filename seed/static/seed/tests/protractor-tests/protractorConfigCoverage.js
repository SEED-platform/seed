// config for protractor tests
exports.config = {
	// framework: 'jasmine2',
	// seleniumAddress: 'http://localhost:4444/wd/hub',
	specs: [
		'seed/static/seed/tests/protractor-tests/adminLogin.spec.js',
		'seed/static/seed/tests/protractor-tests/jasmineTests.spec.js',
		'seed/static/seed/tests/protractor-tests/adminCreateOrgs.spec.js',
		'seed/static/seed/tests/protractor-tests/orgPages.spec.js',
		'seed/static/seed/tests/protractor-tests/datasetPages.spec.js',
		'seed/static/seed/tests/protractor-tests/propPages.spec.js',
		'seed/static/seed/tests/protractor-tests/taxlotPages.spec.js',
		'seed/static/seed/tests/protractor-tests/datasetMatchingPages.spec.js',
		'seed/static/seed/tests/protractor-tests/adminLogout.spec.js',
	],
	baseUrl: 'http://localhost:8000/',
	rootElement: '.app',
	// capabilities: {
	// 	'browserName': 'firefox'
	// },
	params: {
		login: {
			user: 'demo@example.com',
			password: 'demo123'
		},
		testOrg: {
			parent: "Protractor test org",
			child: "Protractor test sub org",
			childRename: "Protractor sub rename",
			cycle: "Protractor test cycle"
		}
	}
}
if (process.env.TRAVIS) {
	exports.config.sauceUser = process.env.SAUCE_USERNAME;
	exports.config.sauceKey = process.env.SAUCE_ACCESS_KEY;
	exports.config.capabilities = {
		'browserName': 'chrome',
		'tunnel-identifier': process.env.TRAVIS_JOB_NUMBER,
		'build': process.env.TRAVIS_BUILD_NUMBER
	};
}
