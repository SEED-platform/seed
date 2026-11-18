import plugin from 'tailwindcss/plugin'

export const iconSize = plugin(
  ({ matchUtilities, theme }) => {
    matchUtilities(
      {
        'icon-size': (size: string) => ({
          width: size,
          height: size,
          minWidth: size,
          minHeight: size,
          fontSize: size,
          lineHeight: size,
          ['svg']: {
            width: size,
            height: size,
          },
        }),
      },
      {
        values: theme('iconSize'),
      },
    )
  },
  {
    theme: {
      iconSize: {
        3: '0.75rem',
        3.5: '0.875rem',
        4: '1rem',
        4.5: '1.125rem',
        5: '1.25rem',
        6: '1.5rem',
        7: '1.75rem',
        8: '2rem',
        10: '2.5rem',
        12: '3rem',
        14: '3.5rem',
        16: '4rem',
        18: '4.5rem',
        20: '5rem',
        22: '5.5rem',
        24: '6rem',
      },
    },
  },
)
