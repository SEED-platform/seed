import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { RouterModule } from '@angular/router'
import type { Observable } from 'rxjs'
import { finalize, Subject, take, tap } from 'rxjs'
import type { Program, ProgramResponse, ProgramUpsertPayload } from '@seed/api'
import { ProgramService } from '@seed/api'
import type { Column } from '@seed/api/column/column.types'
import type { Cycle } from '@seed/api/cycle/cycle.types'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { Organization } from 'app/modules/organizations/organizations.types'

@Component({
  selector: 'seed-program-config',
  templateUrl: './program-config.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, FormsModule, ReactiveFormsModule, RouterModule],
})
export class ProgramConfigComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<ProgramConfigComponent>)
  private _programService = inject(ProgramService)
  private _snackBar = inject(SnackBarService)
  private _unsubscribeAll$ = new Subject<void>()

  metricTypes = [
    { key: 'Target Greater Than Actual', value: 'Target > Actual for Compliance' },
    { key: 'Target Less Than Actual', value: 'Target < Actual for Compliance' },
  ]
  metricColumns: Column[]
  metricDataTypes = ['number', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean']
  maxHeight = window.innerHeight - 200
  program: Program | null = null

  data = inject(MAT_DIALOG_DATA) as {
    programs: Program[];
    cycles: Cycle[];
    filterGroups: { id: number; name: string }[];
    program: Program;
    org: Organization;
    propertyColumns: Column[];
    xAxisColumns: Column[];
  }

  form = new FormGroup({
    actual_emission_column: new FormControl<number>(null),
    actual_energy_column: new FormControl<number>(null),
    cycles: new FormControl<number[]>([], Validators.required),
    emission_metric_type: new FormControl(''),
    energy_metric_type: new FormControl(''),
    filter_group: new FormControl<number | null>(null),
    name: new FormControl('', Validators.required),
    target_emission_column: new FormControl<number>(null),
    target_energy_column: new FormControl<number>(null),
    x_axis_columns: new FormControl<number[]>([], Validators.required),
  })

  ngOnInit(): void {
    this.metricColumns = this.data.propertyColumns.filter((c) => this.validColumn(c, this.metricDataTypes))
  }

  validColumn(column: Column, validTypes: string[]) {
    const isAllowedType = validTypes.includes(column.data_type)
    const notRelated = !column.related
    const notDerived = !column.derived_column
    return isAllowedType && notRelated && notDerived
  }

  selectProgram(program: Program) {
    this.program = program
    this.form.patchValue({
      actual_emission_column: program.actual_emission_column,
      actual_energy_column: program.actual_energy_column,
      cycles: program.cycles,
      emission_metric_type: program.emission_metric_type ?? '',
      energy_metric_type: program.energy_metric_type ?? '',
      filter_group: program.filter_group,
      name: program.name,
      target_emission_column: program.target_emission_column,
      target_energy_column: program.target_energy_column,
      x_axis_columns: program.x_axis_columns,
    })
  }

  newProgram() {
    this.program = null
    this.form.reset({
      actual_emission_column: null,
      actual_energy_column: null,
      cycles: [],
      emission_metric_type: '',
      energy_metric_type: '',
      filter_group: null,
      name: '',
      target_emission_column: null,
      target_energy_column: null,
      x_axis_columns: [],
    })
  }

  removeProgram() {
    this._programService
      .delete(this.data.org.id, this.program.id)
      .pipe(
        take(1),
        finalize(() => {
          this.close()
        }),
      )
      .subscribe()
  }

  removeItem(item: number, key: 'cycles' | 'x_axis_columns') {
    const items = this.form.value[key].filter((i) => i !== item)
    this.form.patchValue({ [key]: items })
  }

  getCycle(id: number) {
    return this.data.cycles.find((cycle) => cycle.id === id).name
  }

  getColumn(id: number) {
    return this.data.xAxisColumns.find((column) => column.id === id).display_name
  }

  getColumnDataType(columnId: number): string | null {
    if (!columnId) return null
    return this.metricColumns.find((column) => column.id === columnId)?.data_type ?? null
  }

  getValidationError() {
    const values = this.form.value
    const hasEnergyMetric = values.actual_energy_column && values.energy_metric_type
    const hasEmissionMetric = values.actual_emission_column && values.emission_metric_type
    const noEnergyMetricType = values.actual_energy_column && !values.energy_metric_type
    const noEmissionMetricType = values.actual_emission_column && !values.emission_metric_type
    const actualEnergyNoTargetNotBoolean
      = values.actual_energy_column && !values.target_energy_column && this.getColumnDataType(values.actual_energy_column) !== 'boolean'
    const actualEmissionNoTargetNotBoolean
      = values.actual_emission_column && !values.target_emission_column && this.getColumnDataType(values.actual_emission_column) !== 'boolean'
    const targetWithoutActual
      = (!values.actual_energy_column && values.target_energy_column) || (!values.actual_emission_column && values.target_emission_column)

    if ((!hasEnergyMetric && !hasEmissionMetric) || noEnergyMetricType || noEmissionMetricType) {
      return 'A completed energy or emission metric is required'
    }
    if (actualEnergyNoTargetNotBoolean || actualEmissionNoTargetNotBoolean) {
      return 'The actual energy or emission column must be boolean if no target column is selected'
    }
    if (targetWithoutActual) {
      return 'The actual energy or emission column must be included when a target column is selected'
    }
    return null
  }

  onSubmit() {
    const validationError = this.getValidationError()
    if (validationError) {
      this._snackBar.alert(validationError)
      return
    }

    const values = this.form.getRawValue()
    const data: ProgramUpsertPayload = {
      ...values,
      cycles: values.cycles ?? [],
      emission_metric_type: values.emission_metric_type || '',
      energy_metric_type: values.energy_metric_type || '',
      filter_group: values.filter_group ?? null,
      x_axis_columns: values.x_axis_columns ?? [],
    }

    const request$: Observable<ProgramResponse> = this.program
      ? this._programService.update(this.data.org.id, this.program.id, data)
      : this._programService.create(this.data.org.id, data)

    request$
      .pipe(
        take(1),
        tap(({ compliance_metric }) => {
          const programId = compliance_metric.id
          this.close(programId)
        }),
      )
      .subscribe()
  }

  close(programId = null) {
    this._dialogRef.close(programId)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
