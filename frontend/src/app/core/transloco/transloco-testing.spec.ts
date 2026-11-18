import { TestBed } from '@angular/core/testing'
import { TranslocoService } from '@jsverse/transloco'
import { getTranslocoTestingModule } from './transloco-testing'

describe('getTranslocoTestingModule', () => {
  it('should configure English without requiring a translation dictionary', async () => {
    await TestBed.configureTestingModule({
      imports: [getTranslocoTestingModule()],
    }).compileComponents()

    const service = TestBed.inject(TranslocoService)
    expect(service.getDefaultLang()).toBe('en_US')
    expect(service.getActiveLang()).toBe('en_US')
    expect(service.getTranslation('en_US')).toEqual({})
  })

  it('should preload test-specific translations and support interpolation', async () => {
    const translations = { Greeting: 'Hello {{ name }}' }
    await TestBed.configureTestingModule({
      imports: [getTranslocoTestingModule(translations)],
    }).compileComponents()

    const service = TestBed.inject(TranslocoService)
    expect(service.getTranslation('en_US')).toEqual(translations)
    expect(service.translate('Greeting', { name: 'SEED' })).toBe('Hello SEED')
  })
})
