import { Location } from '@angular/common'
import { provideLocationMocks } from '@angular/common/testing'
import { TestBed } from '@angular/core/testing'
import { provideRouter } from '@angular/router'
import { ColumnsComponent } from './columns.component'
import { ColumnGeocodingHelpComponent } from './geocoding/help.component'

describe('ColumnsComponent', () => {
  const setup = (path: string) => {
    TestBed.configureTestingModule({ providers: [provideRouter([]), provideLocationMocks()] })
    TestBed.inject(Location).go(path)
    // Construct directly: rendering the full template pulls in the whole drawer/nav component tree
    const component = TestBed.runInInjectionContext(() => new ColumnsComponent())
    component.ngOnInit()
    return component
  }

  it('falls back to the section title when no child route matches', () => {
    const component = setup('/organizations/columns')
    expect(component.pageTitle).toBe('Columns')
    expect(component.useTabs).toBeFalse()
    expect(component.helpComponent).toBeNull()
  })

  it('uses the matching child page info', () => {
    const component = setup('/organizations/columns/geocoding/taxlots')
    expect(component.pageTitle).toBe('Geocoding')
    expect(component.useTabs).toBeTrue()
    expect(component.helpComponent).toBe(ColumnGeocodingHelpComponent)
  })
})
