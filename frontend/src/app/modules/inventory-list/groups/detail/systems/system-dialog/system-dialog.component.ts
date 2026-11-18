import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { DesType, EvseType, GroupSystem, SystemType } from '@seed/api'
import { GroupsService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import type { SystemDialogData } from '../dialog-types'

@Component({
  selector: 'seed-system-dialog',
  templateUrl: './system-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports],
})
export class SystemDialogComponent {
  private _data = inject(MAT_DIALOG_DATA) as SystemDialogData
  private _dialogRef = inject(MatDialogRef<SystemDialogComponent>)
  private _groupsService = inject(GroupsService)

  action = this._data.action
  systemName = this._data.system?.name ?? ''
  systemType: SystemType = (this._data.system?.type as SystemType) ?? 'DES'
  desType: DesType = (this._data.system?.des_type as DesType) ?? 'Boiler'
  evseType: EvseType = (this._data.system?.evse_type as EvseType) ?? 'Level1-120V'
  coolingCapacity: number | null = this._data.system?.cooling_capacity ?? null
  heatingCapacity: number | null = this._data.system?.heating_capacity ?? null
  count = this._data.system?.count ?? 1
  power: number | null = this._data.system?.power ?? null
  voltage: number | null = this._data.system?.voltage ?? null
  efficiency: number | null = this._data.system?.efficiency ?? null
  powerCapacity: number | null = this._data.system?.power_capacity ?? null
  energyCapacity: number | null = this._data.system?.energy_capacity ?? null
  submitted = false
  isEdit = this._data.action === 'edit'

  systemTypes: SystemType[] = ['DES', 'EVSE', 'Battery', 'Aggregate Meter']
  desTypes: DesType[] = ['Boiler', 'Chiller', 'CHP']
  evseTypes: EvseType[] = ['Level1-120V', 'Level2-240V', 'Level3-DC Fast']

  get title(): string {
    if (this.action === 'create') return 'Create System'
    if (this.action === 'edit') return 'Edit System'
    return 'Delete System'
  }

  get isValid(): boolean {
    if (!this.systemName.trim()) return false
    if (this.systemType === 'EVSE') return this.power != null && this.voltage != null
    if (this.systemType === 'Battery') {
      return this.efficiency != null && this.powerCapacity != null && this.energyCapacity != null && this.voltage != null
    }
    return true
  }

  save() {
    if (this.submitted) return
    this.submitted = true

    const payload: Partial<GroupSystem> = { name: this.systemName.trim() }

    // Backend needs `type` for both create and update to resolve the model class
    payload.type = this.systemType

    if (this.systemType === 'DES') {
      payload.des_type = this.desType
      payload.count = this.count
      payload.cooling_capacity = this.desType === 'Chiller' ? this.coolingCapacity : null
      payload.heating_capacity = this.desType !== 'Chiller' ? this.heatingCapacity : null
    } else if (this.systemType === 'EVSE') {
      payload.evse_type = this.evseType
      payload.power = this.power
      payload.voltage = this.voltage
      payload.count = this.count
    } else if (this.systemType === 'Battery') {
      payload.efficiency = this.efficiency
      payload.power_capacity = this.powerCapacity
      payload.energy_capacity = this.energyCapacity
      payload.voltage = this.voltage
    }

    const systemId = this._data.system?.id
    const obs
      = this.action === 'create'
        ? this._groupsService.createSystem(this._data.orgId, this._data.groupId, payload)
        : this._groupsService.updateSystem(this._data.orgId, this._data.groupId, systemId, payload)

    obs.subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: () => {
        this.submitted = false
      },
    })
  }

  deleteSystem() {
    if (this.submitted) return
    this.submitted = true
    const systemId = this._data.system?.id
    this._groupsService.deleteSystem(this._data.orgId, this._data.groupId, systemId).subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: () => {
        this.submitted = false
      },
    })
  }
}
