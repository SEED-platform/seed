import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { UserService } from '../user'
import type {
  FilterGroup,
  FilterGroupInventoryType,
  FilterGroupResponse,
  FilterGroupsResponse,
  FilterGroupUpsertPayload,
} from './filter-group.types'

@Injectable({ providedIn: 'root' })
export class FilterGroupService {
  private _errorService = inject(ErrorService)
  private _filterGroups = new ReplaySubject<FilterGroup[]>(1)
  private _currentFilterGroups: FilterGroup[] = []
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)

  filterGroups$ = this._filterGroups.asObservable()

  constructor() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.list(orgId)
        }),
      )
      .subscribe()
  }

  list(orgId: number, inventoryType?: FilterGroupInventoryType) {
    const inventoryTypeQuery = inventoryType ? `&inventory_type=${encodeURIComponent(inventoryType)}` : ''
    const url = `/api/v3/filter_groups/?organization_id=${orgId}${inventoryTypeQuery}`
    this._httpClient
      .get<FilterGroupsResponse>(url)
      .pipe(
        take(1),
        map(({ data }) => {
          const filterGroups = data.toSorted((a, b) => naturalSort(a.name, b.name))
          this._currentFilterGroups = filterGroups
          this._filterGroups.next(filterGroups)
          return filterGroups
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching filter groups')
        }),
      )
      .subscribe()
  }

  create(orgId: number, payload: FilterGroupUpsertPayload): Observable<FilterGroup> {
    const url = `/api/v3/filter_groups/?organization_id=${orgId}`
    return this._httpClient.post<FilterGroupResponse>(url, payload).pipe(
      map(({ data }) => {
        this._currentFilterGroups = [...this._currentFilterGroups, data].toSorted((a, b) => naturalSort(a.name, b.name))
        this._filterGroups.next(this._currentFilterGroups)
        return data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating filter group')
      }),
    )
  }

  update(orgId: number, id: number, payload: FilterGroupUpsertPayload): Observable<FilterGroup> {
    const url = `/api/v3/filter_groups/${id}/?organization_id=${orgId}`
    return this._httpClient.put<FilterGroupResponse>(url, payload).pipe(
      map(({ data }) => {
        this._currentFilterGroups = this._currentFilterGroups.map((fg) => (fg.id === id ? data : fg))
        this._filterGroups.next(this._currentFilterGroups)
        return data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating filter group')
      }),
    )
  }

  delete(orgId: number, id: number): Observable<{ status: string }> {
    const url = `/api/v3/filter_groups/${id}/?organization_id=${orgId}`
    return this._httpClient.delete<{ status: string }>(url).pipe(
      tap(() => {
        this._currentFilterGroups = this._currentFilterGroups.filter((fg) => fg.id !== id)
        this._filterGroups.next(this._currentFilterGroups)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting filter group')
      }),
    )
  }
}
