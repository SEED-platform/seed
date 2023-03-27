/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */

// config for protractor tests
exports.config = {
  specs: [
    '**/jasmineTests.spec.js'
  ],
  baseUrl: 'http://localhost:80/',
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
  },
  capabilities: {
    browserName: 'chrome'
  }
};
