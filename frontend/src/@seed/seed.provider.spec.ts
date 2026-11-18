import { HttpBackend, HttpXhrBackend } from '@angular/common/http'
import { TestBed } from '@angular/core/testing'
import { ConfirmationService, LoadingService, MediaWatcherService, PlatformService, SplashScreenService } from '@seed/services'
import { provideAuth } from 'app/core/auth/auth.provider'
import { AuthService } from 'app/core/auth/auth.service'
import { MockApiService } from 'app/mock-api'
import { provideSEED } from './seed.provider'

describe('SEED HTTP providers', () => {
  for (const mockApiEnabled of [false, true]) {
    it(`keeps XHR upload support with mock API ${mockApiEnabled ? 'enabled' : 'disabled'}`, () => {
      TestBed.configureTestingModule({
        providers: [
          provideAuth(),
          provideSEED({ mockApi: { enabled: mockApiEnabled } }),
          { provide: AuthService, useValue: {} },
          { provide: ConfirmationService, useValue: {} },
          { provide: LoadingService, useValue: {} },
          { provide: MediaWatcherService, useValue: {} },
          { provide: PlatformService, useValue: {} },
          { provide: SplashScreenService, useValue: {} },
          { provide: MockApiService, useValue: {} },
        ],
      })

      expect(TestBed.inject(HttpBackend)).toBeInstanceOf(HttpXhrBackend)
    })
  }
})
