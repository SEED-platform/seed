import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { MaterialImports } from '@seed/materials'
import { ModalHeaderComponent } from '../modal'

@Component({
  standalone: true,
  selector: 'seed-delete-modal',
  templateUrl: './delete-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent],
})
export class DeleteModalComponent {
  private _dialogRef = inject(MatDialogRef<DeleteModalComponent>)
  data = inject(MAT_DIALOG_DATA) as { instance: string; model: string }

  onSubmit() {
    this.close(true)
  }

  close(success = false) {
    this._dialogRef.close(success)
  }
}
