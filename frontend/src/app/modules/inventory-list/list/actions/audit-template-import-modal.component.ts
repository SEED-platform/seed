import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { Subject, switchMap } from 'rxjs'
import type { Cycle, Organization } from '@seed/api'
import { AuditTemplateService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-audit-template-import-modal',
  templateUrl: './audit-template-import-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ProgressBarComponent, ReactiveFormsModule],
})
export class AuditTemplateImportModalComponent implements OnInit, OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _dialogRef = inject(MatDialogRef<AuditTemplateImportModalComponent>)
  private _auditTemplateService = inject(AuditTemplateService)
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewIds: number[]; org: Organization; cycles: Cycle[] }
  progressBarObj = this._uploaderService.defaultProgressBarObj
  cycleControl = new FormControl<number | null>(null)

  ngOnInit(): void {
    this.cycleControl.setValue(this.data.cycles[0]?.id ?? null)
  }

  onSubmit(): void {
    this.stepper.next()
    this._auditTemplateService
      .batchGetCitySubmissionXml(this.data.orgId, this.data.viewIds, this.cycleControl.value)
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn: () => {
              this._snackBar.success('Audit Template submissions imported successfully.')
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
