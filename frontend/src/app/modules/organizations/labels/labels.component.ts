import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { MatTableDataSource } from '@angular/material/table'
import { filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Label, Organization } from '@seed/api'
import { LabelService, OrganizationService } from '@seed/api'
import { DeleteModalComponent, LabelComponent, PageComponent, TableContainerComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { FormModalComponent } from './modal'

@Component({
  selector: 'seed-organizations-labels',
  templateUrl: './labels.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [LabelComponent, PageComponent, TableContainerComponent, MaterialImports],
})
export class LabelsComponent implements OnInit, OnDestroy {
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _organizationService = inject(OrganizationService)
  private _labelService = inject(LabelService)
  private _dialog = inject(MatDialog)
  labels: Label[]
  organization: Organization
  labelsDataSource = new MatTableDataSource<Label>([])
  labelColumns = ['label', 'shown in list', 'actions']
  allVisible = true

  ngOnInit(): void {
    this._labelService.labels$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((labels) => {
      this.labelsDataSource.data = labels
      if (labels.find((l) => !l.show_in_list)) {
        this.allVisible = false
      }
    })
    this._organizationService.currentOrganization$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organization) => {
      this.organization = organization
    })
  }

  toggleAllShown = (): void => {
    this._labelService.bulkUpdate(this.organization.id, this.labelsDataSource.data, !this.allVisible).subscribe(() => {
      this.refreshLabels()
      this.allVisible = !this.allVisible
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  refreshLabels(): void {
    this._labelService.getByOrgId(this.organization.id).subscribe()
  }

  edit(label: Label) {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { label, organization_id: this.organization.id },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.refreshLabels()
        }),
      )
      .subscribe()
  }

  delete(label: Label) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Label', instance: label.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        switchMap(() => this._labelService.delete(label)),
        tap(() => {
          this.refreshLabels()
        }),
      )
      .subscribe()
  }

  create = () => {
    const newLabel: Omit<Label, 'id' | 'name' | 'color'> = {
      organization_id: this.organization.id,
      show_in_list: true,
    }
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { label: newLabel },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.refreshLabels()
        }),
      )
      .subscribe()
  }
}
