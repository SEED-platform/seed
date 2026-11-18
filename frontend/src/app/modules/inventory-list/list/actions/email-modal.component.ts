import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { RouterModule } from '@angular/router'
import { finalize, Subject, take, tap } from 'rxjs'
import type { EmailTemplate } from '@seed/api'
import { PostOfficeService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-email-modal',
  templateUrl: './email-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ModalHeaderComponent, RouterModule],
})
export class EmailModalComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<EmailModalComponent>)
  private _postOfficeService = inject(PostOfficeService)
  private _snackBar = inject(SnackBarService)
  private _unsubscribeAll$ = new Subject<void>()

  emailTemplates: EmailTemplate[] = []
  selectedTemplateId: number

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    stateIds: number[];
    type: InventoryType;
  }

  ngOnInit(): void {
    this._postOfficeService
      .getEmailTemplates(this.data.orgId)
      .pipe(
        tap((emailTemplates) => {
          this.emailTemplates = emailTemplates
          this.selectedTemplateId = emailTemplates[0]?.id
        }),
        take(1),
      )
      .subscribe()
  }

  // selectTemplate()
  onSubmit() {
    this._postOfficeService
      .sendEmail(this.data.orgId, this.data.stateIds, this.selectedTemplateId, this.data.type)
      .pipe(
        take(1),
        finalize(() => {
          this.close()
        }),
      )
      .subscribe()
  }

  close() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
