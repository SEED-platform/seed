import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import type { MatDialogRef } from '@angular/material/dialog'
import { MatDialog } from '@angular/material/dialog'
import { MatTableDataSource } from '@angular/material/table'
import { combineLatest, filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { BriefOrganization, OrganizationUser, UserAuth } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import { DeleteModalComponent, PageComponent, TableContainerComponent } from '@seed/components'
import type { Config } from '@seed/components/page/page.types'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import { FormModalComponent } from './modal/form-modal.component'
import { ResetPasswordsModalComponent } from './modal/reset-passwords-modal.component'

@Component({
  selector: 'seed-organizations-members',
  templateUrl: './members.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, SharedImports, TableContainerComponent],
})
export class MembersComponent implements OnDestroy, OnInit {
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private _dialog = inject(MatDialog)
  private _organization: BriefOrganization

  private readonly _unsubscribeAll$ = new Subject<void>()
  auth: UserAuth

  membersDataSource = new MatTableDataSource<OrganizationUser>([])
  membersColumns = ['name', 'email', 'access level', 'access level instance', 'role', 'actions']

  ngOnInit(): void {
    // get org id and org users
    combineLatest([this._organizationService.currentOrganization$, this._organizationService.organizationUsers$, this._userService.auth$])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([organization, orgUsers, auth]) => {
        this._organization = organization
        this.membersDataSource.data = orgUsers.sort((a, b) => naturalSort(a.email, b.email))
        this.auth = auth
      })
  }

  get config() {
    const config: Config = { title: 'Members', titleIcon: 'fa-solid:users' }

    if (this.auth?.can_remove_member) {
      Object.assign(config, {
        action: this.resetPasswords,
        actionIcon: 'fa-solid:rotate-left',
        actionText: 'Reset All Passwords',
      })

      if (this.auth.can_invite_member) {
        Object.assign(config, {
          action2: this.inviteMember,
          action2Icon: 'fa-solid:plus',
          action2Text: 'Invite Member',
        })
      }
    }
    return config
  }

  getMembers(orgId: number): void {
    this._organizationService.getOrganizationUsers(orgId).subscribe()
  }

  editMember(member: OrganizationUser): void {
    const dialogRef: MatDialogRef<FormModalComponent, boolean> = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { member, orgId: this._organization.org_id },
    })

    this.fetchMembers(dialogRef)
  }

  deleteMember(member: OrganizationUser): void {
    const dialogRef: MatDialogRef<DeleteModalComponent, boolean> = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Member', instance: member.email },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        switchMap(() => this._organizationService.deleteOrganizationUser(member.user_id, this._organization.id)),
        tap(() => {
          this.getMembers(this._organization.org_id)
        }),
      )
      .subscribe()
  }

  resetPasswords = (): void => {
    const dialogRef: MatDialogRef<ResetPasswordsModalComponent, boolean> = this._dialog.open(ResetPasswordsModalComponent, {
      width: '40rem',
      data: { orgId: this._organization.org_id },
    })
    this.fetchMembers(dialogRef)
  }

  inviteMember = (): void => {
    const dialogRef: MatDialogRef<FormModalComponent, boolean> = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { member: null, orgId: this._organization.org_id },
    })

    this.fetchMembers(dialogRef)
  }

  fetchMembers(dialogRef: MatDialogRef<unknown, boolean>): void {
    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.getMembers(this._organization.org_id)
        }),
      )
      .subscribe()
  }

  trackByFn(_index: number, { email }: OrganizationUser) {
    return email
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
