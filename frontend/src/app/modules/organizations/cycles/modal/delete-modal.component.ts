import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Cycle } from '@seed/api'
import { CycleService } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { ProgressBarObj } from '@seed/services'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-cycles-delete-modal',
  templateUrl: './delete-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, MaterialImports],
})
export class DeleteModalComponent implements OnDestroy {
  private _cycleService = inject(CycleService)
  private _uploaderService = inject(UploaderService)
  private _dialogRef = inject(MatDialogRef<DeleteModalComponent>)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  errorMessage: string
  inProgress = false
  progressBarObj: ProgressBarObj = {
    message: '',
    progress: 0,
    complete: false,
    statusMessage: '',
    progressLastUpdated: null,
    progressLastChecked: null,
  }

  data = inject(MAT_DIALOG_DATA) as { cycle: Cycle; orgId: number }

  onSubmit() {
    this.inProgress = true
    const successFn = () => {
      setTimeout(() => {
        this._snackBar.success('Cycle deleted')
        this.close()
      }, 300)
    }
    const failureFn = () => {
      this._snackBar.alert('Failed to delete cycle')
      this.close()
    }

    // initiate delete cycle task
    this._cycleService
      .delete(this.data.cycle.id, this.data.orgId)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((response: { progress_key: string; value: number }) => {
          this.progressBarObj.progress = response.value
        }),
        switchMap(({ progress_key }) => {
          return this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            failureFn,
            progressBarObj: this.progressBarObj,
          })
        }),
      )
      .subscribe()
  }

  close() {
    this._dialogRef.close()
  }

  dismiss() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
