---
name: responsive-and-a11y
description: Ensure the web application is fully responsive across mobile, tablet, and desktop devices, and meets WCAG accessibility standards.
---

# Responsive Design & Accessibility

## Responsiveness
- Always use a mobile-first approach.
- Define media queries for key breakpoints (e.g., `min-width: 640px` for tablets, `1024px` for desktops).
- Use relative units (`rem`, `em`, `%`, `vh`, `vw`) rather than fixed `px` where appropriate.
- Ensure touch targets are at least 44x44px for mobile users.

## Accessibility (A11y)
- Use semantic HTML tags (`<header>`, `<nav>`, `<main>`, `<article>`, `<footer>`).
- Add `aria-label` or `aria-labelledby` to interactive elements that lack text.
- Ensure contrast ratios meet at least AA standards (4.5:1 for normal text).
- Make sure all interactive elements are focusable via keyboard (`tabindex="0"`) and have clear `:focus-visible` styles.
- Add `alt` attributes to all images.
