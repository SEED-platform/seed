import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { Column, RenameColumnResponse } from '@seed/api'
import { ColumnService } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-columns-rename-modal',
  templateUrl: './rename-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports],
})
export class RenameModalComponent {
  private _dialogRef = inject(MatDialogRef<RenameModalComponent>)
  private _columnService = inject(ColumnService)
  private _snackBar = inject(SnackBarService)

  data = inject(MAT_DIALOG_DATA) as { column: Column; allColumnNames: string[] }

  step = 1
  newName = ''
  nameExists = false
  userAcknowledgement = false
  overwritePreference = false
  inProgress = false
  result: RenameColumnResponse | null = null

  checkNameExists() {
    this.nameExists = this.data.allColumnNames.includes(this.newName)
    if (!this.nameExists) {
      this.overwritePreference = false
    }
  }

  isValid(): boolean {
    if (!this.newName || this.newName === this.data.column.column_name) return false
    if (this.nameExists) return this.userAcknowledgement && this.overwritePreference
    return this.userAcknowledgement
  }

  onSubmit() {
    this.inProgress = true
    this._columnService
      .renameColumn(this.data.column.organization_id, this.data.column.id, this.newName, this.overwritePreference)
      .subscribe({
        next: (response) => {
          this.result = response
          this.step = 2
          this.inProgress = false
          if (response.success) {
            this._snackBar.success('Column renamed successfully')
          }
        },
        error: () => {
          this.inProgress = false
          this._snackBar.alert('Failed to rename column')
        },
      })
  }

  close(refresh = false) {
    this._dialogRef.close(refresh)
  }
}
