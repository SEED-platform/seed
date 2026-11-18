import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { combineLatest, Subject, takeUntil } from 'rxjs'
import type { Column, FacilitiesPlan } from '@seed/api'
import { ColumnService, FacilitiesPlanService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-organizations-settings-facilities-plan',
  templateUrl: './facilities-plan.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, ReactiveFormsModule, SharedImports],
})
export class FacilitiesPlanSettingsComponent implements OnDestroy, OnInit {
  private _columnService = inject(ColumnService)
  private _facilitiesPlanService = inject(FacilitiesPlanService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  facilitiesPlans: FacilitiesPlan[] = []
  selectedPlan: FacilitiesPlan | null = null
  isCreating = false
  isSaving = false

  allColumns: Column[] = []
  booleanColumns: Column[] = []
  numericColumns: Column[] = []

  form = new FormGroup({
    name: new FormControl('', Validators.required),
    energy_running_sum_percentage: new FormControl(0.8, [Validators.required, Validators.min(0), Validators.max(1)]),
    compliance_cycle_year_column: new FormControl<number | null>(null),
    include_in_total_denominator_column: new FormControl<number | null>(null),
    exclude_from_plan_column: new FormControl<number | null>(null),
    require_in_plan_column: new FormControl<number | null>(null),
    electric_energy_usage_column: new FormControl<number | null>(null),
    gas_energy_usage_column: new FormControl<number | null>(null),
    steam_energy_usage_column: new FormControl<number | null>(null),
  })

  get showForm(): boolean {
    return this.isCreating || this.selectedPlan !== null
  }

  ngOnInit(): void {
    combineLatest({
      plans: this._facilitiesPlanService.facilitiesPlans$,
      cols: this._columnService.propertyColumns$,
    })
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(({ plans, cols }) => {
        this.facilitiesPlans = plans
        this.allColumns = cols.filter((c) => c.table_name === 'PropertyState')
        this.booleanColumns = this.allColumns.filter((c) => c.data_type === 'boolean')
        const numericTypes: Column['data_type'][] = [
          'number',
          'float',
          'integer',
          'eui',
          'ghg',
          'ghg_intensity',
          'wui',
          'water_use',
          'area',
        ]
        this.numericColumns = this.allColumns.filter((c) => numericTypes.includes(c.data_type))

        // Re-sync selected plan after reload
        if (this.selectedPlan) {
          this.selectedPlan = plans.find((p) => p.id === this.selectedPlan?.id) ?? null
          if (this.selectedPlan) this._patchForm(this.selectedPlan)
        }
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  selectPlan(plan: FacilitiesPlan): void {
    this.isCreating = false
    this.selectedPlan = plan
    this._patchForm(plan)
  }

  createNew(): void {
    this.selectedPlan = null
    this.isCreating = true
    this.form.reset({
      name: 'New Facilities Plan',
      energy_running_sum_percentage: 0.8,
      compliance_cycle_year_column: null,
      include_in_total_denominator_column: null,
      exclude_from_plan_column: null,
      require_in_plan_column: null,
      electric_energy_usage_column: null,
      gas_energy_usage_column: null,
      steam_energy_usage_column: null,
    })
  }

  save(): void {
    if (this.form.invalid) return
    this.isSaving = true
    const payload = this.form.getRawValue()

    if (this.isCreating) {
      this._facilitiesPlanService.create(payload).subscribe({
        next: () => {
          this.isCreating = false
          this.isSaving = false
        },
        error: () => {
          this.isSaving = false
        },
      })
    } else if (this.selectedPlan) {
      this._facilitiesPlanService.update(this.selectedPlan.id, payload).subscribe({
        next: () => {
          this.isSaving = false
        },
        error: () => {
          this.isSaving = false
        },
      })
    }
  }

  deletePlan(plan: FacilitiesPlan): void {
    this._facilitiesPlanService.delete(plan.id).subscribe({
      next: () => {
        if (this.selectedPlan?.id === plan.id) {
          this.selectedPlan = null
        }
      },
    })
  }

  columnName(col: Column): string {
    return col.display_name || col.column_name
  }

  private _patchForm(plan: FacilitiesPlan): void {
    this.form.patchValue({
      name: plan.name,
      energy_running_sum_percentage: plan.energy_running_sum_percentage,
      compliance_cycle_year_column: plan.compliance_cycle_year_column,
      include_in_total_denominator_column: plan.include_in_total_denominator_column,
      exclude_from_plan_column: plan.exclude_from_plan_column,
      require_in_plan_column: plan.require_in_plan_column,
      electric_energy_usage_column: plan.electric_energy_usage_column,
      gas_energy_usage_column: plan.gas_energy_usage_column,
      steam_energy_usage_column: plan.steam_energy_usage_column,
    })
  }
}
