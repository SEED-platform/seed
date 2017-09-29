/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// config for protractor tests
exports.config = {
  specs: [
    // 'seed/static/seed/tests/protractor-tests/adminLogin.spec.js',
    'seed/static/seed/tests/protractor-tests/jasmineTests.spec.js',
    // 'seed/static/seed/tests/protractor-tests/adminCreateOrgs.spec.js',
    // 'seed/static/seed/tests/protractor-tests/orgPages.spec.js',
    // 'seed/static/seed/tests/protractor-tests/datasetPages.spec.js',
    // 'seed/static/seed/tests/protractor-tests/propPages.spec.js',
    // 'seed/static/seed/tests/protractor-tests/taxlotPages.spec.js',
    // 'seed/static/seed/tests/protractor-tests/datasetMapping.spec.js',
    // 'seed/static/seed/tests/protractor-tests/datasetMatching.spec.js',
    // 'seed/static/seed/tests/protractor-tests/datasetPairing.spec.js',
    // 'seed/static/seed/tests/protractor-tests/miscellaneous.spec.js',
    // 'seed/static/seed/tests/protractor-tests/adminLogout.spec.js'
  ],
  baseUrl: 'http://localhost:8000/',
  rootElement: '.app',
  params: {
    login: {
      user: 'demo@example.com',
      password: 'demo123'
    },
    testOrg: {
      parent: 'Protractor test org',
      child: 'Protractor test sub org',
      childRename: 'Protractor sub rename',
      cycle: 'Protractor test cycle'
    }
  }
};
if (process.env.TRAVIS) {
  exports.config.capabilities = {
    browserName: 'chrome',
    'tunnel-identifier': process.env.TRAVIS_JOB_NUMBER,
    build: process.env.TRAVIS_BUILD_NUMBER
  };
}
