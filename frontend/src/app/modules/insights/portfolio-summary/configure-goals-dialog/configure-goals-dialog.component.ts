import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Router } from '@angular/router'
import { combineLatest, EMPTY, Subject, switchMap, takeUntil } from 'rxjs'
import type {
  AccessLevelInstancesByDepth,
  AccessLevelsByDepth,
  Column,
  Cycle,
  Goal,
  Organization,
  SalesforceGoal,
  SalesforcePartner,
} from '@seed/api'
import { ColumnService, CycleService, GoalService, OrganizationService, SalesforcePortfolioService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { ConfigureGoalsData } from '../portfolio-summary.types'

@Component({
  selector: 'seed-configure-goals-dialog',
  templateUrl: './configure-goals-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FormsModule, MaterialImports, ModalHeaderComponent, ReactiveFormsModule, SharedImports],
})
export class ConfigureGoalsDialogComponent implements OnInit, OnDestroy {
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _cycleService = inject(CycleService)
  private _columnService = inject(ColumnService)
  private _goalService = inject(GoalService)
  private _organizationService = inject(OrganizationService)
  private _salesforcePortfolioService = inject(SalesforcePortfolioService)
  private _dialogRef = inject(MatDialogRef<ConfigureGoalsDialogComponent>)
  private _router = inject(Router)
  private _snackBar = inject(SnackBarService)
  data = inject(MAT_DIALOG_DATA) as ConfigureGoalsData

  goalForm = new FormGroup({
    name: new FormControl('', Validators.required),
    type: new FormControl<'standard' | 'transaction' | null>(null, Validators.required),
    baselineCycle: new FormControl<number | null>(null, Validators.required),
    accessLevel: new FormControl<string | null>(null, Validators.required),
    accessLevelInstanceId: new FormControl<number | null>(null, Validators.required),
    areaColumn: new FormControl<number | null>(null, Validators.required),
    euiColumn1: new FormControl<number | null>(null, Validators.required),
    euiColumn2: new FormControl<number | null>(null),
    euiColumn3: new FormControl<number | null>(null),
    transactionsColumn: new FormControl<number | null>(null),
    targetPercentage: new FormControl<number | null>(null, Validators.required),
    commitmentSqft: new FormControl<number | null>(null, Validators.required),
    salesforcePartnerID: new FormControl<string | null>(null),
    salesforceGoalID: new FormControl<string | null>(null),
  })

  cycles: Cycle[] = []
  accessLevelNames: AccessLevelInstancesByDepth['accessLevelNames'] = []
  accessLevelInstancesByDepth: AccessLevelsByDepth = {}
  accessLevelInstances: AccessLevelsByDepth[keyof AccessLevelsByDepth] = []
  areaColumns: Column[] = []
  euiColumns: Column[] = []
  allColumns: Column[] = []
  goals: Goal[] = []
  currentGoal: Goal | null = null
  organization: Organization
  isLoggedIntoBbSalesforce: boolean
  bb_salesforce_enabled: boolean
  salesforcePartners: SalesforcePartner[] = []
  salesforceGoals: SalesforceGoal[] = []
  isSaving = false
  isDeleting = false

  get isTransactionType(): boolean {
    return this.goalForm.value.type === 'transaction'
  }

  ngOnInit(): void {
    this.isLoggedIntoBbSalesforce = this.data.isLoggedIntoBbSalesforce
    this.bb_salesforce_enabled = this.data.bb_salesforce_enabled
    this.goals = [...this.data.goals]

    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap((organization) => {
          this.organization = organization
          if (!this.isLoggedIntoBbSalesforce) return EMPTY
          return this._salesforcePortfolioService.getPartners(this.organization.id)
        }),
      )
      .subscribe((r) => {
        this.salesforcePartners = r.results
        // If a goal was already selected before partners loaded, populate the goals dropdown now
        const currentPartnerId = this.goalForm.value.salesforcePartnerID
        if (currentPartnerId) {
          this.onPartnerChange(currentPartnerId)
        }
      })

    combineLatest([
      this._cycleService.cycles$,
      this._organizationService.accessLevelTree$,
      this._organizationService.accessLevelInstancesByDepth$,
      this._columnService.propertyColumns$,
    ])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([cycles, { accessLevelNames }, accessLevelsByDepth, propertyColumns]) => {
        this.cycles = cycles
        this.accessLevelNames = accessLevelNames
        this.accessLevelInstancesByDepth = accessLevelsByDepth
        this.areaColumns = propertyColumns.filter((c) => c.data_type === 'area')
        this.euiColumns = propertyColumns.filter((c) => c.data_type === 'eui')
        this.allColumns = propertyColumns
      })

    if (this.goals.length > 0) {
      this.selectGoal(this.goals[0].id)
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

  selectGoal(goalId: number | null | undefined): void {
    if (goalId == null) {
      this.goalForm.reset()
      this.currentGoal = null
      return
    }
    this.currentGoal = this.goals.find((g) => g.id === goalId) ?? null
    if (!this.currentGoal) return
    this.onAccessLevelChange(this.currentGoal.level_name)
    this.onPartnerChange(this.currentGoal.salesforce_partner_id)
    this.goalForm.setValue({
      name: this.currentGoal.name,
      type: this.currentGoal.type,
      baselineCycle: this.currentGoal.baseline_cycle,
      accessLevel: this.currentGoal.level_name,
      accessLevelInstanceId: this.currentGoal.access_level_instance,
      areaColumn: this.currentGoal.area_column,
      euiColumn1: this.currentGoal.eui_column1,
      euiColumn2: this.currentGoal.eui_column2 ?? null,
      euiColumn3: this.currentGoal.eui_column3 ?? null,
      transactionsColumn: this.currentGoal.transactions_column ? Number(this.currentGoal.transactions_column) : null,
      targetPercentage: this.currentGoal.target_percentage,
      commitmentSqft: this.currentGoal.commitment_sqft,
      salesforcePartnerID: this.currentGoal.salesforce_partner_id ?? null,
      salesforceGoalID: this.currentGoal.salesforce_goal_id ?? null,
    })
  }

  onAccessLevelChange(accessLevelName: string): void {
    const depth = this.accessLevelNames.findIndex((name) => name === accessLevelName)
    this.accessLevelInstances = this.accessLevelInstancesByDepth[depth] ?? []
  }

  onPartnerChange(partnerId: string | undefined | null): void {
    const partner = this.salesforcePartners?.find((p) => p.id === partnerId)
    this.salesforceGoals = partner?.goals ?? []
  }

  deleteCurrentGoal(): void {
    if (!this.currentGoal) return
    this.isDeleting = true
    this._goalService
      .deleteGoal(this.currentGoal.id, this.organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(() => {
        this.goals = this.goals.filter((g) => g.id !== this.currentGoal?.id)
        this.currentGoal = null
        this.goalForm.reset()
        this.isDeleting = false
        this._snackBar.success('Goal deleted')
      })
  }

  save(): void {
    if (this.goalForm.invalid) return
    this.isSaving = true
    const v = this.goalForm.value
    const partner = this.bb_salesforce_enabled ? this.salesforcePartners?.find((p) => p.id === v.salesforcePartnerID) : undefined
    const sfGoal = partner?.goals.find((g) => g.id === v.salesforceGoalID)

    const payload = {
      name: v.name,
      type: v.type,
      baseline_cycle: v.baselineCycle,
      access_level_instance: v.accessLevelInstanceId,
      area_column: v.areaColumn,
      eui_column1: v.euiColumn1,
      eui_column2: v.euiColumn2 ?? null,
      eui_column3: v.euiColumn3 ?? null,
      transactions_column: this.isTransactionType ? (v.transactionsColumn ?? null) : null,
      target_percentage: v.targetPercentage,
      commitment_sqft: v.commitmentSqft,
      ...(partner && { salesforce_partner_id: partner.id, salesforce_partner_name: partner.name }),
      ...(sfGoal && { salesforce_goal_id: sfGoal.id, salesforce_goal_name: sfGoal.name }),
    }

    if (this.currentGoal == null) {
      this._goalService
        .createGoal(payload, this.organization.id)
        .pipe(takeUntil(this._unsubscribeAll$))
        .subscribe((goal) => {
          this.currentGoal = goal
          this.goals = [...this.goals, goal]
          this._goalService.get(this.organization.id)
          this.isSaving = false
          this._snackBar.success('Goal created')
        })
    } else {
      this._goalService
        .editGoal(this.currentGoal.id, payload, this.organization.id)
        .pipe(takeUntil(this._unsubscribeAll$))
        .subscribe((goal) => {
          this.currentGoal = goal
          this.goals = this.goals.map((g) => (g.id === goal.id ? goal : g))
          this._goalService.get(this.organization.id)
          this.isSaving = false
          this._snackBar.success('Goal saved')
        })
    }
  }
}
