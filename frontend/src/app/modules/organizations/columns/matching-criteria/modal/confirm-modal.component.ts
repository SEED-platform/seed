import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { catchError, EMPTY, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Column, ProgressResponse } from '@seed/api'
import { ColumnService } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { type ProgressBarObj, UploaderService } from '@seed/services/uploader'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-columns-matching-criteria-confirm-modal',
  templateUrl: './confirm-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, MaterialImports],
})
export class ConfirmModalComponent implements OnDestroy {
  private _columnService = inject(ColumnService)
  private _uploaderService = inject(UploaderService)
  private _dialogRef = inject(MatDialogRef<ConfirmModalComponent>)
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

  data = inject(MAT_DIALOG_DATA) as { columns: Column[]; orgId: number }

  onSubmit() {
    this.inProgress = true

    const successFn = () => {
      setTimeout(() => {
        this._snackBar.success('Criteria Updated')
        this.close(true)
      }, 300)
    }

    const failureFn = () => {
      this._snackBar.alert('Failed to change criteria')
      this.dismiss()
    }

    const changes = {}
    this.inProgress = true
    for (const c of this.data.columns) {
      changes[`${c.id}`] = { is_matching_criteria: !c.is_matching_criteria }
    }
    this.progressBarObj.message = 'Updating matching criteria...'

    this._columnService
      .updateMultipleColumns(this.data.orgId, this.data.columns[0].table_name, changes)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((response: ProgressResponse) => {
          this.progressBarObj.progress = response.progress
        }),
        switchMap(({ progress_key }) => {
          return this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            failureFn,
            progressBarObj: this.progressBarObj,
          })
        }),
        catchError(() => {
          this.inProgress = false
          this.errorMessage = 'An error occurred while updating matching criteria.'
          return EMPTY
        }),
      )
      .subscribe()
  }

  close(success) {
    this._dialogRef.close(success)
  }

  dismiss() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
