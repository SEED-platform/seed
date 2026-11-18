import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import { take } from 'rxjs'
import type { FacilitiesPlanRun } from '@seed/api'
import { InventoryService, UserService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

type BulkEditModalData = {
  run: FacilitiesPlanRun;
  propertyViewIds: number[];
}

@Component({
  selector: 'seed-facilities-plan-bulk-edit-modal',
  templateUrl: './bulk-edit-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, TranslocoDirective],
})
export class BulkEditModalComponent {
  private _dialogRef = inject(MatDialogRef<BulkEditModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _userService = inject(UserService)

  data = inject(MAT_DIALOG_DATA) as BulkEditModalData
  isSaving = false

  complianceCycleYear: string | null = null
  includeInTotalDenominator: boolean | null = null
  excludeFromPlan: boolean | null = null
  requireInPlan: boolean | null = null

  get run(): FacilitiesPlanRun {
    return this.data.run
  }

  get complianceCycleYearColumn() {
    return this.run.columns.compliance_cycle_year_column
  }
  get includeInTotalDenominatorColumn() {
    return this.run.columns.include_in_total_denominator_column
  }
  get excludeFromPlanColumn() {
    return this.run.columns.exclude_from_plan_column
  }
  get requireInPlanColumn() {
    return this.run.columns.require_in_plan_column
  }

  save(): void {
    const valuesByColumnId: Record<number, unknown> = {}

    if (this.complianceCycleYearColumn && this.complianceCycleYear != null) {
      valuesByColumnId[this.complianceCycleYearColumn.id] = this.complianceCycleYear
    }
    if (this.includeInTotalDenominatorColumn && this.includeInTotalDenominator != null) {
      valuesByColumnId[this.includeInTotalDenominatorColumn.id] = this.includeInTotalDenominator
    }
    if (this.excludeFromPlanColumn && this.excludeFromPlan != null) {
      valuesByColumnId[this.excludeFromPlanColumn.id] = this.excludeFromPlan
    }
    if (this.requireInPlanColumn && this.requireInPlan != null) {
      valuesByColumnId[this.requireInPlanColumn.id] = this.requireInPlan
    }

    if (!Object.keys(valuesByColumnId).length) {
      this._dialogRef.close(false)
      return
    }

    this.isSaving = true
    this._userService.currentOrganizationId$.pipe(take(1)).subscribe((orgId) => {
      this._inventoryService
        .batchUpdatePropertyStates(orgId, this.data.propertyViewIds, valuesByColumnId)
        .pipe(take(1))
        .subscribe({
          next: () => {
            this._dialogRef.close(true)
          },
          error: () => {
            this.isSaving = false
          },
        })
    })
  }

  close(): void {
    this._dialogRef.close(false)
  }
}
