import type { IsActiveMatchOptions } from '@angular/router'

// Get the equivalent "IsActiveMatchOptions" options for "exact = false".
export const subsetMatchOptions: IsActiveMatchOptions = {
  paths: 'subset',
  fragment: 'ignored',
  matrixParams: 'ignored',
  queryParams: 'subset',
} as const
