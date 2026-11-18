import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import type { CellClickedEvent } from 'ag-grid-community'
import { of } from 'rxjs'
import type { Dataset, ImportFile } from '@seed/api'
import { CycleService, DatasetService, MediaService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { DatasetComponent } from './dataset.component'

describe('DatasetComponent', () => {
  it('downloads import files with the media service', async () => {
    const download = jasmine.createSpy('download').and.returnValue(of(undefined))
    const importFile = { id: 8, cycle: 1, file: '/seed/media/uploads/data_ab12.csv', uploaded_filename: 'data.csv' } as ImportFile
    const dataset = { id: 2, name: 'Dataset', importfiles: [importFile] } as Dataset
    await TestBed.configureTestingModule({
      imports: [DatasetComponent],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { params: { id: 2 } } } },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: CycleService, useValue: { cycles$: of([{ id: 1, name: '2024' }]) } },
        { provide: DatasetService, useValue: { get: () => of(dataset) } },
        { provide: MatDialog, useValue: {} },
        { provide: MediaService, useValue: { download } },
        { provide: Router, useValue: {} },
        { provide: UserService, useValue: { currentOrganizationId$: of(1) } },
      ],
    })
      .overrideComponent(DatasetComponent, { set: { template: '', imports: [] } })
      .compileComponents()
    const fixture = TestBed.createComponent(DatasetComponent)
    fixture.detectChanges()

    const target = document.createElement('span')
    target.setAttribute('data-action', 'download')
    fixture.componentInstance.onCellClicked({
      colDef: { field: 'actions' },
      data: { id: 8 },
      event: { target },
    } as unknown as CellClickedEvent)

    expect(download).toHaveBeenCalledOnceWith('/seed/media/uploads/data_ab12.csv', 'data.csv')
    fixture.destroy()
  })
})
