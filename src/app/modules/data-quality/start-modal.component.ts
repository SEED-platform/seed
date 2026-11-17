import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from '@angular/material/dialog'
import { switchMap, takeUntil } from 'rxjs'
import { Subject } from 'rxjs/internal/Subject'
import { DataQualityService } from '@seed/api'
import { ProgressBarComponent } from '@seed/components'
import { UploaderService } from '@seed/services/uploader/uploader.service'
import type { InventoryType } from '../inventory'
import { DQCResultsModalComponent } from './results-modal.component'

@Component({
  selector: 'seed-dqc-start-modal',
  templateUrl: './start-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [ProgressBarComponent],
})
export class DQCStartModalComponent implements OnDestroy, OnInit {
  private _dataQualityService = inject(DataQualityService)
  private _dialog = inject(MatDialog)
  private _dialogRef = inject(MatDialogRef<DQCStartModalComponent>)
  private _uploaderService = inject(UploaderService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  progressBarObj = this._uploaderService.defaultProgressBarObj

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    type: InventoryType;
    viewIds: number[];
    goalId?: number;
  }

  ngOnInit() {
    const [propertyViewIds, taxlotViewIds] = this.data.type === 'properties' ? [this.data.viewIds, []] : [[], this.data.viewIds]
    this._dataQualityService
      .startDataQualityCheckForOrg(this.data.orgId, propertyViewIds, taxlotViewIds, this.data.goalId ?? null)
      .pipe(
        switchMap(({ progress_key }) => {
          return this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn: ({ unique_id }) => {
              // data quality run IDs are integers (other tasks' IDs can be strings)
              this.openDataQualityResultsModal(Number(unique_id))
            },
            progressBarObj: this.progressBarObj,
          })
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  openDataQualityResultsModal(dqcId: number) {
    this._dialog.open(DQCResultsModalComponent, {
      width: '50rem',
      data: { orgId: this.data.orgId, dqcId },
    })

    this.close(true)
  }

  close(result?: boolean) {
    this._dialogRef.close(result)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
