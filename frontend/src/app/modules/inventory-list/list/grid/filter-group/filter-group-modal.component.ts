import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

export type FilterGroupModalAction = 'new' | 'rename' | 'delete'

export type FilterGroupModalData = {
  action: FilterGroupModalAction;
  name?: string;
}

@Component({
  selector: 'seed-filter-group-modal',
  templateUrl: './filter-group-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ModalHeaderComponent],
})
export class FilterGroupModalComponent {
  private _dialogRef = inject(MatDialogRef<FilterGroupModalComponent>)
  data = inject(MAT_DIALOG_DATA) as FilterGroupModalData

  name = this.data.name ?? ''

  get title(): string {
    switch (this.data.action) {
      case 'new':
        return 'New Filter Group'
      case 'rename':
        return 'Rename Filter Group'
      case 'delete':
        return 'Delete Filter Group'
    }
  }

  get isValid(): boolean {
    return this.name.trim().length > 0
  }

  onSubmit() {
    if (this.data.action === 'delete') {
      this._dialogRef.close(true)
    } else if (this.isValid) {
      this._dialogRef.close(this.name.trim())
    }
  }

  close() {
    this._dialogRef.close(null)
  }
}
