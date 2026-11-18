import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective, TranslocoService } from '@jsverse/transloco'
import { switchMap, take } from 'rxjs'
import type { ColumnMappingProfile } from '@seed/api'
import { ColumnMappingProfileService, InventoryService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-update-with-espm-modal',
  templateUrl: './update-with-espm-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ModalHeaderComponent, TranslocoDirective],
})
export class UpdateWithEspmModalComponent implements OnInit {
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialogRef = inject(MatDialogRef<UpdateWithEspmModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)
  private _translocoService = inject(TranslocoService)

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewId: number; cycleId: number; pmPropertyId: string }

  busy = false
  errorMessage: string | null = null
  profiles: ColumnMappingProfile[] = []
  selectedProfileId: number | null = null

  // File upload path
  xlsxFile: File | null = null

  // Direct ESPM path
  pmPropertyId = this.data.pmPropertyId ?? ''
  username = ''
  password = ''
  showPassword = false

  ngOnInit(): void {
    this._columnMappingProfileService
      .getProfiles(this.data.orgId)
      .pipe(take(1))
      .subscribe((profiles) => {
        this.profiles = profiles
        this.selectedProfileId = profiles[0]?.id ?? null
      })
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement
    this.xlsxFile = input.files?.[0] ?? null
  }

  uploadFile(): void {
    if (!this.xlsxFile || !this.selectedProfileId) return
    this.busy = true
    this.errorMessage = null
    this._inventoryService
      .updateWithEspm(this.data.orgId, this.data.viewId, this.data.cycleId, this.selectedProfileId, this.xlsxFile)
      .pipe(take(1))
      .subscribe({
        next: (result) => {
          this.handleResult(result)
        },
        error: () => {
          this.errorMessage = this._translocoService.translate('Error importing from ESPM.')
          this.busy = false
        },
      })
  }

  importFromEspm(): void {
    if (!this.pmPropertyId || !this.username || !this.password || !this.selectedProfileId) return
    this.busy = true
    this.errorMessage = null
    this._inventoryService
      .getEspmBuildingXlsx(this.data.orgId, this.pmPropertyId, this.username, this.password)
      .pipe(
        take(1),
        switchMap((fileData: ArrayBuffer) => {
          const blob = new Blob([fileData], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
          return this._inventoryService.updateWithEspm(this.data.orgId, this.data.viewId, this.data.cycleId, this.selectedProfileId, blob)
        }),
      )
      .subscribe({
        next: (result) => {
          this.handleResult(result)
        },
        error: () => {
          this.errorMessage = this._translocoService.translate('Error importing from ESPM.')
          this.busy = false
        },
      })
  }

  handleResult(result: { success: boolean; message?: string }): void {
    if (result?.success === false) {
      this.errorMessage = result.message ?? this._translocoService.translate('Error importing from ESPM.')
      this.busy = false
    } else {
      this._snackBar.success(this._translocoService.translate('Property updated from ESPM successfully.'))
      this._dialogRef.close(true)
    }
  }

  close(): void {
    this._dialogRef.close()
  }
}
