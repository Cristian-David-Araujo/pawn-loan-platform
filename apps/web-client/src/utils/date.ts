type SupportedDateFormat = 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'

let globalDateFormat: SupportedDateFormat = 'DD/MM/YYYY'

export const setGlobalDateFormat = (dateFormat: string | null | undefined) => {
  if (dateFormat === 'DD/MM/YYYY' || dateFormat === 'MM/DD/YYYY' || dateFormat === 'YYYY-MM-DD') {
    globalDateFormat = dateFormat
    return
  }

  globalDateFormat = 'DD/MM/YYYY'
}

export const getGlobalDateFormat = (): SupportedDateFormat => globalDateFormat

const parseDateParts = (value: string): { year: string; month: string; day: string } | null => {
  const isoMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (isoMatch) {
    const [, year, month, day] = isoMatch
    return { year, month, day }
  }

  if (globalDateFormat === 'DD/MM/YYYY') {
    const match = value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
    if (!match) {
      return null
    }
    const [, day, month, year] = match
    return { year, month, day }
  }

  if (globalDateFormat === 'MM/DD/YYYY') {
    const match = value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
    if (!match) {
      return null
    }
    const [, month, day, year] = match
    return { year, month, day }
  }

  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) {
    return null
  }

  const [, year, month, day] = match
  return { year, month, day }
}

const formatByGlobalPattern = (day: string, month: string, year: string) => {
  if (globalDateFormat === 'MM/DD/YYYY') {
    return `${month}/${day}/${year}`
  }

  if (globalDateFormat === 'YYYY-MM-DD') {
    return `${year}-${month}-${day}`
  }

  return `${day}/${month}/${year}`
}

export const formatDateDMY = (value: string | Date | null | undefined): string => {
  if (!value) {
    return '-'
  }

  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const day = String(value.getDate()).padStart(2, '0')
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const year = String(value.getFullYear())
    return formatByGlobalPattern(day, month, year)
  }

  const stringValue = String(value).trim()

  // Supports YYYY-MM-DD and full ISO values like YYYY-MM-DDTHH:mm:ss.
  const isoMatch = stringValue.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (isoMatch) {
    const [, year, month, day] = isoMatch
    return formatByGlobalPattern(day, month, year)
  }

  const parsed = new Date(stringValue)
  if (!Number.isNaN(parsed.getTime())) {
    const day = String(parsed.getDate()).padStart(2, '0')
    const month = String(parsed.getMonth() + 1).padStart(2, '0')
    const year = String(parsed.getFullYear())
    return formatByGlobalPattern(day, month, year)
  }

  return stringValue
}

export const toIsoDate = (value: string | Date | null | undefined): string | null => {
  if (!value) {
    return null
  }

  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const year = String(value.getFullYear())
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const stringValue = String(value).trim()
  const parts = parseDateParts(stringValue)
  if (!parts) {
    return null
  }

  return `${parts.year}-${parts.month}-${parts.day}`
}
