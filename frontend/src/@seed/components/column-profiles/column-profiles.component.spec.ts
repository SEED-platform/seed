import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import { TranslocoService } from '@jsverse/transloco'
import type { GridApi, IRowNode, RowSelectedEvent } from 'ag-grid-community'
import { of } from 'rxjs'
import type { Column } from '@seed/api'
import { ColumnService, InventoryService, OrganizationService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import type { ProfileColumn } from 'app/modules/inventory/inventory.types'
import { ColumnProfilesComponent } from './column-profiles.component'

describe('ColumnProfilesComponent profile settings', () => {
  let component: ColumnProfilesComponent

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: ColumnService, useValue: {} },
        { provide: InventoryService, useValue: {} },
        { provide: OrganizationService, useValue: {} },
        { provide: UserService, useValue: {} },
        { provide: MatDialog, useValue: {} },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: TranslocoService, useValue: { translate: (key: string) => key } },
      ],
    })
    component = TestBed.runInInjectionContext(() => new ColumnProfilesComponent())
    component.profileType = 'list'
    component.columns = [
      { id: 1, column_name: 'alpha', display_name: 'Alpha' },
      { id: 2, column_name: 'beta', display_name: 'Beta' },
      { id: 3, column_name: 'gamma', display_name: 'Gamma' },
    ] as Column[]
  })

  afterEach(() => {
    component.ngOnDestroy()
  })

  it('loads saved order and puts pinned columns first', () => {
    component.setRowData(new Set([1, 2, 3]), [
      { id: 3, order: 1, pinned: false },
      { id: 2, order: 2, pinned: true },
      { id: 1, order: 3, pinned: false },
    ])

    expect(component.getSelectedProfileColumns().map((row) => [row.id, row.order, row.pinned])).toEqual([
      [2, 1, true],
      [3, 2, false],
      [1, 3, false],
    ])
  })

  it('preserves order and pins when adding or removing a column', () => {
    component.setRowData(new Set([1, 3]), [
      { id: 3, order: 1, pinned: true },
      { id: 1, order: 2, pinned: false },
    ])
    component.setRowData(new Set([1, 2, 3]))
    expect(component.getSelectedProfileColumns().map((row) => row.id)).toEqual([3, 1, 2])
    expect(component.rowData[0].pinned).toBeTrue()

    component.setRowData(new Set([1, 2]))
    component.setRowData(new Set([1, 2, 3]))
    expect(component.getSelectedProfileColumns().map((row) => row.id)).toEqual([1, 2, 3])
    expect(component.rowData.find((row) => row.id === 3).pinned).toBeFalse()
  })

  it('saves drag order rather than stale order values', () => {
    component.setRowData(new Set([1, 2, 3]))
    const [first, second, third] = component.rowData
    component.gridApi = {
      forEachNodeAfterFilterAndSort: (callback) => {
        for (const [index, data] of [third, first, second].entries()) callback({ data } as IRowNode, index)
      },
      getSelectedRows: () => [first, second, third],
    } as GridApi
    spyOn(component, 'setSelectedRows')

    component.onRowDragEnd()

    expect(component.getSelectedProfileColumns().map((row) => [row.id, row.order])).toEqual([
      [3, 1],
      [1, 2],
      [2, 3],
    ])
  })

  it('supports numeric keyboard ordering within the selected columns', () => {
    component.setRowData(new Set([1, 2, 3]))
    component.setColumnOrder(component.rowData[2], 1)
    expect(component.getSelectedProfileColumns().map((row) => row.id)).toEqual([3, 1, 2])
  })

  it('allows derived columns to be pinned and selects them automatically', () => {
    component.setRowData(new Set())
    const row = component.rowData[0]
    row.derived_column = 1
    const setSelected = jasmine.createSpy('setSelected')
    component.gridApi = {
      getSelectedRows: () => [],
    } as unknown as GridApi
    spyOn(component, 'setRowData')

    component.togglePinned(row, setSelected)

    expect(setSelected).toHaveBeenCalledOnceWith(true)
    expect(row.pinned).toBeTrue()
    expect(component.getSelectedProfileColumns().map((column) => column.id)).toContain(row.id)
    expect(component.setRowData).toHaveBeenCalledWith(new Set([row.id]), component.rowData)
  })

  it('pins the focused pin cell with Enter or Space and suppresses grid shortcuts', () => {
    component.setRowData(new Set([1]))
    component.gridApi = {
      getSelectedRows: () => [],
    } as unknown as GridApi
    spyOn(component, 'setRowData')

    for (const key of ['Enter', ' ']) {
      const row = { ...component.rowData[0] }
      const event = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key })
      const setSelected = jasmine.createSpy('setSelected')
      spyOn(event, 'stopPropagation')

      const suppressed = component.onPinCellKeyDown(event, row, setSelected)

      expect(suppressed).toBeTrue()
      expect(event.defaultPrevented).toBeTrue()
      expect(event.stopPropagation).toHaveBeenCalled()
      expect(setSelected).toHaveBeenCalledOnceWith(true)
      expect(row.pinned).toBeTrue()
    }
  })

  it('does not suppress other pin-cell keyboard events', () => {
    const event = new KeyboardEvent('keydown', { key: 'ArrowDown' })
    const setSelected = jasmine.createSpy('setSelected')
    spyOn(component, 'togglePinned')

    const suppressed = component.onPinCellKeyDown(event, {} as ProfileColumn, setSelected)

    expect(suppressed).toBeFalse()
    expect(event.defaultPrevented).toBeFalse()
    expect(setSelected).not.toHaveBeenCalled()
    expect(component.togglePinned).not.toHaveBeenCalled()
  })

  it('captures deselection and clears pins before the delayed refresh', () => {
    component.setRowData(new Set([1]), [{ id: 1, order: 1, pinned: true }])
    const row = component.rowData[0]
    component.onRowSelected({ data: row, source: 'checkboxSelected', node: { isSelected: () => false } } as RowSelectedEvent)
    expect(component.getSelectedProfileColumns()).toEqual([])
    expect(row.pinned).toBeFalse()
  })

  it('retains detail profile order without enabling list-only pins', () => {
    component.profileType = 'detail'
    component.setRowData(new Set([1, 2]), [
      { id: 2, order: 1, pinned: true },
      { id: 1, order: 2, pinned: false },
    ])
    expect(component.getSelectedProfileColumns().map((row) => [row.id, row.pinned])).toEqual([
      [2, false],
      [1, false],
    ])
  })
})
