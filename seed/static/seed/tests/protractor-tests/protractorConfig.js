/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// config for protractor tests
exports.config = {
  specs: [
    // 'adminLogin.spec.js',
    'jasmineTests.spec.js',
    // 'adminCreateOrgs.spec.js',
    // 'orgPages.spec.js',
    // 'datasetPages.spec.js',
    // 'propPages.spec.js',
    // 'taxlotPages.spec.js',
    // 'datasetMapping.spec.js',
    // 'datasetMatching.spec.js',
    // 'datasetPairing.spec.js',
    // 'miscellaneous.spec.js',
    // 'adminLogout.spec.js'
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
