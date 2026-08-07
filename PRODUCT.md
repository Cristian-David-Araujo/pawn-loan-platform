# Product context

Durable context for design work on this repository. Written for the `/impeccable` commands
and for anyone picking up the frontend. Engineering detail lives in [CLAUDE.md](CLAUDE.md);
this file only carries what a designer needs and could not infer from the code.

## What this is

A loan-management back office for a small pawn and consumer lender. Staff use it to register
customers, issue loans against pledged goods, accrue monthly interest, take payments at a
counter, hold and hand back collateral, and print the documents a customer walks out with.

It is **internal software**. There is no public surface, no marketing page, no sign-up, and
no customer login. Everyone who sees this screen works here and was given an account by an
administrator.

## Who uses it

Three roles, and they are not three permission levels on one job — they are three different
people standing in different places.

- **Collector** — at the counter, facing a customer, most of the day. Takes interest and
  principal payments, hands pledges back, prints receipts. Cannot open a loan, register a
  pledge, or pull a report. This is the highest-volume, most time-pressured use of the app,
  and it is where a misread number costs real money.
- **Loan officer** — opens and edits credit: loans, customers, pledges, renewals, reports.
  Works in longer sittings than the collector, mostly in forms and tables.
- **Administrator** — the above plus user management, portfolio-wide settings, backups, and
  the two disposal actions (liquidate, sell). Rarely at the counter.

The system must always keep one active administrator; an installation that loses its last
one cannot recover from inside the app.

## The usage scene

An office or a shop counter under ordinary indoor light, on a desktop or laptop, often with
a customer waiting on the other side of the desk. Sessions are long and repetitive. The same
screens are read hundreds of times a week by people who already know where everything is.

This is what settles most design questions here: **the interface is a tool in someone's
hands, not a thing to be admired.** Speed of reading beats novelty. Density is correct.
Familiarity is a feature — a control that behaves like the control it resembles is doing its
job. Motion that makes someone wait is a defect.

**Light and dark are both shipped, and "system" is the default.** The room is not one
room: the counter is usually bright, the back office often is not, and a closing shift runs
into the evening. Light was the only mode until an operator asked for the choice, and the
answer that fits the scene is to follow the machine unless someone says otherwise — a
person who sets their laptop to dark at 6pm should not have to set the app separately, and
a person who explicitly picked light must keep it when the machine switches.

The printed documents stay light in both. They are printed on white paper, and a browser
drops backgrounds when printing, so a dark receipt would hand the customer a blank page.

## What the product is about

Money that belongs to someone else, and goods that belong to someone else.

Every number on these screens is a claim about a debt or a pledge, and someone is going to
act on it — collect it, write it off, or hand back a wedding ring against it. The design
consequences are concrete:

- **Figures must be scannable and unambiguous.** Amounts align, use tabular figures, and
  never move under the eye between rows.
- **Money-moving actions must be legible before they are taken.** The screen states what will
  happen and to which loan, before the button.
- **Nothing destructive is one click.** Reversals need a typed reason; forced closures need a
  reason; a restore needs a typed phrase.
- **State is never decoration.** Overdue, in custody, released, reversed — these are facts a
  reader acts on, so they get semantic color, not brand color.

## Language and locale

Spanish first, English second, both shipped and switchable; the operator's staff work in
Spanish. Every string goes through `vue-i18n` with a key in **both** blocks. Currency is
Colombian pesos, which means long numbers with thousands separators and no decimals in
practice — layouts must hold `1.250.000` without wrapping. Dates follow a configurable
format set from the portfolio settings, defaulting to `America/Bogota`.

## Voice

Plain, specific, and calm. It states what happened and what to do next.

- Controls name their action. Errors name the problem and the recovery.
- No exclamation marks in confirmations. No "Oops". No cheerleading.
- No product jargon where a domain word exists — the staff say *abono*, *empeño*, *custodia*,
  and the interface should too.

## Anti-references

The visual world this must not drift into:

- **The generic AI dashboard.** Indigo-to-violet gradients, glass panels, a purple-tinted
  hero metric row, Inter everywhere. It is the default any model reaches for and it says
  nothing about this business.
- **Consumer fintech.** Big friendly cards, celebratory motion, rounded pill everything. This
  is a ledger, not a spending app.
- **A marketing site wearing a dashboard's clothes.** No background photography, no scroll
  choreography, no whitespace that pushes the next table row below the fold.

## Fixed constraints

These are settled and are not design questions:

- Vue 3 + Vite, plain CSS with custom properties. No Tailwind, no component framework.
- Create and edit forms live in modals opened from the page header, never inline above a
  table.
- The four printable documents are deliberately restrained and print on ordinary office
  paper. They are evidence, not brand surface.
- The left sidebar is the navigation. It is standard, and standard is right here.
