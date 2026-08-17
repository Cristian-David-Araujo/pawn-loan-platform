/**
 * Checks the WCAG AA contrast of every foreground/background token pair, in both themes.
 *
 * This exists because eyeballing does not work. `--placeholder` shipped at 3.4:1 against a
 * comment claiming 4.6:1 — on hints that carry real information, like the expected date
 * format — and nothing caught it until the dark palette was built and the two themes were
 * measured against each other. A second theme doubles the surface area for exactly this
 * class of defect, so it gets a test rather than a promise.
 *
 * Run with `npm run check:contrast`. CI runs it beside `vue-tsc`.
 */
import { readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const CSS = join(ROOT, 'src', 'assets', 'main.css')

/**
 * Pairs that a reader actually sees together. Each carries its own minimum, because WCAG
 * asks 4.5:1 of body text and 3:1 of a large or non-text indicator.
 */
const PAIRS = [
  ['--text', '--bg', 'body text on the canvas', 4.5],
  ['--text', '--surface', 'body text on a panel', 4.5],
  ['--text', '--surface-soft', 'text on a table header', 4.5],
  ['--text-secondary', '--surface', 'secondary text on a panel', 4.5],
  ['--muted', '--bg', 'muted text on the canvas', 4.5],
  ['--muted', '--surface', 'muted text on a panel', 4.5],
  ['--muted', '--surface-soft', 'label on a table header', 4.5],
  ['--placeholder', '--surface', 'placeholder inside a field', 4.5],
  ['--placeholder', '--bg', 'placeholder on the canvas', 4.5],
  ['--text-inverse', '--ink', 'primary button label', 4.5],
  ['--on-accent', '--accent', 'text on an accent fill', 4.5],
  ['--on-danger', '--danger', 'text on a danger fill', 4.5],
  ['--accent', '--surface', 'a link, or accent text on a panel', 4.5],
  ['--success-text', '--success-soft', 'a success pill', 4.5],
  ['--warning-text', '--warning-soft', 'a warning pill', 4.5],
  ['--danger-text', '--danger-soft', 'a danger pill', 4.5],
  // The resting state of a destructive row action (.btn-destructive): the danger hue drawn
  // as an icon on the panel it sits on. It reached AA in dark and failed it in light while
  // these buttons were three different classes, which is how the drift was noticed.
  // A day inside a from/to range: normal text over the accent wash.
  ['--text', '--accent-soft', 'a day inside a date range', 4.5],
  ['--danger-text', '--surface', 'a destructive row action', 4.5],
  ['--danger-text', '--danger-soft', 'a destructive row action, hovered', 4.5],
  ['--info-text', '--info-soft', 'an info pill', 4.5],
  ['--sidebar-text', '--sidebar-bg', 'the active sidebar link', 4.5],
  ['--sidebar-link', '--sidebar-bg', 'a resting sidebar link', 4.5],
  ['--sidebar-muted', '--sidebar-bg', "the sidebar's role label", 4.5],
  ['--accent-on-dark', '--sidebar-bg', 'the active-nav rule (non-text)', 3]
]

const readBlock = (css, selector) => {
  const start = css.indexOf(selector)
  if (start === -1) throw new Error(`Could not find "${selector}" in main.css`)
  const open = css.indexOf('{', start)
  let depth = 0
  let close = -1
  for (let i = open; i < css.length; i++) {
    if (css[i] === '{') depth++
    else if (css[i] === '}' && --depth === 0) {
      close = i
      break
    }
  }
  const body = css.slice(open + 1, close)
  const tokens = {}
  for (const match of body.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    tokens[match[1]] = match[2].trim()
  }
  return tokens
}

const luminance = (hex) => {
  const h = hex.replace('#', '')
  const channels = [0, 2, 4]
    .map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)))
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

const contrast = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

const css = readFileSync(CSS, 'utf8')
const light = readBlock(css, ':root {')
// The dark block overrides a subset, so it inherits everything it does not restate.
const dark = { ...light, ...readBlock(css, "[data-theme='dark'] {") }

let failures = 0
let skipped = 0

for (const [themeName, tokens] of [['light', light], ['dark', dark]]) {
  console.log(`\n${themeName}`)
  for (const [fg, bg, label, min] of PAIRS) {
    const foreground = tokens[fg]
    const background = tokens[bg]

    // rgba() and other non-hex values compose against whatever is behind them, which this
    // static check cannot resolve. Reported rather than silently passed.
    if (!foreground?.startsWith('#') || !background?.startsWith('#')) {
      console.log(`  skip  ${label} — ${fg} or ${bg} is not a hex value`)
      skipped++
      continue
    }

    const ratio = contrast(foreground, background)
    const ok = ratio >= min
    if (!ok) failures++
    console.log(
      `  ${ok ? 'ok  ' : 'FAIL'}  ${ratio.toFixed(2).padStart(6)}:1  (needs ${min})  ${label}`
    )
  }
}

console.log(
  `\n${PAIRS.length * 2} pair(s) checked across both themes — ${failures} failure(s), ${skipped} skipped.`
)

if (failures) {
  console.error('\nContrast below WCAG AA. Adjust the token, do not lower the threshold.')
  process.exit(1)
}
