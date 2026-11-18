import { TestBed } from '@angular/core/testing'
import { ActivatedRoute, Router } from '@angular/router'
import { NEVER } from 'rxjs'
import { ConfigService, VersionService } from '@seed/api'
import { SeedNavigationService } from '@seed/components'
import { MediaWatcherService } from '@seed/services'
import { NavigationService } from 'app/core/navigation/navigation.service'
import { MainLayoutComponent } from './main.component'

describe('MainLayoutComponent', () => {
  it('clears nav hover when collapsing and expands on the next click', () => {
    let hovered = true
    const handleMouseLeave = jasmine.createSpy('handleMouseLeave').and.callFake(() => {
      hovered = false
    })

    TestBed.configureTestingModule({
      providers: [
        { provide: MediaWatcherService, useValue: { onMediaChange$: NEVER } },
        { provide: NavigationService, useValue: { getNavigation: () => [] } },
        { provide: SeedNavigationService, useValue: { getComponent: () => ({ handleMouseLeave }) } },
        { provide: VersionService, useValue: { version$: NEVER } },
        { provide: ConfigService, useValue: { config$: NEVER } },
        { provide: Router, useValue: { events: NEVER } },
        { provide: ActivatedRoute, useValue: {} },
      ],
    })

    const component = TestBed.runInInjectionContext(() => new MainLayoutComponent())
    component.navigationAppearance = 'default'
    component.toggleNavigationAppearance()
    expect(component.navigationAppearance).toBe('dense')
    expect(hovered).toBeFalse()
    expect(handleMouseLeave).toHaveBeenCalledTimes(1)

    component.toggleNavigationAppearance()
    expect(component.navigationAppearance).toBe('default')
    expect(handleMouseLeave).toHaveBeenCalledTimes(1)
  })
})
