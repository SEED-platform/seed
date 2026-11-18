// @ts-check
import cspellESLintPluginRecommended from '@cspell/eslint-plugin/recommended'
import eslint from '@eslint/js'
import stylistic from '@stylistic/eslint-plugin'
import angular from 'angular-eslint'
import github from 'eslint-plugin-github'
import importPlugin from 'eslint-plugin-import'
// import perfectionist from 'eslint-plugin-perfectionist'
import unusedImports from 'eslint-plugin-unused-imports'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  cspellESLintPluginRecommended,
  {
    files: ['**/*.ts', '**/*.mts'],
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.strictTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
      ...angular.configs.tsRecommended,
      importPlugin.flatConfigs.recommended,
      importPlugin.flatConfigs.typescript,
      stylistic.configs.customize({
        arrowParens: true,
        braceStyle: '1tbs',
        commaDangle: 'always-multiline',
        indent: 2,
        jsx: false,
        quoteProps: 'as-needed',
        semi: false,
      }),
    ],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      github,
      'unused-imports': unusedImports,
    },
    settings: {
      'import/resolver': {
        typescript: true,
        node: true,
      },
    },
    processor: angular.processInlineTemplates,
    rules: {
      '@angular-eslint/component-selector': ['error', {
        type: 'element',
        prefix: ['seed', 'auth', 'layout'],
        style: 'kebab-case',
      }],
      // Existing Eager components retain pre-v22 change detection behavior.
      '@angular-eslint/prefer-on-push-component-change-detection': 'off',
      '@stylistic/lines-between-class-members': 'off',
      '@stylistic/member-delimiter-style': ['error', {
        multiline: {
          delimiter: 'semi',
          requireLast: true,
        },
        singleline: {
          delimiter: 'semi',
          requireLast: false,
        },
        multilineDetection: 'brackets',
      }],
      '@stylistic/quotes': ['error', 'single', {
        avoidEscape: true,
      }],
      '@stylistic/type-annotation-spacing': 'error',
      '@typescript-eslint/consistent-type-definitions': ['error', 'type'],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/member-ordering': ['error', {
        default: [
          'signature',
          'field',
          'constructor',
          'accessor',
          'static-method',
          'decorated-method',
          'public-method',
          'private-method',
          'method'
        ]
      }],
      '@typescript-eslint/naming-convention': ['error', {
        selector: 'variableLike',
        modifiers: ['unused'],
        format: ['camelCase'],
        leadingUnderscore: 'require'
      }, {
        selector: 'memberLike',
        modifiers: ['private'],
        format: ['camelCase'],
        leadingUnderscore: 'require'
      }],
      '@typescript-eslint/no-extraneous-class': 'off',
      '@typescript-eslint/no-for-in-array': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/no-unused-vars': 'off',
      // Enable later
      '@typescript-eslint/no-useless-default-assignment': 'off',
      '@typescript-eslint/no-use-before-define': 'error',
      '@typescript-eslint/prefer-for-of': 'error',
      '@typescript-eslint/restrict-template-expressions': ['error', {
        allowNumber: true,
      }],
      'github/array-foreach': 'error',
      'import/no-deprecated': 'error',
      'import/no-empty-named-blocks': 'error',
      'import/no-extraneous-dependencies': 'error',
      'import/no-mutable-exports': 'error',
      'import/no-unused-modules': 'error',
      'import/no-useless-path-segments': ['error', {
        noUselessIndex: true,
      }],
      'import/order': ['error', {
        alphabetize: {
          order: 'asc',
          orderImportKind: 'asc',
          caseInsensitive: true,
        },
        groups: [
          'builtin',
          'external',
          'internal',
          'parent',
          'sibling',
          'index',
          'object',
        ],
        'newlines-between': 'never',
      }],
      'no-sequences': ['error', {
        allowInParentheses: false,
      }],
      'object-shorthand': 'error',
      'prefer-template': 'error',
      'semi-style': ['error', 'first'],
      'sort-imports': ['error', {
        ignoreCase: true,
        ignoreDeclarationSort: true,
      }],
      'unused-imports/no-unused-imports': 'error',
      // TODO enable (or remove) after enable strict
      '@typescript-eslint/no-unnecessary-boolean-literal-compare': 'off',
      '@typescript-eslint/no-unnecessary-condition': 'off',
      '@typescript-eslint/prefer-nullish-coalescing': 'off',
      // TODO
      '@typescript-eslint/unbound-method': 'off',
      'camelcase': 'off',
      'import/no-cycle': 'off',
    },
  },
  {
    files: ['**/*.d.ts'],
    rules: {
      '@typescript-eslint/consistent-type-definitions': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    // Angular 20.2+ marks the entire legacy trigger-based animation DSL as deprecated.
    // Keep the deprecation rule active project-wide, but don't block lint on the files
    // that intentionally encapsulate the existing animation layer until a full
    // animate.enter/animate.leave migration is scheduled.
    files: [
      'src/@seed/animations/**/*.ts',
      'src/@seed/components/drawer/drawer.component.ts',
      'src/@seed/components/navigation/vertical/vertical.component.ts',
      'src/app/app.config.ts',
    ],
    rules: {
      '@typescript-eslint/no-deprecated': 'off',
    },
  },
  {
    // chroma-js exposes `contrast` at runtime, but its published typings still model the
    // API around the default export. Keep the readable call site and suppress only this
    // false-positive import rule for the helper.
    files: ['src/@seed/tailwind/utils/generate-contrasts.ts'],
    rules: {
      'import/no-named-as-default-member': 'off',
    },
  },
  {
    files: ['**/*.html'],
    extends: [
      ...angular.configs.templateRecommended,
      ...angular.configs.templateAccessibility,
    ],
    rules: {
      '@angular-eslint/template/prefer-control-flow': 'error',
      // TODO
      '@angular-eslint/template/click-events-have-key-events': 'off',
      '@angular-eslint/template/interactive-supports-focus': 'off',
    },
  },
)
