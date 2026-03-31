export const formatDateDMY = (value: string | Date | null | undefined): string => {
  if (!value) {
    return '-'
  }

  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const day = String(value.getDate()).padStart(2, '0')
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const year = String(value.getFullYear())
    return `${day}-${month}-${year}`
  }

  const stringValue = String(value).trim()

  // Supports YYYY-MM-DD and full ISO values like YYYY-MM-DDTHH:mm:ss.
  const isoMatch = stringValue.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (isoMatch) {
    const [, year, month, day] = isoMatch
    return `${day}-${month}-${year}`
  }

  const parsed = new Date(stringValue)
  if (!Number.isNaN(parsed.getTime())) {
    const day = String(parsed.getDate()).padStart(2, '0')
    const month = String(parsed.getMonth() + 1).padStart(2, '0')
    const year = String(parsed.getFullYear())
    return `${day}-${month}-${year}`
  }

  return stringValue
}
