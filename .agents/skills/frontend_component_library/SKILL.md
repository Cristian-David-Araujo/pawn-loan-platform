---
name: frontend-component-library
description: Generate standard, reusable frontend components (buttons, cards, modals, navbars) using modern CSS or a specified framework.
---

# Frontend Component Library
When asked to build a component or layout, use the following standardized approaches:

1. **Buttons**:
   - Primary: Vibrant background, light text, soft shadow, scale on hover.
   - Secondary: Transparent background, colored border, colored text, background fill on hover.
2. **Cards**:
   - Rounded corners (e.g., `border-radius: 12px` or `16px`).
   - Soft borders or shadows to distinguish from background.
   - Include hover effects (slight lift or shadow expansion).
3. **Navbars**:
   - Sticky top with backdrop blur (`position: sticky; top: 0; backdrop-filter: blur(10px); z-index: 50;`).
4. **Modals/Dialogs**:
   - Centered using Flexbox or Grid.
   - Dimmed backdrop (`background: rgba(0, 0, 0, 0.5)`).
   - Smooth entry animation (fade-in or slide-up).
