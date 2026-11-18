import { CommonModule } from '@angular/common'
import { ChangeDetectionStrategy, Component, Input, type OnChanges, type OnInit, type SimpleChanges } from '@angular/core'
import { forwardRef } from '@angular/core'
import { type FormControl, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms'
import { map, type Observable, startWith } from 'rxjs'
import { type Column } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-header-autocomplete',
  templateUrl: './seed-header-autocomplete.component.html',
  imports: [CommonModule, SharedImports, MaterialImports, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.Eager,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SeedHeaderAutocompleteComponent),
      multi: true,
    },
  ],
})
export class SeedHeaderAutocompleteComponent implements OnChanges, OnInit {
  @Input() formControl: FormControl
  @Input() columns: Column[]
  @Input() label: string
  @Input() tableName: string
  filteredColumns: Observable<Column[]>

  ngOnInit() {
    this.filteredColumns = this.formControl.valueChanges.pipe(
      startWith(''),
      map((val: string) => this.filter(val)),
    )
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ('tableName' in changes && changes.tableName.previousValue !== changes.tableName.currentValue) {
      this.filteredColumns = this.formControl.valueChanges.pipe(
        startWith(''),
        map((val: string) => this.filter(val)),
      )
    }
  }

  filter(val: string) {
    return this.columns.filter(
      (col) => col.table_name === this.tableName && col.column_name.toLocaleLowerCase().includes(val.toLocaleLowerCase()),
    )
  }
  displayFn = (a: string) => {
    if (this.columns) {
      const col = this.columns.find((c) => c.column_name === a)
      if (col) {
        return col.display_name
      } else {
        return a
      }
    } else {
      return a
    }
  }

  registerOnChange(fn: () => void) {
    this.formControl.registerOnChange(fn)
  }

  registerOnTouched(fn: () => void) {
    fn()
  }

  writeValue(value) {
    this.formControl.setValue(value)
  }
}
