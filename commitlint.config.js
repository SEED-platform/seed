module.exports = {
  'extends': ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'docs',
        'feat',
        'fix',
        'refactor',
        'style',
        'test',
        'build',
      ]
    ]
  }
};
