# Artifacts Builder

Build elaborate, multi-component HTML artifacts using React, Tailwind CSS, and shadcn/ui.

## When to Use
- Complex frontend demos, dashboards, or interactive tools
- Artifacts requiring state management, routing, or UI components
- Not for simple single-file HTML snippets

## Process
1. Initialize project with React 18 + TypeScript + Vite + Tailwind + shadcn/ui
2. Develop the artifact by editing generated code
3. Bundle all code into a single HTML file using Parcel + html-inline
4. Present the bundled artifact to the user

## Stack
- React 18 + TypeScript (via Vite)
- Tailwind CSS 3.4+ with shadcn/ui theming
- Parcel for bundling to single HTML
- 40+ shadcn/ui components pre-installed

## Style Guidelines
Avoid "AI slop": no excessive centered layouts, purple gradients, uniform rounded corners, or Inter font defaults.
