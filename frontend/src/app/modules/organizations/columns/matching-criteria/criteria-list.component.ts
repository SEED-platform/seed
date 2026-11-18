import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, ViewEncapsulation } from '@angular/core'
import { type Column } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-matching-criteria-list',
  templateUrl: './criteria-list.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, MaterialImports],
})
export class CriteriaListComponent {
  @Input() columns: Column[]
  @Output() removeColumnEvent = new EventEmitter<Column>()

  removeColumn(column: Column) {
    this.removeColumnEvent.emit(column)
  }

  canRemove(column: Column) {
    return !column.is_matching_criteria
  }
}
