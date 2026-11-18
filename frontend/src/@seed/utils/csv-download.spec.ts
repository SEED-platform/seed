import { csvDownload } from './csv-download'

describe('csvDownload', () => {
  let anchor: HTMLAnchorElement
  let createObjectURL: jasmine.Spy

  beforeEach(() => {
    // Keeps downloadBlob's deferred revoke from running after the spies are gone
    jasmine.clock().install()
    anchor = document.createElement('a')
    spyOn(anchor, 'click')
    spyOn(document, 'createElement').and.returnValue(anchor)
    createObjectURL = spyOn(URL, 'createObjectURL').and.returnValue('blob:test')
    spyOn(URL, 'revokeObjectURL')
  })

  afterEach(() => {
    jasmine.clock().uninstall()
  })

  it('quotes every field and escapes quotes, commas, and newlines', async () => {
    csvDownload('meters', [
      { cycle: '2024 "Annual", v2', note: 'line 1\nline 2', count: 3, missing: null },
      { cycle: 'C:\\path', note: undefined, count: 0, missing: { id: 1 } },
    ])

    expect(anchor.download).toBe('meters.csv')
    expect(anchor.click).toHaveBeenCalled()
    const [blob] = createObjectURL.calls.mostRecent().args as [Blob]
    expect(await blob.text()).toBe(
      ['"cycle","note","count","missing"', '"2024 ""Annual"", v2","line 1\nline 2","3",""', '"C:\\path","","0","{""id"":1}"'].join('\n'),
    )
  })

  it('does nothing for an empty collection', () => {
    csvDownload('meters', [])

    expect(createObjectURL).not.toHaveBeenCalled()
    expect(anchor.click).not.toHaveBeenCalled()
  })
})
