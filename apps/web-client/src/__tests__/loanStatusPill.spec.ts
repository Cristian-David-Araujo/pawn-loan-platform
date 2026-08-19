/**
 * What a loan's row says about it without being opened.
 *
 * The pause was reachable only from inside the loan detail, and there only as the *label of
 * the button that undoes it* — so "is this loan still accruing?" could not be answered from
 * any list. These pin the two halves of the fix: the pause is shown, and it is shown *beside*
 * the status rather than instead of it, because a loan can be paused and overdue at once and
 * that pairing is the one an operator most needs to see.
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

import LoanStatusPill from '../components/LoanStatusPill.vue'
import { messages } from '../i18n/messages'
import { loanStatusKey, loanStatusPillClass } from '../utils/loanStatus'
import { userLabel } from '../utils/userLabel'

const i18n = createI18n({ legacy: false, locale: 'es', fallbackLocale: 'en', messages })
const render = (props: { status: string; paused?: boolean; pauseReason?: string }) =>
  mount(LoanStatusPill, { props, global: { plugins: [i18n] } })

describe('the loan status cell', () => {
  it('shows only the status when the loan is running', () => {
    const wrapper = render({ status: 'active' })
    expect(wrapper.findAll('.pill')).toHaveLength(1)
    expect(wrapper.text()).toBe('Activo')
  })

  it('adds a second chip when the interest is paused, keeping the status', () => {
    const wrapper = render({ status: 'overdue', paused: true })
    const pills = wrapper.findAll('.pill')
    expect(pills).toHaveLength(2)
    // The status survives: a paused loan can still be in arrears, and the arrears are the
    // half that says money is at risk.
    expect(pills[0].text()).toBe('Vencido')
    expect(pills[1].text()).toBe('Pausado')
    expect(pills[1].classes()).toContain('pill-paused')
  })

  it('carries the reason as the tooltip, so it needs no second click', () => {
    const wrapper = render({ status: 'active', paused: true, pauseReason: 'Acuerdo con el cliente' })
    expect(wrapper.find('.pill-paused').attributes('title')).toBe('Acuerdo con el cliente')
  })

  it('leaves no stray title attribute when there is no reason', () => {
    const wrapper = render({ status: 'active', paused: true })
    expect(wrapper.find('.pill-paused').attributes('title')).toBeUndefined()
  })
})

describe('the two class vocabularies', () => {
  /* `loanStatusClass` used to be one name serving the printed document only, while two views
     kept private copies of the screen map. Splitting them is only safe if they stay different
     where they are meant to differ. */
  it('parts company on a foreclosure', () => {
    expect(loanStatusPillClass('overdue')).toBe('pill-warning')
    expect(loanStatusPillClass('defaulted')).toBe('pill-overdue')
  })

  it('gives a closed loan no tone at all, and an unknown value none either', () => {
    expect(loanStatusPillClass('closed')).toBe('')
    expect(loanStatusPillClass('something-new')).toBe('')
    // The label still echoes, which is how an unmapped state gets reported instead of vanishing.
    expect(loanStatusKey('something-new')).toBe('something-new')
  })
})

describe('naming the operator behind a record', () => {
  it('prefers the full name, falls back to the username', () => {
    expect(userLabel({ full_name: 'Ana Ruiz', username: 'aruiz' })).toBe('Ana Ruiz')
    expect(userLabel({ full_name: '', username: 'aruiz' })).toBe('aruiz')
    expect(userLabel({ full_name: '   ', username: 'aruiz' })).toBe('aruiz')
  })

  it('answers null rather than a dash, leaving the surface to decide', () => {
    expect(userLabel(null)).toBeNull()
    expect(userLabel(undefined)).toBeNull()
    expect(userLabel({})).toBeNull()
  })
})
