import { provideHttpClient, withInterceptors, withXhr } from '@angular/common/http'
import type { EnvironmentProviders, Provider } from '@angular/core'
import { importProvidersFrom, inject, provideAppInitializer, provideEnvironmentInitializer } from '@angular/core'
import { MatDialogModule } from '@angular/material/dialog'
import { MAT_FORM_FIELD_DEFAULT_OPTIONS } from '@angular/material/form-field'
import { MOCK_API_DEFAULT_DELAY, mockApiInterceptor } from '@seed/mock-api'
import type { SEEDConfig } from '@seed/services'
import {
  ConfirmationService,
  loadingInterceptor,
  LoadingService,
  MediaWatcherService,
  PlatformService,
  SEED_CONFIG,
  SplashScreenService,
} from '@seed/services'
import { MockApiService } from '../app/mock-api'

export type SEEDProviderConfig = {
  mockApi?: {
    enabled: boolean;
    delay?: number;
  };
  seed?: SEEDConfig;
}

/**
 * SEED provider
 */
export const provideSEED = (config: SEEDProviderConfig): (Provider | EnvironmentProviders)[] => {
  // Base providers
  const providers: (Provider | EnvironmentProviders)[] = [
    {
      // Use the 'fill' appearance on Angular Material form fields by default
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: {
        appearance: 'fill',
      },
    },
    {
      provide: MOCK_API_DEFAULT_DELAY,
      useValue: config.mockApi?.delay ?? 0,
    },
    {
      provide: SEED_CONFIG,
      useValue: config.seed ?? {},
    },

    importProvidersFrom(MatDialogModule),
    provideEnvironmentInitializer(() => inject(ConfirmationService)),

    provideHttpClient(withXhr(), withInterceptors([loadingInterceptor])),
    provideEnvironmentInitializer(() => inject(LoadingService)),
    provideEnvironmentInitializer(() => inject(MediaWatcherService)),
    provideEnvironmentInitializer(() => inject(PlatformService)),
    provideEnvironmentInitializer(() => inject(SplashScreenService)),
  ]

  // Mock Api services
  if (config.mockApi?.enabled) {
    providers.push(
      provideHttpClient(withXhr(), withInterceptors([mockApiInterceptor])),
      provideAppInitializer(() => {
        inject(MockApiService)
      }),
    )
  }

  // Return the providers
  return providers
}
