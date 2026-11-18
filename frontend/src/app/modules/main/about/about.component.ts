import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { Subject, takeUntil } from 'rxjs'
import { VersionService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { TermsService } from '@seed/services'

@Component({
  selector: 'seed-about',
  templateUrl: './about.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [PageComponent, SharedImports],
})
export class AboutComponent implements OnInit, OnDestroy {
  private _termsService = inject(TermsService)
  private _versionService = inject(VersionService)

  version: string
  sha: string
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    this._versionService.version$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ version, sha }) => {
      this.version = version
      this.sha = sha
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  showTermsOfService(): void {
    this._termsService.showTermsOfService()
  }
}
