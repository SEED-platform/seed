import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { ReplaySubject, tap } from 'rxjs'
import type { VersionResponse } from './version.types'

@Injectable({ providedIn: 'root' })
export class VersionService {
  private _httpClient = inject(HttpClient)
  private _version = new ReplaySubject<VersionResponse>(1)
  version$ = this._version.asObservable()

  get(): Observable<VersionResponse> {
    return this._httpClient.get<VersionResponse>('/api/version/').pipe(
      tap((version) => {
        this._version.next(version)
      }),
    )
  }
}
