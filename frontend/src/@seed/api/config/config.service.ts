import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { shareReplay } from 'rxjs'
import type { ConfigResponse } from './config.types'

@Injectable({ providedIn: 'root' })
export class ConfigService {
  private _httpClient = inject(HttpClient)

  private _config$: Observable<ConfigResponse>

  // Singleton request
  get config$(): Observable<ConfigResponse> {
    if (!this._config$) {
      this._config$ = this._httpClient.get<ConfigResponse>('/api/config/').pipe(shareReplay(1))
    }
    return this._config$
  }
}
