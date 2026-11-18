import plugin from 'tailwindcss/plugin'

const withSeedRgbAlpha = (token: string, alpha: string) => `rgb(var(--seed-${token}-rgb) / ${alpha})`

export const utilities = plugin(({ addComponents }) => {
  /*
   * Add base components. These are very important for everything to look
   * correct. We are adding these to the 'components' layer because they must
   * be defined before pretty much everything else.
   */
  addComponents({
    '.mat-icon': {
      '--tw-text-opacity': '1',
      color: withSeedRgbAlpha('mat-icon', 'var(--tw-text-opacity)'),
    },
    '.text-default': {
      '--tw-text-opacity': '1 !important',
      color: `${withSeedRgbAlpha('text-default', 'var(--tw-text-opacity)')} !important`,
    },
    '.text-secondary': {
      '--tw-text-opacity': '1 !important',
      color: `${withSeedRgbAlpha('text-secondary', 'var(--tw-text-opacity)')} !important`,
    },
    '.text-hint': {
      '--tw-text-opacity': '1 !important',
      color: `${withSeedRgbAlpha('text-hint', 'var(--tw-text-opacity)')} !important`,
    },
    '.text-disabled': {
      '--tw-text-opacity': '1 !important',
      color: `${withSeedRgbAlpha('text-disabled', 'var(--tw-text-opacity)')} !important`,
    },
    '.divider': {
      color: 'var(--seed-divider) !important',
    },
    '.bg-card': {
      '--tw-bg-opacity': '1 !important',
      backgroundColor: `${withSeedRgbAlpha('bg-card', 'var(--tw-bg-opacity)')} !important`,
    },
    '.bg-default': {
      '--tw-bg-opacity': '1 !important',
      backgroundColor: `${withSeedRgbAlpha('bg-default', 'var(--tw-bg-opacity)')} !important`,
    },
    '.bg-dialog': {
      '--tw-bg-opacity': '1 !important',
      backgroundColor: `${withSeedRgbAlpha('bg-dialog', 'var(--tw-bg-opacity)')} !important`,
    },
    '.ring-bg-default': {
      '--tw-ring-opacity': '1 !important',
      '--tw-ring-color': `${withSeedRgbAlpha('bg-default', 'var(--tw-ring-opacity)')} !important`,
    },
    '.ring-bg-card': {
      '--tw-ring-opacity': '1 !important',
      '--tw-ring-color': `${withSeedRgbAlpha('bg-card', 'var(--tw-ring-opacity)')} !important`,
    },
  })

  addComponents({
    '.bg-hover': {
      backgroundColor: 'var(--seed-bg-hover) !important',
    },
  })
})
