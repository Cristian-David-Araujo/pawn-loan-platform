---
name: ux-layout-and-hierarchy
description: Ensure the web application follows proper visual hierarchy, layout cleanliness, and avoids UI redundancies (like massive inline forms on list pages).
---

# UX Layout & Hierarchy Guidelines

When building or updating UI views, enforce these rules to maintain a clean, intuitive, and professional interface:

1. **Avoid Clutter on List Views**:
   - Do NOT place large creation or editing forms directly inline above or below a data table. This breaks visual hierarchy.
   - Primary data tables should be the focus of the "View" page.

2. **Use Modals for Creation/Edition**:
   - Any secondary action like "Create New Item" (e.g., Create Customer, Create Loan) MUST open in a modal (`.modal-backdrop` > `.modal-panel`).
   - If the form is too complex for a modal, it should be moved to a dedicated new page route (e.g., `/loans/new`).

3. **Top-Level Actions**:
   - The primary action to trigger these modals MUST be placed in the top right of the screen, specifically inside the `<template #actions>` slot of the `PageHeader` component.

4. **Empty States**:
   - If a table or list has no data, always provide a clear `.empty-state` div indicating there is no data, rather than showing just an empty table header.

5. **Logical Grouping**:
   - Group related form fields inside `.form-section` containers with clear `.form-section-title` headings to improve cognitive load for the user.
