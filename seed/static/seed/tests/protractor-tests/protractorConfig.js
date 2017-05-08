// config for protractor tests
exports.config = {
	// framework: 'jasmine2',
	// seleniumAddress: 'http://localhost:4444/wd/hub',
	specs: [
		'adminLogin.spec.js',
		'jasmineTests.spec.js',
		'adminCreateOrgs.spec.js',
		'orgPages.spec.js',
		'datasetPages.spec.js',
		'propPages.spec.js',
		'taxlotPages.spec.js',
		'datasetMatchingPages.spec.js',
		'adminLogout.spec.js',
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
	// exports.config.sauceUser = process.env.SAUCE_USERNAME;
	// exports.config.sauceKey = process.env.SAUCE_ACCESS_KEY;
	exports.config.capabilities = {
		'browserName': 'chrome',
		'tunnel-identifier': process.env.TRAVIS_JOB_NUMBER,
		'build': process.env.TRAVIS_BUILD_NUMBER
	};
}
