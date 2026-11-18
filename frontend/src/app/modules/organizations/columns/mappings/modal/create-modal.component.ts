import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { map } from 'rxjs'
import type { Column, ColumnMapping, ColumnMappingProfile } from '@seed/api'
import { ColumnMappingProfileService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SeedHeaderAutocompleteComponent } from './seed-header-autocomplete.component'

@Component({
  selector: 'seed-column-mappings-create-modal',
  templateUrl: './create-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule, SharedImports, SeedHeaderAutocompleteComponent],
})
export class CreateModalComponent implements OnInit {
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialogRef = inject(MatDialogRef<CreateModalComponent>)
  errorMessage: string
  inProgress = false
  profile: ColumnMappingProfile
  form = new FormGroup({
    name: new FormControl('', [Validators.required]),
    mappings: new FormArray([]),
  })
  columns: Column[]
  data = inject(MAT_DIALOG_DATA) as { org_id: number; columns: Column[] }

  ngOnInit(): void {
    this.profile = { profile_type: 'Normal', name: '', id: null, mappings: [] }
    this.profile.mappings = []
    this.columns = this.data.columns
    this.addMapping()
  }

  getToField(index: number) {
    const group = this.form.controls.mappings.controls[index] as FormGroup
    return group.controls.to_field as FormControl
  }

  getTableName(index: number): string {
    const group = this.form.controls.mappings.controls[index] as FormGroup
    const control = group.controls.to_table_name as FormControl
    return control.value as string
  }

  onSubmit() {
    this.profile.name = this.form.get('name').value
    for (const m of this.mappings.controls) {
      this.addToMapping(m as FormGroup)
    }
    this._columnMappingProfileService
      .create(this.data.org_id, this.profile)
      .pipe(
        map((response) => {
          this._dialogRef.close(response.data.id)
        }),
      )
      .subscribe()
  }

  close() {
    this._dialogRef.close()
  }

  get mappings() {
    return this.form.get('mappings') as FormArray
  }

  addMapping() {
    const mapping = new FormGroup({
      to_table_name: new FormControl('PropertyState', [Validators.required]),
      to_field: new FormControl('', []),
      from_field: new FormControl('', [Validators.required]),
      from_units: new FormControl(''),
    })
    mapping.get('from_units').disable()
    mapping.get('to_field').valueChanges.subscribe((val) => {
      this.setMeasurementSelect(mapping, val)
    })
    this.mappings.push(mapping)
  }

  setMeasurementSelect(mapping: FormGroup, field: string): void {
    const col = this.columns.find((c) => c.table_name === (mapping.get('to_table_name').value as string) && c.column_name === field)
    if (!col) {
      return null
    }
    if (['area', 'eui', 'ghg', 'wui', 'ghg_intensity', 'water_use'].includes(col.data_type)) {
      mapping.get('from_units').enable()
      mapping.get('from_units').setValidators(Validators.required)
    } else {
      mapping.get('from_units').disable()
      mapping.get('from_units').clearValidators()
    }
  }

  removeMapping(index: number) {
    this.mappings.removeAt(index)
  }

  addToMapping(f: FormGroup) {
    const mapping: ColumnMapping = {
      from_field: f.get('from_field').value as string,
      to_field: f.get('to_field').value as string,
      to_table_name: f.get('to_table_name').value as 'PropertyState' | 'TaxLotState',
      from_units: f.get('from_units').value as string,
      is_omitted: false,
    }
    this.profile.mappings.push(mapping)
  }

  unitSelections(index: number) {
    const mapping = this.form.controls.mappings.controls[index] as FormGroup
    const col = this.columns.find(
      (c) => c.table_name === mapping.get('to_table_name').value && c.column_name === mapping.get('to_field').value,
    )
    if (!col) {
      return []
    }
    switch (col.data_type) {
      case 'area':
        return [
          { id: 'ft**2', value: 'square feet' },
          { id: 'm**2', value: 'square metres' },
        ]
      case 'eui':
        return [
          { id: 'kBtu/ft**2/year', value: 'kBtu/ft²/year' },
          { id: 'kWh/m**2/year', value: 'kWh/m²/year' },
          { id: 'GJ/m**2/year', value: 'GJ/m²/year' },
          { id: 'MJ/m**2/year', value: 'MJ/m²/year' },
          { id: 'kBtu/m**2/year', value: 'kBtu/m²/year' },
        ]
      case 'ghg':
        return [
          { id: 'MtCO2e/year', value: 'MtCO2e/year' },
          { id: 'kgCO2e/year', value: 'kgCO2e/year' },
        ]
      case 'wui':
        return [
          { id: 'kgal/ft**2/year', value: 'kgal/ft²/year' },
          { id: 'gal/ft**2/year', value: 'gal/ft²/year' },
          { id: 'L/m**2/year', value: 'L/m²/year' },
        ]
      case 'ghg_intensity':
        return [
          { id: 'MtCO2e/ft**2/year', value: 'MtCO2e/ft²/year' },
          { id: 'kgCO2e/ft**2/year', value: 'kgCO2e/ft²/year' },
          { id: 'MtCO2e/m**2/year', value: 'MtCO2e/m²/year' },
          { id: 'kgCO2e/m**2/year', value: 'kgCO2e/m²/year' },
        ]
      case 'water_use':
        return [
          { id: 'kgal/year', value: 'kgal/year' },
          { id: 'gal/year', value: 'gal/year' },
          { id: 'L/year', value: 'L/year' },
        ]
      default:
        return []
    }
  }
}
