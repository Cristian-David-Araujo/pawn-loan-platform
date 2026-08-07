---
name: Pawn Loan Platform
description: The visual system for a pawn and consumer lender's back office.
colors:
  canvas: "#faf9f7"
  surface: "#ffffff"
  surface-soft: "#f5f4f1"
  surface-hover: "#eceae5"
  ink: "#232019"
  ink-hover: "#3a352c"
  petrol: "#0d5c53"
  petrol-hover: "#0a4a43"
  petrol-soft: "#e6f0ee"
  petrol-border: "#b9d4cf"
  petrol-on-dark: "#4ba599"
  text: "#1c1a17"
  text-secondary: "#44403a"
  text-muted: "#6b655c"
  text-inverse: "#faf9f7"
  text-disabled: "#b5b0a6"
  placeholder: "#8f8a80"
  on-fill: "#ffffff"
  line: "#e4e2dd"
  line-light: "#efedea"
  line-strong: "#d3d0c9"
  line-hover: "#b9b5ab"
  sidebar: "#1a1815"
  sidebar-text: "#f5f4f1"
  sidebar-link: "#cbc6ba"
  sidebar-muted: "#918a7d"
  success: "#15803d"
  warning: "#b45309"
  danger: "#b42318"
  danger-hover: "#97180f"
  info: "#1e5a97"
typography:
  headline:
    fontFamily: "Manrope, ui-sans-serif, -apple-system, sans-serif"
    fontSize: "1.7rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.022em"
  title:
    fontFamily: "Manrope, ui-sans-serif, -apple-system, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.018em"
  body:
    fontFamily: "Manrope, ui-sans-serif, -apple-system, sans-serif"
    fontSize: "0.93rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Manrope, ui-sans-serif, -apple-system, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 600
    letterSpacing: "0.06em"
  micro:
    fontFamily: "Manrope, ui-sans-serif, -apple-system, sans-serif"
    fontSize: "0.62rem"
    fontWeight: 700
  data:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.82rem"
    fontWeight: 500
    fontFeature: "tnum"
rounded:
  xs: "4px"
  sm: "6px"
  md: "10px"
  lg: "14px"
  xl: "18px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "#faf9f7"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.9rem"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.ink-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.9rem"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "0.6rem 0.8rem"
    height: "44px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "1.25rem"
  pill:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.xs}"
    padding: "0.16rem 0.45rem"
    typography: "{typography.label}"
  nav-link:
    textColor: "#cbc6ba"
    rounded: "{rounded.sm}"
    padding: "0.55rem 0.7rem"
  nav-link-active:
    backgroundColor: "rgba(255, 255, 255, 0.09)"
    textColor: "#f5f4f1"
---

# Design System: Pawn Loan Platform

## Overview

**Creative North Star: "The Counter Ledger"**

This is a tool held in someone's hands while a customer waits on the other side of the desk.
It takes its character from the thing it replaced: a warm paper ledger, ruled in hairlines,
written in a hand that stays legible after the hundredth entry. Not the vault, not the
strongroom, not a fintech app — the book the amounts were kept in.

Everything follows from the fact that **every number on these screens is money that belongs
to somebody else.** Figures are set in a monospaced face and aligned so a column of pesos
cannot shift under the eye between rows. Colour is scarce enough that when it appears it
means something: a status, a selection, a place. Surfaces are quiet so the figures on them
are not. Motion reports that something changed and then gets out of the way.

The rejected world is specific and was the incumbent: the generic AI dashboard — indigo
gradients on the sidebar and on every button, frosted panels, a decorative circle behind
each stat tile, Inter everywhere. It looked like a product demo rather than a place of
record, and some of it worked against the reading: proportional digits in money columns, a
hover lift on cards that cannot be clicked, four competing background states in one table.

**Key Characteristics:**
- Warm neutrals throughout; no cool grey anywhere
- Figures in a monospaced face with tabular alignment
- One accent, spent only on orientation
- Ink, not accent, for primary actions
- Flat surfaces, hairline separation, shadows only where something genuinely floats
- Density is correct; whitespace serves grouping, not spectacle

## Colors

A warm monochrome canvas with a single cool accent held in reserve, plus four semantic hues
that never do decorative work.

### Primary
- **Ledger Ink** (#232019): every primary action. Not the accent, deliberately. Each table
  row here carries an action, and an accent-coloured button on all of them leaves the accent
  meaning nothing.
- **Counter Petrol** (#0d5c53): orientation only — the active nav item, focus rings, the
  selected row, sort indicators, the current page, links. 7.9:1 on white.

### Neutral
- **Warm Bone** (#faf9f7): the page canvas. Off-white and warm, so a white card sits on it.
- **Card White** (#ffffff): panels, table bodies, inputs, popovers.
- **Oat** (#f5f4f1) / **Oat Deep** (#eceae5): table headers, row hover, quiet fills.
- **Vault Black** (#1a1815): the sidebar. A flat second neutral layer, no gradient.
- **Ledger Text** (#1c1a17) / **Secondary** (#44403a) / **Muted** (#6b655c): warm off-blacks;
  never pure black. Muted holds 5.2:1 on the canvas.
- **Rule** (#e4e2dd) / **Rule Light** (#efedea) / **Rule Strong** (#d3d0c9) / **Rule Hover**
  (#b9b5ab): the hairlines that carry nearly all the structure, plus the border a control
  takes under the pointer.
- **Placeholder** (#8f8a80) and **Disabled** (#b5b0a6): text that is present but is not
  being asked to carry meaning — a prompt in an empty field, a day outside the displayed
  month. Both hold AA on their own surface.
- **On Fill** (#ffffff): text on a saturated fill. Deliberately not the same token as
  `--surface`, which happens to share the value: a surface and a foreground are different
  ideas and a future dark mode would move one without the other.

### Tertiary — semantic
- **Ledger Green** (#15803d), **Amber Notice** (#b45309), **Arrears Red** (#b42318),
  **Slate Blue** (#1e5a97). Separated by hue angle so `overdue`, `upcoming`, `current` and
  `warning` are never confusable at pill size. Each carries a `-soft` fill, a `-border` and
  a darker `-text` variant that holds AA on its own fill.

### Themes

Both themes ship, and `system` is the default. The dark palette is the same warm family
turned down — not a cool slate, which is where most dark modes drift and where this one
would stop reading as the same product. Surfaces climb as they come forward (canvas
`#171612`, panel `#1f1d19`, raised `#272420`, hover `#322e28`), and text tops out at
`#f2f0eb` rather than pure white, which haloes at this contrast and is tiring over a shift.

Two things invert rather than darken:

- **Ink becomes paper.** A near-black primary button on a near-black field would vanish, so
  `--ink` inverts to `#ece8e0` with dark text. The idea was never "dark", it was "not the
  accent", and that survives the inversion.
- **The sidebar drops below the canvas** (`#100f0c`) instead of rising above it, so the
  chrome recedes and content reads as the nearer surface. It also takes a hairline border,
  which it does not need against a bone canvas.

The accent lightens to `#4ba599` so it reads on a dark field, which is why `--on-accent`
and `--on-danger` exist as separate tokens: the two fills move in opposite directions
between themes, and white on the lightened accent would be 2.9:1.

`data-theme` is written on `<html>` before first paint by an inline script in `index.html`,
so the CSS is a plain attribute selector rather than a `prefers-color-scheme` block. The
media query cannot express "the operator chose light on a machine set to dark", and
carrying the palette twice to support both is how the two halves drift apart.

**The Both-Themes Rule.** A colour is not done until it has been measured in both.
`npm run check:contrast` checks every foreground/background pair in both themes against
WCAG AA and CI runs it — that check is what caught `--placeholder` shipping at 3.4:1 behind
a comment that claimed 4.6:1.

### Named Rules

**The Orientation Rule.** Petrol answers exactly one question: *where am I, and what is
selected*. It never fills a button, never tints a panel, never marks a status. If a use of
the accent is not answering that question, it is decoration and belongs in ink or a neutral.

**The One Grey Family Rule.** Every neutral is warm. A cool grey anywhere — a `#64748b`, a
`#cbd5e1`, an undefined token falling back to a Tailwind default — is a defect, not a
variation. Three such fallbacks were live in this codebase.

## Typography

**UI Font:** Manrope (with `ui-sans-serif`, system sans)
**Data Font:** JetBrains Mono (with `ui-monospace`)

**Character:** Manrope is geometric and slightly narrow, which holds up in dense forms and
long labels without the anonymity of the system default. JetBrains Mono appears only where
figures are, and the pairing reads as ledger rather than as terminal because the mono is
confined to numerals, codes and identifiers.

One UI family carries headings, labels, buttons, body and controls. A display face in a
product label would be a costume.

### Hierarchy

Root is 15px and is the rem basis only — never a text size. `body` names `--fs-base`
explicitly, so nothing inherits the raw root value and lands between steps.

- **Headline** (700, 1.7rem / 25.5px, 1.2, -0.022em): page-level `h1`; rare.
- **Title** (700, 1.4rem / 21px, 1.25, -0.018em): `h2`, page titles, modal headings.
- **Subtitle** (600, 1.2rem / 18px): `h3`, section headings inside a card.
- **Body** (400, 0.93rem / 14px, 1.6): prose, input values, list content.
- **Secondary** (500, 0.82rem / 12.3px): table cells, meta, helper text, buttons.
- **Label** (600, 0.72rem / 10.8px, 0.06em, uppercase): table headers, nav section titles.
- **Micro** (700, 0.62rem / 9.3px): counters, sort markers, the help glyph. Below the label
  step on purpose, and it never carries a word an operator needs in order to work.
- **Data** (JetBrains Mono, tabular): every amount, custody code, page number and date cell.

The scale ratio is 1.13–1.2 between adjacent steps, which is the Operate range. The
`flat-type-hierarchy` detector rule wants ≥1.25 and is waived in `.impeccable/config.json`
with the reasoning written out there.

### Named Rules

**The Tabular Figures Rule.** Any number a reader compares against another number is set in
`--font-mono` with `tabular-nums`. Money, custody codes, page numbers, calendar days,
counts. A proportional digit in a money column is a defect, because it moves the thousands
place between rows and the eye has to re-find it every time.

**The Right-Aligned Money Rule.** Amounts are right-aligned in tables. `td.text-right` gets
tabular figures automatically, because in this app a right-aligned cell is always a figure.

## Layout

A two-column app shell: a fixed 268px sidebar and a fluid content column, collapsing to an
off-canvas drawer below 1080px. The drawer slides on `transform`, not `left`.

Content sits in a 1.5rem page gutter (1rem on mobile) with no max-width: tables here are
wide on purpose and an operator with a large monitor should get the columns, not letterboxed
whitespace. Cards group by hairline and padding rather than by nesting; a card inside a card
is always wrong.

Spacing rhythm is 0.25 / 0.5 / 1 / 1.5rem. Tighter within a group, looser between groups,
more space above a heading than below it. Density is deliberate — this is a data surface and
whitespace that pushes the next table row below the fold costs the operator a scroll on
every customer.

## Elevation & Depth

**Almost entirely flat, with structure carried by hairlines and tonal layering.** Shadows
appear only on things that genuinely float above the page: popovers, dropdowns, modals, and
the mobile drawer. A card at rest has a 1px border and, at most, `--shadow-xs`.

Cards do not lift on hover. A panel that reacts to the pointer but cannot be clicked is a
lie about what it does — that hover lift was in the incumbent system and is removed.

### Shadow Vocabulary
- **`--shadow-xs`** (`0 1px 2px rgba(35,32,25,0.05)`): a card's slight separation from canvas.
- **`--shadow-sm`**: the login card and the active tab.
- **`--shadow-md`**: dropdowns, autocomplete lists, the date popover.
- **`--shadow-lg`**: modal panels and the mobile sidebar.
- **`--shadow-focus`** (`0 0 0 3px rgba(13,92,83,0.22)`): the focus ring, paired with a
  border shift to petrol.

Every shadow is tinted with the warm neutral (`35,32,25`) rather than pure black, carries a
real vertical offset, and implies one light source from above.

### Named Rules

**The No-Halo Rule.** A zero-offset glow is decoration, not depth. Every shadow here has an
offset and a soft blur.

## Shapes

Crisp rather than soft, and tighter inside than outside. Radii run 4 / 6 / 10 / 14 / 18px:
`--radius-xs` on inner elements (pills, badges, table header corners, calendar days),
`--radius-sm` on controls (buttons, inputs, form sections), `--radius` on cards and
popovers, `--radius-lg` on modal panels.

`--radius-full` is reserved for genuinely circular things. Status pills use `--radius-xs`,
not a pill shape — a lozenge on every row of a dense table adds visual noise without adding
meaning.

Borders are 1px. A coloured left border thicker than 1px on a card or alert is a default
this system does not take.

## Components

### Buttons
- **Shape:** gently squared (6px), 38px tall, 44px on touch.
- **Primary:** ink fill (#232019), warm white text, no border, no shadow.
- **Hover / Active:** background shifts to #3a352c; `:active` presses down 1px. No lift, no
  scale — the translate-and-grow hover is the generic dashboard default.
- **Secondary:** white fill, `--line-strong` border, secondary text.
- **Ghost:** transparent until hover, for low-priority row actions where a filled button on
  every row would be heavy.
- **Danger:** flat `--danger` fill. Reserved for actions that destroy or reverse.
- **Loading:** `.is-loading` hides the label and spins a ring in place, so the control that
  started the work is the control that reports it.

### Inputs / Fields
- **Style:** white fill, 1px `--line-strong`, 6px radius, 44px minimum.
- **Focus:** border to petrol plus a 3px petrol ring. Never outline-only, never ring-only.
- **Invalid:** `aria-invalid` or `.is-invalid` turns the border red and the ring red.
- **Disabled:** oat fill, muted text, not-allowed cursor.
- **Money** goes through `CurrencyInput`, which is monospaced and grouped by the portfolio's
  currency. **Dropdowns** go through `CustomSelect`, **dates** through `DateInputField` —
  there is no raw `<select>` in the app, and adding one breaks the vocabulary.

### Tables
The densest surface in the product and the one most read.
- Hairline rows, uppercase micro-label headers on an oat fill, sticky header.
- **No zebra striping.** With a hover row, a selected row and a status pill already
  competing, a fourth background state made a wide money table harder to track.
- **Selection** tints the row petrol-soft and marks it with an inset rule on the first cell.
- Money columns are right-aligned and tabular.

### Pills & Badges
Small, squared (4px), 10.8px semibold. Each semantic hue pairs its `-soft` fill with its
`-border` and its `-text`. The same meaning is always the same hue on every screen.

### Navigation
Flat vault-black sidebar, no gradient. Links are 14px medium in a warm light grey; hover
lifts the background 6% white; the active link takes a 9% white fill, full-weight text and a
3px petrol rule down its left edge — the one place the accent appears in the chrome.

### Empty & Loading States
- **Empty:** an icon tile, a title, one line saying what the list holds, and the action that
  fills it. Never a bare table header.
- **Loading:** skeletons in the shape of the content that is coming — `.skeleton-row` for
  tables, skeleton tiles for stat cards. Not a spinner centred in an empty panel, which
  makes the layout jump when the rows land.

### Printable documents
The four printed documents in `InvoicePrintView` are their own restrained world: whitespace
carries the structure, one accent, one emphasis weight, one hairline, no panel fills. They
consume this system's colour tokens so a receipt cannot print in a retired palette, and they
set `tabular-nums`, but they do not take the app's mono face, its radii, or its shadows.

## Do's and Don'ts

### Do:
- **Do** set every figure a reader compares in `--font-mono` with tabular figures.
- **Do** reach for a hairline and spacing before a fill, a border or a shadow.
- **Do** spend `--accent` only on orientation: active nav, focus, selection, sort, links.
- **Do** give every interactive element a default, hover, focus-visible, active and disabled
  state before shipping it.
- **Do** name a step from the type scale. An ad-hoc `font-size: 0.85rem` in a scoped block
  is what flattened the rendered hierarchy.
- **Do** put a new shared class in `main.css`. A class that exists only in markup styles
  nothing — `.page-header-actions`, `.fw-bold`, `.text-warning-dark`, `.spinner-small`,
  `.mt-24` and `.notice-info` were all live examples.

### Don't:
- **Don't** introduce a cool grey, or a `var(--some-token, #hardcoded)` fallback for a token
  this system does not define. Three of those were shipping the old palette.
- **Don't** use a gradient. Not on the sidebar, not on a button, not behind a stat tile.
- **Don't** lift a card on hover, or scale a button toward the cursor.
- **Don't** animate `width`, `height`, `padding` or `margin`. Transform and opacity.
- **Don't** add a fourth background state to a table row.
- **Don't** put a raw `<select>`, a raw money `<input>`, or a Unicode glyph standing in for
  an icon anywhere in `views/` or `components/`.
- **Don't** write an inline `style` attribute or an arbitrary `z-index`. The scale runs
  `--z-sticky` 8 → `--z-popover` 40 → `--z-backdrop` 90 → `--z-sidebar` 100 → `--z-modal`
  200 → `--z-confirm` 300 → `--z-dropdown` 1000 → `--z-skip-link` 1100.
- **Don't** leave a literal colour, radius or type size in a rule. Every one of them belongs
  in `:root` with a name. The `design-system-*` detector rules compare the stylesheet against
  the frontmatter above and will say so — that check is what turned nine such values here
  into the tokens `--line-hover`, `--placeholder`, `--text-disabled`, `--on-fill`,
  `--accent-on-dark`, `--danger-hover`, `--sidebar-link`, `--fs-2xs` and `--z-skip-link`.
- **Don't** ship a user-facing string that is not a `vue-i18n` key present in **both**
  locale blocks. `npm run check:i18n` enforces it.
