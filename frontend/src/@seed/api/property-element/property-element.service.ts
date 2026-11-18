import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError } from 'rxjs'
import { ErrorService } from '@seed/services'
import type { PropertyElement } from './property-element.types'

@Injectable({ providedIn: 'root' })
export class PropertyElementService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)

  getElements(orgId: number, propertyId: number): Observable<PropertyElement[]> {
    const url = `/api/v3/properties/${propertyId}/elements/`
    return this._httpClient
      .get<PropertyElement[]>(url, { params: { organization_id: orgId } })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error fetching building elements')))
  }
}
