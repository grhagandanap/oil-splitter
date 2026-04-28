/**
 * Minimal client-side TSV / CSV parser used for the paste-from-spreadsheet
 * flow. The first row is treated as the header. Cells that look numeric are
 * converted to numbers (so the backend's float coercion succeeds without an
 * extra round trip).
 *
 * The parser intentionally stays small — it does not handle quoted fields with
 * embedded delimiters. Most spreadsheet copy-paste payloads are tab-delimited
 * and free of quotes, so this trade-off keeps the dependency surface tiny.
 */

export type ParsedTable = {
  headers: string[]
  rows: Array<Record<string, unknown>>
  delimiter: string
}

export function detectDelimiter(text: string): string {
  const firstLine = text.split(/\r?\n/, 1)[0] ?? ''
  if (firstLine.includes('\t')) return '\t'
  if (firstLine.includes(';')) return ';'
  return ','
}

function coerceCell(value: string): unknown {
  const trimmed = value.trim()
  if (trimmed === '') return null

  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    const asNumber = Number(trimmed)
    if (Number.isFinite(asNumber)) return asNumber
  }

  return trimmed
}

export function parseTable(text: string, delimiter?: string): ParsedTable {
  const cleanText = text.replace(/\r\n?/g, '\n').trim()
  if (!cleanText) {
    return { headers: [], rows: [], delimiter: delimiter ?? '\t' }
  }

  const sep = delimiter ?? detectDelimiter(cleanText)
  const lines = cleanText.split('\n').filter((line) => line.trim().length > 0)
  const [headerLine, ...dataLines] = lines

  const headers = headerLine.split(sep).map((h) => h.trim())
  const rows = dataLines.map((line) => {
    const cells = line.split(sep)
    const record: Record<string, unknown> = {}
    headers.forEach((header, idx) => {
      record[header] = coerceCell(cells[idx] ?? '')
    })
    return record
  })

  return { headers, rows, delimiter: sep }
}
