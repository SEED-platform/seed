import typography from '@tailwindcss/typography'
import colors from 'tailwindcss/colors'
import defaultTheme from 'tailwindcss/defaultTheme'
import { screens } from './src/@seed/services/config/config.screens'
import type { Palette, Themes } from './src/@seed/tailwind/plugins'
import { iconSize, theming, utilities } from './src/@seed/tailwind/plugins'

const palette: Palette = {
  50: '#eff5fe',
  100: '#e2ecfd',
  200: '#c4dafa',
  300: '#a1c6f8',
  400: '#74b0f5',
  500: '#2196f3',
  600: '#1e88dc',
  700: '#1a78c3',
  800: '#1766a6',
  900: '#005191',
  DEFAULT: '#005191',
}

const themes: Themes = {
  default: {
    primary: {
      ...palette,
    },
    accent: {
      ...colors.slate,
      DEFAULT: colors.slate[800],
    },
    warn: {
      ...colors.red,
      DEFAULT: colors.red[600],
    },
    'on-warn': {
      500: colors.red[50],
    },
  },
}

export default {
  darkMode: ['selector', '.dark'],
  content: ['./src/**/*.{html,scss,ts}'],
  important: true,
  theme: {
    fontSize: {
      xs: '0.625rem',
      sm: '0.75rem',
      md: '0.8125rem',
      base: '0.875rem',
      lg: '1rem',
      xl: '1.125rem',
      '2xl': '1.25rem',
      '3xl': '1.5rem',
      '4xl': '2rem',
      '5xl': '2.25rem',
      '6xl': '2.5rem',
      '7xl': '3rem',
      '8xl': '4rem',
      '9xl': '6rem',
      '10xl': '8rem',
    },
    screens,
    extend: {
      animation: {
        'spin-slow': 'spin 3s linear infinite',
      },
      colors: {
        gray: colors.slate,
      },
      flex: {
        0: '0 0 auto',
      },
      fontFamily: {
        sans: `"Inter Variable", ${defaultTheme.fontFamily.sans.join(',')}`,
        mono: `"Fira Code Variable", ${defaultTheme.fontFamily.mono.join(',')}`,
      },
      opacity: {
        12: '0.12',
        38: '0.38',
        87: '0.87',
      },
      rotate: {
        '-270': '270deg',
        15: '15deg',
        30: '30deg',
        60: '60deg',
        270: '270deg',
      },
      scale: {
        '-1': '-1',
      },
      zIndex: {
        '-1': -1,
        1: 1,
        2: 2,
        49: 49,
        60: 60,
        70: 70,
        80: 80,
        90: 90,
        99: 99,
        999: 999,
        9999: 9999,
        99999: 99999,
      },
      spacing: {
        13: '3.25rem',
        15: '3.75rem',
        18: '4.5rem',
        22: '5.5rem',
        26: '6.5rem',
        30: '7.5rem',
        50: '12.5rem',
        90: '22.5rem',

        // Bigger values
        100: '25rem',
        120: '30rem',
        128: '32rem',
        140: '35rem',
        160: '40rem',
        180: '45rem',
        192: '48rem',
        200: '50rem',
        240: '60rem',
        256: '64rem',
        280: '70rem',
        320: '80rem',
        360: '90rem',
        400: '100rem',
        480: '120rem',

        // Fractional values
        '1/2': '50%',
        '1/3': '33.333333%',
        '2/3': '66.666667%',
        '1/4': '25%',
        '2/4': '50%',
        '3/4': '75%',
      },
      minHeight: ({ theme }) => ({
        ...theme('spacing'),
      }),
      maxHeight: {
        none: 'none',
      },
      minWidth: ({ theme }) => ({
        ...theme('spacing'),
        screen: '100vw',
      }),
      maxWidth: ({ theme }) => ({
        ...theme('spacing'),
        screen: '100vw',
      }),
      transitionDuration: {
        400: '400ms',
      },
      transitionTimingFunction: {
        drawer: 'cubic-bezier(0.25, 0.8, 0.25, 1)',
      },

      // @tailwindcss/typography
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            color: 'var(--seed-text-default)',
            '[class~="lead"]': {
              color: 'var(--seed-text-secondary)',
            },
            a: {
              color: 'var(--seed-primary-500)',
              textDecoration: 'none', // remove underline by default
              '&:hover, &:focus': {
                textDecoration: 'underline', // add underline on hover and focus
              },
            },
            strong: {
              color: 'var(--seed-text-default)',
            },
            'ol > li::before': {
              color: 'var(--seed-text-secondary)',
            },
            'ul > li::before': {
              backgroundColor: 'var(--seed-text-hint)',
            },
            hr: {
              borderColor: 'var(--seed-border)',
            },
            blockquote: {
              color: 'var(--seed-text-default)',
              borderLeftColor: 'var(--seed-border)',
            },
            h1: {
              color: 'var(--seed-text-default)',
            },
            h2: {
              color: 'var(--seed-text-default)',
            },
            h3: {
              color: 'var(--seed-text-default)',
            },
            h4: {
              color: 'var(--seed-text-default)',
            },
            'figure figcaption': {
              color: 'var(--seed-text-secondary)',
            },
            code: {
              color: 'var(--seed-text-default)',
              fontWeight: '500',
            },
            'a code': {
              color: 'var(--seed-primary)',
            },
            pre: {
              color: theme('colors.white'),
              backgroundColor: theme('colors.gray.800'),
            },
            thead: {
              color: 'var(--seed-text-default)',
              borderBottomColor: 'var(--seed-border)',
            },
            'tbody tr': {
              borderBottomColor: 'var(--seed-border)',
            },
            'ol[type="A" s]': false,
            'ol[type="a" s]': false,
            'ol[type="I" s]': false,
            'ol[type="i" s]': false,
          },
        },
        sm: {
          css: {
            code: {
              fontSize: '1em',
            },
            pre: {
              fontSize: '1em',
            },
            table: {
              fontSize: '1em',
            },
          },
        },
      }),
    },
  },
  corePlugins: {
    appearance: false,
    clear: false,
    container: false,
    float: false,
    placeholderColor: false,
    placeholderOpacity: false,
    verticalAlign: false,
  },
  plugins: [
    utilities,
    iconSize,
    theming({ themes }),
    typography,
  ],
}
