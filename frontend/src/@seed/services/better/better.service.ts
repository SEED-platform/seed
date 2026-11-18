import { HttpClient, HttpHeaders } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, of } from 'rxjs'
import type { BetterTokenVerificationResponse } from './better.types'

@Injectable({ providedIn: 'root' })
export class BetterService {
  private _httpClient = inject(HttpClient)
  better_host = 'https://better-lbnl-development.herokuapp.com' // TODO - need to figure out how to configure this.
  better_url = `${this.better_host}/api/v1`

  verifyBetterToken(token: string): Observable<boolean> {
    const url = `/api/v3/analyses/verify_better_token/?better_token=${token}`
    const headers = new HttpHeaders({
      accept: 'application/json',
      Authorization: `Token ${token}`,
    })
    return this._httpClient.get<BetterTokenVerificationResponse>(url, { headers }).pipe(
      map(() => {
        return true
      }),
      catchError(() => {
        return of(false)
      }),
    )
  }
}
