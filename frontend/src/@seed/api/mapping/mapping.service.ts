import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { catchError, map, type Observable } from 'rxjs'
import { ErrorService } from '@seed/services'
import type { MappedData } from '../dataset'
import type { ProgressResponse, SubProgressResponse } from '../progress'
import { UserService } from '../user'
import type { FirstFiveRowsResponse, MappingSuggestionsResponse, MatchingResultsResponse, RawColumnNamesResponse } from './mapping.types'

@Injectable({ providedIn: 'root' })
export class MappingService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _userService = inject(UserService)

  mappingSuggestions(orgId: number, importFileId: number): Observable<MappingSuggestionsResponse> {
    const url = `/api/v3/import_files/${importFileId}/mapping_suggestions/?organization_id=${orgId}`
    return this._httpClient.get<MappingSuggestionsResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching mapping suggestions')
      }),
    )
  }

  rawColumnNames(orgId: number, importFileId: number): Observable<string[]> {
    const url = `/api/v3/import_files/${importFileId}/raw_column_names/?organization_id=${orgId}`
    return this._httpClient.get<RawColumnNamesResponse>(url).pipe(
      map(({ raw_columns }) => raw_columns),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching raw column names')
      }),
    )
  }

  firstFiveRows(orgId: number, importFileId: number): Observable<Record<string, unknown>[]> {
    const url = `/api/v3/import_files/${importFileId}/first_five_rows/?organization_id=${orgId}`
    return this._httpClient.get<FirstFiveRowsResponse>(url).pipe(
      map(({ first_five_rows }) => first_five_rows),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching first five rows')
      }),
    )
  }

  startMapping(orgId: number, importFileId: number, mappedData: MappedData): Observable<unknown> {
    const url = `/api/v3/organizations/${orgId}/column_mappings/?import_file_id=${importFileId}`
    return this._httpClient.post(url, mappedData).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error starting mapping')
      }),
    )
  }

  remapBuildings(orgId: number, importFileId: number): Observable<ProgressResponse> {
    const url = `/api/v3/import_files/${importFileId}/map/?organization_id=${orgId}`
    return this._httpClient.post<ProgressResponse>(url, { remap: true, mark_as_done: false }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error remapping buildings')
      }),
    )
  }

  mappingResults(orgId: number, importFileId: number): Observable<ProgressResponse> {
    const url = `/api/v3/import_files/${importFileId}/mapping_results/?organization_id=${orgId}`
    return this._httpClient.post<ProgressResponse>(url, {}).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching mapping results')
      }),
    )
  }

  mappingDone(orgId: number, importFileId: number): Observable<{ message: string; status: string }> {
    const url = `/api/v3/import_files/${importFileId}/mapping_done/?organization_id=${orgId}`
    return this._httpClient.post<{ message: string; status: string }>(url, {}).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching mapping results')
      }),
    )
  }

  startMatchMerge(orgId: number, importFileId: number): Observable<ProgressResponse | SubProgressResponse> {
    const url = `/api/v3/import_files/${importFileId}/start_system_matching_and_geocoding/?organization_id=${orgId}`
    // returns ProgressResponse if already matched
    return this._httpClient.post<ProgressResponse | SubProgressResponse>(url, {}).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error starting match merge')
      }),
    )
  }

  getMatchingResults(orgId: number, importFileId: number): Observable<MatchingResultsResponse> {
    const url = `/api/v3/import_files/${importFileId}/matching_and_geocoding_results/?organization_id=${orgId}`
    return this._httpClient.get<MatchingResultsResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error getting matching and geocoding results')
      }),
    )
  }
}
