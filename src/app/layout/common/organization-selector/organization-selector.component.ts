import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { TranslocoService } from '@jsverse/transloco'
import { filter, Subject, switchMap, takeUntil } from 'rxjs'
import type { BriefOrganization, CurrentUser } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { ConfirmationService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

// The confirmation dialog renders its message as HTML
const escapeHtml = (value: string): string =>
  value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;')

@Component({
  selector: 'seed-organization-selector',
  templateUrl: './organization-selector.component.html',
  encapsulation: ViewEncapsulation.None,
  exportAs: 'organization-selector',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, SharedImports],
})
export class OrganizationSelectorComponent implements OnInit, OnDestroy {
  private _confirmationService = inject(ConfirmationService)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _transloco = inject(TranslocoService)
  private _userService = inject(UserService)

  private readonly _unsubscribeAll$ = new Subject<void>()
  currentUser: CurrentUser
  organizations: BriefOrganization[]

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.currentUser = currentUser
    })
    this._organizationService.organizations$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organizations) => {
      this.organizations = [...organizations].sort((a, b) => a.name.localeCompare(b.name))
    })
  }

  selectOrganization(org: BriefOrganization) {
    if (org.user_role) {
      this._userService.setDefaultOrganization(org.id).pipe(takeUntil(this._unsubscribeAll$)).subscribe()
      return
    }

    // Only superusers can see organizations they aren't a member of
    if (!this.currentUser.is_superuser) {
      this._snackBar.alert(
        this._transloco.translate('You are not a member of "{{orgName}}" and cannot switch to it.', { orgName: org.name }),
      )
      return
    }
    this._joinOrganization(org)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  /*
   * Offer to add the superuser to the organization as an owner, then switch to it
   */
  private _joinOrganization(org: BriefOrganization) {
    const message = [
      `${this._transloco.translate("Your superuser account isn't a member of this organization:")} <strong>${escapeHtml(org.name)}</strong>`,
      this._transloco.translate('Would you like to add yourself as an owner so you can access it?'),
    ].join('<br /><br />')

    this._confirmationService
      .open({
        title: this._transloco.translate('Join Organization'),
        message,
        icon: { name: 'heroicons-outline:user-plus', color: 'primary' },
        actions: {
          confirm: { label: this._transloco.translate('Add Me as an Owner'), color: 'primary' },
          cancel: { label: this._transloco.translate('Cancel') },
        },
      })
      .afterClosed()
      .pipe(
        filter((result) => result === 'confirmed'),
        switchMap(() => this._organizationService.addUserToOrganization(org.id, this.currentUser.id)),
        // Refresh the list so the organization no longer shows as one they aren't a member of
        switchMap(() => this._organizationService.getBrief()),
        switchMap(() => this._userService.setDefaultOrganization(org.id)),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe({ error: () => undefined })
  }
}
