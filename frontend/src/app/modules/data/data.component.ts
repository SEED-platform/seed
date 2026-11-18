import { CommonModule } from '@angular/common'
import type { AfterViewInit, OnInit } from '@angular/core'
import { Component, inject, viewChild, ViewEncapsulation } from '@angular/core'
import { MatSort } from '@angular/material/sort'
import { MatTableDataSource } from '@angular/material/table'
import { ActivatedRoute, Router } from '@angular/router'
import { from, skip } from 'rxjs'
import type { Dataset } from '@seed/api'
import { UserService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-data',
  templateUrl: './data.component.html',
  encapsulation: ViewEncapsulation.None,
  // changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, MaterialImports, PageComponent],
})
export class DataComponent implements OnInit, AfterViewInit {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _userService = inject(UserService)

  readonly sort = viewChild.required(MatSort)
  datasetsDataSource = new MatTableDataSource<Dataset>()
  datasetsColumns = ['name', 'importfiles', 'updated_at', 'last_modified_by', 'actions']

  ngOnInit(): void {
    this._init()

    // Rerun resolver and initializer on org change
    this._userService.currentOrganizationId$.pipe(skip(1)).subscribe(() => {
      from(this._router.navigate([this._router.url])).subscribe(() => {
        this._init()
      })
    })
  }

  createDataset(): void {
    console.log('create dataset')
  }

  ngAfterViewInit(): void {
    this.datasetsDataSource.sort = this.sort()
  }

  trackByFn(_index: number, { id }: Dataset) {
    return id
  }

  private _init() {
    this.datasetsDataSource.data = this._route.snapshot.data.datasets as Dataset[]
  }
}
