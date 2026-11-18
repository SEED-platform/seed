import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import type { Observable } from 'rxjs'
import { BehaviorSubject, of, throwError } from 'rxjs'
import type { CurrentUser, OrganizationUserResponse, OrganizationUserSettings } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { ProfileSettingsComponent } from './settings.component'

describe('ProfileSettingsComponent', () => {
  let component: ProfileSettingsComponent
  let fixture: ComponentFixture<ProfileSettingsComponent>
  let currentUser: CurrentUser
  let scheme$: BehaviorSubject<'dark' | 'light'>
  let configChanges: { scheme: 'auto' | 'dark' | 'light' }[]
  let updateOrganizationUser: jasmine.Spy
  let showSuccess: jasmine.Spy

  beforeEach(async () => {
    currentUser = {
      id: 1,
      org_id: 2,
      org_user_id: 3,
      settings: { colorScheme: 'light' },
    } as CurrentUser
    scheme$ = new BehaviorSubject<'dark' | 'light'>('light')
    configChanges = []
    updateOrganizationUser = jasmine
      .createSpy('updateOrganizationUser')
      .and.callFake((_orgUserId: number, _orgId: number, settings: OrganizationUserSettings): Observable<OrganizationUserResponse> => {
        return of({ data: { settings }, status: 'success' } as OrganizationUserResponse)
      })
    showSuccess = jasmine.createSpy('success')

    await TestBed.configureTestingModule({
      imports: [ProfileSettingsComponent],
      providers: [
        { provide: UserService, useValue: { currentUser$: of(currentUser) } },
        { provide: OrganizationService, useValue: { updateOrganizationUser } },
        {
          provide: ConfigService,
          useValue: {
            scheme$: scheme$.asObservable(),
            set config(config: { scheme: 'auto' | 'dark' | 'light' }) {
              configChanges.push(config)
              scheme$.next(config.scheme === 'auto' ? 'light' : config.scheme)
            },
          },
        },
        { provide: SnackBarService, useValue: { success: showSuccess } },
      ],
    })
      .overrideComponent(ProfileSettingsComponent, { set: { template: '' } })
      .compileComponents()

    fixture = TestBed.createComponent(ProfileSettingsComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  afterEach(() => {
    fixture.destroy()
  })

  it('applies and persists a selected scheme', () => {
    component.setScheme('dark')

    expect(configChanges).toEqual([{ scheme: 'dark' }])
    expect(updateOrganizationUser).toHaveBeenCalledOnceWith(3, 2, { colorScheme: 'dark' })
    expect(currentUser.settings.colorScheme).toBe('dark')
    expect(showSuccess).toHaveBeenCalledOnceWith('Changes Saved')
    expect(component.saving).toBeFalse()
  })

  it('restores the previous scheme when persistence fails', () => {
    updateOrganizationUser.and.returnValue(throwError(() => new Error('Save failed')))

    component.setScheme('dark')

    expect(configChanges).toEqual([{ scheme: 'dark' }, { scheme: 'light' }])
    expect(currentUser.settings.colorScheme).toBe('light')
    expect(component.saving).toBeFalse()
  })

  it('does not save an already-persisted scheme again', () => {
    component.setScheme('light')

    expect(configChanges).toEqual([])
    expect(updateOrganizationUser).not.toHaveBeenCalled()
  })
})
