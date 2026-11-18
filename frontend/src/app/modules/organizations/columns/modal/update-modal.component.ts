import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject, takeUntil } from 'rxjs'
import type { ProgressResponse } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services/uploader/uploader.service'
import type { ProgressBarObj } from '@seed/services/uploader/uploader.types'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-columns-update-modal',
  templateUrl: './update-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, MaterialImports],
})
export class UpdateModalComponent implements OnDestroy, OnInit {
  private _uploaderService = inject(UploaderService)
  private _dialogRef = inject(MatDialogRef<UpdateModalComponent>)
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

  data = inject(MAT_DIALOG_DATA) as { progressResponse: ProgressResponse }

  ngOnInit(): void {
    this.inProgress = true
    const successFn = () => {
      setTimeout(() => {
        this._snackBar.success('Columns Updated')
        this.close()
      }, 300)
    }
    const failureFn = () => {
      this._snackBar.alert('Failed to update columns')
      this.close()
    }

    this._uploaderService
      .checkProgressLoop({
        progressKey: this.data.progressResponse.progress_key,
        successFn,
        failureFn,
        progressBarObj: this.progressBarObj,
      })
      .pipe(takeUntil(this._unsubscribeAll$))
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
