import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { Subject, switchMap } from 'rxjs'
import { InventoryService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-update-derived-data',
  templateUrl: './update-derived-data.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class UpdateDerivedDataComponent implements OnInit, OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _dialogRef = inject(MatDialogRef<UpdateDerivedDataComponent>)
  private _inventoryService = inject(InventoryService)
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  propertyViewIds: number[] = []
  taxlotViewIds: number[] = []
  inProgress = false
  progressBarObj = this._uploaderService.defaultProgressBarObj

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewIds: number[]; type: string }

  ngOnInit(): void {
    const target = this.data.type === 'properties' ? 'propertyViewIds' : 'taxlotViewIds'
    this[target] = this.data.viewIds
  }

  onSubmit() {
    const successFn = () => {
      this._snackBar.success('Derived data updated successfully.')
      this.close(true)
    }

    this.stepper.next()
    this._inventoryService
      .updateDerivedData(this.data.orgId, this.propertyViewIds, this.taxlotViewIds)
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            progressBarObj: this.progressBarObj,
          }),
        ),
      )
      .subscribe()
  }

  close(success = false) {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
