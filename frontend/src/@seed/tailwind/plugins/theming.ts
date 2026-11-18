import fs from 'node:fs'
import path from 'node:path'
import chroma from 'chroma-js'
import { defaults, flatten, get, isEmpty, keys, map, omitBy, pick } from 'lodash-es'
import colors from 'tailwindcss/colors'
import flattenColorPalette from 'tailwindcss/lib/util/flattenColorPalette'
import plugin from 'tailwindcss/plugin'
import { generateContrasts } from '../utils/generate-contrasts'
import { generateSCSS } from '../utils/generate-scss'
import type { Theme, Themes } from './theming.types'

/**
 * Normalizes the provided theme by omitting empty values and values that
 * start with "on" from each palette. Also sets the correct DEFAULT value
 * of each palette.
 */
const normalizeTheme = (theme: Theme) => {
  return Object.fromEntries(
    map(
      omitBy(theme, (palette, paletteName) => paletteName.startsWith('on') || isEmpty(palette)),
      (palette, paletteName) => [
        paletteName,
        {
          ...palette,
          DEFAULT: palette.DEFAULT || palette[500],
        },
      ],
    ),
  )
}

// Emit space-separated channels so downstream CSS can use modern
// `rgb(var(--seed-*-rgb) / alpha)` syntax consistently.
const toRgbChannels = (color: string) => chroma(color).rgb().join(' ')

const withSeedRgbAlpha = (token: string, alpha = '<alpha-value>') => `rgb(var(--seed-${token}-rgb) / ${alpha})`

// -----------------------------------------------------------------------------------------------------
// @ SEED TailwindCSS Main Plugin
// -----------------------------------------------------------------------------------------------------
export const theming = plugin.withOptions(
  (options: { themes: Themes }) =>
    ({ addComponents, e, theme }) => {
      /**
       * Create user themes object by going through the provided themes and
       * merging them with the provided "default" so, we can have a complete
       * set of color palettes for each user theme.
       */
      const userThemes = Object.fromEntries(
        map(options.themes, (theme, themeName) => [themeName, defaults({}, theme, options.themes.default)]),
      )

      /**
       * Normalize the themes and assign it to the themes object. This will
       * be the final object that we create a SASS map from
       */
      let themes = Object.fromEntries(map(userThemes, (theme, themeName) => [themeName, normalizeTheme(theme)]))

      /**
       * Go through the themes to generate the contrasts and filter the
       * palettes to only have "primary", "accent" and "warn" objects.
       */
      themes = Object.fromEntries(
        map(themes, (theme, themeName) => [
          themeName,
          pick(
            Object.fromEntries(
              map(theme, (palette, paletteName) => [
                paletteName,
                {
                  ...palette,
                  contrast: Object.fromEntries(
                    map(generateContrasts(palette), (color, hue) => [hue, get(userThemes[themeName], [`on-${paletteName}`, hue]) || color]),
                  ),
                },
              ]),
            ),
            ['primary', 'accent', 'warn'],
          ),
        ]),
      )

      // Generate the SASS map by attaching the appropriate class selectors to encapsulate each theme
      const sassMap = generateSCSS({
        // @ts-expect-error: TODO fix types
        'user-themes': Object.fromEntries(
          map(themes, (theme, themeName) => [
            themeName,
            {
              selector: `'.theme-${themeName}'`,
              ...theme,
            },
          ]),
        ),
      })

      /* Get the file path */
      const filename = path.resolve(__dirname, '../../styles/user-themes.scss')

      let previousSassMap: string
      try {
        previousSassMap = fs.readFileSync(filename, { encoding: 'utf8' })
      } catch (err) {
        console.error(err)
      }

      /* Write the file if the map has changed */
      if (sassMap !== previousSassMap) {
        try {
          fs.writeFileSync(filename, sassMap, { encoding: 'utf8' })
        } catch (err) {
          console.error(err)
        }
      }

      /**
       * Iterate through the user's themes and build Tailwind components containing
       * CSS Custom Properties using the colors from them. This allows switching
       * themes by simply replacing a class name as well as nesting them.
       */
      addComponents(
        Object.fromEntries(
          map(options.themes, (theme, themeName) => [
            themeName === 'default' ? 'body, .theme-default' : `.theme-${e(themeName)}`,
            Object.fromEntries(
              flatten(
                // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
                map(
                  // eslint-disable-next-line @typescript-eslint/no-unsafe-call
                  flattenColorPalette(
                    Object.fromEntries(
                      flatten(
                        map(normalizeTheme(theme), (palette, paletteName) => [
                          [e(paletteName), palette],
                          [
                            `on-${e(paletteName)}`,
                            Object.fromEntries(
                              map(generateContrasts(palette), (color, hue) => [hue, get(theme, [`on-${paletteName}`, hue]) || color]),
                            ),
                          ],
                        ]),
                      ),
                    ),
                  ),
                  (color: string, key: string) => [
                    [`--seed-${e(key)}`, color],
                    [`--seed-${e(key)}-rgb`, toRgbChannels(color)],
                  ],
                ),
              ),
            ),
          ]),
        ),
      )

      /**
       * Generate scheme based css custom properties and utility classes
       */
      const schemeCustomProps = map(['light', 'dark'], (colorScheme) => {
        const isDark = colorScheme === 'dark'
        const background = theme(`seed.customProps.background.${colorScheme}`)
        const foreground = theme(`seed.customProps.foreground.${colorScheme}`)
        const lightSchemeSelectors = 'body.light, .light, .dark .light'
        const darkSchemeSelectors = 'body.dark, .dark, .light .dark'

        return {
          [isDark ? darkSchemeSelectors : lightSchemeSelectors]: {
            /**
             * If a custom property is not available, browsers will use
             * the fallback value. In this case, we want to use '--is-dark'
             * as the indicator of a dark theme so, we can use it like this:
             * background-color: var(--is-dark, red);
             *
             * If we set '--is-dark' as "true" on dark themes, the above rule
             * won't work because of the said "fallback value" logic. Therefore,
             * we set the '--is-dark' to "false" on light themes and not set it
             * at all on dark themes so that the fallback value can be used on
             * dark themes.
             *
             * On light themes, since '--is-dark' exists, the above rule will be
             * interpolated as:
             * "background-color: false"
             *
             * On dark themes, since '--is-dark' doesn't exist, the fallback value
             * will be used ('red' in this case) and the rule will be interpolated as:
             * "background-color: red"
             *
             * It's easier to understand and remember like this.
             */
            ...(!isDark ? { '--is-dark': 'false' } : {}),

            /* Generate custom properties from customProps */
            ...Object.fromEntries(
              flatten(
                map(background, (color: string, key) => [
                  [`--seed-${e(key)}`, color],
                  [`--seed-${e(key)}-rgb`, toRgbChannels(color)],
                ]),
              ),
            ),
            ...Object.fromEntries(
              flatten(
                map(foreground, (color: string, key) => [
                  [`--seed-${e(key)}`, color],
                  [`--seed-${e(key)}-rgb`, toRgbChannels(color)],
                ]),
              ),
            ),
          },
        }
      })

      addComponents(schemeCustomProps)
    },
  (options) => {
    return {
      theme: {
        extend: {
          /**
           * Add 'Primary', 'Accent' and 'Warn' palettes as colors so all color utilities
           * are generated for them; "bg-primary", "text-on-primary", "bg-accent-600" etc.
           * This will also allow using arbitrary values with them such as opacity and such.
           */
          colors: Object.fromEntries(
            flatten(
              // eslint-disable-next-line @typescript-eslint/no-unsafe-call
              map(keys(flattenColorPalette(normalizeTheme(options.themes.default))), (name) => [
                [name, withSeedRgbAlpha(name)],
                [`on-${name}`, withSeedRgbAlpha(`on-${name}`)],
              ]),
            ),
          ),
        },
        seed: {
          customProps: {
            background: {
              light: {
                'bg-app-bar': '#fff',
                'bg-card': '#fff',
                'bg-default': colors.slate[100],
                'bg-dialog': '#fff',
                'bg-hover': chroma(colors.slate[400]).alpha(0.12).css(),
                'bg-status-bar': colors.slate[300],
              },
              dark: {
                'bg-app-bar': colors.slate[900],
                'bg-card': colors.slate[800],
                'bg-default': colors.slate[900],
                'bg-dialog': colors.slate[800],
                'bg-hover': 'rgb(255 255 255 / 5%)',
                'bg-status-bar': colors.slate[900],
              },
            },
            foreground: {
              light: {
                'text-default': colors.slate[800],
                'text-secondary': colors.slate[500],
                'text-hint': colors.slate[400],
                'text-disabled': colors.slate[400],
                border: colors.slate[200],
                divider: colors.slate[200],
                icon: colors.slate[500],
                'mat-icon': colors.slate[500],
              },
              dark: {
                'text-default': '#fff',
                'text-secondary': colors.slate[400],
                'text-hint': colors.slate[500],
                'text-disabled': colors.slate[600],
                border: chroma(colors.slate[100]).alpha(0.12).css(),
                divider: chroma(colors.slate[100]).alpha(0.12).css(),
                icon: colors.slate[400],
                'mat-icon': colors.slate[400],
              },
            },
          },
        },
      },
    }
  },
)
