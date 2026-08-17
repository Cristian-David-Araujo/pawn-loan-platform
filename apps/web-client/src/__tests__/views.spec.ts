/**
 * Every view mounts and renders something.
 *
 * This is deliberately shallow. It is not testing behaviour — it is testing that the
 * component *exists at runtime*, which is the failure this project actually keeps having and
 * the one its other gates are blind to.
 *
 * Three times in a single sitting a change left a view rendering an empty page: a `const`
 * read before its declaration in `<script setup>` (temporal dead zone), a `<template>` left
 * unbalanced by an edit, and a still-used symbol deleted by a cleanup. `vue-tsc` reported the
 * first two as *unused variables*, because an invalid template makes it stop counting
 * template usage — so its verdict inverts precisely when something is badly broken. Each one
 * was found by driving a real browser by hand.
 *
 * A mount catches all three in milliseconds.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createRouter, createWebHistory } from 'vue-router'

import { messages } from '../i18n/messages'

// The store and the API reach the network on mount; the views under test do not care what
// they answer, only that they can be rendered at all.
/* An empty answer that fits every shape these views destructure: some assign the response
   straight to a list and call `.filter` on it, others read `.items` or `.groups` off it. An
   array carrying those keys satisfies both without the mock having to know which endpoint
   was called — it is standing in for "nothing came back", not for any particular payload. */
const emptyResponse = Object.assign([] as unknown[], {
  items: [],
  groups: [],
  allocations: [],
  total_pending_interest: 0,
  total_pending_penalty: 0,
  total_outstanding: 0,
  available_advance_balance: 0
})

vi.mock('../services/api', () => ({
  apiClient: { request: vi.fn().mockResolvedValue(emptyResponse) },
  apiErrorMessage: (e: unknown) => String(e)
}))

const i18n = createI18n({ legacy: false, locale: 'es', fallbackLocale: 'en', messages })

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/customers', name: 'customers', component: { template: '<div />' } },
    { path: '/customers/:id/:tab?', name: 'customer-detail', component: { template: '<div />' } },
    { path: '/loans', name: 'loans', component: { template: '<div />' } },
    { path: '/loans/:id', name: 'loan-detail', component: { template: '<div />' } }
  ]
})

const views = import.meta.glob<{ default: unknown }>('../views/*.vue')

describe('every view renders', () => {
  for (const [path, load] of Object.entries(views)) {
    const name = path.split('/').pop() as string

    it(`${name} mounts and produces markup`, async () => {
      const module = await load()
      await router.push('/customers/1/overview')
      await router.isReady()

      const wrapper = mount(module.default as never, {
        global: { plugins: [i18n, router], stubs: { RouterLink: true, RouterView: true } }
      })

      // An empty render is the exact symptom: the setup threw, or the template did not compile.
      expect(wrapper.html().trim().length).toBeGreaterThan(0)
    })
  }
})
