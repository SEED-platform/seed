import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { GroupMeterConfig, GroupService, GroupSystem } from '@seed/api'
import { GroupsService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

export type EditMeterDialogData = {
  orgId: number;
  groupId: number;
  meter: {
    id: number;
    alias: string;
    connection_type: string;
    property_id: number | null;
    property_display_field: string | null;
    system_id: number | null;
    service_id: number | null;
    config: GroupMeterConfig;
  };
}

@Component({
  selector: 'seed-edit-meter-dialog',
  templateUrl: './edit-meter-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports],
})
export class EditMeterDialogComponent implements OnInit {
  private _data = inject(MAT_DIALOG_DATA) as EditMeterDialogData
  private _dialogRef = inject(MatDialogRef<EditMeterDialogComponent>)
  private _groupsService = inject(GroupsService)

  meter = this._data.meter
  alias = this._data.meter.alias ?? ''
  direction: 'imported' | 'exported' = this._data.meter.config?.direction ?? 'imported'
  connection: 'outside' | 'service' = this._data.meter.config?.connection ?? 'outside'
  use: 'using' | 'offering' | null = this._data.meter.config?.use !== 'outside' ? (this._data.meter.config?.use ?? null) : null
  selectedSystemId: number | null = this._data.meter.config?.system_id ?? null
  selectedServiceId: number | null = this._data.meter.config?.service_id ?? null

  systemOptions: GroupSystem[] = []
  serviceOptions: GroupService[] = []
  useOptions: { value: string; display: string }[] = [{ value: 'using', display: 'Using a Service' }]

  loading = true
  submitted = false
  error = ''

  // Property meters can't change "use" — it's always "using"
  get isPropertyMeter(): boolean {
    return !!this._data.meter.property_id
  }

  // System meters can also "offer" a service
  get isSystemMeter(): boolean {
    return !!this._data.meter.system_id
  }

  ngOnInit() {
    if (this.isSystemMeter) {
      this.useOptions.push({ value: 'offering', display: 'Offering a Service (Total)' })
    }

    // Fetch the current group to get its systems/services
    this._groupsService.get(this._data.orgId, this._data.groupId).subscribe((group) => {
      this.systemOptions = group.systems ?? []
      // Pre-populate service options from config
      if (this.selectedSystemId) {
        this.onSystemSelected(false)
      }
      this.loading = false
    })
  }

  onConnectionChanged() {
    this.use = null
    this.selectedSystemId = null
    this.selectedServiceId = null
    this.serviceOptions = []
    this.error = ''

    if (this.connection === 'service' && this.isPropertyMeter) {
      this.use = 'using'
    }
  }

  onUseSelected(reset = true) {
    if (reset) {
      this.selectedSystemId = null
      this.selectedServiceId = null
      this.serviceOptions = []
    }

    // If "offering", system is already known
    if (this.isSystemMeter && this.use === 'offering') {
      this.selectedSystemId = this._data.meter.system_id
      this.onSystemSelected(reset)
    }
  }

  onSystemSelected(reset = true) {
    if (reset) {
      this.selectedServiceId = null
    }
    const system = this.systemOptions.find((s) => s.id === this.selectedSystemId)
    this.serviceOptions = system?.services ?? []
  }

  get formValid(): boolean {
    if (!this.direction) return false
    if (this.connection === 'outside') return true
    return !!this.use && !!this.selectedSystemId && !!this.selectedServiceId
  }

  save() {
    if (this.submitted || !this.formValid) return
    this.submitted = true
    this.error = ''

    const config: Record<string, unknown> = {
      direction: this.direction,
      use: this.connection === 'outside' ? 'outside' : this.use,
    }

    if (this.connection === 'service' && this.selectedServiceId) {
      config.service_id = this.selectedServiceId
    }

    const payload: { alias?: string; connection_config: Record<string, unknown> } = { connection_config: config }
    if (this.alias !== this._data.meter.alias) {
      payload.alias = this.alias
    }

    this._groupsService.updateMeter(this._data.orgId, this._data.groupId, this._data.meter.id, payload).subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: () => {
        this.submitted = false
      },
    })
  }
}
