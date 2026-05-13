# Avant Visual System

## Reusable Prompt

Use the following prompt when creating new versions of the Avant Streamlit dashboard:

```text
Create a premium data dashboard for Streamlit with a strong enterprise visual language.

Visual direction:
- Fixed light theme for the main workspace.
- Dark sidebar in deep navy/petrol, with stronger contrast than the content area.
- Main content area bright and clean, with subtle gradients and soft atmospheric color.
- Accent colors must be vivid and confident: turquoise as the primary interactive accent, electric blue as secondary accent, and coral/red for alert or contrast moments.
- The interface should feel modern, technical, executive, and slightly bold, not minimalist or washed out.

Color palette:
- Sidebar background: #11243A to #0C1B2D
- Sidebar titles and active emphasis: #19D0BC and #10B8A3
- Main page background: #E7EDF6 with soft gradients toward #F5F8FD
- Primary text: #1F3146
- Secondary text: #556A82
- Primary accent: #10C9BB
- Secondary accent: #1778E6
- Contrast accent: #F04D63
- Borders: #D2DEEC / #B9C8DB
- Card background: white with subtle blue tint gradients

Typography:
- Use "Segoe UI" or "IBM Plex Sans" as the main type family.
- Titles in uppercase with wider letter spacing.
- Section titles must feel compact, technical, and dashboard-like.
- Metric values should be darker and heavier than surrounding text.

Component behavior:
- Sidebar must look modular, with grouped blocks, subtle borders, translucent inner panels, and strong visual hierarchy.
- The sidebar should never share the same visual treatment as the main plotting area.
- Tabs must feel like control chips, with the active tab receiving a brighter, more saturated treatment.
- Cards, metrics, tables, forms, and charts should use rounded corners, soft but visible shadows, and crisp borders.
- Inputs and selectors should look polished and elevated, never flat.
- Checkboxes and selection controls must have fully styled states, including hover, focus, and checked.
- Tables must have refined headers, alternating row backgrounds, and clear but elegant borders.
- Graphs should inherit the same palette: turquoise, blue, coral/red, deep navy, and muted steel blue.

Mood:
- Think “executive climate intelligence dashboard”.
- The result should feel more assertive than a generic light theme.
- Avoid purple-heavy palettes, default Streamlit styling, or plain gray enterprise UI.
- Keep the layout readable and production-safe, but visually memorable.
```

## Design Tokens

Use these tokens as the base for future implementations:

```yaml
theme:
  mode: light

colors:
  page_bg: "#E7EDF6"
  page_bg_soft: "#F5F8FD"
  surface_base: "#FFFFFF"
  surface_muted: "#F6F9FD"
  surface_alt: "#EDF3FB"
  surface_strong: "#E0E8F4"

  text_primary: "#1F3146"
  text_secondary: "#556A82"
  text_muted: "#7F91A6"

  accent_primary: "#10C9BB"
  accent_primary_strong: "#17D2BF"
  accent_secondary: "#1778E6"
  accent_danger: "#F04D63"
  accent_ink: "#16273C"

  sidebar_bg: "#11243A"
  sidebar_bg_strong: "#0C1B2D"
  sidebar_text: "#EDF5FB"
  sidebar_text_muted: "#8EA8C2"
  sidebar_title: "#19D0BC"
  sidebar_active: "#10B8A3"

  border_soft: "#D2DEEC"
  border_strong: "#B9C8DB"
  border_focus: "#93B9D7"

  table_header: "#E8F0FA"
  table_row_alt: "#F2F7FD"

  chart_turquoise: "#10C9BB"
  chart_blue: "#1778E6"
  chart_coral: "#F04D63"
  chart_navy: "#16273C"
  chart_steel: "#7F98B4"

effects:
  shadow_soft: "0 16px 38px rgba(27, 46, 74, 0.12)"
  shadow_card: "0 20px 42px rgba(27, 46, 74, 0.14)"
  shadow_large: "0 20px 42px rgba(27, 46, 74, 0.14)"

radii:
  input: "12px"
  card: "16px"
  panel: "18px"
  chip: "999px"

typography:
  family_base: "\"Segoe UI\", \"IBM Plex Sans\", sans-serif"
  title_case: "uppercase"
  title_tracking: "0.07em"
  section_tracking: "0.08em"
```

## Layout Rules

- Sidebar always dark, content area always light.
- Sidebar must use modular blocks with internal grouping.
- Plot area must stay brighter than filters.
- Active controls must use turquoise or blue.
- Destructive or alert emphasis must use coral/red.
- Avoid full-flat backgrounds; prefer soft gradients.
- Charts and tables must follow the same palette as the shell.
- Do not let default Streamlit colors override the visual system.

## Component Notes

### Sidebar

- Use a vertical dark gradient.
- Use section headers with a thin accent bar.
- Use translucent inner cards for filter groups.
- Keep labels light and controls dark-translucent.

### Tabs

- Base tab should look like a soft elevated chip.
- Active tab should be brighter, more saturated, and more contrasted.
- Each tab panel may receive a unique subtle tinted background, but never a heavy block color.

### Buttons

- Default button: white/blue-tinted gradient with strong border.
- Primary action button: turquoise gradient with strong glow and high contrast.
- Hover state should feel more vivid, not only darker.

### Tables

- White table body.
- Blue-tinted table header.
- Alternating rows with subtle cool tint.
- Borders visible but refined.

### Charts

- Primary sequence:
  - turquoise
  - coral/red
  - electric blue
  - dark navy
  - steel blue
- Grid lines should be light and cool-toned.
- Background should remain clean and bright.

## Reference Summary

The desired identity is:

- executive
- climate-tech
- premium dashboard
- assertive light theme
- dark modular sidebar
- vivid turquoise/blue/coral accents
- sharp, clean, data-first presentation
