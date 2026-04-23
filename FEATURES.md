# Features — Current & Planned

## Current Features

### Discovery Page (`/`)
- [x] Live 3D network topology graph (canvas/Three.js) with physical underlay, virtual overlay, and combined view modes
- [x] Real-time fault highlighting — faulty nodes change colour on the graph
- [x] Fault injection sidebar — categorised rack of production-grade faults, inject per node
- [x] NOC Live Status scoreboard — Security Drift, Maintenance Queue, Fleet Health
- [x] Node inspector panel — click a node to inspect hostname, role, site, state
- [x] Active incidents panel — shows all injected faults with tag, time, and label
- [x] Scenario Engine modal — 11 failure playbooks (BGP hijack, fibre cut, DDoS, STP storm, etc.) with intensity slider
- [x] Network Reset button — clears all faults, alarms, and drift state across Hub + Simulator
- [x] Layer mode toggle — Physical Underlay / Virtual Overlay / Combined
- [x] Pause/resume graph simulation
- [x] Camera reset button

### NAPI Ops Page (`/ops`)
- [x] Southbound ingestion pipeline visualisation (3-step flow diagram)
- [x] Live TMF-642 alarm registry table — Incident ID, Severity, Probable Cause, Resource, State, Time
- [x] Alarm mediation stats — parse count, latency

### Inventory Page (`/inventory`)
- [x] Full device inventory table — Hostname, IP, Site, Role, Vendor, Model, Status
- [x] Text search filter
- [x] Vendor dropdown filter

### Platform-wide
- [x] WebSocket real-time updates across all pages and browser tabs
- [x] Southbound telemetry stream footer — SYSLOG, METRIC, NETFLOW log panel
- [x] System status indicator with live beacon (SYSTEMS SYNCHRONIZED / BACKBONE OFFLINE)
- [x] Auto-reconnect WebSocket on disconnect (3s retry)
- [x] SYNC_STATE on reconnect — restores current fault/alarm/mode state to new tabs
- [x] SYSTEM_RESET broadcast — all open tabs clear fault state simultaneously
- [x] Honest mediation engine — regex/threshold TMF-642 normalisation, no inference
- [x] Heartbeat monitor — Communication Loss alarm after 25s silence per hostname
- [x] Simulation mode tracking — NORMAL / CHAOS propagated to all clients

### Simulator (Backend)
- [x] TelemetryProducer — NetFlow (500ms), ambient syslog (5s), SNMP metrics (15s)
- [x] Security drift graduation (30s), version aging (60s)
- [x] 11 scenario playbooks with asyncio task execution
- [x] Fault injection via `trigger_incident` — staged syslog symptom storm at 50ms intervals
- [x] Opaque diagnostic sentinel (`%%SYSTEM-1-ANOMALY`) for agent detection
- [x] Topology sync from Hub (`/api/infrastructure/sync`)

### MANO API (Backend)
- [x] VNF cold migration — atomic Neo4j transaction, vCPU capacity validation, PROVISIONING blackout
- [x] VNF patching — 60s blackout, concurrent patch limit (max 5)
- [x] Health verification — watchdog cancellation during VALIDATION window (120s)
- [x] Maintenance window awareness — 50% provisioning delay discount during 02:00–05:00 local
- [x] State sync to Simulator on all VNF lifecycle transitions

---

## Planned Features

### Frontend Redesign (Visual Overhaul)

#### Phase 1 — Design System
- [ ] CSS custom property token system (surfaces, accents, borders, radius, shadows)
- [ ] Dot-grid background pattern on main viewport
- [ ] Noise/grain texture overlay for depth
- [ ] Custom scrollbar matching the dark theme

#### Phase 2 — Component Library
- [ ] Gradient-border card panels (CSS `::before` mask technique)
- [ ] Pill-style severity badges with translucent fill + glow
- [ ] Improved primary action buttons — gradient fill, glow on hover
- [ ] Table redesign — sticky header blur, zebra striping, left-accent row hover
- [ ] Telemetry log entries — colour-coded left border per type, fade-in animation, relative timestamps

#### Phase 3 — Discovery Page
- [ ] Fault rack accordion — animated open/close, category count badge
- [ ] NOC scoreboard metric tiles — large number, threshold colour ring, sparkline placeholder
- [ ] Rich node inspector card — status ring, property key/value rows, fault history chips
- [ ] Active fault cards — gradient red border, relative time ("2m ago"), dismiss button
- [ ] Layer mode segmented pill control (replace raw buttons)

#### Phase 4 — Ops Page
- [ ] Animated pipeline diagram — travelling dot along dashed connector lines
- [ ] Alarm table sortable column headers
- [ ] Row-level severity tinting on alarm table
- [ ] `IN SERVICE` / `RAISED` animated pill badges
- [ ] Total alarm count badge in table header

#### Phase 5 — Inventory Page
- [ ] Pill-style vendor filter chips (replace `<select>`)
- [ ] Search input with clear button
- [ ] Compact / comfortable table density toggle
- [ ] Hostname and IP values in monospace
- [ ] Coloured status pills on Status column

#### Phase 6 — Graph Visualisation
- [ ] Layered node rings — outer glow ring (pulses on fault), inner radial gradient fill
- [ ] Node size encoding by role (routers larger than VNFs)
- [ ] Travelling particle animation along active traffic paths
- [ ] INTERCONNECT link opacity proportional to bandwidth
- [ ] HOSTS link rendered as thin dashed cyan
- [ ] Red pulsing halo on faulty nodes (CSS keyframes via canvas)
- [ ] Rich hover tooltip card — hostname, role chip, site, state badge, last fault
- [ ] Tooltip entrance animation (`transform: translateY`)
- [ ] Radial gradient bloom background on canvas (blue-purple centre)

#### Phase 7 — Header & Navigation
- [ ] Frosted glass header (`backdrop-filter: blur(20px)`)
- [ ] Animated underline on active nav item
- [ ] Typewriter animation on status label at connection
- [ ] Thin 1px cyan→purple gradient separator below header

---

## Known Issues / Tech Debt

- [ ] Alarm deduplication — only Communication Loss is deduplicated; all other alarm types accumulate on long runs
- [ ] Startup order dependency — Simulator falls back to local JSON (wrong key schema) if Neo4j is offline at boot; manual `/api/infrastructure/sync` required after Neo4j comes up
- [ ] `requirements.txt` is stale — lists Streamlit/LangGraph/LangChain (old planned architecture); actual runtime deps are FastAPI, uvicorn, httpx, apscheduler, neo4j, pydantic, python-dotenv
- [ ] APScheduler "max instances" warnings on the 500ms NetFlow job under load (benign but noisy)
- [ ] Browser caches `type="module"` JS aggressively — Ctrl+Shift+R required after any JS change during development
