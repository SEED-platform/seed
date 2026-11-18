import { CommonModule } from '@angular/common'
import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import { take } from 'rxjs'
import type { CycleGoal, SalesforceAnnualReport, SalesforceSummaryEntry, SalesforceSummaryResponse } from '@seed/api'
import { GoalService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { SyncSalesforceData } from '../portfolio-summary.types'

type ComparisonRow = {
  label: string;
  seed: number | string | null;
  salesforce: number | string | null;
}

type PastCycleRow = {
  cycleName: string;
  seedEiAnnual: number;
  sfEiAnnual: number | null;
  seedPortfolioEui: number;
  sfPortfolioEui: number | null;
  seedNewEnergySavings: number;
  sfNewEnergySavings: number | null;
  seedPortfolioKbtu: number;
  sfPortfolioKbtu: number | null;
}

@Component({
  selector: 'seed-sync-salesforce-dialog',
  templateUrl: './sync-salesforce-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FormsModule, MaterialImports, ModalHeaderComponent, TranslocoDirective],
})
export class SyncSalesforceDialogComponent implements OnInit {
  private _goalService = inject(GoalService)
  private _dialogRef = inject(MatDialogRef<SyncSalesforceDialogComponent>)
  private _snackBar = inject(SnackBarService)
  data = inject(MAT_DIALOG_DATA) as SyncSalesforceData

  isLoading = false
  hasError = false
  latestEntry: SalesforceSummaryEntry | null = null
  pastEntries: [string, SalesforceSummaryEntry][] = []
  baselineRows: ComparisonRow[] = []
  currentYearRows: ComparisonRow[] = []
  pastCycleRows: PastCycleRow[] = []
  reportStatus: string | null = null
  reviewStatus: string | null = null

  readonly reportStatusOptions = [
    '00. Baselining',
    '00. Partner not engaged',
    '00. Partner under reengagement',
    '00. No Information Available',
    '01. No response to requests for annual data',
    '02. Partner experiencing data challenges',
    '03. Partner working on data',
    '04. Data received, under staff review',
    '05. Data returned for corrections',
    '06. Annual report reviewed by staff',
    '07. Quality check complete (industrial only)',
    '08. Finalized, ready for data display',
    '09. Data display live on web',
  ]

  readonly reviewStatusOptions = [
    'A. Report Needed',
    'B. Report in Progress',
    'C. Report in Progress (Complex)',
    'D. Report on Hold/Partner Update Needed',
    'E. Report Completed (AM Send to Partner)',
    'F. Report and Summary Sent to Partner',
    'G. Feedback Received/Edits Needed from Data Team',
    'H. Final Report Approved for Solution Center',
    'I. Report Under Consideration for Goal Achievement',
    'J. Display Needed',
    'K. New PowerBI Needed',
    'L. Display Generated, Ready for Publish',
    'M. Display Published (AMs QC)',
    'N. AM QC Complete',
    'O. Issues for Data Team',
    'P. Data Team QC Complete',
    'Q. Opt-Out of Display',
  ]

  get goalDetails(): { label: string; value: string }[] {
    const { goal } = this.data
    return [
      { label: 'Salesforce Partner', value: `${goal.salesforce_partner_name ?? ''} (${goal.salesforce_partner_id ?? ''})` },
      { label: 'Salesforce Goal', value: `${goal.salesforce_goal_name ?? ''} (${goal.salesforce_goal_id ?? ''})` },
    ]
  }

  get hasSfData(): boolean {
    return this.latestEntry != null && this._hasSfReport(this.latestEntry.salesforce)
  }

  ngOnInit() {
    // Defer to avoid ExpressionChangedAfterItHasBeenCheckedError from the global loading bar interceptor.
    setTimeout(() => {
      this._loadSummary()
    })
  }

  dismiss() {
    this._dialogRef.close()
  }

  syncCurrent() {
    if (!this.latestEntry) return
    this.isLoading = true
    this._goalService
      .updateSalesforceCurrent(this.data.goal.id, this.latestEntry.id, this.reportStatus, this.reviewStatus, this.data.organization.id)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this._snackBar.success('Salesforce goal and current annual report updated successfully')
          this._loadSummary()
        },
        error: () => {
          this.isLoading = false
        },
      })
  }

  syncHistorical() {
    if (!this.pastEntries.length) return
    this.isLoading = true
    const cycleGoalIds = this.pastEntries.map(([, entry]) => entry.id)
    this._goalService
      .updateSalesforceHistorical(this.data.goal.id, cycleGoalIds, this.data.organization.id)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this._snackBar.success('Salesforce historical reports updated successfully')
          this._loadSummary()
        },
        error: () => {
          this.isLoading = false
        },
      })
  }

  isMismatch(seed: number | string | null, salesforce: number | string | null): boolean {
    if (!this.hasSfData) return false
    return String(seed) !== String(salesforce)
  }

  isMatch(seed: number | string | null, salesforce: number | string | null): boolean {
    if (!this.hasSfData) return false
    return String(seed) === String(salesforce)
  }

  private _hasSfReport(sf: SalesforceAnnualReport | Record<string, never>): sf is SalesforceAnnualReport {
    return 'id' in sf
  }

  private _loadSummary() {
    this.isLoading = true
    this._goalService
      .getSalesforceSummary(this.data.goal.id, this.data.organization.id)
      .pipe(take(1))
      .subscribe({
        next: (data) => {
          this.isLoading = false
          this.hasError = false
          this._processSummary(data)
        },
        error: () => {
          this.isLoading = false
          this.hasError = true
        },
      })
  }

  private _processSummary(data: SalesforceSummaryResponse) {
    const currentCycleName = this.data.currentCycleGoal.current_cycle.name
    this.latestEntry = data[currentCycleName] ?? null
    this.pastEntries = Object.entries(data).filter(([k]) => k !== currentCycleName)

    if (this.latestEntry) {
      this._buildBaselineRows(this.latestEntry, this.data.currentCycleGoal)
      this._buildCurrentYearRows(this.latestEntry, this.data.currentCycleGoal)
    }
    this._buildPastCycleRows()
  }

  private _buildBaselineRows(entry: SalesforceSummaryEntry, _cycleGoal: CycleGoal) {
    const sf = this._hasSfReport(entry.salesforce) ? entry.salesforce : null
    this.baselineRows = [
      { label: 'Baseline portfolio kBtu', seed: entry.seed.baseline_total_kbtu, salesforce: sf?.baseline_portfolio_kbtu ?? null },
      { label: 'Baseline portfolio EUI', seed: entry.seed.baseline_weighted_eui, salesforce: sf?.baseline_portfolio_eui ?? null },
    ]
  }

  private _buildCurrentYearRows(entry: SalesforceSummaryEntry, cycleGoal: CycleGoal) {
    const sf = this._hasSfReport(entry.salesforce) ? entry.salesforce : null
    const currentKbtu = Number(entry.seed.current_total_kbtu)
    const seedNewSavings = entry.seed.baseline_total_kbtu - currentKbtu
    const seedEiAnnual = entry.seed.baseline_weighted_eui - entry.seed.current_weighted_eui

    this.currentYearRows = [
      { label: 'Reporting Year Start', seed: cycleGoal.current_cycle.start, salesforce: sf?.reporting_year_start ?? null },
      { label: 'Reporting Year End', seed: cycleGoal.current_cycle.end, salesforce: sf?.reporting_year_end ?? null },
      { label: 'Number of Properties', seed: entry.seed.total_properties, salesforce: sf?.number_of_properties ?? null },
      { label: 'Portfolio Average EUI', seed: entry.seed.current_weighted_eui, salesforce: sf?.portfolio_average_eui ?? null },
      { label: 'Portfolio kBtu (BBC Total Energy)', seed: entry.seed.current_total_kbtu, salesforce: sf?.portfolio_kbtu ?? null },
      { label: 'New Energy Savings', seed: seedNewSavings, salesforce: sf?.new_energy_savings ?? null },
      { label: 'EI Annual Improvement', seed: seedEiAnnual, salesforce: sf?.ei_annual_improvement ?? null },
      { label: 'Total EI Improvement', seed: entry.seed.eui_change, salesforce: sf?.total_ei_improvement ?? null },
      { label: 'Shared Square Feet', seed: entry.seed.shared_sqft, salesforce: sf?.shared_square_feet ?? null },
      { label: 'Reviewed Square Feet', seed: entry.seed.current_total_sqft, salesforce: sf?.reviewed_square_feet ?? null },
    ]
    if (sf) {
      this.reportStatus = sf.report_status
      this.reviewStatus = sf.review_status
    }
  }

  private _buildPastCycleRows() {
    this.pastCycleRows = this.pastEntries.map(([, entry]) => {
      const sf = this._hasSfReport(entry.salesforce) ? entry.salesforce : null
      const currentKbtu = Number(entry.seed.current_total_kbtu)
      const seedNewSavings = entry.seed.baseline_total_kbtu - currentKbtu
      const seedEiAnnual = entry.seed.baseline_weighted_eui - entry.seed.current_weighted_eui
      return {
        cycleName: `${entry.seed.current_cycle_name}${sf?.id ? ` (${sf.id})` : ''}`,
        seedEiAnnual,
        sfEiAnnual: sf?.ei_annual_improvement ?? null,
        seedPortfolioEui: entry.seed.current_weighted_eui,
        sfPortfolioEui: sf?.portfolio_average_eui ?? null,
        seedNewEnergySavings: seedNewSavings,
        sfNewEnergySavings: sf?.new_energy_savings ?? null,
        seedPortfolioKbtu: currentKbtu,
        sfPortfolioKbtu: sf?.portfolio_kbtu ?? null,
      }
    })
  }
}
