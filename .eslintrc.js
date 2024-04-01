module.exports = {
  extends: 'airbnb-base',
  parserOptions: {
    ecmaVersion: 2024
  },
  env: {
    browser: true,
    es6: true,
    jasmine: true,
    jquery: true
  },
  globals: {
    _: true,
    $filter: true,
    $route: true,
    angular: true,
    angularDragula: true,
    BE: true,
    Chart: true,
    dimple: true,
    inject: true,
    module: true,
    moment: true,
    ol: true,
    pluralize: true,
    protractor: true,
    qq: true,
    saveAs: true,
    Spinner: true,
    Terraformer: true,
    UniqueBuildingIdentification: true
  },
  plugins: [
    'angular',
    'prefer-arrow',
    'protractor'
  ],
  rules: {
    'arrow-parens': [
      'error',
      'always'
    ],
    'comma-dangle': [
      'error',
      'never'
    ],
    'func-style': [
      'error',
      'declaration',
      {
        allowArrowFunctions: true
      }
    ],
    'linebreak-style': 'off',
    'max-len': [
      'warn',
      200,
      2,
      {
        ignoreUrls: true,
        ignoreComments: true,
        ignoreRegExpLiterals: true,
        ignoreStrings: true,
        ignoreTemplateLiterals: true
      }
    ],
    'no-continue': 'off',
    'no-plusplus': 'off',
    'no-restricted-globals': ['error', {
      name: 'isFinite',
      message: 'Use Number.isFinite instead'
    }, {
      name: 'isNaN',
      message: 'Use Number.isNaN instead'
    }],
    'no-restricted-syntax': [
      'error',
      // 'ForInStatement',
      'LabeledStatement',
      'WithStatement'
    ],
    'no-sequences': 'error',
    'object-shorthand': [
      'error',
      'properties'
    ],
    'operator-linebreak': [
      'error',
      'after'
    ],
    'prefer-arrow/prefer-arrow-functions': [
      'error',
      {
        disallowPrototype: true,
        singleReturnOnly: true,
        classPropertiesAllowed: false
      }
    ],
    // FIX LATER
    camelcase: 'off',
    'consistent-return': 'off',
    'default-case': 'off',
    'guard-for-in': 'off',
    'no-alert': 'off',
    'no-console': 'off',
    'no-param-reassign': 'off',
    'no-shadow': 'off',
    'no-underscore-dangle': 'off',
    'no-use-before-define': 'off',
    'prefer-destructuring': 'off'
  },
  overrides: [{
    files: [
      'seed/static/seed/js/controllers/data_quality_modal_controller.js',
      'seed/static/seed/js/directives/sdScrollSync.js',
      'seed/static/seed/js/services/search_service.js'
    ],
    rules: {
      'func-names': 'off'
    }
  }]
};
