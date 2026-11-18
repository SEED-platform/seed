import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { NgxWigModule } from 'ngx-wig'
import { filter, map, Subject, switchMap, takeUntil, tap } from 'rxjs'
import { type EmailTemplate, PostOfficeService, UserService } from '@seed/api'
import { DeleteModalComponent, NotFoundComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-organizations-email-templates',
  templateUrl: './email-templates.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports, NgxWigModule, NotFoundComponent, PageComponent, ReactiveFormsModule],
})
export class EmailTemplatesComponent implements OnDestroy, OnInit {
  private _dialog = inject(MatDialog)
  private _orgId: number
  private _postOfficeService = inject(PostOfficeService)
  private _snackBarService = inject(SnackBarService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  helpOpened = false
  templates: EmailTemplate[]
  selectedTemplate: EmailTemplate
  selectedTemplateForm = new FormGroup({
    selectedTemplate: new FormControl<number | null>(null),
  })
  templateForm = new FormGroup({
    subject: new FormControl('', [Validators.required]),
    html_content: new FormControl('', [Validators.required]),
  })

  ngOnInit(): void {
    this._userService.currentOrganizationId$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((orgId) => {
          this._orgId = orgId
        }),
        switchMap(() => this._postOfficeService.emailTemplates$),
        map((templates) => templates.sort((a, b) => naturalSort(a.name, b.name))),
        tap((templates) => {
          this.templates = templates
          this.selectedTemplate = this.templates[0]
          this.setForm()
        }),
      )
      .subscribe()
  }

  setForm() {
    if (this.selectedTemplate) {
      this.selectedTemplateForm.get('selectedTemplate').setValue(this.selectedTemplate.id)
      this.selectTemplate()
    } else {
      this.selectedTemplateForm.reset()
      this.templateForm.reset({}, { emitEvent: false })
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  toggleHelp = () => {
    this.helpOpened = !this.helpOpened
  }

  selectTemplate() {
    this.selectedTemplate = this.templates.find((t) => t.id === this.selectedTemplateForm.get('selectedTemplate').value)
    this.templateForm.get('subject').patchValue(this.selectedTemplate.subject)
    this.templateForm.get('html_content').patchValue(this.selectedTemplate.html_content)
  }

  refreshTemplates(selectedId: number | null): void {
    this._postOfficeService.getEmailTemplates(this._orgId).subscribe(() => {
      if (selectedId) {
        this.selectedTemplateForm.get('selectedTemplate').setValue(selectedId)
        this.selectTemplate()
      } else {
        this.selectedTemplateForm.get('selectedTemplate').setValue(this.templates[0].id)
        this.selectTemplate()
      }
    })
  }

  rename() {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { template: this.selectedTemplate, organization_id: this._orgId },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.refreshTemplates(this.selectedTemplate.id)
        }),
      )
      .subscribe()
  }

  create() {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { organization_id: this._orgId },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((newId: number) => {
          this.refreshTemplates(newId)
        }),
      )
      .subscribe()
  }

  delete() {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Email Template', instance: this.selectedTemplate.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        switchMap(() => this._postOfficeService.delete(this.selectedTemplate.id, this._orgId)),
        tap(() => {
          this.refreshTemplates(null)
        }),
      )
      .subscribe()
  }

  save() {
    const html = this.templateForm.get('html_content').value
    const div = document.createElement('div')
    div.innerHTML = html
    const text = div.textContent || div.innerText || ''
    this.selectedTemplate.subject = this.templateForm.get('subject').value
    this.selectedTemplate.html_content = html
    this.selectedTemplate.content = text
    this._postOfficeService.update(this._orgId, this.selectedTemplate).subscribe(() => {
      this.refreshTemplates(this.selectedTemplate.id)
      this._snackBarService.success('Template Updated')
    })
  }
}
