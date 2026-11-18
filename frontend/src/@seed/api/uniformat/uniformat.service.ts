import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map } from 'rxjs'
import { ErrorService } from '@seed/services'
import type { UniformatLookup } from './uniformat.types'

@Injectable({ providedIn: 'root' })
export class UniformatService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)

  getUniformat(): Observable<UniformatLookup> {
    return this._httpClient.get<{ id: string; category: string; parent: string | null }[]>('/api/v3/uniformat/').pipe(
      map((items) =>
        items.reduce<UniformatLookup>((acc, { id, category, parent }) => {
          acc[id] = { category, parent }
          return acc
        }, {}),
      ),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error fetching uniformat data')),
    )
  }
}
