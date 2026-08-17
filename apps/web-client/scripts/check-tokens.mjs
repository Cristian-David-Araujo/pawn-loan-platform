#!/usr/bin/env node
/**
 * Fails when a CSS custom property is referenced but never defined.
 *
 * This bug class has now happened twice. The first time, `--color-primary`, `--color-text`
 * and `--color-text-muted` were referenced and never defined, leaving three controls painting
 * in the pre-redesign palette. The second time, `--on-fill` was used by `.btn-danger`, the
 * selected calendar day and the active pagination button — none of which had the colour they
 * were written to have, because an undefined `var()` with no fallback makes the declaration
 * invalid at computed-value time and `color` then *inherits*.
 *
 * That inheritance is what made it survive review: on the dark theme the inherited colour is
 * near-white, so a white-on-red button looked exactly right. Only the light theme exposed it.
 *
 * `check:contrast` could not catch either one. It measures token *pairs* — the palette's
 * intent — and both times the intended tokens were correct; the stylesheet simply referenced
 * something else. This check closes that gap: it compares what the CSS asks for against what
 * the CSS defines.
 *
 * A `var(--x, fallback)` is allowed: a deliberate fallback is a decision, not a typo.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')
const SRC = join(ROOT, 'src')

/** Properties the browser inherits, where an invalid `var()` fails silently instead of
 *  falling back to something obviously wrong. These are the dangerous ones. */
const INHERITED = new Set(['color', 'font-family', 'font-size', 'font-weight', 'line-height'])

const walk = (dir) =>
  readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry)
    return statSync(full).isDirectory() ? walk(full) : [full]
  })

const files = walk(SRC).filter((f) => /\.(css|vue)$/.test(f))

const defined = new Set()
const used = []

for (const file of files) {
  const text = readFileSync(file, 'utf8')

  for (const match of text.matchAll(/(--[\w-]+)\s*:/g)) {
    defined.add(match[1])
  }

  // `var(--x)` with no comma is the risky form; `var(--x, y)` carries its own answer.
  for (const match of text.matchAll(/([\w-]+)\s*:\s*[^;{}]*?var\(\s*(--[\w-]+)\s*\)/g)) {
    const [, property, token] = match
    const line = text.slice(0, match.index).split('\n').length
    used.push({ file, line, property, token })
  }
}

const missing = used.filter((u) => !defined.has(u.token))

for (const { file, line, property, token } of missing) {
  const risk = INHERITED.has(property) ? 'INHERITS — renders a wrong colour silently' : 'invalid'
  console.log(`  FAIL  ${relative(ROOT, file)}:${line}  ${property}: var(${token})  — undefined, ${risk}`)
}

console.log(
  `\n${defined.size} token(s) defined, ${used.length} bare var() reference(s) checked — ` +
    `${missing.length} undefined.`
)

if (missing.length) {
  console.log('\nDefine the token, or use one that exists. Do not add a fallback to silence this.')
  process.exit(1)
}
