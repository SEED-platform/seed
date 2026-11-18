import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { take } from 'rxjs'
import { InventoryService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-update-with-building-sync-modal',
  templateUrl: './update-with-building-sync-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, MaterialImports, ModalHeaderComponent],
})
export class UpdateWithBuildingSyncModalComponent {
  private _dialogRef = inject(MatDialogRef<UpdateWithBuildingSyncModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewId: number; cycleId: number }

  errorMessage: string | null = null
  file: File | null = null
  uploading = false

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement
    this.file = input.files?.[0] ?? null
  }

  upload(): void {
    if (!this.file) return
    this.uploading = true
    this.errorMessage = null
    this._inventoryService
      .updateWithBuildingSync(this.data.orgId, this.data.viewId, this.data.cycleId, this.file)
      .pipe(take(1))
      .subscribe({
        next: (result) => {
          this._snackBar.success(result.message ?? 'Property updated with BuildingSync successfully.')
          this._dialogRef.close(true)
        },
        error: () => {
          this.errorMessage = 'Error updating property with BuildingSync file.'
          this.uploading = false
        },
      })
  }

  close(): void {
    this._dialogRef.close()
  }
}
