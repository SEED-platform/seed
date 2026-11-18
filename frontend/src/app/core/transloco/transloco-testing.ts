import type { ModuleWithProviders } from '@angular/core'
import { TranslocoTestingModule } from '@jsverse/transloco'

export function getTranslocoTestingModule(translations: Record<string, string> = {}): ModuleWithProviders<TranslocoTestingModule> {
  return TranslocoTestingModule.forRoot({
    langs: { en_US: translations },
    translocoConfig: { availableLangs: ['en_US'], defaultLang: 'en_US' },
    preloadLangs: true,
  })
}
