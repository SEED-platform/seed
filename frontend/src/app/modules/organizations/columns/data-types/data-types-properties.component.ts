import { type AfterViewInit, ChangeDetectionStrategy, Component, type OnInit, ViewChild, ViewEncapsulation } from '@angular/core'
import { ReactiveFormsModule } from '@angular/forms'
import { MatPaginator } from '@angular/material/paginator'
import { map, takeUntil } from 'rxjs'
import { TableContainerComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import { DataTypesComponent } from './data-types.component'

@Component({
  selector: 'seed-organizations-column-data-types-properties',
  templateUrl: './data-types.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, TableContainerComponent, MaterialImports, MatPaginator, ReactiveFormsModule],
})
export class DataTypesPropertiesComponent extends DataTypesComponent implements AfterViewInit, OnInit {
  type = 'PropertyState'

  @ViewChild(MatPaginator) paginator: MatPaginator

  ngOnInit(): void {
    this._columnService.propertyColumns$
      .pipe(takeUntil(this._unsubscribeAll$))
      .pipe(
        map((columns) => {
          this.columns = columns.sort((a, b) => naturalSort(a.display_name, b.display_name))
          this.initializeFormControls()
          if (this.columns.length > 0) {
            this.isLoading = false
          }
          this.columnTableDataSource.data = this.columns
        }),
      )
      .subscribe()
  }

  ngAfterViewInit(): void {
    this.columnTableDataSource.paginator = this.paginator
  }
}
