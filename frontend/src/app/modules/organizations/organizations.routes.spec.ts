import { Component } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import type { Routes } from '@angular/router'
import { provideRouter, Router, RouterOutlet, UrlSegment } from '@angular/router'
import { RouterTestingHarness } from '@angular/router/testing'
import columnsRoutes from './columns/columns.routes'
import organizationsRoutes, { dataQualityTypeMatcher, derivedColumnsTypeMatcher } from './organizations.routes'

@Component({ template: '<router-outlet />', imports: [RouterOutlet] })
class StubParentComponent {}

@Component({ template: '' })
class StubLeafComponent {}

// Keep the real paths, matchers and redirects, but swap heavy components, resolvers and lazy children for stubs
const stubRoutes = (routes: Routes, lazyChildren: Record<string, Routes> = {}): Routes =>
  routes.map(({ component, loadChildren, resolve: _resolve, canDeactivate: _canDeactivate, ...route }) => {
    if (loadChildren) {
      return { ...route, component: StubParentComponent, children: lazyChildren[route.path] ?? [{ path: '**', component: StubLeafComponent }] }
    }
    return component ? { ...route, component: StubLeafComponent } : route
  })

const segments = (...paths: string[]) => paths.map((path) => new UrlSegment(path, {}))

describe('Organizations routes', () => {
  describe('type matchers', () => {
    it('return null instead of throwing when there are no segments', () => {
      expect(dataQualityTypeMatcher([])).toBeNull()
      expect(derivedColumnsTypeMatcher([])).toBeNull()
    })

    it('match valid page/type pairs only', () => {
      expect(dataQualityTypeMatcher(segments('data-quality', 'goal'))?.posParams.type.path).toBe('goal')
      expect(derivedColumnsTypeMatcher(segments('derived-columns', 'taxlots'))?.posParams.type.path).toBe('taxlots')
      expect(derivedColumnsTypeMatcher(segments('derived-columns', 'goal'))).toBeNull()
      expect(dataQualityTypeMatcher(segments('data-quality'))).toBeNull()
    })
  })

  describe('navigation', () => {
    let router: Router

    beforeEach(() => {
      TestBed.configureTestingModule({
        providers: [
          provideRouter([
            {
              path: 'organizations',
              children: stubRoutes(organizationsRoutes, { columns: stubRoutes(columnsRoutes) }),
            },
          ]),
        ],
      })
      router = TestBed.inject(Router)
    })

    const navigate = async (url: string) => {
      const harness = await RouterTestingHarness.create()
      await harness.navigateByUrl(url)
      return router.url
    }

    it('redirects the bare organizations URL to settings', async () => {
      expect(await navigate('/organizations')).toBe('/organizations/settings')
    })

    it('redirects the bare columns URL to the property column list', async () => {
      expect(await navigate('/organizations/columns')).toBe('/organizations/columns/list/properties')
    })

    for (const url of [
      '/organizations/columns/list/taxlots',
      '/organizations/columns/geocoding/taxlots',
      '/organizations/columns/mappings',
      '/organizations/data-quality/goal',
      '/organizations/derived-columns/properties',
      '/organizations/members',
    ]) {
      it(`keeps the deep link ${url}`, async () => {
        expect(await navigate(url)).toBe(url)
      })
    }
  })
})
