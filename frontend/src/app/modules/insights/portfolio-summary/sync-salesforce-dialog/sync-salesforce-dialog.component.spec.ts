import { NO_ERRORS_SCHEMA } from '@angular/core'
import type { ComponentFixture } from '@angular/core/testing'
import { fakeAsync, TestBed, tick } from '@angular/core/testing'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { of, Subject, throwError } from 'rxjs'
import type { CycleGoal, Goal, Organization, SalesforceSummaryResponse } from '@seed/api'
import { GoalService } from '@seed/api'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { SyncSalesforceData } from '../portfolio-summary.types'
import { SyncSalesforceDialogComponent } from './sync-salesforce-dialog.component'

// ─── Mock data ────────────────────────────────────────────────────────────────

const mockGoal: Goal = {
  id: 1,
  name: 'Test Goal',
  organization: 2,
  access_level_instance: 1,
  access_level_instance_name: 'Root',
  area_column: 1,
  area_column_name: 'Gross Floor Area',
  baseline_cycle: 1,
  baseline_cycle_name: 'FY2020',
  commitment_sqft: 100000,
  eui_column1: 1,
  eui_column1_name: 'Site EUI',
  level_name: 'Organization',
  level_name_index: 0,
  partner_note: '',
  partner_note_approval: false,
  salesforce_partner_id: 'P001',
  salesforce_partner_name: 'Test Partner',
  salesforce_goal_id: 'G001',
  salesforce_goal_name: 'Test SF Goal',
  target_percentage: 20,
  type: 'standard',
  cycle_goals: [],
}

const mockCycleGoal: CycleGoal = {
  id: 10,
  current_cycle: { id: 5, name: 'FY2024', start: '2024-01-01', end: '2024-12-31' },
}

const mockOrganization = { id: 2 } as Organization

const mockDialogData: SyncSalesforceData = {
  goal: mockGoal,
  currentCycleGoal: mockCycleGoal,
  organization: mockOrganization,
}

const mockSeedSummary = {
  baseline_cycle_name: 'FY2020',
  baseline_total_sqft: 500000,
  baseline_total_kbtu: 10000000,
  baseline_weighted_eui: 100,
  total_properties: 50,
  shared_sqft: 450000,
  total_passing: 40,
  total_new_or_acquired: 5,
  passing_committed: 35,
  passing_shared: 30,
  current_cycle_name: 'FY2024',
  current_total_sqft: 480000,
  current_total_kbtu: '9000000',
  current_weighted_eui: 88,
  sqft_change: -20000,
  eui_change: -12,
}

const mockSfReport = {
  id: 'AR001',
  baseline_portfolio_kbtu: 10000000,
  baseline_portfolio_eui: 100,
  reporting_year_start: '2024-01-01',
  reporting_year_end: '2024-12-31',
  number_of_properties: 50,
  portfolio_average_eui: 88,
  shared_square_feet: 450000,
  reviewed_square_feet: 480000,
  ei_annual_improvement: 12,
  portfolio_kbtu: 9000000,
  total_ei_improvement: -12,
  new_energy_savings: 1000000,
  report_status: '06. Annual report reviewed by staff',
  review_status: 'B. Report in Progress',
}

const mockSummaryResponse: SalesforceSummaryResponse = {
  FY2024: { id: 10, seed: mockSeedSummary, salesforce: mockSfReport },
  FY2023: {
    id: 9,
    seed: { ...mockSeedSummary, current_cycle_name: 'FY2023', current_total_kbtu: '9200000', current_weighted_eui: 90, eui_change: -10 },
    salesforce: {
      ...mockSfReport,
      id: 'AR002',
      portfolio_average_eui: 91,
      ei_annual_improvement: 10,
      new_energy_savings: 800000,
      portfolio_kbtu: 9200000,
    },
  },
}

// ─── Suite ────────────────────────────────────────────────────────────────────

describe('SyncSalesforceDialogComponent', () => {
  let component: SyncSalesforceDialogComponent
  let fixture: ComponentFixture<SyncSalesforceDialogComponent>
  let getSalesforceSummarySpy: jasmine.Spy
  let updateSalesforceCurrentSpy: jasmine.Spy
  let updateSalesforceHistoricalSpy: jasmine.Spy
  let dialogRefCloseSpy: jasmine.Spy
  let snackBarSuccessSpy: jasmine.Spy

  beforeEach(async () => {
    getSalesforceSummarySpy = jasmine.createSpy('getSalesforceSummary').and.returnValue(of(mockSummaryResponse))
    updateSalesforceCurrentSpy = jasmine.createSpy('updateSalesforceCurrent').and.returnValue(of({ status: 'success' }))
    updateSalesforceHistoricalSpy = jasmine.createSpy('updateSalesforceHistorical').and.returnValue(of({ status: 'success' }))
    dialogRefCloseSpy = jasmine.createSpy('close')
    snackBarSuccessSpy = jasmine.createSpy('success')

    await TestBed.configureTestingModule({
      imports: [SyncSalesforceDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: MatDialogRef, useValue: { close: dialogRefCloseSpy } },
        {
          provide: GoalService,
          useValue: {
            getSalesforceSummary: getSalesforceSummarySpy,
            updateSalesforceCurrent: updateSalesforceCurrentSpy,
            updateSalesforceHistorical: updateSalesforceHistoricalSpy,
          },
        },
        { provide: SnackBarService, useValue: { success: snackBarSuccessSpy } },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    })
      .overrideComponent(SyncSalesforceDialogComponent, {
        set: {
          // Strip TranslocoDirective and Material imports — tests cover class logic only
          template: '<div></div>',
          imports: [],
          schemas: [NO_ERRORS_SCHEMA],
        },
      })
      .compileComponents()

    fixture = TestBed.createComponent(SyncSalesforceDialogComponent)
    component = fixture.componentInstance
    // Do not call fixture.detectChanges() here — each group controls timing
  })

  afterEach(() => {
    fixture.destroy()
  })

  // ─── Creation ───────────────────────────────────────────────────────────────

  it('should create', () => {
    fixture.detectChanges()
    expect(component).toBeTruthy()
  })

  // ─── Loading state ───────────────────────────────────────────────────────────

  describe('loading state', () => {
    it('should not start loading before ngOnInit setTimeout fires', () => {
      fixture.detectChanges() // schedules setTimeout but does not fire it
      expect(component.isLoading).toBeFalse()
    })

    it('should be loading while the request is in-flight', fakeAsync(() => {
      const pending$ = new Subject<SalesforceSummaryResponse>()
      getSalesforceSummarySpy.and.returnValue(pending$.asObservable())
      fixture.detectChanges()
      tick(0)
      expect(component.isLoading).toBeTrue()
      pending$.complete()
    }))

    it('should finish loading after the summary response arrives', fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
      expect(component.isLoading).toBeFalse()
    }))

    it('should set isLoading false when the request errors', fakeAsync(() => {
      getSalesforceSummarySpy.and.returnValue(throwError(() => new Error('500')))
      fixture.detectChanges()
      tick(0)
      expect(component.isLoading).toBeFalse()
    }))
  })

  // ─── Summary processing ──────────────────────────────────────────────────────

  describe('after summary loads', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
    }))

    it('should set latestEntry for the current cycle', () => {
      expect(component.latestEntry?.id).toBe(10)
    })

    it('should put non-current cycles into pastEntries', () => {
      expect(component.pastEntries.length).toBe(1)
      expect(component.pastEntries[0][0]).toBe('FY2023')
    })

    it('should build 2 baseline rows', () => {
      expect(component.baselineRows.length).toBe(2)
    })

    it('should map baseline kBtu from seed and salesforce correctly', () => {
      const row = component.baselineRows[0]
      expect(row.label).toBe('Baseline portfolio kBtu')
      expect(row.seed).toBe(10000000)
      expect(row.salesforce).toBe(10000000)
    })

    it('should build 10 current-year rows', () => {
      expect(component.currentYearRows.length).toBe(10)
    })

    it('should use the cycle start/end dates from the CycleGoal', () => {
      const startRow = component.currentYearRows.find((r) => r.label === 'Reporting Year Start')
      expect(startRow?.seed).toBe('2024-01-01')
    })

    it('should compute New Energy Savings as baseline_kbtu − current_kbtu', () => {
      const row = component.currentYearRows.find((r) => r.label === 'New Energy Savings')
      expect(row?.seed).toBe(10000000 - 9000000)
    })

    it('should populate reportStatus from the Salesforce annual report', () => {
      expect(component.reportStatus).toBe('06. Annual report reviewed by staff')
    })

    it('should populate reviewStatus from the Salesforce annual report', () => {
      expect(component.reviewStatus).toBe('B. Report in Progress')
    })

    it('should build one past-cycle row', () => {
      expect(component.pastCycleRows.length).toBe(1)
    })

    it('should include the Salesforce annual report ID in the past cycle name', () => {
      expect(component.pastCycleRows[0].cycleName).toContain('AR002')
    })

    it('should compute seedEiAnnual for past cycles as baseline_eui − current_eui', () => {
      // baseline_weighted_eui: 100, current_weighted_eui: 90 → 10
      expect(component.pastCycleRows[0].seedEiAnnual).toBe(10)
    })
  })

  // ─── hasSfData ───────────────────────────────────────────────────────────────

  describe('hasSfData', () => {
    it('should be false before any data loads', () => {
      fixture.detectChanges()
      expect(component.hasSfData).toBeFalse()
    })

    it('should be true after loading when the latest entry has Salesforce data', fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
      expect(component.hasSfData).toBeTrue()
    }))

    it('should be false when the latest entry has an empty salesforce object', fakeAsync(() => {
      const noSfData: SalesforceSummaryResponse = { FY2024: { id: 10, seed: mockSeedSummary, salesforce: {} } }
      getSalesforceSummarySpy.and.returnValue(of(noSfData))
      fixture.detectChanges()
      tick(0)
      expect(component.hasSfData).toBeFalse()
    }))
  })

  // ─── isMismatch / isMatch ────────────────────────────────────────────────────

  describe('isMismatch', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
    }))

    it('should return false when the values are equal', () => {
      expect(component.isMismatch(100, 100)).toBeFalse()
    })

    it('should return true when the values differ', () => {
      expect(component.isMismatch(100, 90)).toBeTrue()
    })

    it('should return false when hasSfData is false regardless of values', fakeAsync(() => {
      const noSfData: SalesforceSummaryResponse = { FY2024: { id: 10, seed: mockSeedSummary, salesforce: {} } }
      getSalesforceSummarySpy.and.returnValue(of(noSfData))
      const ctx1 = component as unknown as { _loadSummary: () => void }
      ctx1._loadSummary()
      expect(component.isMismatch(100, 90)).toBeFalse()
    }))
  })

  describe('isMatch', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
    }))

    it('should return true when the values are equal', () => {
      expect(component.isMatch(100, 100)).toBeTrue()
    })

    it('should return false when the values differ', () => {
      expect(component.isMatch(100, 90)).toBeFalse()
    })

    it('should return false when hasSfData is false regardless of values', fakeAsync(() => {
      const noSfData: SalesforceSummaryResponse = { FY2024: { id: 10, seed: mockSeedSummary, salesforce: {} } }
      getSalesforceSummarySpy.and.returnValue(of(noSfData))
      const ctx2 = component as unknown as { _loadSummary: () => void }
      ctx2._loadSummary()
      expect(component.isMatch(100, 100)).toBeFalse()
    }))
  })

  // ─── goalDetails ─────────────────────────────────────────────────────────────

  describe('goalDetails', () => {
    beforeEach(() => {
      fixture.detectChanges()
    })

    it('should format the partner label with name and ID', () => {
      expect(component.goalDetails[0]).toEqual({ label: 'Salesforce Partner', value: 'Test Partner (P001)' })
    })

    it('should format the goal label with name and ID', () => {
      expect(component.goalDetails[1]).toEqual({ label: 'Salesforce Goal', value: 'Test SF Goal (G001)' })
    })

    it('should render empty strings gracefully when salesforce fields are undefined', () => {
      component.data = {
        ...mockDialogData,
        goal: { ...mockGoal, salesforce_partner_name: undefined, salesforce_partner_id: undefined },
      }
      expect(component.goalDetails[0].value).toBe(' ()')
    })
  })

  // ─── syncCurrent ─────────────────────────────────────────────────────────────

  describe('syncCurrent', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
      getSalesforceSummarySpy.calls.reset()
    }))

    it('should call updateSalesforceCurrent with the correct arguments', () => {
      component.reportStatus = '06. Annual report reviewed by staff'
      component.reviewStatus = 'B. Report in Progress'
      component.syncCurrent()
      expect(updateSalesforceCurrentSpy).toHaveBeenCalledWith(1, 10, '06. Annual report reviewed by staff', 'B. Report in Progress', 2)
    })

    it('should show a success snackbar', () => {
      component.syncCurrent()
      expect(snackBarSuccessSpy).toHaveBeenCalledWith('Salesforce goal and current annual report updated successfully')
    })

    it('should reload the summary on success', () => {
      component.syncCurrent()
      expect(getSalesforceSummarySpy).toHaveBeenCalledWith(1, 2)
    })

    it('should not call the service when latestEntry is null', () => {
      component.latestEntry = null
      component.syncCurrent()
      expect(updateSalesforceCurrentSpy).not.toHaveBeenCalled()
    })

    it('should set isLoading true at the start of the sync', () => {
      const pending$ = new Subject<{ status: string }>()
      updateSalesforceCurrentSpy.and.returnValue(pending$.asObservable())
      component.syncCurrent()
      expect(component.isLoading).toBeTrue()
      pending$.complete()
    })

    it('should set isLoading false on error', () => {
      updateSalesforceCurrentSpy.and.returnValue(throwError(() => new Error('error')))
      component.syncCurrent()
      expect(component.isLoading).toBeFalse()
    })
  })

  // ─── syncHistorical ──────────────────────────────────────────────────────────

  describe('syncHistorical', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges()
      tick(0)
      getSalesforceSummarySpy.calls.reset()
    }))

    it('should call updateSalesforceHistorical with past cycle goal IDs', () => {
      component.syncHistorical()
      expect(updateSalesforceHistoricalSpy).toHaveBeenCalledWith(1, [9], 2)
    })

    it('should show a success snackbar', () => {
      component.syncHistorical()
      expect(snackBarSuccessSpy).toHaveBeenCalledWith('Salesforce historical reports updated successfully')
    })

    it('should reload the summary on success', () => {
      component.syncHistorical()
      expect(getSalesforceSummarySpy).toHaveBeenCalledWith(1, 2)
    })

    it('should not call the service when there are no past entries', () => {
      component.pastEntries = []
      component.syncHistorical()
      expect(updateSalesforceHistoricalSpy).not.toHaveBeenCalled()
    })

    it('should set isLoading true at the start of the sync', () => {
      const pending$ = new Subject<{ status: string }>()
      updateSalesforceHistoricalSpy.and.returnValue(pending$.asObservable())
      component.syncHistorical()
      expect(component.isLoading).toBeTrue()
      pending$.complete()
    })

    it('should set isLoading false on error', () => {
      updateSalesforceHistoricalSpy.and.returnValue(throwError(() => new Error('error')))
      component.syncHistorical()
      expect(component.isLoading).toBeFalse()
    })
  })

  // ─── Error handling ──────────────────────────────────────────────────────────

  describe('error handling', () => {
    it('should set hasError true when the summary request fails', fakeAsync(() => {
      getSalesforceSummarySpy.and.returnValue(throwError(() => new Error('500')))
      fixture.detectChanges()
      tick(0)
      expect(component.hasError).toBeTrue()
    }))

    it('should clear hasError on a subsequent successful load', fakeAsync(() => {
      getSalesforceSummarySpy.and.returnValue(throwError(() => new Error('500')))
      fixture.detectChanges()
      tick(0)
      expect(component.hasError).toBeTrue()

      getSalesforceSummarySpy.and.returnValue(of(mockSummaryResponse))
      const ctx3 = component as unknown as { _loadSummary: () => void }
      ctx3._loadSummary()
      expect(component.hasError).toBeFalse()
    }))
  })

  // ─── dismiss ─────────────────────────────────────────────────────────────────

  describe('dismiss', () => {
    it('should call dialogRef.close()', () => {
      fixture.detectChanges()
      component.dismiss()
      expect(dialogRefCloseSpy).toHaveBeenCalled()
    })
  })
})
