# Design Tokens

## Overview

Centralized definition of all visual design tokens used across the ModelLens UI. These tokens are implemented as CSS custom properties (variables) on the `:root` selector. All component specs reference tokens by name with their concrete values noted in parentheses.

Does not define behavior or logic. Serves purely as the single source of truth for visual constants.

## Boundaries

- Owns: definition of all color, typography, spacing, and shape tokens.
- Must not: contain any component logic, layout rules, or responsive breakpoints.
- Must not: define dark mode variants (light mode only).

## Dependencies

None — this is a leaf reference document.

## Behavior

1. All tokens are declared as CSS custom properties on `:root`.
2. Components consume tokens via `var(--token-name)` in their styles.
3. No fallback values are needed (tokens are always defined).

## Token Definitions

### Colors — Background

| Token | Value | Usage |
|---|---|---|
| `--color-bg-page` | `#F5F6F8` | Page-level background |
| `--color-bg-surface` | `#FFFFFF` | Cards, panels, inputs, header |
| `--color-bg-canvas-idle` | `#FFFFFF` | StreamViewer idle placeholder |

### Colors — Text

| Token | Value | Usage |
|---|---|---|
| `--color-text-primary` | `#2C3E50` | Headings, input text, label text |
| `--color-text-muted` | `#6B7B8D` | Secondary text, idle messages, threshold display |

### Colors — Border

| Token | Value | Usage |
|---|---|---|
| `--color-border` | `#D4DAE0` | Card borders, input borders, header bottom border, dividers |

### Colors — Interactive (Primary Action)

| Token | Value | Usage |
|---|---|---|
| `--color-primary` | `#5B8CB8` | Primary button background (enabled), bounding box stroke, label badge background, link-style text buttons |
| `--color-primary-disabled` | `#A8C4DC` | Primary button background (disabled) |

### Colors — Interactive (Secondary / Stop Action)

| Token | Value | Usage |
|---|---|---|
| `--color-secondary` | `#6B7B8D` | Stop button background (enabled) |
| `--color-secondary-disabled` | `#D4DAE0` | Stop button background (disabled) |

### Colors — Constant

| Token | Value | Usage |
|---|---|---|
| `--color-white` | `#FFFFFF` | Button text, label overlay text |

### Typography

| Token | Value | Usage |
|---|---|---|
| `--font-family` | `system-ui, -apple-system, sans-serif` | All UI text |
| `--font-size-heading` | `1.5rem` | Header h1 |
| `--font-size-body` | `1.1rem` | Idle placeholder text |
| `--font-size-small` | `0.85rem` | Bulk action buttons (Select All / Clear All) |
| `--font-size-caption` | `0.8rem` | Confidence threshold display |
| `--font-size-canvas-label` | `14px` | Canvas bounding box label text |

### Spacing

| Token | Value | Usage |
|---|---|---|
| `--spacing-xs` | `4px` | Dropdown margin-top, label badge inner padding vertical, bulk action button padding |
| `--spacing-sm` | `8px` | Gap between buttons in a row, gap between bulk actions, margin-top for update button, label badge text padding |
| `--spacing-md` | `12px` | Input/select horizontal padding, header vertical padding, card internal padding-block, gap between form elements |
| `--spacing-lg` | `16px` | Main content padding vertical, gap between sections, card padding, column gap |
| `--spacing-xl` | `24px` | Main content padding horizontal, header horizontal padding |

### Shape

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | `4px` | Buttons, inputs, select, canvas, dropdown, idle placeholder |
| `--radius-md` | `8px` | Card containers (CameraConfig) |

### Layout

| Token | Value | Usage |
|---|---|---|
| `--canvas-width` | `800` | Canvas logical width (attribute, not CSS) |
| `--canvas-height` | `450` | Canvas logical height (attribute, not CSS) |
| `--canvas-aspect` | `16/9` | Canvas CSS aspect-ratio |
| `--dropdown-max-height` | `300px` | TargetLabels dropdown panel max-height |
| `--dropdown-list-max-height` | `220px` | TargetLabels label list scroll area max-height |

## Inputs

None (static definitions).

## Outputs

A CSS stylesheet (or `<style>` block) providing all custom properties on `:root`.

## Invariants

- Every color, font, spacing, and shape value used by any component must be defined here.
- No component may introduce a visual constant that is not listed in this document.
- Token values must match the reference implementation in `tmp/` exactly.

## Edge Cases

None — static definitions only.

## Related

- [App](../App.md): consumes page-level tokens.
- [Header](../components/Header.md): consumes heading, surface, border tokens.
- [CameraConfig](../components/CameraConfig.md): consumes form element tokens.
- [StreamViewer](../components/StreamViewer.md): consumes canvas, bounding box tokens.
- [TargetLabels](../components/TargetLabels.md): consumes dropdown, interactive tokens.
