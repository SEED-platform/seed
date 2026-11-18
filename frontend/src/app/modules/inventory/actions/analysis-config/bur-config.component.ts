import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { Subject, takeUntil, tap } from 'rxjs'
import type { Column } from '@seed/api'
import { ColumnService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'

@Component({
  selector: 'seed-bur-config',
  templateUrl: './bur-config.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FormsModule, MaterialImports, ReactiveFormsModule],
})
// BUR: Building Upgrade Recommendation
export class BurConfigComponent implements OnInit, OnDestroy {
  @Input() orgId: number
  @Output() formChange = new EventEmitter<FormGroup>()
  private _columnService = inject(ColumnService)
  private _unsubscribeAll$ = new Subject<void>()
  propertyColumns: Column[] = []

  fields: {
    name: string;
    label: string;
    hint?: string;
    type: 'number' | 'select';
    options?: Column[];
    group?: string;
    control: FormControl<number | null>;
  }[]
  form = new FormGroup({
    column_params: new FormGroup({
      total_eui: new FormControl<number | null>(null, Validators.required),
      gas_eui: new FormControl<number | null>(null, Validators.required),
      electric_eui: new FormControl<number | null>(null, Validators.required),
      target_gas_eui: new FormControl<number | null>(null, Validators.required),
      target_electric_eui: new FormControl<number | null>(null, Validators.required),
      condition_index: new FormControl<number | null>(null, Validators.required),
      has_bas: new FormControl<number | null>(null, Validators.required),
    }),
    total_eui_goal: new FormControl(40),
    ff_eui_goal: new FormControl(20),
    year_built_threshold: new FormControl(2008),
    fair_actual_to_benchmark_eui_ratio: new FormControl(1.2),
    poor_actual_to_benchmark_eui_ratio: new FormControl(1.3),
    building_sqft_threshold: new FormControl(10000),
    condition_index_threshold: new FormControl(90),
    ff_fired_equipment_rsl_threshold: new FormControl(15),
  })

  ngOnInit(): void {
    this.getColumns()
      .pipe(
        tap(() => {
          this.setForm()
          this.watchForm()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  getColumns() {
    return this._columnService.propertyColumns$.pipe(
      tap(
        (propertyColumns) =>
          (this.propertyColumns = propertyColumns
            .filter((c) => c.table_name === 'PropertyState')
            .sort((a, b) => naturalSort(a.display_name, b.display_name))),
      ),
      takeUntil(this._unsubscribeAll$),
    )
  }

  setForm() {
    this.fields = [
      // column param fields
      {
        name: 'total_eui',
        label: 'Total EUI Column',
        type: 'select',
        options: this.propertyColumns.filter((c) => c.data_type === 'eui'),
        group: 'column_params',
        control: this.form.get('column_params.total_eui') as FormControl<number>,
      },
      {
        name: 'gas_eui',
        label: 'Gas EUI Column',
        type: 'select',
        options: this.propertyColumns.filter((c) => c.data_type === 'eui'),
        group: 'column_params',
        control: this.form.get('column_params.gas_eui') as FormControl<number>,
      },
      {
        name: 'electric_eui',
        label: 'Electric EUI Column',
        type: 'select',
        options: this.propertyColumns.filter((c) => c.data_type === 'eui'),
        group: 'column_params',
        control: this.form.get('column_params.electric_eui') as FormControl<number>,
      },
      {
        name: 'target_gas_eui',
        label: 'Target Gas EUI Column',
        type: 'select',
        options: this.propertyColumns.filter((c) => c.data_type === 'eui'),
        group: 'column_params',
        control: this.form.get('column_params.target_gas_eui') as FormControl<number>,
      },
      {
        name: 'target_electric_eui',
        label: 'Target Electric EUI Column',
        type: 'select',
        options: this.propertyColumns.filter((c) => c.data_type === 'eui'),
        group: 'column_params',
        control: this.form.get('column_params.target_electric_eui') as FormControl<number>,
      },
      {
        name: 'condition_index',
        label: 'Condition Index Column',
        type: 'select',
        options: this.propertyColumns,
        group: 'column_params',
        control: this.form.get('column_params.condition_index') as FormControl<number>,
      },
      {
        name: 'has_bas',
        label: 'Building has BAS Column',
        hint: 'Select the field that indicates whether or not the building has a Building Automation System (BAS). This analysis expects a boolean field.',
        type: 'select',
        options: this.propertyColumns,
        group: 'column_params',
        control: this.form.get('column_params.has_bas') as FormControl<number>,
      },
      // other fields
      {
        name: 'total_eui_goal',
        label: 'Total EUI Threshold',
        hint: 'Total EUI Threshold for the building (includes Electricity, Gas, etc.)',
        type: 'number',
        control: this.form.get('total_eui_goal') as FormControl<number>,
      },
      {
        name: 'ff_eui_goal',
        label: 'Fossil Fuel EUI Goal',
        hint: 'Fossil Fuel EUI Goal for the building (includes Gas, Etc.)',
        type: 'number',
        control: this.form.get('ff_eui_goal') as FormControl<number>,
      },
      {
        name: 'year_built_threshold',
        label: 'Year Built Threshold',
        hint: 'The year built to use as a comparison threshold in the calculations',
        type: 'number',
        control: this.form.get('year_built_threshold') as FormControl<number>,
      },
      {
        name: 'fair_actual_to_benchmark_eui_ratio',
        label: 'Fair Actual to Benchmark EUI Ratio',
        hint: 'The fair ratio of Total EUI to Benchmark Total EUI value to use. Ratio = Total EUI/Benchmark EUI',
        type: 'number',
        control: this.form.get('fair_actual_to_benchmark_eui_ratio') as FormControl<number>,
      },
      {
        name: 'poor_actual_to_benchmark_eui_ratio',
        label: 'Poor Actual to Benchmark EUI Ratio',
        hint: 'The poor ratio of Total EUI to Benchmark Total EUI value to use. Ratio = Total EUI/Benchmark EUI',
        type: 'number',
        control: this.form.get('poor_actual_to_benchmark_eui_ratio') as FormControl<number>,
      },
      {
        name: 'building_sqft_threshold',
        label: 'Building Square Footage Threshold',
        hint: 'The gross square footage to use as a comparison threshold in the calculations',
        type: 'number',
        control: this.form.get('building_sqft_threshold') as FormControl<number>,
      },
      {
        name: 'condition_index_threshold',
        label: 'Condition Index Threshold',
        hint: 'The condition index to use as a comparison threshold in the calculations',
        type: 'number',
        control: this.form.get('condition_index_threshold') as FormControl<number>,
      },
      {
        name: 'ff_fired_equipment_rsl_threshold',
        label: 'FF Fired Equipment RSL Threshold',
        hint: 'The remaining service life threshold for fossil fuel fired equipment',
        type: 'number',
        control: this.form.get('ff_fired_equipment_rsl_threshold') as FormControl<number>,
      },
    ]
  }

  watchForm() {
    this.form.valueChanges
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.formChange.emit(this.form)
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
