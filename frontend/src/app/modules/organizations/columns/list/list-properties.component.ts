import {
  type AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  type OnDestroy,
  type OnInit,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core'
import { MatPaginator } from '@angular/material/paginator'
import { combineLatest, takeUntil } from 'rxjs'
import { TableContainerComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import { ListComponent } from './list.component'

@Component({
  selector: 'seed-organizations-columns-list-properties',
  templateUrl: './list.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, MaterialImports, TableContainerComponent],
})
export class ListPropertiesComponent extends ListComponent implements AfterViewInit, OnDestroy, OnInit {
  type = 'properties'
  @ViewChild(MatPaginator) paginator: MatPaginator

  ngOnInit(): void {
    combineLatest([this._columnService.propertyColumns$, this._organizationService.currentOrganization$])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([columns, organization]) => {
        this.organization = organization
        this.columnTableDataSource.data = columns.sort((a, b) => naturalSort(a.display_name, b.display_name))
        this.buildColumnList()
      })
  }

  ngAfterViewInit(): void {
    this.columnTableDataSource.paginator = this.paginator
  }
}
