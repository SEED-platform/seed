import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective, TranslocoService } from '@jsverse/transloco'
import { Subject, switchMap, takeUntil } from 'rxjs'
import type { Cycle } from '@seed/api'
import { InventoryService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType, Profile, ProfileColumn } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-copy-to-cycle-modal',
  templateUrl: './copy-to-cycle-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent, TranslocoDirective],
})
export class CopyToCycleModalComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<CopyToCycleModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private _translocoService = inject(TranslocoService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
    cycles: Cycle[];
    profiles: Profile[];
    currentCycleId: number;
  }

  availableCycles: Cycle[] = []
  selectedCycleId: number | null = null
  selectedProfileId: number | null = null
  inProgress = false
  progressBarObj = this._uploaderService.defaultProgressBarObj

  ngOnInit(): void {
    this.availableCycles = this.data.cycles.filter((c) => c.id !== this.data.currentCycleId)
    if (this.data.profiles.length === 1) {
      this.selectedProfileId = this.data.profiles[0].id
    }
  }

  get listViewProfiles(): Profile[] {
    return this.data.profiles
  }

  get canSubmit(): boolean {
    return this.selectedCycleId !== null && this.selectedProfileId !== null && !this.inProgress
  }

  onSubmit(): void {
    if (!this.canSubmit) return

    this.inProgress = true

    this._inventoryService
      .getColumnListProfile(this.selectedProfileId)
      .pipe(
        switchMap((fullProfile) => {
          const columnIds = (fullProfile.columns ?? []).map((c: ProfileColumn) => c.id)
          return this._inventoryService.copyToCycle(this.data.orgId, this.selectedCycleId, this.data.viewIds, columnIds)
        }),
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn: () => {
              this._snackBar.success(this._translocoService.translate('Inventory copied to cycle successfully.'))
              this.close(true)
            },
            progressBarObj: this.progressBarObj,
          }),
        ),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe({
        error: () => {
          this.inProgress = false
        },
      })
  }

  close(success = false): void {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
