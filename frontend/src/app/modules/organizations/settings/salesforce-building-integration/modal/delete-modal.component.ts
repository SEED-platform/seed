import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { SalesforceMapping } from '@seed/api'
import { SalesforceService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-salesforce-delete-modal',
  templateUrl: './delete-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class DeleteModalComponent implements OnInit {
  private _salesforceService = inject(SalesforceService)
  private _dialogRef = inject(MatDialogRef<DeleteModalComponent>)
  columnName: string

  create = true
  data = inject(MAT_DIALOG_DATA) as { salesforceMapping: SalesforceMapping | null; columnName: string }
  salesforceMapping: SalesforceMapping

  ngOnInit(): void {
    this.salesforceMapping = this.data.salesforceMapping
    this.columnName = this.data.columnName
  }

  onSubmit() {
    this._salesforceService.deleteMapping(this.salesforceMapping).subscribe()
    this.close()
  }

  close() {
    this._dialogRef.close()
  }
}
