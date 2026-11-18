import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { Column, ColumnMapping, ColumnMappingProfile } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'
import { SeedHeaderAutocompleteComponent } from './seed-header-autocomplete.component'

@Component({
  selector: 'seed-column-mappings-edit-modal',
  templateUrl: './edit-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule, SeedHeaderAutocompleteComponent],
})
export class EditModalComponent implements OnInit {
  private _dialogRef = inject(MatDialogRef<EditModalComponent>)
  errorMessage: string
  inProgress = false
  mapping: ColumnMapping
  profile: ColumnMappingProfile
  columns: Column[]
  from_fields: string[]
  form = new FormGroup({
    is_omitted: new FormControl<boolean | null>(null),
    to_table_name: new FormControl('', [Validators.required]),
    to_field: new FormControl('', []),
    from_field: new FormControl('', []),
    from_units: new FormControl(''),
  })
  data = inject(MAT_DIALOG_DATA) as { mapping: ColumnMapping; org_id: number; columns: Column[]; profile: ColumnMappingProfile }

  ngOnInit(): void {
    this.mapping = this.data.mapping
    this.columns = this.data.columns
    this.profile = this.data.profile
    this.from_fields = this.profile.mappings
      .filter((m) => {
        if (
          m.from_field === this.mapping.from_field
          && m.to_field === this.mapping.to_field
          && m.to_table_name === this.mapping.to_table_name
        ) {
          return false
        } else {
          return true
        }
      })
      .map((m) => m.from_field)
    this.form.get('to_field').disable()
    this.form.get('to_table_name').valueChanges.subscribe((val) => {
      if (val) {
        this.form.get('to_field').enable()
      }
    })
    this.form.get('is_omitted').valueChanges.subscribe((val) => {
      if (!val) {
        this.form.get('to_field').setValidators(Validators.required)
      } else {
        this.form.get('to_field').clearValidators()
      }
    })
    this.form.get('to_field').valueChanges.subscribe((val) => {
      this.setMeasurementSelect(val)
    })
    this.form.get('from_field').setValidators([Validators.required, SEEDValidators.uniqueValue(this.from_fields)])
    this.form.patchValue(this.mapping)
  }

  onSubmit() {
    this._dialogRef.close(this.form.value)
  }

  close() {
    this._dialogRef.close()
  }

  readonly(): boolean {
    if (this.profile && this.profile.profile_type !== 'Normal') {
      return true
    } else {
      return false
    }
  }

  getColumn(to_field: string): Column | null {
    return this.columns.find((c) => c.column_name === to_field)
  }

  setMeasurementSelect(field: string): void {
    const col = this.getColumn(field)
    if (!col) {
      return null
    }
    if (['area', 'eui', 'ghg', 'wui', 'ghg_intensity', 'water_use'].includes(col.data_type)) {
      this.form.get('from_units').enable()
      this.form.get('from_units').setValidators(Validators.required)
    } else {
      this.form.get('from_units').disable()
      this.form.get('from_units').clearValidators()
    }
  }

  unitSelections() {
    const col = this.columns.find((c) => c.column_name === this.form.get('to_field').value)
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
