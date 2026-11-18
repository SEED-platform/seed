import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import { take } from 'rxjs'
import { ColumnService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-columns-create-modal',
  templateUrl: './create-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, TranslocoDirective],
})
export class CreateColumnModalComponent {
  private _dialogRef = inject(MatDialogRef<CreateColumnModalComponent>)
  private _columnService = inject(ColumnService)
  private _snackBar = inject(SnackBarService)

  data = inject(MAT_DIALOG_DATA) as { orgId: number; tableName: string; existingNames: string[] }

  columnName = ''
  inProgress = false

  get isDuplicate(): boolean {
    return this.data.existingNames.includes(this.columnName.trim())
  }

  get isValid(): boolean {
    return this.columnName.trim().length > 0 && !this.isDuplicate
  }

  create(): void {
    if (!this.isValid) return
    this.inProgress = true
    this._columnService
      .createColumn(this.data.orgId, this.columnName.trim(), this.data.tableName)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this._snackBar.success(`Column "${this.columnName.trim()}" created.`)
          this._dialogRef.close(true)
        },
        error: () => {
          this.inProgress = false
        },
      })
  }

  close(): void {
    this._dialogRef.close()
  }
}
