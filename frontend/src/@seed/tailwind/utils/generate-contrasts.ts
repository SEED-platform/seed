import chroma from 'chroma-js'
import type { Palette } from '../plugins'

/**
 * Generates contrasting counterparts of the given palette.
 * The provided palette must be in the same format with
 * default Tailwind color palettes.
 */
export const generateContrasts = (palette: Palette) => {
  const lightColor = '#fff'
  let darkColor = '#fff'

  // Iterate through the palette to find the darkest color
  for (const color of Object.values(palette)) {
    darkColor = chroma.contrast(color, '#fff') > chroma.contrast(darkColor, '#fff') ? color : darkColor
  }

  // Generate the contrasting colors
  return Object.fromEntries(
    Object.entries(palette).map(([hue, color]) => [
      hue,
      chroma.contrast(color, darkColor) > chroma.contrast(color, lightColor) ? darkColor : lightColor,
    ]),
  )
}
