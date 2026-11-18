import { CommonModule } from '@angular/common'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { finalize } from 'rxjs'
import { OrganizationService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { DeleteInstanceData } from '..'

@Component({
  selector: 'seed-delete-instance-dialog',
  templateUrl: './delete-instance-dialog.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports, SharedImports],
})
export class DeleteInstanceDialogComponent {
  private _data = inject(MAT_DIALOG_DATA) as DeleteInstanceData
  private _dialogRef = inject(MatDialogRef<DeleteInstanceDialogComponent>)
  private _organizationService = inject(OrganizationService)

  readonly instance = this._data.instance
  readonly warnings = this._data.warnings
  submitted = false

  delete() {
    if (!this.submitted) {
      this.submitted = true
      this._organizationService
        .deleteAccessLevelInstance(this._data.organizationId, this._data.instance.id)
        .pipe(
          finalize(() => {
            this._dialogRef.close()
          }),
        )
        .subscribe()
    } else {
      this._dialogRef.close()
    }
  }
}
