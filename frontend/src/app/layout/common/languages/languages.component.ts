import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import type { LangDefinition } from '@jsverse/transloco'
import { TranslocoService } from '@jsverse/transloco'
import { Subject, takeUntil } from 'rxjs'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-languages',
  templateUrl: './languages.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  exportAs: 'languages',
  imports: [CommonModule, MaterialImports],
})
export class LanguagesComponent implements OnInit, OnDestroy {
  private _translocoService = inject(TranslocoService)

  private readonly _unsubscribeAll$ = new Subject<void>()
  availableLangs: LangDefinition[]
  activeLang: string
  // Map languages to ISO country codes for matching flags
  static readonly flagCodes: Record<string, string> = {
    en_US: 'us',
    fr_CA: 'ca',
    es: 'mx',
  }

  get flagCodes() {
    return LanguagesComponent.flagCodes
  }

  ngOnInit(): void {
    // Get the available languages from transloco
    this.availableLangs = this._translocoService.getAvailableLangs().filter((lang) => typeof lang === 'object')

    // Subscribe to language changes
    this._translocoService.langChanges$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((activeLang) => {
      // Get the active lang
      this.activeLang = activeLang
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  // Set the active language
  setActiveLang(lang: string): void {
    this._translocoService.setActiveLang(lang)
  }
}
