import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { RouterModule } from '@angular/router'
import { of, Subject, switchMap, takeUntil } from 'rxjs'
import type { ProgressResponse, SubProgressResponse } from '@seed/api'
import { MappingService } from '@seed/api'
import { ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { CheckProgressLoopParams } from '@seed/services/uploader'
import { UploaderService } from '@seed/services/uploader'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory'
import { ResultsComponent } from './results.component'

@Component({
  selector: 'seed-match-merge',
  templateUrl: './match-merge.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ProgressBarComponent, RouterModule, ResultsComponent],
})
export class MatchMergeComponent implements OnDestroy {
  @Input() datasetId: number
  @Input() cycleId: number
  @Input() importFileId: number
  @Input() inventoryType: InventoryType
  @Input() orgId: number
  @Output() matchMergeComplete = new EventEmitter<null>()

  private _mappingService = inject(MappingService)
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  inProgress = true

  progressBarObj = this._uploaderService.defaultProgressBarObj
  subProgressBarObj = this._uploaderService.defaultProgressBarObj

  startMatchMerge() {
    this.inProgress = true
    this._mappingService
      .mappingDone(this.orgId, this.importFileId)
      .pipe(
        switchMap(() => this._mappingService.startMatchMerge(this.orgId, this.importFileId)),
        switchMap((response) => this.checkProgressResponse(response)),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  checkProgressResponse(response: ProgressResponse | SubProgressResponse) {
    // check if its already matched and skip progress step
    if ((response as ProgressResponse).progress === 100) {
      this.inProgress = false
      return of(null)
    }
    return this.checkProgress(response as SubProgressResponse)
  }

  checkProgress(data: SubProgressResponse) {
    const successFn = () => {
      this.matchMergeComplete.emit()
      this.inProgress = false
      this._snackBar.success('Data Upload Complete')
    }

    const { progress_data, sub_progress_data } = data
    const mainParams: CheckProgressLoopParams = {
      progressKey: progress_data.progress_key,
      successFn,
      progressBarObj: this.progressBarObj,
    }

    const subParams: CheckProgressLoopParams = {
      progressKey: sub_progress_data.progress_key,
      progressBarObj: this.subProgressBarObj,
    }

    return this._uploaderService.checkProgressLoopMainSub(mainParams, subParams)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
