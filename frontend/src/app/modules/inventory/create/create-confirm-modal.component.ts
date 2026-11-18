import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoPipe } from '@jsverse/transloco'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-inventory-create-confirm-modal',
  templateUrl: './create-confirm-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, TranslocoPipe],
})
export class CreateConfirmModalComponent {
  private _dialogRef = inject(MatDialogRef<CreateConfirmModalComponent>)
  data = inject(MAT_DIALOG_DATA) as { title: string; body: string; confirmText: string; confirmIcon: string }

  onSubmit() {
    this.close(true)
  }

  close(confirmed = false) {
    this._dialogRef.close(confirmed)
  }
}
