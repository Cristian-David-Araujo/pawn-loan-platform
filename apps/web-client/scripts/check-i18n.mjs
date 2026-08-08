/**
 * Fails when a translation key is referenced but not defined, or defined in one locale
 * and not the other.
 *
 * `t()` renders a missing key as the key itself, so nothing throws, nothing logs, and the
 * defect ships: the interface simply prints `common.loading` where a word belongs. That is
 * how six keys — including `common.notes`, which lands on a printed customer document —
 * survived in this codebase without anyone noticing, and how `common.confirmAction` came to
 * answer a Spanish-first team in English through a single-language fallback.
 *
 * Run with `npm run check:i18n`. CI runs it beside `vue-tsc`.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SRC = join(ROOT, 'src')
const MESSAGES = join(SRC, 'i18n', 'messages.ts')

const walk = (dir) =>
  readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry)
    return statSync(full).isDirectory() ? walk(full) : [full]
  })

/** Every `t('a.b')` / `t("a.b")` / `t(`a.b`)` in the app, mapped to where it was found. */
const collectReferences = () => {
  const referenced = new Map()
  for (const file of walk(SRC)) {
    if (!file.endsWith('.vue') && !file.endsWith('.ts')) continue
    if (file === MESSAGES) continue
    const text = readFileSync(file, 'utf8')
    for (const match of text.matchAll(/\bt\(\s*['"`]([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)['"`]/g)) {
      if (!referenced.has(match[1])) referenced.set(match[1], relative(ROOT, file))
    }
  }
  return referenced
}

/**
 * Reads the locale blocks out of messages.ts by evaluating the object literal. The file is
 * plain data with no imports, which is what makes this safe and keeps the check free of a
 * TypeScript toolchain.
 */
const loadDictionary = () => {
  const raw = readFileSync(MESSAGES, 'utf8')
  const start = raw.indexOf('{', raw.indexOf('messages'))
  if (start === -1) throw new Error('Could not find the messages object in messages.ts')

  let depth = 0
  let end = -1
  for (let i = start; i < raw.length; i++) {
    if (raw[i] === '{') depth++
    else if (raw[i] === '}' && --depth === 0) {
      end = i + 1
      break
    }
  }
  if (end === -1) throw new Error('Unbalanced braces in the messages object')

  return new Function(`return ${raw.slice(start, end)}`)()
}

const flatten = (obj, prefix = '', out = new Set()) => {
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) flatten(value, path, out)
    else out.add(path)
  }
  return out
}

const referenced = collectReferences()
const dictionary = loadDictionary()
const locales = Object.keys(dictionary)
const flat = Object.fromEntries(locales.map((code) => [code, flatten(dictionary[code] ?? {})]))

const problems = []

for (const [key, file] of referenced) {
  const missingIn = locales.filter((code) => !flat[code].has(key))
  if (missingIn.length) {
    problems.push(`missing from ${missingIn.join(' and ')}: ${key}   (${file})`)
  }
}

// A key defined on one side only is a half-translated string waiting to surface.
for (const code of locales) {
  for (const key of flat[code]) {
    const absentFrom = locales.filter((other) => other !== code && !flat[other].has(key))
    if (absentFrom.length) {
      problems.push(`defined in ${code} but not ${absentFrom.join(' or ')}: ${key}`)
    }
  }
}

const summary = locales.map((code) => `${code}: ${flat[code].size}`).join('   ')
console.log(`i18n check — ${referenced.size} keys referenced   ${summary}`)

if (problems.length) {
  console.error(`\n${problems.length} problem(s):`)
  for (const problem of [...new Set(problems)].sort()) console.error(`  ${problem}`)
  process.exit(1)
}

console.log('All referenced keys resolve, and both locales carry the same set.')
