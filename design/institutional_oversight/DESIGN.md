---
name: Institutional Oversight
colors:
  surface: '#f8f9fb'
  surface-dim: '#d9dadc'
  surface-bright: '#f8f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#edeef0'
  surface-container-high: '#e7e8ea'
  surface-container-highest: '#e1e2e4'
  on-surface: '#191c1e'
  on-surface-variant: '#42474f'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f3'
  outline: '#727780'
  outline-variant: '#c2c7d1'
  surface-tint: '#2d6197'
  primary: '#00355f'
  on-primary: '#ffffff'
  primary-container: '#0f4c81'
  on-primary-container: '#8ebdf9'
  inverse-primary: '#a0c9ff'
  secondary: '#1b6d24'
  on-secondary: '#ffffff'
  secondary-container: '#a0f399'
  on-secondary-container: '#217128'
  tertiary: '#532800'
  on-tertiary: '#ffffff'
  tertiary-container: '#743b00'
  on-tertiary-container: '#f9a767'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4ff'
  primary-fixed-dim: '#a0c9ff'
  on-primary-fixed: '#001c37'
  on-primary-fixed-variant: '#07497d'
  secondary-fixed: '#a3f69c'
  secondary-fixed-dim: '#88d982'
  on-secondary-fixed: '#002204'
  on-secondary-fixed-variant: '#005312'
  tertiary-fixed: '#ffdcc4'
  tertiary-fixed-dim: '#ffb780'
  on-tertiary-fixed: '#2f1400'
  on-tertiary-fixed-variant: '#6f3800'
  background: '#f8f9fb'
  on-background: '#191c1e'
  surface-variant: '#e1e2e4'
  warning-orange: '#F57C00'
  danger-red: '#D32F2F'
  border-gray: '#E5E7EB'
  surface-white: '#FFFFFF'
  text-main: '#1F2937'
typography:
  display-kpi:
    fontFamily: IBM Plex Sans
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: IBM Plex Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: IBM Plex Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  table-data:
    fontFamily: IBM Plex Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  sidebar-width: 280px
  container-padding: 2rem
  gutter: 1.5rem
  stack-sm: 0.5rem
  stack-md: 1rem
---

## Brand & Style

This design system is built upon the pillars of **precision, accountability, and institutional trust**. Designed for environmental surveillance, the aesthetic rejects decorative trends in favor of a "Government Dashboard" utility. It prioritizes information density and clear hierarchy to assist officials in high-stakes monitoring and decision-making.

The visual style is **Corporate / Modern** with a focus on structured data. It utilizes a white-label, systematic approach characterized by:
- **Utilitarian Clarity:** High-contrast text and purposeful use of color.
- **Structural Integrity:** Use of thin, consistent borders to define zones rather than aggressive shadows.
- **Data-First Layouts:** Minimalist containers that recede to let environmental metrics and AI analysis take center stage.

## Colors

The palette is anchored in **Government Blue (#0F4C81)** to evoke stability and authority. **Environmental Green (#2E7D32)** is used as a secondary color specifically for compliance and healthy status indicators.

- **Primary & Secondary:** Reserved for action-oriented elements (buttons, active navigation) and status indications.
- **Functional Accents:** Warning Orange and Danger Red are strictly reserved for alerts, risk levels, and critical system failures.
- **Neutrals:** The background uses a cool off-white (#F7F8FA) to reduce eye strain, while the surface remains pure white (#FFFFFF) to create a clear "paper-like" layer for content.

## Typography

**IBM Plex Sans** is the sole typeface for this design system. Its technical, engineered character aligns with the application’s surveillance and forensic nature.

- **KPI Typography:** Large, semi-bold weights for high-level metrics.
- **Data Tables:** A slightly reduced font size (13px) is used for tables to increase information density without compromising legibility.
- **Labels:** Uppercase styles with increased letter spacing are used for table headers and section overviews to differentiate metadata from actionable content.

## Layout & Spacing

The layout follows a **Fixed-Fluid Grid** model:
- **Sidebar:** A fixed 280px vertical navigation bar on the left for persistent access to surveillance modules.
- **Main Content:** A fluid area that utilizes a 12-column grid for dashboard widgets and data tables.
- **Density:** Spacing is tight (8px/16px increments) to minimize scrolling and keep essential AI analysis visible at a glance.
- **Responsive Behavior:** On tablet, the sidebar collapses into an icon-only rail. On mobile, the sidebar is hidden behind a hamburger menu, and all grid elements stack vertically into a single column.

## Elevation & Depth

This design system avoids high-contrast shadows to maintain a professional, flat aesthetic. Depth is communicated via **Tonal Layers and Borders**:

- **Level 0 (Background):** #F7F8FA. The canvas for all content.
- **Level 1 (Surface):** #FFFFFF with a 1px solid border (#E5E7EB). Used for KPI cards, tables, and content sections.
- **Level 2 (Overlay):** Used only for dropdowns and tooltips. These include a very soft, diffused shadow (0px 4px 12px rgba(0,0,0,0.05)) to separate them from the underlying data.
- **Active State:** Elements are highlighted with a 2px left-border (in Primary Blue) rather than a shadow to indicate focus.

## Shapes

The shape language is **Soft yet Structured**. A 0.25rem (4px) base radius is applied to almost all components.

- **Standard Elements:** Buttons, Input fields, and Cards use the 4px radius.
- **Badges:** Use a 2px radius or sharp corners to distinguish status indicators from actionable buttons.
- **Strictness:** Large-scale rounding (pills/circles) is prohibited except for user avatars and notification pips, ensuring the UI feels rigorous and institutional.

## Components

### Sidebar Navigation
The sidebar uses a dark-tinted variation of the Primary Blue or a high-contrast White. Active items feature a Primary Blue background with a high-contrast white icon. Group headers are in `label-caps`.

### Data Tables
Tables are the core of the application. 
- **Style:** Minimalist borders between rows; no vertical borders. 
- **Density:** High. Row heights are restricted to 40px. 
- **Sorting:** Interactive headers with chevron icons.
- **Numbers:** Use tabular lining for alignment in columns.

### KPI Cards
Simple, white containers with a 1px border. The top contains a small icon and label; the center features the `display-kpi` value; the bottom contains a small trend indicator (e.g., "+2.4%").

### Badges & Risk Levels
Rectangular with light background tints:
- **Critical:** Red background (10% opacity) + Red text.
- **High:** Orange background (10% opacity) + Orange text.
- **Normal:** Green background (10% opacity) + Green text.

### Charts
- **Palette:** Use the Primary Blue as the base, with variations in saturation for multi-series data. 
- **Axes:** Thin light-gray grid lines.
- **Interactivity:** Tooltips should follow the "Level 2" elevation style.

### Buttons
- **Primary:** Solid #0F4C81, White text.
- **Secondary:** Solid #2E7D32, White text (Compliance/Success actions).
- **Outline:** Transparent, 1px #E5E7EB border, #1F2937 text.
- **Danger:** Solid #D32F2F, White text.

### Filters & Inputs
Inputs use a white background with a 1px #E5E7EB border. Focus states use a 1px #0F4C81 border with a subtle 2px blue outer glow.