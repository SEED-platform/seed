import { TestBed } from '@angular/core/testing'
import { ConfirmationService } from '../confirmation'
import { TermsService } from './terms.service'

const TEST_EMAIL = 'test@example.com'
const ACCEPTED_AT_KEY = `nlrTermsAcceptedAt:${TEST_EMAIL}`
const ACCEPTANCE_DAYS = 90
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000

describe('TermsService', () => {
  let service: TermsService

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: ConfirmationService, useValue: { open: jasmine.createSpy('open') } }],
    })
    service = TestBed.inject(TermsService)
    localStorage.removeItem(ACCEPTED_AT_KEY)
    jasmine.clock().install()
    jasmine.clock().mockDate(new Date('2026-01-01T00:00:00Z'))
  })

  afterEach(() => {
    localStorage.removeItem(ACCEPTED_AT_KEY)
    jasmine.clock().uninstall()
  })

  it('records acceptance in browser storage', () => {
    service.recordTermsAcceptance(TEST_EMAIL)

    expect(localStorage.getItem(ACCEPTED_AT_KEY)).toBe(Date.now().toString())
    expect(service.hasAcceptedTerms(TEST_EMAIL)).toBeTrue()
  })

  it('keeps acceptance valid for less than 90 days', () => {
    localStorage.setItem(ACCEPTED_AT_KEY, (Date.now() - ACCEPTANCE_DAYS * MILLISECONDS_PER_DAY + 1).toString())

    expect(service.hasAcceptedTerms(TEST_EMAIL)).toBeTrue()
  })

  it('expires acceptance after 90 days', () => {
    localStorage.setItem(ACCEPTED_AT_KEY, (Date.now() - ACCEPTANCE_DAYS * MILLISECONDS_PER_DAY).toString())

    expect(service.hasAcceptedTerms(TEST_EMAIL)).toBeFalse()
  })

  it('rejects missing, malformed, and future acceptance dates', () => {
    expect(service.hasAcceptedTerms(TEST_EMAIL)).toBeFalse()

    localStorage.setItem(ACCEPTED_AT_KEY, 'not-a-date')
    expect(service.hasAcceptedTerms(TEST_EMAIL)).toBeFalse()

    localStorage.setItem(ACCEPTED_AT_KEY, (Date.now() + 1).toString())
    expect(service.hasAcceptedTerms(TEST_EMAIL)).toBeFalse()
  })

  it('does not share acceptance between different accounts', () => {
    service.recordTermsAcceptance(TEST_EMAIL)

    expect(service.hasAcceptedTerms('other@example.com')).toBeFalse()
  })
})
