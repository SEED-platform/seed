import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { map, of } from 'rxjs'

@Injectable({ providedIn: 'root' })
export class MapService {
  private _httpClient: HttpClient = inject(HttpClient)
  disadvantaged: Record<string, boolean> = {}

  checkDisadvantagedStatus(tractIds: string[]): Observable<void> {
    const idsToFetch = tractIds.filter((id) => !(id in this.disadvantaged))
    if (!idsToFetch.length) {
      return of(undefined)
    }

    const url = '/api/v3/eeej/filter_disadvantaged_tracts/'
    return this._httpClient.post<{ status: string; disadvantaged: string[] }>(url, { tract_ids: tractIds }).pipe(
      map(({ disadvantaged }) => {
        for (const id of idsToFetch) {
          this.disadvantaged[id] = disadvantaged.includes(id)
        }
      }),
    )
  }

  isDisadvantaged(tractId: string): boolean {
    if (tractId in this.disadvantaged) {
      return this.disadvantaged[tractId]
    }
    // TODO: address this comment
    // console.error(`Tract ${tractId} hasn't previously been fetched, run checkDisadvantagedStatus first`)
    return false
  }
}
