import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { InventoryService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import type { PropertyDocumentExtension, PropertyDocumentType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-detail-document-upload',
  templateUrl: './document-upload.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class DocumentUploadModalComponent {
  private _dialogRef = inject(MatDialogRef<DocumentUploadModalComponent>)
  private _inventoryService = inject(InventoryService)
  readonly allowedTypes = ['application/pdf', 'application/dxf', 'text/plain', 'application/octet-stream']
  file?: File

  extMap: Record<PropertyDocumentType, PropertyDocumentExtension> = {
    'application/pdf': 'PDF',
    'application/dxf': 'DXF',
    'text/plain': 'IDF',
    'application/octet-stream': 'OSM',
  }

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewId: number }

  onUpload() {
    if (!this.file) return
    const fileExt = this.extMap[this.file.type as PropertyDocumentType]
    this._inventoryService.uploadPropertyDocument(this.data.orgId, this.data.viewId, this.file, fileExt).subscribe(() => {
      this.dismiss()
    })
  }

  onSelectFile(fileList: FileList): Promise<void> {
    if (fileList.length === 0) {
      return
    }

    const [file] = fileList
    if (!this.allowedTypes.includes(file.type)) {
      return
    }
    this.file = file
  }

  dismiss() {
    this._dialogRef.close()
  }
}
