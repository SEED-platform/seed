module.exports = {
  env: {
    jasmine: true
  },
  globals: {
    module: true
  },
  rules: {
    'import/no-extraneous-dependencies': 'off',
    'no-global-assign': ['error', {
      exceptions: ['confirm']
    }]
  }
};
