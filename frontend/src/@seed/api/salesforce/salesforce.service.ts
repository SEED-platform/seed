import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import {
  type SalesforceConfig,
  type SalesforceConfigResponse,
  type SalesforceConfigsResponse,
  type SalesforceConnectionTestResponse,
  type SalesforceMapping,
  type SalesforceMappingDeleteResponse,
  type SalesforceMappingResponse,
  type SalesforceMappingsResponse,
} from './salesforce.types'

@Injectable({ providedIn: 'root' })
export class SalesforceService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)

  private _config = new ReplaySubject<SalesforceConfig>(1)
  private _mappings = new ReplaySubject<SalesforceMapping[]>(1)

  config$ = this._config.asObservable()
  mappings$ = this._mappings.asObservable()

  constructor() {
    // Fetch current org data whenever user org id changes
    this._userService.currentOrganizationId$.subscribe((organizationId) => {
      this.getConfig(organizationId).subscribe()
      this.getMappings(organizationId).subscribe()
    })
  }

  getConfig(organizationId: number): Observable<SalesforceConfigsResponse> {
    const url = `/api/v3/salesforce_configs/?organization_id=${organizationId}`
    return this._httpClient.get<SalesforceConfigsResponse>(url).pipe(
      map((response) => {
        if (response.salesforce_configs.length == 0) {
          this._config.next({} as SalesforceConfig)
        } else {
          this._config.next(response.salesforce_configs[0])
        }
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching Salesforce config')
      }),
    )
  }

  getMappings(organizationId: number): Observable<SalesforceMappingsResponse> {
    const url = `/api/v3/salesforce_mappings/?organization_id=${organizationId}`
    return this._httpClient.get<SalesforceMappingsResponse>(url).pipe(
      map((response) => {
        this._mappings.next(response.salesforce_mappings)
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching Salesforce mappings')
      }),
    )
  }

  create(organizationId: number, config: SalesforceConfig): Observable<SalesforceConfig> {
    const url = `/api/v3/salesforce_configs/?organization_id=${organizationId}`
    return this._httpClient.post<SalesforceConfigResponse>(url, { ...config }).pipe(
      map((response) => {
        this._config.next(response.salesforce_config)
        return response.salesforce_config
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating Salesforce config')
      }),
    )
  }

  update(organizationId: number, config: SalesforceConfig, message?: string): Observable<SalesforceConfig> {
    const url = `/api/v3/salesforce_configs/${config.id}/?organization_id=${organizationId}`
    return this._httpClient.put<SalesforceConfigResponse>(url, { ...config }).pipe(
      map((response) => {
        this._snackBar.success(message || 'Salesforce configuration updated')
        this._config.next(response.salesforce_config)
        return response.salesforce_config
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating Salesforce config')
      }),
    )
  }

  test_connection(organizationId: number, config: SalesforceConfig): Observable<SalesforceConnectionTestResponse> {
    const url = `/api/v3/salesforce_configs/salesforce_connection/?organization_id=${organizationId}`
    return this._httpClient.post<SalesforceConnectionTestResponse>(url, { salesforce_config: config }).pipe(
      map((response) => {
        this._snackBar.success('Salesforce Connection: Success')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Salesforce Connection Error: ${error.message}`)
      }),
    )
  }

  createMapping(organizationId: number, mapping: Omit<SalesforceMapping, 'id'>): Observable<SalesforceMappingResponse> {
    const url = `/api/v3/salesforce_mappings/?organization_id=${organizationId}`
    return this._httpClient.post<SalesforceMappingResponse>(url, { ...mapping }).pipe(
      map((response) => {
        this._snackBar.success('Salesforce Mapping Created')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating Salesforce mapping')
      }),
    )
  }

  updateMapping(organizationId: number, mapping: SalesforceMapping): Observable<SalesforceMappingResponse> {
    const url = `/api/v3/salesforce_mappings/${mapping.id}/?organization_id=${organizationId}`
    return this._httpClient.put<SalesforceMappingResponse>(url, { ...mapping }).pipe(
      map((response) => {
        this._snackBar.success('Salesforce Mapping Updated')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating Salesforce mapping')
      }),
    )
  }

  deleteMapping(mapping: SalesforceMapping): Observable<SalesforceMappingDeleteResponse> {
    const url = `/api/v3/salesforce_mappings/${mapping.id}/?organization_id=${mapping.organization_id}`
    return this._httpClient.delete<SalesforceMappingDeleteResponse>(url).pipe(
      map((response) => {
        this._snackBar.success('Salesforce Mapping Removed')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Salesforce Mapping could not be removed: ${error.message}`)
      }),
    )
  }
}
