import type { EnvironmentProviders, Provider } from '@angular/core'
import { inject, provideEnvironmentInitializer } from '@angular/core'
import { IconsService } from 'app/core/icons/icons.service'

export const provideIcons = (): (Provider | EnvironmentProviders)[] => {
  return [provideEnvironmentInitializer(() => inject(IconsService))]
}
