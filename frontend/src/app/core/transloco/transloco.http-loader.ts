import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Translation, TranslocoLoader } from '@jsverse/transloco'
import type { Observable } from 'rxjs'

@Injectable({ providedIn: 'root' })
export class TranslocoHttpLoader implements TranslocoLoader {
  private _httpClient = inject(HttpClient)

  /**
   * Get translation
   *
   * @param lang
   */
  getTranslation(lang: string): Observable<Translation> {
    return this._httpClient.get<Translation>(`./i18n/${lang}.json`)
  }
}
