import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject } from 'rxjs'
import { ErrorService } from '@seed/services/error/error.service'
import type { ProgressResponse } from '../progress'
import { UserService } from '../user'
import type {
  AuditTemplateConfig,
  AuditTemplateConfigCreateResponse,
  AuditTemplateConfigResponse,
  AuditTemplateReportTypesResponse,
} from './audit-template.types'

@Injectable({ providedIn: 'root' })
export class AuditTemplateService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _errorService = inject(ErrorService)
  private _reportTypes = new ReplaySubject<string[]>(1)
  private _auditTemplateConfig = new ReplaySubject<AuditTemplateConfig>(1)
  reportTypes$ = this._reportTypes.asObservable()
  auditTemplateConfig$ = this._auditTemplateConfig.asObservable()

  constructor() {
    this.getReportTypes().subscribe()
    this._userService.currentOrganizationId$.subscribe((organizationId) => {
      this.getConfigs(organizationId).subscribe()
    })
  }

  getReportTypes(): Observable<string[]> {
    const url = '/api/v3/audit_template/report_types/'
    return this._httpClient.get<AuditTemplateReportTypesResponse>(url).pipe(
      map((response) => {
        this._reportTypes.next(response.data)
        return response.data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching Audit Template report types')
      }),
    )
  }

  getConfigs(organizationId: number): Observable<AuditTemplateConfig> {
    const url = `/api/v3/audit_template_configs/?organization_id=${organizationId}`
    return this._httpClient.get<AuditTemplateConfigResponse>(url).pipe(
      map((response) => {
        this._auditTemplateConfig.next(response.data[0])
        return response.data[0]
      }),
      catchError((error: HttpErrorResponse) => {
        // TODO need to figure out error handling
        return this._errorService.handleError(error, 'Error fetching audit template configs')
      }),
    )
  }

  create(auditTemplateConfig: AuditTemplateConfig): Observable<AuditTemplateConfig> {
    const url = `/api/v3/audit_template_configs/?organization_id=${auditTemplateConfig.organization}`
    return this._httpClient.post<AuditTemplateConfigCreateResponse>(url, { ...auditTemplateConfig }).pipe(
      map((r) => {
        this._auditTemplateConfig.next(r.data)
        return r.data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating Audit Template Config')
      }),
    )
  }

  update(auditTemplateConfig: AuditTemplateConfig): Observable<AuditTemplateConfig | null> {
    const url = `/api/v3/audit_template_configs/${auditTemplateConfig.id}/?organization_id=${auditTemplateConfig.organization}`
    return this._httpClient.put<AuditTemplateConfigResponse>(url, { ...auditTemplateConfig }).pipe(
      map((r) => {
        this._auditTemplateConfig.next(r.data[0])
        return r.data[0]
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating Audit Template Config')
      }),
    )
  }

  batchExportToAuditTemplate(orgId: number, propertyViewIds: number[]): Observable<ProgressResponse> {
    const url = `/api/v3/audit_template/batch_export_to_audit_template/?organization_id=${orgId}`
    return this._httpClient.post<ProgressResponse>(url, { property_view_ids: propertyViewIds }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error exporting to Audit Template')
      }),
    )
  }

  batchGetCitySubmissionXml(orgId: number, viewIds: number[], defaultCycle: number | null): Observable<ProgressResponse> {
    const url = `/api/v3/audit_template/batch_get_city_submission_xml/?organization_id=${orgId}`
    return this._httpClient.put<ProgressResponse>(url, { view_ids: viewIds, default_cycle: defaultCycle }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error importing Audit Template submissions')
      }),
    )
  }
  exportBuildingSyncAtFile(orgId: number, viewId: number): Observable<string> {
    const url = '/api/v3/audit_template/export_buildingsync_at_file/'
    return this._httpClient.get(url, { params: { organization_id: orgId, view_id: viewId }, responseType: 'text' }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error exporting Audit Template XML')
      }),
    )
  }
}
