import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import { take } from 'rxjs'
import type { FacilitiesPlanRun } from '@seed/api'
import { FacilitiesPlanRunService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-facilities-plan-delete-modal',
  templateUrl: './delete-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, TranslocoDirective],
})
export class DeleteModalComponent {
  private _dialogRef = inject(MatDialogRef<DeleteModalComponent>)
  private _facilitiesPlanRunService = inject(FacilitiesPlanRunService)

  data = inject(MAT_DIALOG_DATA) as { run: FacilitiesPlanRun }
  isDeleting = false

  delete(): void {
    this.isDeleting = true
    this._facilitiesPlanRunService
      .delete(this.data.run.id)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this._dialogRef.close(true)
        },
        error: () => {
          this.isDeleting = false
        },
      })
  }

  close(): void {
    this._dialogRef.close(false)
  }
}
