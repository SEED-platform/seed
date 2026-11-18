import { CommonModule } from '@angular/common'
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
  selector: 'seed-organizations-column-data-types-taxlots',
  templateUrl: './data-types.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, SharedImports, TableContainerComponent, MaterialImports, MatPaginator, ReactiveFormsModule],
})
export class DataTypesTaxLotsComponent extends DataTypesComponent implements AfterViewInit, OnInit {
  type = 'TaxLotState'
  @ViewChild(MatPaginator) paginator: MatPaginator

  ngOnInit(): void {
    this._columnService.taxLotColumns$
      .pipe(takeUntil(this._unsubscribeAll$))
      .pipe(
        map((columns) => {
          this.columns = columns.sort((a, b) => naturalSort(a.display_name, b.display_name))
          this.initializeFormControls()
          this.columnTableDataSource.data = this.columns
        }),
      )
      .subscribe()
  }

  ngAfterViewInit() {
    this.columnTableDataSource.paginator = this.paginator
  }
}
