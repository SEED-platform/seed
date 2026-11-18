import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { Subject, switchMap } from 'rxjs'
import { AuditTemplateService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-audit-template-export-modal',
  templateUrl: './audit-template-export-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class AuditTemplateExportModalComponent implements OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _dialogRef = inject(MatDialogRef<AuditTemplateExportModalComponent>)
  private _auditTemplateService = inject(AuditTemplateService)
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewIds: number[] }
  progressBarObj = this._uploaderService.defaultProgressBarObj

  onSubmit(): void {
    this.stepper.next()
    this._auditTemplateService
      .batchExportToAuditTemplate(this.data.orgId, this.data.viewIds)
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn: () => {
              this._snackBar.success('Properties exported to Audit Template successfully.')
              this.close(true)
            },
            progressBarObj: this.progressBarObj,
          }),
        ),
      )
      .subscribe()
  }

  close(success = false): void {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
