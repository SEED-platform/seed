import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { Subject, takeUntil, tap } from 'rxjs'
import type { Column } from '@seed/api'
import { ColumnService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'

@Component({
  selector: 'seed-hvac-config',
  templateUrl: './hvac-config.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class HvacConfigComponent implements OnInit, OnDestroy {
  @Input() orgId: number
  @Output() formChange = new EventEmitter<FormGroup>()
  private _columnService = inject(ColumnService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  areaColumns: Column[] = []

  form = new FormGroup({
    floor_area_column: new FormControl<number | null>(null, Validators.required),
  })

  ngOnInit(): void {
    this._columnService.propertyColumns$
      .pipe(
        tap((columns) => {
          this.areaColumns = columns
            .filter((c) => c.table_name === 'PropertyState' && c.data_type === 'area')
            .sort((a, b) => naturalSort(a.display_name, b.display_name))
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this.form.valueChanges
      .pipe(
        tap(() => {
          this.formChange.emit(this.form)
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this.formChange.emit(this.form)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
