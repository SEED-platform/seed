import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { MatIconTestingModule } from '@angular/material/icon/testing'
import { of, throwError } from 'rxjs'
import type { BriefOrganization, CurrentUser } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import { ConfirmationService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { getTranslocoTestingModule } from 'app/core/transloco/transloco-testing'
import { OrganizationSelectorComponent } from './organization-selector.component'

// Superusers see every organization but can only use the ones they are a member of, so picking another one offers to
// add them as an owner instead of refusing to switch (SEED issue #4618)
describe('OrganizationSelectorComponent', () => {
  let component: OrganizationSelectorComponent
  let fixture: ComponentFixture<OrganizationSelectorComponent>
  let organizationService: jasmine.SpyObj<OrganizationService>
  let userService: jasmine.SpyObj<UserService>
  let confirmationService: jasmine.SpyObj<ConfirmationService>
  let snackBar: jasmine.SpyObj<SnackBarService>

  const memberOrg = { id: 1, name: 'Member Org', user_role: 'owner' } as BriefOrganization
  const otherOrg = { id: 2, name: 'Other <Org>', user_role: null } as BriefOrganization

  const setup = async (currentUser: Partial<CurrentUser>, dialogResult = 'confirmed') => {
    organizationService = jasmine.createSpyObj<OrganizationService>('OrganizationService', ['addUserToOrganization', 'getBrief'], {
      organizations$: of([memberOrg, otherOrg]),
    })
    organizationService.addUserToOrganization.and.returnValue(of({ status: 'success' }))
    organizationService.getBrief.and.returnValue(of([memberOrg, { ...otherOrg, user_role: 'owner' }]))
    userService = jasmine.createSpyObj<UserService>('UserService', ['setDefaultOrganization'], { currentUser$: of(currentUser as CurrentUser) })
    userService.setDefaultOrganization.and.returnValue(of({ status: 'success' } as never))
    confirmationService = jasmine.createSpyObj<ConfirmationService>('ConfirmationService', ['open'])
    confirmationService.open.and.returnValue({ afterClosed: () => of(dialogResult) } as never)
    snackBar = jasmine.createSpyObj<SnackBarService>('SnackBarService', ['alert'])

    await TestBed.configureTestingModule({
      imports: [OrganizationSelectorComponent, MatIconTestingModule, getTranslocoTestingModule()],
      providers: [
        { provide: OrganizationService, useValue: organizationService },
        { provide: UserService, useValue: userService },
        { provide: ConfirmationService, useValue: confirmationService },
        { provide: SnackBarService, useValue: snackBar },
      ],
    }).compileComponents()

    fixture = TestBed.createComponent(OrganizationSelectorComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  }

  it('switches to an organization the user is a member of without asking', async () => {
    await setup({ id: 3, is_superuser: true, org_name: 'Member Org' })

    component.selectOrganization(memberOrg)

    expect(confirmationService.open).not.toHaveBeenCalled()
    expect(userService.setDefaultOrganization).toHaveBeenCalledOnceWith(1)
  })

  it('offers to add a superuser to an organization they are not a member of, then switches to it', async () => {
    await setup({ id: 3, is_superuser: true, org_name: 'Member Org' })

    component.selectOrganization(otherOrg)

    expect(confirmationService.open).toHaveBeenCalledTimes(1)
    const { message } = confirmationService.open.calls.mostRecent().args[0]
    expect(message).toContain('<strong>Other &lt;Org&gt;</strong>')
    expect(organizationService.addUserToOrganization).toHaveBeenCalledOnceWith(2, 3)
    expect(organizationService.getBrief).toHaveBeenCalled()
    expect(userService.setDefaultOrganization).toHaveBeenCalledOnceWith(2)
  })

  it('stays on the current organization when the superuser declines', async () => {
    await setup({ id: 3, is_superuser: true, org_name: 'Member Org' }, 'canceled')

    component.selectOrganization(otherOrg)

    expect(organizationService.addUserToOrganization).not.toHaveBeenCalled()
    expect(userService.setDefaultOrganization).not.toHaveBeenCalled()
  })

  it('does not switch when adding the superuser fails', async () => {
    await setup({ id: 3, is_superuser: true, org_name: 'Member Org' })
    organizationService.addUserToOrganization.and.returnValue(throwError(() => new Error('Forbidden')))

    component.selectOrganization(otherOrg)

    expect(userService.setDefaultOrganization).not.toHaveBeenCalled()
  })

  it('still refuses a non-superuser who somehow sees an organization they are not a member of', async () => {
    await setup({ id: 4, is_superuser: false, org_name: 'Member Org' })

    component.selectOrganization(otherOrg)

    expect(confirmationService.open).not.toHaveBeenCalled()
    expect(snackBar.alert).toHaveBeenCalled()
    expect(userService.setDefaultOrganization).not.toHaveBeenCalled()
  })
})
