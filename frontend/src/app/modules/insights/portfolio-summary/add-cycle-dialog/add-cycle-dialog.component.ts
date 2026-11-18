import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Router } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import type { AnnualReport, Cycle, CycleGoal } from '@seed/api'
import { CycleService, GoalService, SalesforcePortfolioService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { AddCycleData } from '../portfolio-summary.types'

@Component({
  selector: 'seed-add-cycle-dialog',
  templateUrl: './add-cycle-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports, ModalHeaderComponent, SharedImports],
})
export class AddCycleDialogComponent implements OnInit, OnDestroy {
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _cycleService = inject(CycleService)
  private _goalService = inject(GoalService)
  private _router = inject(Router)
  private _salesforcePortfolioService = inject(SalesforcePortfolioService)
  private _dialogRef = inject(MatDialogRef<AddCycleDialogComponent>)
  data = inject(MAT_DIALOG_DATA) as AddCycleData

  cycles: Cycle[] = []
  selectedCycle: Cycle | null = null
  selectedAnnualReport: AnnualReport | null = null
  isLoggedIntoBbSalesforce = false
  annualReports: AnnualReport[] = []
  isSaving = false

  get isEditing(): boolean {
    return !!this.data.existingCycleGoal
  }

  get title(): string {
    return this.isEditing ? 'Edit Cycle' : 'Add Cycle'
  }

  ngOnInit(): void {
    this.isLoggedIntoBbSalesforce = this.data.isLoggedIntoBbSalesforce

    this._cycleService.cycles$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((cycles) => {
      this.cycles = cycles
      if (this.isEditing) {
        const existingId = this.data.existingCycleGoal?.current_cycle.id
        this.selectedCycle = cycles.find((c) => c.id === existingId) ?? null
      }
    })

    if (this.isLoggedIntoBbSalesforce) {
      this._salesforcePortfolioService.getAnnualReports(this.data.currentGoal.id).subscribe((annualReports) => {
        this.annualReports = annualReports.results
        if (this.isEditing && this.data.existingCycleGoal?.salesforce_annual_report_id) {
          const existingReportId = this.data.existingCycleGoal?.salesforce_annual_report_id
          this.selectedAnnualReport = this.annualReports.find((r) => r.id === existingReportId) ?? null
        }
      })
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  close(): void {
    this._dialogRef.close()
  }

  goToSalesforceSettings(): void {
    this._dialogRef.close()
    void this._router.navigate(['/organizations/settings/salesforce-building-integration'])
  }

  onCycleChange(cycleId: number): void {
    this.selectedCycle = this.cycles.find((c) => c.id === cycleId) ?? null
  }

  onAnnualReportChange(reportId: string | null): void {
    this.selectedAnnualReport = reportId ? (this.annualReports.find((r) => r.id === reportId) ?? null) : null
  }

  submit(): void {
    if (!this.selectedCycle) return
    this.isSaving = true
    const obs = this.isEditing
      ? this._goalService.editCycleGoal(
          this.data.currentGoal.id,
          this.data.existingCycleGoal?.id ?? 0,
          this.selectedCycle.id,
          this.selectedAnnualReport?.id,
          this.selectedAnnualReport?.name,
        )
      : this._goalService.createCycleGoal(
          this.data.currentGoal.id,
          this.selectedCycle.id,
          this.selectedAnnualReport?.id,
          this.selectedAnnualReport?.name,
        )

    obs.pipe(takeUntil(this._unsubscribeAll$)).subscribe((cycleGoal: CycleGoal) => {
      this._dialogRef.close(cycleGoal)
    })
  }
}
