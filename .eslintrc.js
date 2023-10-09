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
    'no-plusplus': 'off',
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
    'no-console': 'off',
    'no-param-reassign': 'off'
  }
  //  "rules": {
  //    "angular/log": "off",
  //    "angular/no-service-method": "off",
  //    "array-bracket-spacing": "warn",
  //    "block-scoped-var": "warn",
  //    "brace-style": "warn",
  /// /    "camelcase": "warn",
  //    "comma-dangle": ["error", "never"],
  //    "comma-spacing": "warn",
  //    "dot-notation": "warn",
  //    "eol-last": "error",
  //    "indent": ["error", 2, {"SwitchCase": 1}],
  //    "key-spacing": "warn",
  //    "no-console": "warn",
  //    "no-mixed-spaces-and-tabs": "warn",
  //    "no-multi-spaces": "warn",
  //    "no-trailing-spaces": "warn",
  //    "no-unused-vars": "warn",
  //    "quote-props": ["error", "as-needed", {"keywords": true}],
  //    "quotes": ["warn", "single", {"avoidEscape": true}],
  //    "semi": ["error", "always"],
  //    "space-before-blocks": "warn",
  //    "space-before-function-paren": "warn",
  //    "space-infix-ops": "warn"
  //  }
};
