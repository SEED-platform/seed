import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { finalize, Subject, tap } from 'rxjs'
import { InventoryService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-femp-export-modal',
  templateUrl: './femp-export-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class FempExportModalComponent implements OnDestroy {
  private _dialog = inject(MatDialogRef<FempExportModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)
  private _unsubscribeAll$ = new Subject<void>()

  exportType: 'evaluation' | 'facility' = 'evaluation'
  filename = ''
  inProgress = false

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
  }

  setExportType(type: 'evaluation' | 'facility'): void {
    this.exportType = type
  }

  onSubmit() {
    const filename = this.filename.trim()
    if (!filename) return
    const downloadFilename = filename.toLowerCase().endsWith('.xlsx') ? filename : `${filename}.xlsx`
    this.inProgress = true
    const exportRequest
      = this.exportType === 'evaluation'
        ? this._inventoryService.evaluationExportToCts(this.data.orgId, this.data.viewIds, downloadFilename)
        : this._inventoryService.facilityBpsExportToCts(this.data.orgId, this.data.viewIds, downloadFilename)

    exportRequest
      .pipe(
        tap((response) => {
          this.downloadData(response, downloadFilename)
        }),
        finalize(() => {
          this.inProgress = false
          this.close()
        }),
      )
      .subscribe()
  }

  downloadData(data: Blob, filename: string) {
    const a = document.createElement('a')
    const url = URL.createObjectURL(data)
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    this._snackBar.success(`Exported ${filename}`)
  }

  close(): void {
    this._dialog.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
