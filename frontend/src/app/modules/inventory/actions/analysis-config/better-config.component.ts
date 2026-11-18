import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { Subject, takeUntil, tap } from 'rxjs'
import type { BenchmarkDataType, Cycle, SavingsTarget, SelectMetersType } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'

@Component({
  selector: 'seed-better-config',
  templateUrl: './better-config.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class BetterConfigComponent implements OnInit, OnDestroy {
  @Input() cycles: Cycle[]
  @Input() orgId: number
  @Input() viewIds: number[] = []
  @Output() formChange = new EventEmitter<FormGroup>()
  private _unsubscribeAll$ = new Subject<void>()

  form = new FormGroup({
    benchmark_data_type: new FormControl<BenchmarkDataType>(null, [Validators.required]),
    cycle_id: new FormControl<number>(null),
    enable_pvwatts: new FormControl(false),
    meter: new FormGroup({
      start_date: new FormControl<string>(null),
      end_date: new FormControl<string>(null, SEEDValidators.afterDate('start_date')),
    }),
    min_model_r_squared: new FormControl(0.6, [Validators.required]),
    preprocess_meters: new FormControl(false),
    portfolio_analysis: new FormControl(false),
    savings_target: new FormControl<SavingsTarget>(null, [Validators.required]),
    select_meters: new FormControl<SelectMetersType>('all', [Validators.required]),
  })
  benchmarkDataTypes: BenchmarkDataType[] = ['DEFAULT', 'GENERATE']
  savingsTargets: SavingsTarget[] = ['AGGRESSIVE', 'CONSERVATIVE', 'NOMINAL']

  ngOnInit(): void {
    const cycle = this.cycles?.[0]
    this.form.patchValue({
      cycle_id: cycle?.id,
      meter: {
        start_date: new Date(cycle?.start).toISOString(),
        end_date: new Date(cycle?.end).toISOString(),
      },
    })
    console.log(this.form.value)
    this.watchForm()
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

    this.form
      .get('select_meters')
      ?.valueChanges.pipe(
        tap((selection) => {
          if (selection !== 'date_range') {
            this.form.get('meter.start_date')?.setValue(null)
            this.form.get('meter.end_date')?.setValue(null)
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
