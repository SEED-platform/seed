import type { IsActiveMatchOptions } from '@angular/router'

// Get the equivalent "IsActiveMatchOptions" options for "exact = true".
export const exactMatchOptions: IsActiveMatchOptions = {
  paths: 'exact',
  fragment: 'ignored',
  matrixParams: 'ignored',
  queryParams: 'exact',
} as const
