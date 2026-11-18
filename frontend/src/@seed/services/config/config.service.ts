import { inject, Injectable } from '@angular/core'
import { colorSchemeDarkBlue, colorSchemeLight, type Theme, themeAlpine } from 'ag-grid-community'
import { BehaviorSubject, map, type Observable } from 'rxjs'
import { SEED_CONFIG } from './config.constants'
import type { SEEDConfig } from './config.types'

@Injectable({ providedIn: 'root' })
export class ConfigService {
  private _config = new BehaviorSubject(inject(SEED_CONFIG))

  get config$() {
    return this._config.asObservable()
  }

  set config(value: Partial<SEEDConfig>) {
    // Merge the new config over to the current config
    const config = {
      ...this._config.getValue(),
      ...value,
    }

    // Execute the observable
    this._config.next(config)
  }

  get scheme$(): Observable<'dark' | 'light'> {
    // If the scheme is set to auto, we need to check the system preference
    return this.config$.pipe(
      map(({ scheme }) => {
        return scheme === 'auto' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : scheme
      }),
    )
  }

  get gridTheme$(): Observable<Theme> {
    return this.scheme$.pipe(map((theme) => themeAlpine.withPart(theme === 'dark' ? colorSchemeDarkBlue : colorSchemeLight)))
  }
}
