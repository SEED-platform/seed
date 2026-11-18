import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { RouterModule } from '@angular/router'
import { Subject, takeUntil, tap } from 'rxjs'
import type { AnalysisConfig, AnalysisCreateData, AnalysisServiceType, CurrentUser, Cycle } from '@seed/api'
import { AnalysisService, ConfigService, CycleService, UserService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'
import { BetterConfigComponent, BurConfigComponent, HvacConfigComponent, SimpleConfigComponent } from './analysis-config'

@Component({
  selector: 'seed-analysis-run-modal',
  templateUrl: './analysis-run-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [
    BetterConfigComponent,
    BurConfigComponent,
    FormsModule,
    HvacConfigComponent,
    MaterialImports,
    ModalHeaderComponent,
    ReactiveFormsModule,
    RouterModule,
    SimpleConfigComponent,
  ],
})
export class AnalysisRunModalComponent implements OnInit, OnDestroy {
  private _analysisService = inject(AnalysisService)
  private _configService = inject(ConfigService)
  private _dialogRef = inject(MatDialogRef<AnalysisRunModalComponent>)
  private _cycleService = inject(CycleService)
  private _userService = inject(UserService)
  private _unsubscribeAll$ = new Subject<void>()
  config: AnalysisConfig = {}
  currentUser: CurrentUser
  cycles: Cycle[] = []
  cycle: Cycle
  configInvalid = true
  runningAnalysis = false

  serviceTypes = [
    { value: 'CO2', display: 'Average Annual CO2' },
    { value: 'BETTER', display: 'BETTER' },
    { value: 'BSyncr', display: 'BSyncr' },
    { value: 'Building Upgrade Recommendation', display: 'Building Upgrade Recommendation' },
    { value: 'Element Statistics', display: 'Element Statistics' },
    { value: 'EEEJ', display: 'Energy Equity & Environmental Justice (EEEJ)' },
    { value: 'EUI', display: 'EUI' },
    { value: 'HVAC Metrics', display: 'HVAC Metrics' },
  ]

  existingNames: string[] = []

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    analysesLink?: string;
  }

  form = new FormGroup({
    access_level_instance_id: new FormControl<number | null>(null),
    name: new FormControl<string | null>(null, [Validators.required]),
    property_view_ids: new FormControl(this.data.viewIds),
    service: new FormControl<AnalysisServiceType | null>(null, [Validators.required]),
  })

  ngOnInit(): void {
    this._configService.config$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ integrations }) => {
      if (!integrations.better) this.serviceTypes = this.serviceTypes.filter(({ value }) => value !== 'BETTER')
    })
    this.getCurrentUser()
    this.getCycles()
    this.getAnalyses()
  }

  getCurrentUser() {
    this._userService.currentUser$
      .pipe(
        tap((currentUser) => {
          this.currentUser = currentUser
          this.form.patchValue({ access_level_instance_id: currentUser.ali_id })
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  getCycles() {
    this._cycleService.getCycles(this.data.orgId)
    this._cycleService.cycles$
      .pipe(
        tap((cycles) => {
          this.cycles = cycles
          this.cycle = cycles[0] || null
        }),
      )
      .subscribe()
  }

  getAnalyses() {
    const { orgId } = this.data
    this._analysisService.getAnalyses(orgId)
    this._analysisService.analyses$
      .pipe(
        tap((analyses) => {
          this.existingNames = analyses.map((a) => a.name)
          this.form.get('name')?.setValidators([Validators.required, SEEDValidators.uniqueValue(this.existingNames)])
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  onFormChange(configForm: FormGroup) {
    this.configInvalid = configForm.invalid
    this.config = configForm.value as AnalysisConfig
  }

  get service() {
    return this.form.value.service
  }

  onSubmit() {
    const data = { ...this.form.value, configuration: this.config } as AnalysisCreateData
    this._analysisService.create(this.data.orgId, data).subscribe(() => {
      this.runningAnalysis = true
    })
  }

  close(success = false) {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
