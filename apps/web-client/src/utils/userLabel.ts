/**
 * How an operator is named on screen and on paper.
 *
 * Eight places wrote `x.full_name || x.username || '-'` by hand, and they had already
 * drifted: the printed statement omitted the dash, `UsersView` fell back to the *email*
 * rather than the username, and two tables carried the expression twice each (header and
 * cell) so a change had to be made in both halves of the same row.
 *
 * Returns `null` rather than a dash or a sentinel, for the reason `getCustomerName` does:
 * what an absent name reads as is a decision for the surface. A table shows a dash, a
 * printed document leaves the line out entirely, and neither should have to know the
 * other's convention — nor to recognise some magic string in order to replace it.
 */
export interface DisplayableUser {
  full_name?: string | null
  username?: string | null
}

export const userLabel = (user?: DisplayableUser | null): string | null => {
  const name = user?.full_name?.trim() || user?.username?.trim()
  return name || null
}
