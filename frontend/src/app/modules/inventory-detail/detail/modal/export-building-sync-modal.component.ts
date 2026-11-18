import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { take } from 'rxjs'
import type { ColumnMappingProfile } from '@seed/api'
import { ColumnMappingProfileService, InventoryService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-export-building-sync-modal',
  templateUrl: './export-building-sync-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ModalHeaderComponent],
})
export class ExportBuildingSyncModalComponent implements OnInit {
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialogRef = inject(MatDialogRef<ExportBuildingSyncModalComponent>)
  private _inventoryService = inject(InventoryService)

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewId: number }

  downloading = false
  errorMessage: string | null = null
  profiles: ColumnMappingProfile[] = []
  selectedProfileId: number | null = null

  ngOnInit(): void {
    this._columnMappingProfileService
      .getProfiles(this.data.orgId, ['BuildingSync Default', 'BuildingSync Custom'])
      .pipe(take(1))
      .subscribe((profiles) => {
        this.profiles = profiles
        this.selectedProfileId = profiles[0]?.id ?? null
      })
  }

  download(): void {
    if (!this.selectedProfileId) return
    this.downloading = true
    this.errorMessage = null
    this._inventoryService
      .getBuildingSync(this.data.orgId, this.data.viewId, this.selectedProfileId)
      .pipe(take(1))
      .subscribe({
        next: (xml) => {
          const blob = new Blob([xml], { type: 'application/xml;charset=utf-8;' })
          const a = document.createElement('a')
          a.href = URL.createObjectURL(blob)
          a.download = `buildingsync_property_${this.data.viewId}.xml`
          a.click()
          URL.revokeObjectURL(a.href)
          this.close()
        },
        error: () => {
          this.errorMessage = 'Error downloading BuildingSync file.'
          this.downloading = false
        },
      })
  }

  close(): void {
    this._dialogRef.close()
  }
}
