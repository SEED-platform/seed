import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'

@Injectable({ providedIn: 'root' })
export class SwaggerService {
  private _httpClient = inject(HttpClient)

  getSchema(): Observable<Record<string, unknown>> {
    return this._httpClient.get<Record<string, unknown>>('/api/swagger/?format=openapi')
  }
}
