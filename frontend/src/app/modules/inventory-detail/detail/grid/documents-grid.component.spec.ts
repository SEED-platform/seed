import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import type { CellClickedEvent } from 'ag-grid-community'
import { of } from 'rxjs'
import { InventoryService, MediaService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { DocumentsGridComponent } from './documents-grid.component'

describe('DocumentsGridComponent', () => {
  it('downloads documents with the media service', async () => {
    const download = jasmine.createSpy('download').and.returnValue(of(undefined))
    await TestBed.configureTestingModule({
      imports: [DocumentsGridComponent],
      providers: [
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: InventoryService, useValue: {} },
        { provide: MatDialog, useValue: {} },
        { provide: MediaService, useValue: { download } },
      ],
    })
      .overrideComponent(DocumentsGridComponent, { set: { template: '', imports: [] } })
      .compileComponents()
    const component = TestBed.createComponent(DocumentsGridComponent).componentInstance

    const target = document.createElement('span')
    target.setAttribute('data-action', 'download')
    const data = { id: 4, file: '/api/v3/media/inventory_documents/plan_ab12.pdf', filename: 'plan.pdf' }
    component.onCellClicked({ colDef: { field: 'actions' }, data, event: { target } } as unknown as CellClickedEvent)

    expect(download).toHaveBeenCalledOnceWith('/api/v3/media/inventory_documents/plan_ab12.pdf', 'plan.pdf')
  })
})
