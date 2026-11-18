import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { combineLatest, filter, Subject, switchMap, tap } from 'rxjs'
import type { Note } from '@seed/api'
import { ColumnService, NoteService, OrganizationService, UserService } from '@seed/api'
import { DeleteModalComponent, NotFoundComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryStateType, InventoryType } from 'app/modules/inventory/inventory.types'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-inventory-detail-notes',
  templateUrl: './notes.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, NotFoundComponent, PageComponent],
})
export class NotesComponent implements OnDestroy, OnInit {
  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _dialog = inject(MatDialog)
  private _organizationService = inject(OrganizationService)
  private _notesService = inject(NoteService)
  private _userService = inject(UserService)
  private _route = inject(ActivatedRoute)
  private readonly _unsubscribeAll$ = new Subject<void>()

  displayName: string
  columnDefs: ColDef[]
  columnMap: Record<string, string> = {}
  viewId: number
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  gridHeight: number
  notes: Note[]
  orgId: number
  pageTitle: string
  rowData: Record<string, unknown>[] = []
  tableName: InventoryStateType
  type: InventoryType
  viewDisplayField$: Observable<string>

  ngOnInit(): void {
    this.getParams()
      .pipe(
        switchMap(() => this._userService.currentOrganizationId$),
        switchMap((orgId) => this.getDependencies(orgId)),
        tap(() => {
          this.setGrid()
        }),
      )
      .subscribe()
  }

  getParams() {
    return this._route.parent.paramMap.pipe(
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.type = params.get('type') as InventoryType
        this.displayName = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
        this.tableName = this.type === 'taxlots' ? 'TaxLotState' : 'PropertyState'
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, this.type)
      }),
    )
  }

  getDependencies(orgId: number) {
    this.orgId = orgId
    this._notesService.list(this.orgId, this.viewId, this.type)
    const columns$ = this.type === 'taxlots' ? this._columnService.taxLotColumns$ : this._columnService.propertyColumns$

    return combineLatest([this._notesService.notes$, columns$]).pipe(
      tap(([notes, columns]) => {
        this.notes = notes
        const typeColumns = columns.filter((c) => c.table_name === this.tableName)
        this.columnMap = Object.fromEntries(typeColumns.map((c) => [c.column_name, c.display_name]))
      }),
    )
  }

  setGrid() {
    this.setColumnDefs()
    this.setRowData()
    this.updateGridHeight()
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'id', hide: true },
      { field: 'created', headerName: 'Created', cellClass: 'text-secondary' },
      { field: 'content', headerName: 'Note', cellRenderer: this.noteTextRenderer, valueFormatter: ({ value }) => JSON.stringify(value) },
      { field: 'type', headerName: 'Type', cellClass: 'text-secondary' },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer },
    ]
  }

  setRowData() {
    this.rowData = []
    for (const note of this.notes) {
      const row = {
        id: note.id,
        created: this.formatDate(note.created),
        type: note.name,
        content: this.formatNoteContent(note),
      }
      this.rowData.push(row)
    }
  }

  formatDate(dateString: string) {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', { dateStyle: 'long', timeStyle: 'short' })
  }

  formatNoteContent(note: Note) {
    if (note.text) {
      return [`<li>${note.text}</li>`]
    }

    const content: string[] = []
    if (note.log_data?.length) {
      for (const log of note.log_data) {
        const displayName = this.columnMap[log.field] ?? log.field
        const newValue = typeof log.new_value === 'object' ? JSON.stringify(log.new_value) : log.new_value
        const previousValue = typeof log.previous_value === 'object' ? JSON.stringify(log.previous_value) : log.previous_value
        content.push(`<li>${displayName} : <span class="text-secondary">${previousValue} → ${newValue}</span></li>`)
      }
    }
    return content
  }

  noteTextRenderer = (params: { value: string[] }) => {
    return `<ul>${params.value.map((log) => `<li>${log}</li>`).join('')}</ul>`
  }

  actionRenderer = (params: { data: { type: 'Manually Created' } }) => {
    const canEdit = params.data.type === 'Manually Created'
    return `
      <div class="flex gap-2 mt-2 align-center">
      <span class="material-icons cursor-pointer text-secondary" title="Delete" data-action="delete">clear</span>
      ${canEdit ? '<span class="material-icons-outlined  cursor-pointer text-secondary" title="Edit" data-action="edit">edit</span>' : ''}
      </div>
    `
  }

  onGridReady(event: GridReadyEvent) {
    this.gridApi = event.api
    this.gridApi.sizeColumnsToFit()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'actions') return

    const target = event.event.target as HTMLElement
    const action = target.getAttribute('data-action')
    const { id } = event.data as { id: number }

    if (action === 'edit') {
      this.editNote(id)
    } else if (action === 'delete') {
      this.deleteNote(id)
    }
  }

  getRowHeight = (params: { data: { content: string[] } }) => {
    const contentLength = params.data.content.length
    return Math.max(contentLength * 40, 42)
  }

  updateGridHeight() {
    const div = document.querySelector('#content')
    if (!div) return 0

    const divHeight = div.getBoundingClientRect().height ?? 1
    this.gridHeight = Math.min(this.rowData.length * 42 + 50, divHeight)
  }

  createNote = () => {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewId: this.viewId, type: this.type, note: null },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap(() => {
          this.updateGridHeight()
        }),
      )
      .subscribe()
  }

  editNote(id: number) {
    const note = this.notes.find((n) => n.id === id)

    this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewId: this.viewId, type: this.type, note },
    })
  }

  deleteNote(id: number) {
    const note = this.notes.find((n) => n.id === id)
    const noteDate = `from ${this.formatDate(note.created)}`

    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Note', instance: noteDate },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._notesService.delete(this.orgId, this.viewId, id, this.type)),
        tap(() => {
          this.updateGridHeight()
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
