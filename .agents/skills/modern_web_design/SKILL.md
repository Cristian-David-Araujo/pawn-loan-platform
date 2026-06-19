---
name: modern-web-design
description: Apply modern web design aesthetics, including glassmorphism, dynamic animations, and vibrant curated color palettes. Use this when the user asks for a beautiful, premium, or modern web interface.
---

# Modern Web Design Aesthetics
When building or updating UI components for this web application, follow these guidelines to ensure a premium, WOW-factor experience:

1. **Color Palette & Contrast**:
   - Do NOT use basic colors (e.g., plain red, blue).
   - Use HSL tailored colors or subtle gradients (e.g., `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`).
   - Implement dark mode with soft darks (e.g., `#121212`, `#1e1e1e`) instead of pure black `#000`.
2. **Typography**:
   - Use modern Google Fonts like Inter, Roboto, or Outfit.
   - Establish a strong typographic hierarchy (e.g., large bold headings, readable secondary text).
3. **Glassmorphism & Shadows**:
   - Use soft drop shadows (`box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)`).
   - For premium feel, use backdrop filters: `backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.1);`.
4. **Micro-animations & Interactions**:
   - All interactive elements (buttons, links, cards) MUST have hover states.
   - Add smooth transitions (`transition: all 0.3s ease-in-out`).
   - Use slight scaling on hover (`transform: translateY(-2px) scale(1.02)`).
5. **Layouts**:
   - Use CSS Grid and Flexbox for clean, organized layouts.
   - Ensure generous whitespace and padding to let elements breathe.
