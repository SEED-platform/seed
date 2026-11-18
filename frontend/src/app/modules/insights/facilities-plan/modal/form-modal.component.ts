import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import { combineLatest, Subject, take, takeUntil } from 'rxjs'
import type { AccessLevelsByDepth, Column, Cycle, FacilitiesPlan, FacilitiesPlanRun } from '@seed/api'
import { CycleService, FacilitiesPlanRunService, OrganizationService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

type FormModalData = {
  facilitiesPlans: FacilitiesPlan[];
  allColumns: Column[];
  existingRun: FacilitiesPlanRun | null;
}

@Component({
  selector: 'seed-facilities-plan-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule, TranslocoDirective],
})
export class FormModalComponent implements OnDestroy, OnInit {
  private _cycleService = inject(CycleService)
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _facilitiesPlanRunService = inject(FacilitiesPlanRunService)
  private _organizationService = inject(OrganizationService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as FormModalData

  cycles: Cycle[] = []
  accessLevelNames: string[] = []
  accessLevelInstancesByDepth: AccessLevelsByDepth = {}
  selectedLevelIndex: number | null = null
  potentialInstances: { id: number; name: string }[] = []
  selectedColumnIds: number[] = []
  isEditing = !!this.data.existingRun
  isSaving = false

  form = new FormGroup({
    facilities_plan: new FormControl<number | null>(null, Validators.required),
    name: new FormControl('', Validators.required),
    cycle: new FormControl<number | null>(null, Validators.required),
    ali: new FormControl<number | null>(null, Validators.required),
  })

  get availableColumns(): Column[] {
    return this.data.allColumns.filter((c) => !this.selectedColumnIds.includes(c.id))
  }

  ngOnInit(): void {
    combineLatest({
      cycles: this._cycleService.cycles$,
      tree: this._organizationService.accessLevelTree$,
      byDepth: this._organizationService.accessLevelInstancesByDepth$,
    })
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(({ cycles, tree, byDepth }) => {
        this.cycles = cycles
        this.accessLevelNames = tree.accessLevelNames
        this.accessLevelInstancesByDepth = byDepth

        if (this.isEditing && this.data.existingRun) {
          const run = this.data.existingRun
          this.form.patchValue({
            facilities_plan: run.facilities_plan,
            name: run.name,
            cycle: run.cycle,
            ali: run.ali,
          })
          this.selectedColumnIds = run.display_columns.map((c) => c.id)
          this.form.controls.ali.disable()
        } else {
          this.selectedLevelIndex = 0
          this._updatePotentialInstances()
        }
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  onLevelIndexChange(index: number): void {
    this.selectedLevelIndex = index
    this.form.patchValue({ ali: null })
    this._updatePotentialInstances()
  }

  addColumn(columnId: number): void {
    if (!this.selectedColumnIds.includes(columnId)) {
      this.selectedColumnIds = [...this.selectedColumnIds, columnId]
    }
  }

  removeColumn(columnId: number): void {
    this.selectedColumnIds = this.selectedColumnIds.filter((id) => id !== columnId)
  }

  getColumnName(id: number): string {
    const col = this.data.allColumns.find((c) => c.id === id)
    return col?.display_name || col?.column_name || String(id)
  }

  save(): void {
    if (this.form.invalid) return
    const val = this.form.getRawValue()
    if (!val.facilities_plan || !val.name) return
    this.isSaving = true

    if (this.isEditing && this.data.existingRun) {
      this._facilitiesPlanRunService
        .update(this.data.existingRun.id, {
          facilities_plan: val.facilities_plan,
          name: val.name,
          display_columns: this.selectedColumnIds,
        })
        .pipe(take(1))
        .subscribe({
          next: () => {
            this._dialogRef.close(true)
          },
          error: () => {
            this.isSaving = false
          },
        })
    } else {
      if (!val.cycle || !val.ali) return
      this._facilitiesPlanRunService
        .create({
          facilities_plan: val.facilities_plan,
          name: val.name,
          cycle: val.cycle,
          ali: val.ali,
          display_columns: this.selectedColumnIds,
        })
        .pipe(take(1))
        .subscribe({
          next: () => {
            this._dialogRef.close(true)
          },
          error: () => {
            this.isSaving = false
          },
        })
    }
  }

  close(): void {
    this._dialogRef.close(false)
  }

  private _updatePotentialInstances(): void {
    if (this.selectedLevelIndex == null) return
    this.potentialInstances = this.accessLevelInstancesByDepth[this.selectedLevelIndex] ?? []
    // Auto-select when there's only one option
    if (this.potentialInstances.length === 1) {
      this.form.patchValue({ ali: this.potentialInstances[0].id })
    }
  }
}
