import { HttpClient, type HttpErrorResponse } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { catchError, map, type Observable, ReplaySubject, Subject, takeUntil, tap } from 'rxjs'
import { UserService } from '@seed/api'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { CreateEmailTemplateResponse, EmailTemplate, ListEmailTemplatesResponse, SendEmailResponse } from './postoffice.types'

@Injectable({ providedIn: 'root' })
export class PostOfficeService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _errorService = inject(ErrorService)
  private _emailTemplates = new ReplaySubject<EmailTemplate[]>()
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  orgId: number
  emailTemplates$ = this._emailTemplates.asObservable()

  constructor() {
    this._userService.currentOrganizationId$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organizationId) => {
      this.getEmailTemplates(organizationId).subscribe()
    })
  }

  getEmailTemplates(organizationId: number): Observable<EmailTemplate[]> {
    const url = `/api/v3/postoffice/?organization_id=${organizationId}`
    return this._httpClient.get<ListEmailTemplatesResponse>(url).pipe(
      map((response) => response.data),
      tap((emailTemplates) => {
        this._emailTemplates.next(emailTemplates)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Could not fetch email templates')
      }),
    )
  }

  create(organization_id: number, name: string): Observable<EmailTemplate> {
    const url = '/api/v3/postoffice/'
    return this._httpClient.post<CreateEmailTemplateResponse>(url, { name, organization_id }).pipe(
      map((response: CreateEmailTemplateResponse) => {
        return response.data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'could not create template')
      }),
    )
  }

  update(organization_id: number, template: EmailTemplate): Observable<EmailTemplate> {
    const url = `/api/v3/postoffice/${template.id}/?organization_id=${organization_id}`
    return this._httpClient.put<CreateEmailTemplateResponse>(url, { ...template }).pipe(
      map((response: CreateEmailTemplateResponse) => {
        return response.data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'could not update template')
      }),
    )
  }

  delete(id: number, organization_id: number): Observable<unknown> {
    const url = `/api/v3/postoffice/${id}/?organization_id=${organization_id}`
    return this._httpClient.delete(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'could not delete template')
      }),
    )
  }

  sendEmail(orgId: number, stateIds: number[], template_id: number, inventory_type: string): Observable<SendEmailResponse> {
    const url = `/api/v3/postoffice_email/?organization_id=${orgId}`
    const data = {
      from_email: 'blankl@example.com', // Dummy email. The backend will assign the appropriate email.
      template_id,
      inventory_id: stateIds,
      inventory_type,
    }
    return this._httpClient.post<SendEmailResponse>(url, data).pipe(
      tap(({ status }) => {
        if (status === 'success') {
          this._snackBar.success('Successfully sent email')
        } else {
          this._snackBar.alert('Error sending email')
        }
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error sending email')
      }),
    )
  }
}
