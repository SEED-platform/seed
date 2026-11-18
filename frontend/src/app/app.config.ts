import { DOCUMENT } from '@angular/common'
import { provideHttpClient, withXhr } from '@angular/common/http'
import type { ApplicationConfig } from '@angular/core'
import { inject, Injectable, isDevMode, provideAppInitializer } from '@angular/core'
import { DateAdapter, MAT_DATE_FORMATS } from '@angular/material/core'
import { LuxonDateAdapter } from '@angular/material-luxon-adapter'
import { Title } from '@angular/platform-browser'
import { provideAnimations } from '@angular/platform-browser/animations'
import type { RouterStateSnapshot } from '@angular/router'
import { provideRouter, TitleStrategy, UrlSerializer, withInMemoryScrolling, withRouterConfig } from '@angular/router'
import { provideTransloco, TranslocoService } from '@jsverse/transloco'
import { catchError, firstValueFrom, of, tap } from 'rxjs'
import { provideSEED } from '@seed'
import { ConfigService } from '@seed/api'
import { LowerCaseUrlSerializer } from '@seed/routing/url.serializer'
import { appRoutes } from 'app/app.routes'
import { provideAuth } from 'app/core/auth/auth.provider'
import { provideIcons } from 'app/core/icons/icons.provider'
import { TranslocoHttpLoader } from './core/transloco/transloco.http-loader'

@Injectable({ providedIn: 'root' })
export class TemplatePageTitleStrategy extends TitleStrategy {
  private _title = inject(Title)

  override updateTitle(routerState: RouterStateSnapshot) {
    const title = this.buildTitle(routerState)
    this._title.setTitle(`${title ? `${title} - ` : ''}SEED Platform™`)
  }
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideAnimations(),
    provideHttpClient(withXhr()),
    provideRouter(
      appRoutes,
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
      withRouterConfig({ onSameUrlNavigation: 'reload', paramsInheritanceStrategy: 'emptyOnly' }),
    ),
    { provide: UrlSerializer, useClass: LowerCaseUrlSerializer },
    { provide: TitleStrategy, useClass: TemplatePageTitleStrategy },
    { provide: DateAdapter, useClass: LuxonDateAdapter },
    {
      provide: MAT_DATE_FORMATS,
      useValue: {
        parse: {
          dateInput: 'D',
        },
        display: {
          dateInput: 'DDD',
          monthYearLabel: 'LLL yyyy',
          dateA11yLabel: 'DD',
          monthYearA11yLabel: 'LLLL yyyy',
        },
      },
    },
    provideTransloco({
      config: {
        availableLangs: [
          {
            id: 'en_US',
            label: 'English',
          },
          {
            id: 'fr_CA',
            label: 'French',
          },
          {
            id: 'es',
            label: 'Spanish',
          },
        ],
        defaultLang: 'en_US',
        fallbackLang: 'en_US',
        reRenderOnLangChange: true,
        prodMode: !isDevMode(),
      },
      loader: TranslocoHttpLoader,
    }),
    provideAppInitializer(() => {
      const translocoService = inject(TranslocoService)
      const defaultLang = translocoService.getDefaultLang()
      translocoService.setActiveLang(defaultLang)

      return firstValueFrom(translocoService.load(defaultLang))
    }),
    provideAppInitializer(() => {
      const splashLogo = inject(DOCUMENT).querySelector<HTMLImageElement>('seed-splash-screen img')
      return firstValueFrom(
        inject(ConfigService).config$.pipe(
          tap(({ branding }) => {
            if (!splashLogo) return
            splashLogo.src = branding.logo_url || 'images/logo.svg'
            splashLogo.alt = branding.logo_url ? '' : 'SEED Platform logo'
            splashLogo.hidden = false
          }),
          catchError(() => {
            if (splashLogo) splashLogo.hidden = false
            return of(null)
          }),
        ),
      )
    }),
    provideAuth(),
    provideIcons(),
    provideSEED({
      ...(isDevMode()
        ? {
            mockApi: {
              enabled: false,
              delay: 200,
            },
          }
        : {}),
      seed: {
        layout: 'main',
        scheme: 'auto',
        // scheme: 'light',
        // At least 8 characters, one uppercase letter, one lowercase letter, and one number
        passwordPattern: /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$/,

        theme: 'theme-default',
        themes: [
          {
            id: 'theme-default',
            name: 'Default',
          },
        ],
      },
    }),
  ],
}
