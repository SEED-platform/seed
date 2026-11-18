import { AsyncPipe } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { booleanAttribute, ChangeDetectionStrategy, Component, inject, input, ViewEncapsulation } from '@angular/core'
import { MatProgressBarModule } from '@angular/material/progress-bar'
import { asyncScheduler, observeOn, Subject, takeUntil } from 'rxjs'
import { LoadingService } from '@seed/services'

@Component({
  selector: 'seed-loading-bar',
  templateUrl: './loading-bar.component.html',
  styleUrl: './loading-bar.component.scss',
  encapsulation: ViewEncapsulation.None,
  exportAs: 'seedLoadingBar',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AsyncPipe, MatProgressBarModule],
})
export class SEEDLoadingBarComponent implements OnInit, OnDestroy {
  private _loadingService = inject(LoadingService)

  autoMode = input(true, { transform: booleanAttribute })
  mode: 'determinate' | 'indeterminate'
  progress = 0
  show$ = this._loadingService.show$.pipe(observeOn(asyncScheduler))
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    this._loadingService.mode$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((value) => {
      this.mode = value
    })

    this._loadingService.progress$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((value) => {
      this.progress = value
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
