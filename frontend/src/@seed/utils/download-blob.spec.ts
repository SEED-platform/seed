import { downloadBlob } from './download-blob'

describe('downloadBlob', () => {
  beforeEach(() => {
    jasmine.clock().install()
  })

  afterEach(() => {
    jasmine.clock().uninstall()
  })

  it('saves the blob with the file name and revokes its URL after the click', () => {
    const anchor = document.createElement('a')
    spyOn(anchor, 'click')
    spyOn(document, 'createElement').and.returnValue(anchor)
    const blob = new Blob(['data'])
    spyOn(URL, 'createObjectURL').and.returnValue('blob:test')
    const revokeObjectURL = spyOn(URL, 'revokeObjectURL')

    downloadBlob(blob, 'data.csv')

    expect(URL.createObjectURL).toHaveBeenCalledWith(blob)
    expect(anchor.href).toBe('blob:test')
    expect(anchor.download).toBe('data.csv')
    expect(anchor.click).toHaveBeenCalled()
    expect(revokeObjectURL).not.toHaveBeenCalled()

    jasmine.clock().tick(0)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test')
  })
})
