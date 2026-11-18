import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, interval, of, switchMap, takeWhile, throwError } from 'rxjs'
import type { ProgressResponse } from '.'

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private _httpClient = inject(HttpClient)

  /*
   * Fetches progress for a given progress key
   */
  checkProgress(progressKey: string): Observable<ProgressResponse> {
    const url = `/api/v3/progress/${progressKey}/`
    return this._httpClient.get<ProgressResponse>(url).pipe(
      catchError((error) => {
        console.error('Error fetching progress:', error)
        return of(null)
      }),
    )
  }

  /*
   * Checks a progress key for updates until it completes
   */
  checkProgressLoop$(progressKey: string): Observable<ProgressResponse> {
    return interval(750).pipe(
      switchMap(() => this.checkProgress(progressKey)),
      takeWhile((response) => response.progress < 100, true),
      catchError(() => {
        // TODO the interval needs to continue if the error was network-related
        return throwError(() => new Error('Progress check failed'))
      }),
    )
  }
}
