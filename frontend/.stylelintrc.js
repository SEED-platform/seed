module.exports = {
  extends: 'stylelint-config-standard-scss',
  rules: {
    // Fix later
    'no-descending-specificity': null,
    // Theme RGB tokens are emitted as space-separated channels so we can use
    // the modern `rgb(var(--seed-*-rgb) / alpha)` form consistently.
    'color-function-alias-notation': 'without-alpha',
    // Kebab-case, plus Tailwind CSS theme namespace resets such as `--text-*: initial`
    'custom-property-pattern': [
      '^([a-z][a-z0-9]*)(-[a-z0-9]+)*(-\\*)?$',
      {
        message: 'Expected custom property name to be kebab-case'
      }
    ],
    'declaration-property-value-disallowed-list': {
      '/.*/': [
        /rgba\(var\(--seed-[^)]+-rgb\),/,
        /rgb\(var\(--seed-[^)]+-rgb\),/,
      ]
    },
    'scss/at-rule-no-unknown': [
      true,
      {
        // Tailwind CSS directives
        ignoreAtRules: ['custom-variant', 'plugin', 'reference', 'source', 'theme', 'utility', 'variant']
      }
    ],
    'scss/dollar-variable-pattern': [
      '^([a-z][a-z0-9]*)(-[a-z0-9]+)*|([a-z][a-z0-9]*)(_[a-z0-9]+)*$',
      {
        message: 'Expected variable to be kebab-case or snake_case'
      }
    ],
    'scss/no-global-function-names': null,
    'selector-class-pattern': [
      '^([a-z][a-z0-9]*)(-[a-z0-9]+)*|([a-z][a-z0-9]*)(_[a-z0-9]+)*$',
      {
        message: 'Expected class selector to be kebab-case or snake_case'
      }
    ],
    'selector-id-pattern': [
      '^([a-z][a-z0-9]*)(-[a-z0-9]+)*|([a-z][a-z0-9]*)(_[a-z0-9]+)*$',
      {
        message: 'Expected id selector to be kebab-case or snake_case'
      }
    ],
    'value-keyword-case': [
      'lower',
      {
        camelCaseSvgKeywords: true,
        // Font family names in Tailwind CSS theme variables (src/styles/tailwind.css)
        ignoreProperties: [/^--font-/]
      }]
  }
};
