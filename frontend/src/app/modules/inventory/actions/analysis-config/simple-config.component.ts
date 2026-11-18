import type { OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms'
import { Subject, takeUntil, tap } from 'rxjs'
import type { AnalysisServiceType, BSyncrModelTypes, Cycle, SelectMetersType } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'

@Component({
  selector: 'seed-simple-config',
  templateUrl: './simple-config.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class SimpleConfigComponent implements OnChanges, OnDestroy, OnInit {
  @Input() cycles: Cycle[] = []
  @Input() service: AnalysisServiceType
  @Output() formChange = new EventEmitter<FormGroup>()

  private _unsubscribeAll$ = new Subject<void>()

  aboutMap = {
    BSyncr:
      'The BSyncr analysis leverages the Normalized Metered Energy Consumption (NMEC) analysis to calculate a change point model. The data are passed to the analysis using BuildingSync. The result of the analysis are the coefficients of the change point model.',
    EUI: "The EUI analysis will sum the property's meter readings for the last twelve months to calculate the energy use per square footage per year.If there are missing meter readings, then the analysis will return a less that 100% coverage to alert the user that there is a missing meter reading.",
    CO2: "This analysis calculates the average annual CO2 emissions for the property's meter data. The analysis requires an eGRID Subregion to be defined in order to accurately determine the emission rates.",
    EEEJ: "The EEEJ Analysis uses each property's address to identify the 2010 census tract. Based on census tract, disadvantaged community classification and energy burden information can be retrieved from the CEJST dataset. The number of affordable housing locations is retrieved from HUD datasets. Location is used to generate a link to view an EJScreen Report providing more demographic indicators.",
    'Element Statistics':
      "The Element Statistics analysis looks through a property's element data (if any) to count the number of elements of type 'D.D.C.Control Panel'. It also generates the aggregated (average) condition index values for EISA 2007-432 elements and saves those quantities to the property.",
  }
  formMap: Record<string, FormGroup> = {}
  form: FormGroup

  bsyncrModelOptions: BSyncrModelTypes[] = [
    'Simple Linear Regression',
    'Three bsyncrOptionsParameter Linear Model Cooling',
    'Three Parameter Linear Model Heating',
    'Four Parameter Linear Model',
  ]

  formBSyncr = new FormGroup({
    model_type: new FormControl<BSyncrModelTypes>('Simple Linear Regression'),
  })
  formEUI = new FormGroup({
    cycle_id: new FormControl<number>(null),
    select_meters: new FormControl<SelectMetersType>('all'),
    meter: new FormGroup({
      start_date: new FormControl<string>(null),
      end_date: new FormControl<string>(null, SEEDValidators.afterDate('start_date')),
    }),
  })
  formCO2 = new FormGroup({
    save_co2_results: new FormControl(false),
  })
  formEEEJ = new FormGroup({})
  formES = new FormGroup({})

  ngOnInit() {
    this.formMap = {
      BSyncr: this.formBSyncr,
      EUI: this.formEUI,
      CO2: this.formCO2,
      EEEJ: this.formEEEJ,
      'Element Statistics': this.formES,
    }
    this.form = this.formMap[this.service]
    this.formChange.emit(this.form)
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.service) {
      this.form = this.formMap[this.service]
      if (!this.form) return

      this.watchForm()
    }
  }

  watchForm() {
    this.form.valueChanges
      .pipe(
        tap(() => {
          this.formChange.emit(this.form)
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    if (this.service === 'EUI') {
      this.form.get('cycle_id')?.setValue(this.cycles?.[0]?.id || null)
      this.watchSelectMeters()
    }
  }

  watchSelectMeters() {
    this.form
      .get('select_meters')
      ?.valueChanges.pipe(
        tap((selection) => {
          // reset dates
          if (selection !== 'date_range') {
            for (const field of ['meter.start_date', 'meter.end_date']) {
              if (this.form.get(field)?.value) {
                this.form.get(field)?.setValue(null)
              }
            }
          }
          // reset cycle_id
          if (selection === 'select_cycle' && !this.form.get('cycle_id')?.value) {
            const defaultCycleId = this.cycles?.[0]?.id || null
            this.form.get('cycle_id')?.setValue(defaultCycleId)
          }
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
