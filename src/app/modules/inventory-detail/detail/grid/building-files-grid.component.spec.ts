import { TestBed } from '@angular/core/testing'
import type { CellClickedEvent } from 'ag-grid-community'
import { of } from 'rxjs'
import { MediaService } from '@seed/api'
import { ConfigService } from '@seed/services'
import type { BuildingFile, ViewResponse } from 'app/modules/inventory/inventory.types'
import { BuildingFilesGridComponent } from './building-files-grid.component'

describe('BuildingFilesGridComponent', () => {
  it('downloads building files with the media service', async () => {
    const download = jasmine.createSpy('download').and.returnValue(of(undefined))
    await TestBed.configureTestingModule({
      imports: [BuildingFilesGridComponent],
      providers: [
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: MediaService, useValue: { download } },
      ],
    })
      .overrideComponent(BuildingFilesGridComponent, { set: { template: '', imports: [] } })
      .compileComponents()
    const fixture = TestBed.createComponent(BuildingFilesGridComponent)
    const component = fixture.componentInstance
    const file = {
      created: '2026-01-01',
      file: '/media/buildingsync_files/building.xml',
      file_type: 'BuildingSync',
      filename: 'building.xml',
    }
    component.view = { state: { files: [file as BuildingFile] } } as ViewResponse
    fixture.detectChanges()

    component.onCellClicked({ colDef: { field: 'actions' }, data: component.rowData[0] } as CellClickedEvent)

    expect(download).toHaveBeenCalledOnceWith('/media/buildingsync_files/building.xml', 'building.xml')
  })
})
