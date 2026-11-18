import { inject, Injectable } from '@angular/core'
import { MatIconRegistry } from '@angular/material/icon'
import { DomSanitizer } from '@angular/platform-browser'
import { LanguagesComponent } from '../../layout/common/languages/languages.component'

@Injectable({ providedIn: 'root' })
export class IconsService {
  private _domSanitizer = inject(DomSanitizer)
  private _matIconRegistry = inject(MatIconRegistry)

  constructor() {
    this._registerIconSets([
      // material-twotone is the default
      { namespace: null, url: 'icons/material-twotone.svg' },
      { namespace: 'mat-outline', url: 'icons/material-outline.svg' },
      { namespace: 'mat-solid', url: 'icons/material-solid.svg' },
      { namespace: 'heroicons-outline', url: 'icons/heroicons-outline.svg' },
      { namespace: 'heroicons-solid', url: 'icons/heroicons-solid.svg' },
      { namespace: 'fa-brands', url: 'icons/fa-brands.svg' },
      { namespace: 'fa-regular', url: 'icons/fa-regular.svg' },
      { namespace: 'fa-solid', url: 'icons/fa-solid.svg' },
    ])
    this._registerFlagIcons(Object.values(LanguagesComponent.flagCodes))
  }

  private _registerIconSets(iconSets: { namespace: string | null; url: string }[]): void {
    for (const { namespace, url } of iconSets) {
      const safeUrl = this._domSanitizer.bypassSecurityTrustResourceUrl(url)
      if (namespace) {
        this._matIconRegistry.addSvgIconSetInNamespace(namespace, safeUrl)
      } else {
        this._matIconRegistry.addSvgIconSet(safeUrl)
      }
    }
  }

  private _registerFlagIcons(flagCodes: string[]): void {
    for (const flagCode of flagCodes) {
      this._matIconRegistry.addSvgIconInNamespace(
        'flag',
        flagCode,
        this._domSanitizer.bypassSecurityTrustResourceUrl(`images/flags/${flagCode}.svg`),
      )
    }
  }
}
