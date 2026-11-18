import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { Subject, takeUntil } from 'rxjs'
import type { MeterWithUnits, Organization } from '@seed/api'
import { MeterTypesService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import * as UnitOptions from './units.types'

@Component({
  selector: 'seed-organizations-settings-display-units',
  templateUrl: './display-units.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, ReactiveFormsModule, SharedImports],
})
export class DisplayUnitsComponent implements OnDestroy, OnInit {
  private _organizationService = inject(OrganizationService)
  private _meterTypesService = inject(MeterTypesService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  betterVerifiedIcon = ''
  betterVerifiedIconColor = 'primary'
  organization: Organization
  options = UnitOptions
  unitsForm = new FormGroup({
    display_units_eui: new FormControl('', Validators.required),
    display_units_ghg: new FormControl('', Validators.required),
    display_units_ghg_intensity: new FormControl('', Validators.required),
    display_units_water_use: new FormControl('', Validators.required),
    display_units_wui: new FormControl('', Validators.required),
    display_units_area: new FormControl('', Validators.required),
    display_decimal_places: new FormControl(0, Validators.required),
    thermal_conversion_assumption: new FormControl(1, [Validators.min(1), Validators.max(2)]),
  })
  energyMeterForm = new FormGroup({})
  waterMeterForm = new FormGroup({})
  waterMeters: MeterWithUnits[]
  energyMeters: MeterWithUnits[]

  ngOnInit(): void {
    this._organizationService.currentOrganization$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organization) => {
      this.organization = organization
      for (const field of Object.keys(this.unitsForm.controls)) {
        this.unitsForm.get(field).setValue(this.organization[field])
      }
      for (const emu of Object.keys(this.organization.display_meter_units)) {
        this.energyMeterForm.addControl(emu, new FormControl(this.organization.display_meter_units[emu], Validators.required))
      }
      for (const wmu of Object.keys(this.organization.display_meter_water_units)) {
        this.waterMeterForm.addControl(wmu, new FormControl(this.organization.display_meter_water_units[wmu], Validators.required))
      }
    })
    this._meterTypesService.energyMeters$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((energyMeters) => {
      this.energyMeters = energyMeters
    })
    this._meterTypesService.waterMeters$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((waterMeters) => {
      this.waterMeters = waterMeters
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  energyMeterFields(): string[] {
    return Object.keys(this.energyMeterForm.controls)
  }

  waterMeterFields(): string[] {
    return Object.keys(this.waterMeterForm.controls)
  }

  energyUnitsFor(field): string[] {
    if (!this.energyMeters) {
      return []
    }
    const e = this.energyMeters.find((e) => e.name === field)
    if (e) {
      return e.units
    } else {
      console.log('could not find field ', field)
      return []
    }
  }

  waterUnitsFor(field): string[] {
    if (!this.waterMeters) {
      return []
    }
    const w = this.waterMeters.find((w) => w.name === field)
    if (w) {
      return w.units
    } else {
      console.log('could not find field ', field)
      return []
    }
  }

  submit(): void {
    if (this.unitsForm.valid) {
      this.organization.display_units_eui = this.unitsForm.get('display_units_eui').value
      this.organization.display_units_ghg = this.unitsForm.get('display_units_ghg').value
      this.organization.display_units_ghg_intensity = this.unitsForm.get('display_units_ghg_intensity').value
      this.organization.display_units_water_use = this.unitsForm.get('display_units_water_use').value
      this.organization.display_units_wui = this.unitsForm.get('display_units_wui').value
      this.organization.display_units_area = this.unitsForm.get('display_units_area').value
      this.organization.display_decimal_places = this.unitsForm.get('display_decimal_places').value
      this.organization.thermal_conversion_assumption = this.unitsForm.get('thermal_conversion_assumption').value
      this.submitEnergyMeters()
      this.submitWaterMeters()
      this._organizationService.updateSettings(this.organization).subscribe()
    }
  }

  submitEnergyMeters(): void {
    if (this.energyMeterForm.valid) {
      for (const field of this.energyMeterFields()) {
        const control = this.energyMeterForm.controls[field] as FormControl
        this.organization.display_meter_units[field] = control.value as string
      }
    }
  }

  submitWaterMeters(): void {
    if (this.waterMeterForm.valid) {
      for (const field of this.waterMeterFields()) {
        const control = this.waterMeterForm.controls[field] as FormControl
        this.organization.display_meter_water_units[field] = control.value as string
      }
    }
  }
}
