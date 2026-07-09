---
version: alpha
name: Amazon Web Services
description: "AWS Orange (#FF9900) accent on a white/light-gray canvas. Functional over beautiful — the console manages 200+ services with information density and wayfinding as design priorities. Dense left navigation, resource tables, and status-coded infrastructure at 13px base type."

colors:
  primary: "#FF9900"
  on-primary: "#FFFFFF"
  primary-hover: "#EC7211"
  ink: "#16191F"
  ink-muted: "#545B64"
  ink-subdued: "#879596"
  canvas: "#FFFFFF"
  canvas-subdued: "#F2F3F3"
  surface-1: "#FFFFFF"
  surface-2: "#F2F3F3"
  border: "#D5DBDB"
  border-subtle: "#EAEDED"
  nav-background: "#232F3E"
  nav-active: "#FF9900"
  status-running: "#1D8348"
  status-stopped: "#E74C3C"
  status-pending: "#F39C12"
  status-provisioning: "#3498DB"
  link: "#0073BB"
  link-hover: "#005276"

typography:
  display:
    fontFamily: "Amazon Ember, Helvetica Neue, Arial, sans-serif"
    fontSize: 24px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: -0.01em
  body:
    fontFamily: "Amazon Ember, Helvetica Neue, Arial, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0em

spacing:
  base: 4px
  scale: [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]

radius:
  sm: 2px
  md: 4px
  lg: 4px
  pill: 9999px

shadows:
  card: "0 1px 4px rgba(0,0,0,0.1)"
  elevated: "0 4px 12px rgba(0,0,0,0.12)"
  modal: "0 8px 40px rgba(0,0,0,0.2)"

motion:
  duration-fast: 100ms
  duration-base: 150ms
  easing: cubic-bezier(0.2, 0, 0, 1)
---

## Rationale

**200 services, one interface** — The AWS Management Console is one of the most complex web applications ever shipped. EC2, S3, RDS, Lambda, CloudFormation, IAM, CloudFront, and hundreds more services each have their own dashboard, their own resource tables, and their own workflows — all accessible from a single console. The design mandate is wayfinding at industrial scale. AWS Orange (#FF9900) is the consistent brand signal; the rest of the UI is engineered to disappear.

**Functional over beautiful as a deliberate position** — AWS made a conscious decision early in its product life that the console's audience — developers, infrastructure engineers, DevOps teams — is optimized for information over aesthetics. Dense tables, small type (13px base), and no decorative elements are not failures of design investment but intentional optimizations. An engineer scanning 500 EC2 instances for a stopped instance in the wrong region does not need visual delight. They need reliable status colors and sortable columns.

**Orange as trust through continuity** — Amazon's heritage orange carries enormous brand equity for a specific audience: engineers who have used AWS since its launch. The orange never dominates the interface; it accents — primary button fills, active navigation items, the AWS logo mark. Its restraint prevents the orange from feeling cheap or alarming (which warm colors can, in dense technical UIs) while maintaining the brand thread across 200 service consoles.

**The nav is the product** — Because the service surface is so large, the left navigation is itself a primary user interface, not a frame for one. AWS Console's global navigation groups services into categories (Compute, Storage, Database, Networking, Security, etc.) with collapsible sections. Users spend as much cognitive energy navigating between services as using them. Search, pinned favorites, and recently visited services are first-class features of the nav, not afterthoughts.

## 1. Visual Theme & Atmosphere
The AWS console presents as clean government-infrastructure aesthetic: white surfaces, light gray backgrounds, dark navy navigation, and orange accents. There is no warmth, no personality injection, no playful illustration. The visual environment says: this is serious infrastructure management. Treat it accordingly.

The top navigation bar is dark navy (#232F3E), carrying the AWS logo, the account/region selector, and global search. Below it, individual service consoles own their left navigation sidebar (also dark, 220px wide) and a white main content area. The dark-nav / white-content split creates an immediate spatial hierarchy: the nav is the frame, the content is the work.

## 2. Color System
**Canvas**:
- Page background: #F2F3F3 — very light gray, keeps the overall console from feeling stark
- Content surface: #FFFFFF — all cards, tables, and panels
- Border: #D5DBDB — defines sections and table rows
- Subtle border: #EAEDED — internal dividers within sections

**Navigation**:
- Global nav / sidebar: #232F3E — deep navy, consistent across all service consoles
- Active nav item: orange left border (#FF9900) or highlighted background
- Nav text: #FFFFFF (primary), #8D9699 (inactive)

**Primary accent**:
- AWS Orange: #FF9900 — primary buttons, active states, visual accents
- Hover: #EC7211 — darker amber on interaction

**Text**:
- Default: #16191F — near-black, high contrast on white
- Muted: #545B64 — secondary labels, help text, column headers
- Subdued: #879596 — tertiary metadata, timestamps

**Links**:
- #0073BB — standard blue for hyperlinks (resource ARNs, service names)
- Hover: #005276 — deep blue

**Infrastructure status** (critical for EC2, RDS, ECS workflows):
- Running / Active: #1D8348 green
- Stopped / Terminated: #E74C3C red
- Pending / Initializing: #F39C12 amber
- Provisioning / Creating: #3498DB blue

## 3. Typography
Amazon Ember (licensed for AWS use) is a clean humanist grotesque. At 13px body — smaller than most modern web applications — it prioritizes density over comfort. This is intentional: an EC2 instances table might show 50 rows with 8 columns on a standard monitor, and every pixel of font size removed allows more rows and columns to be visible without scrolling.

Table column headers: 12px, weight 700, subdued ink (#545B64). Table cell values: 13px, weight 400. Resource identifiers (instance IDs, bucket names) use 13px monospace — AWS uses a monospace override for any machine-generated identifier to aid visual scanning and copy accuracy.

Heading scale within service dashboards: 20px for the page title (e.g., "EC2 Instances"), 16px for section headers within a page (e.g., "Instance Details"), 13px 600-weight for subsection labels.

## 4. Components & Patterns
**Resource table** (the primary pattern of the entire console):
- Fixed or auto-width columns; sortable headers with directional triangles
- Row-level checkbox (leftmost) for bulk actions
- Inline status badge (Running / Stopped / Pending / Provisioning) using semantic color tokens
- Row action dropdown on the right ("Instance State", "Connect", "Modify") 
- Filtering by tag, state, or custom filter above the table
- Column picker (right side) to show/hide columns

**Left navigation sidebar**:
- Service-specific, 220px wide, dark background
- Collapsible sections ("Instances", "Images", "Network & Security", etc.)
- Active page item: orange left border + slightly lighter background
- Count badges on items (e.g., "Alarms (3)")

**Service dashboard card**:
- White card, 4px border-left in status color for at-a-glance health
- Title, metric value (large, 24px+), subtitle with trend or comparison

**Breadcrumb navigation**:
- Service name > Resource type > Resource ID
- Each segment a blue link except the last (current page, plain text)

**Wizard / multi-step form** (used for launch workflows):
- Left sidebar showing step names with completion indicators
- Each step: full-page form with one or more sections
- "Next" button (orange primary) + "Previous" button (secondary/ghost)

**Alert / notification banner**:
- Top of page, full-width, icon + text + optional action link
- Success: green left border; Error: red; Warning: amber; Info: blue

## 5. Spacing & Layout
The console uses a 4px base grid. Main content area padding: 20px horizontal, 20px top. Table row height: 36px (comfortable for scanning with dense data). Between sections on a page: 24px. Between cards in a dashboard: 16px.

The service navigation sidebar is fixed at 220px. The global top nav is 56px. The main content area is fully fluid — tables expand to available width, which on ultrawide monitors can be 1600px+. AWS does not constrain content width; infrastructure engineers often use very wide screens precisely to see more table columns.

Form layouts inside wizards use a max-width of 900px to prevent extremely wide input fields that hurt usability.

## 6. Motion & Interaction
Motion is minimal and fast. Button clicks produce immediate visual feedback (100ms darkening). Status changes in resource tables use 0-animation (instant update) after API polling returns new state — no fade-in or slide-in to mask the operational nature of the data.

Dropdowns open at 100ms. Modals fade in at 150ms. The console's loading states use a simple orange progress bar across the top of the content area (similar to NProgress patterns) — functional loading indication without a blocking overlay.

Table row selection uses instant highlight at 0ms. Bulk action toolbar slides down from the top of the table at 150ms when rows are selected.

## Accessibility

### Contrast Ratios
- **#16191F on #FFFFFF**: 19.4:1 — passes AAA
- **#545B64 muted on #FFFFFF**: 6.3:1 — passes AA
- **#879596 subdued on #FFFFFF**: 4.5:1 — passes AA (borderline)
- **#FFFFFF on #FF9900 primary button**: 2.8:1 — fails AA for small text; AWS Orange must only be used for buttons with 18px+ or bold 14px+ text
- **#FFFFFF on nav #232F3E**: 14.8:1 — passes AAA
- **#FFFFFF on #1D8348 running status**: 5.1:1 — passes AA
- **#FFFFFF on #E74C3C stopped status**: 4.6:1 — passes AA

### Minimum Requirements
- **Focus indicator**: visible 2px outline; AWS uses orange (#FF9900) focus rings on interactive elements in the dark nav, blue (#0073BB) on white surfaces
- **Status indication**: all resource states use text label AND color — never color-only
- **Table accessibility**: proper `<th scope>` on headers; sortable columns marked with aria-sort; selected rows with aria-selected
- **Form validation**: inline text error messages with aria-describedby; error icon + color + text (never color-only)

### Motion
- Respects `prefers-reduced-motion`: yes — progress bar and transition animations disabled
- Loading indicators fallback to static spinner under reduced-motion

### Notes
- AWS Orange (#FF9900) fails WCAG AA for normal text on white (2.8:1) — it must never be used as a text color on white backgrounds; it is safe only as a button background with white text at large sizes
- The 13px base font size is smaller than the 16px WCAG guideline recommendation; AWS addresses this through high contrast (19.4:1) to compensate
- Region and account selectors in the global nav are critical wayfinding elements — they must have adequate focus states since mis-selecting a region in AWS can have significant operational consequences
