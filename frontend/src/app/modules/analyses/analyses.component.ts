import type { AfterViewInit, OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { filter, Subject, tap } from 'rxjs'
import type { Analysis, Cycle } from '@seed/api'
import { AnalysisService, CycleService, UserService } from '@seed/api'
import { AnalysesGridComponent, NotFoundComponent, PageComponent } from '@seed/components'

@Component({
  selector: 'seed-analyses',
  templateUrl: './analyses.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AnalysesGridComponent, NotFoundComponent, PageComponent],
})
export class AnalysesComponent implements AfterViewInit, OnDestroy {
  private _analysisService = inject(AnalysisService)
  private _cycleService = inject(CycleService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  analyses: Analysis[] = []
  cycles: Cycle[] = []
  orgId: number
  ready = false

  ngAfterViewInit() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.orgId = orgId
          this.getCycles()
          this.getAnalyses()
        }),
      )
      .subscribe()
  }

  getCycles() {
    this._cycleService.cycles$.subscribe((cycles) => (this.cycles = cycles))
  }

  getAnalyses() {
    this._analysisService.analyses$
      .pipe(
        filter(Boolean),
        tap((analyses) => {
          setTimeout(() => {
            // suppress ExpressionChangedAfterItHasBeenCheckedError
            this.analyses = analyses
          })
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
