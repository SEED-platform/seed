import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { GroupsService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import type { ServiceDialogData } from '../dialog-types'

@Component({
  selector: 'seed-service-dialog',
  templateUrl: './service-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports],
})
export class ServiceDialogComponent {
  private _data = inject(MAT_DIALOG_DATA) as ServiceDialogData
  private _dialogRef = inject(MatDialogRef<ServiceDialogComponent>)
  private _groupsService = inject(GroupsService)

  action = this._data.action
  systemName = this._data.systemName
  serviceName = this._data.service?.name ?? ''
  emissionFactor: number | null = this._data.service?.emission_factor ?? null
  submitted = false

  get title(): string {
    if (this.action === 'create') return `Create Service for ${this.systemName}`
    if (this.action === 'edit') return `Edit Service for ${this.systemName}`
    return `Delete Service for ${this.systemName}`
  }

  get isValid(): boolean {
    return this.serviceName.trim().length > 0
  }

  save() {
    if (this.submitted) return
    this.submitted = true

    const payload = {
      name: this.serviceName.trim(),
      emission_factor: this.emissionFactor,
      system_id: this._data.systemId,
    }

    const serviceId = this._data.service?.id
    const obs
      = this.action === 'create'
        ? this._groupsService.createService(this._data.orgId, this._data.groupId, this._data.systemId, payload)
        : this._groupsService.updateService(this._data.orgId, this._data.groupId, this._data.systemId, serviceId, payload)

    obs.subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: () => {
        this.submitted = false
      },
    })
  }

  deleteService() {
    if (this.submitted) return
    this.submitted = true
    const serviceId = this._data.service?.id
    this._groupsService.deleteService(this._data.orgId, this._data.groupId, this._data.systemId, serviceId).subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: () => {
        this.submitted = false
      },
    })
  }
}
