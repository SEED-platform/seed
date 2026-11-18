import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { BehaviorSubject, catchError, type Observable, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory'
import type { Note, NoteData } from './notes.types'

@Injectable({ providedIn: 'root' })
export class NoteService {
  private _errorService = inject(ErrorService)
  private _notes = new BehaviorSubject<Note[]>([])
  private _httpClient = inject(HttpClient)
  private _snackBar = inject(SnackBarService)

  notes$ = this._notes.asObservable()

  list(orgId: number, viewId: number, type: InventoryType) {
    const url = `/api/v3/${type}/${viewId}/notes/?organization_id=${orgId}`
    this._httpClient
      .get<Note[]>(url)
      .pipe(
        take(1),
        tap((notes) => {
          this._notes.next(notes)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching notes')
        }),
      )
      .subscribe()
  }

  create(orgId: number, viewId: number, noteData: NoteData, type: InventoryType): Observable<Note> {
    const url = `/api/v3/${type}/${viewId}/notes/`
    const body = { ...noteData, organization_id: orgId }
    return this._httpClient.post<Note>(url, body).pipe(
      tap(() => {
        this._snackBar.success('Note created successfully')
        this.list(orgId, viewId, type)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating note')
      }),
    )
  }

  update(orgId: number, viewId: number, noteId: number, noteData: NoteData, type: InventoryType): Observable<Note> {
    const url = `/api/v3/${type}/${viewId}/notes/${noteId}/`
    const body = { ...noteData, organization_id: orgId }
    return this._httpClient.put<Note>(url, body).pipe(
      tap(() => {
        this._snackBar.success('Note updated successfully')
        this.list(orgId, viewId, type)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating note')
      }),
    )
  }

  delete(orgId: number, viewId: number, noteId: number, type: InventoryType): Observable<void> {
    const url = `/api/v3/${type}/${viewId}/notes/${noteId}/?organization_id=${orgId}`
    return this._httpClient.delete<null>(url).pipe(
      tap(() => {
        this._snackBar.success('Note deleted successfully')
        this.list(orgId, viewId, type)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting note')
      }),
    )
  }
}
