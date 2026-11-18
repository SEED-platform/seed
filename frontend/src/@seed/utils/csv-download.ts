import { downloadBlob } from './download-blob'

// Quote every field and double embedded quotes (RFC 4180), so commas, quotes, and newlines survive
const csvField = (value: unknown) => {
  const text = value == null ? '' : typeof value === 'string' ? value : JSON.stringify(value)
  return `"${text.replaceAll('"', '""')}"`
}

export const csvDownload = (title: string, data: Record<string, unknown>[]) => {
  if (!data.length) return

  const headers = Object.keys(data[0])
  const csv = [headers, ...data.map((row) => headers.map((header) => row[header]))]
    .map((fields) => fields.map(csvField).join(','))
    .join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `${title}.csv`)
}
