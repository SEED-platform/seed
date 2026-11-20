import { TestBed } from '@angular/core/testing'
import { MatIconTestingModule } from '@angular/material/icon/testing'
import type { IHeaderParams } from 'ag-grid-community'
import { of } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { getTranslocoTestingModule } from 'app/core/transloco/transloco-testing'
import type { InventoryType } from 'app/modules/inventory/inventory.types'
import { CellHeaderMenuComponent } from './cell-header-menu.component'

// Related (other inventory type) columns aren't sortable, and the API ignores their sorts
describe('CellHeaderMenuComponent', () => {
  const openMenu = async ({ sortable, sort = null }: { sortable: boolean; sort?: 'asc' | 'desc' | null }) => {
    await TestBed.configureTestingModule({
      imports: [CellHeaderMenuComponent, MatIconTestingModule, getTranslocoTestingModule()],
      providers: [
        { provide: ConfigService, useValue: { scheme$: of('light') } },
        { provide: OrganizationService, useValue: {} },
      ],
    }).compileComponents()

    const fixture = TestBed.createComponent(CellHeaderMenuComponent)
    const component = fixture.componentInstance
    const colId = 'address_line_1_7'
    component.agInit({
      column: {
        getColId: () => colId,
        getColDef: () => ({ field: colId }),
        isPinned: () => null,
        isSortable: () => sortable,
        addEventListener: () => undefined,
      },
      api: { addEventListener: () => undefined, getColumnState: () => [{ colId, sort }] },
      displayName: 'Address Line 1 (Tax Lot)',
      eGridHeader: document.createElement('div'),
      currentUser: { org_id: 1, org_user_id: 2, settings: {} } as CurrentUser,
      type: 'properties' as InventoryType,
    } as unknown as IHeaderParams & { currentUser: CurrentUser; type: InventoryType })
    fixture.detectChanges()

    component.toggleMenu()
    fixture.detectChanges()
    const items = component.overlayRef.overlayElement.querySelectorAll('[role="menuitem"]')
    return Array.from(items, (item) => item.textContent.trim())
  }

  it('offers sorting for sortable columns', async () => {
    const items = await openMenu({ sortable: true })
    expect(items).toContain('Sort Ascending')
    expect(items).toContain('Sort Descending')
    expect(items).not.toContain('Clear Sort')
  })

  it('does not offer sorting for unsortable columns', async () => {
    const items = await openMenu({ sortable: false })
    expect(items).not.toContain('Sort Ascending')
    expect(items).not.toContain('Sort Descending')
    expect(items).not.toContain('Clear Sort')
    expect(items).toContain('Hide Column')
  })

  it('still clears a saved sort on an unsortable column', async () => {
    const items = await openMenu({ sortable: false, sort: 'desc' })
    expect(items).not.toContain('Sort Ascending')
    expect(items).toContain('Clear Sort')
  })
})
