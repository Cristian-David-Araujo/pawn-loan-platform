type SupportedDateFormat = 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'

let globalDateFormat: SupportedDateFormat = 'DD/MM/YYYY'

export const setGlobalDateFormat = (dateFormat: string | null | undefined) => {
  if (dateFormat === 'DD/MM/YYYY' || dateFormat === 'MM/DD/YYYY' || dateFormat === 'YYYY-MM-DD') {
    globalDateFormat = dateFormat
    return
  }

  globalDateFormat = 'DD/MM/YYYY'
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
