module.exports = {
  extends: 'airbnb-base',
  parserOptions: {
    ecmaVersion: 2022
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
    'consistent-return': 'warn',
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
    'no-plusplus': 'off',
    'no-restricted-syntax': [
      'error',
      'ForInStatement',
      'LabeledStatement',
      'WithStatement'
    ],
    'no-sequences': 'error',
    'no-shadow': 'warn',
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
    'default-case': 'off',
    'no-console': 'off',
    'no-param-reassign': 'off',
    'no-underscore-dangle': 'off',
    'prefer-destructuring': 'off'
  }
};
