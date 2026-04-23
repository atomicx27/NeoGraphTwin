# Implementation Reference

Technical internals for the three services that make up the Apex Platform.

---

## 1. Hub / UI Server — `src/ui/server.py` (port 8888)

### Startup

Templates (`discovery.html`, `ops.html`, `inventory.html`) are read from disk and cached in memory at startup. **HTML changes require a server restart.**

### ConnectionManager

Central state object. Holds:
- `active_connections` — map of WebSocket → metadata (`is_human` flag)
- `active_alarms` — list of TMF-642 alarm dicts (appended by mediation engine + heartbeat monitor)
- `active_debug_faults` — list of `INTERNAL_UI_DEBUG` events (simulator fault injections; human-only)
- `simulation_mode` — `"NORMAL"` | `"CHAOS"`
- `last_seen` — hostname → last heartbeat timestamp

### WebSocket Protocol

Clients connect to `/ws/events`. If a client sends `IDENTIFY:HUMAN_UI`, it is flagged as a human UI and receives:
1. An immediate `SYNC_STATE` event with current alarm/fault/mode state
2. All future `INTERNAL_UI_DEBUG` broadcasts (simulator fault visualisation)

Non-human connections (agents, tools) receive everything _except_ `INTERNAL_UI_DEBUG`.

### Telemetry Ingestion — `POST /api/v1/telemetry/ingest`

All telemetry from the Simulator arrives here. Pipeline:
1. Update heartbeat for the hostname
2. Track `simulation_mode` if present in payload
3. If `INTERNAL_UI_DEBUG` with `state=FAULTY`, store in `active_debug_faults`
4. Run `HonestMediationEngine` normalisation on SYSLOG and METRIC events
5. If a normalised alarm is produced, append to `active_alarms` and broadcast as `TMF_ALARM`
6. Broadcast the raw event to all eligible connections

### HonestMediationEngine — `src/ui/mediation_engine.py`

Regex + threshold only. No inference, no LLM.

| Pattern | Alarm type |
|---|---|
| BGP keywords | Routing alarm — BGP Session Down |
| OSPF keywords | Routing alarm — OSPF Adjacency Lost |
| LINK/interface keywords | Equipment alarm — Physical Link Down |
| CPU > 90% | Performance alarm — CPU Threshold Exceeded |
| `%%SYSTEM-1-ANOMALY` sentinel | Diagnostic alarm — Opaque Anomaly |

Each alarm gets a deterministic ID: `ALM-{TYPE}-{timestamp}-{hostname}`.

### Heartbeat Monitor

Background task runs every 5 seconds. Any hostname silent for > 25 seconds gets a `Communication Loss` `TMF_ALARM` raised and broadcast. Alarm is deduplicated — one per hostname per silence period.

### Network Reset — `POST /api/reset`

1. Clears `active_debug_faults` and `active_alarms` on the Hub
2. Calls `POST /api/infrastructure/reset` on the Simulator (timeout 10s)
3. Broadcasts `SYSTEM_RESET` to all WS clients so every open browser tab clears its local fault state

---

## 2. Infrastructure Simulator — `src/sim/network_app.py` (port 9999)

### Startup

1. Loads `fault_symptoms_database.json`
2. Tries to fetch topology from Hub (`/api/topology`). Falls back to `data/apex/infrastructure_sid.json` if Hub is offline.
3. Starts APScheduler jobs:

| Job | Interval | What it does |
|---|---|---|
| `emit_flow` | 500ms | Random NetFlow record between two live nodes |
| `emit_ambient_syslog` | 5s | Background syslog noise (tagged `is_ambient`) |
| `emit_metric` | 15s | SNMP-style CPU/memory metrics |
| `increment_drift` | 30s | Advances security drift score on random nodes |
| `age_versions` | 60s | Increments `version_age` on VNFs |

### TelemetryProducer — `src/sim/telemetry_producer.py`

Owns `nodes`, `edges`, `active_incidents`, `drifts`, `link_overrides`.

**`trigger_incident(fault_id, hostname)`**: Looks up fault in symptoms DB, staggers all symptom syslogs at 50ms intervals (event storm), then sends an opaque `%%SYSTEM-1-ANOMALY` sentinel. Sends `INTERNAL_UI_DEBUG` with `state=FAULTY` to the Hub — this is human-only visual highlighting, not ground truth for agents.

**`resolve_incident(hostname, fault_id)`**: Clears the incident, sends `INTERNAL_UI_DEBUG` with `state=ACTIVE`, and emits a recovery syslog.

### ScenarioEngine — `src/sim/scenarios/engine.py`

11 built-in playbooks executed as asyncio tasks:

| Playbook ID | Description |
|---|---|
| `fiber_cut` | Backbone link down PAR ↔ MUM, traffic reroute |
| `thermal_cascade` | Paris PoP thermal evacuation |
| `mass_zero_day` | Mass CVE patch race |
| `bgp_route_leak` | Traffic hijack via misconfigured peer |
| `bgp_hijack` | Unauthorised ASN announcement |
| `bgp_flap` | Repeated hold-timer expiry |
| `memory_leak_daemon` | Control plane slow crash |
| `dns_amplification_ddos` | Edge link saturation |
| `cert_expiration` | VPN & management plane collapse |
| `spanning_tree_storm` | L2 broadcast storm (STP loop) |
| `qos_misconfig` | Silent VoIP throttle |

**`stop_all()`**: Cancels all running tasks, clears `link_overrides`, flips FAILED→ACTIVE on all nodes.

### Topology Sync — `POST /api/infrastructure/sync`

Re-fetches topology from Hub and reloads the producer's node/edge lists. Call this after Neo4j comes online if the simulator started first.

### Full Reset — `POST /api/infrastructure/reset`

Stops scenarios, clears `active_incidents`, `drifts`, `_fault_queue`, `link_overrides`, resets all node states to `ACTIVE` and `version_age` to 0.

---

## 3. MANO API — `src/sim/orchestrator_api.py` (port 9998)

VNF lifecycle management. Reads/writes Neo4j directly and syncs state to the Simulator via `POST /api/infrastructure/update_node`.

### VNF States

```
ACTIVE → PROVISIONING → VALIDATION → ACTIVE
                                   ↘ FAILED  (watchdog timeout)
ACTIVE → PATCHING → ACTIVE
```

### Endpoints

**`POST /api/mano/migrate_vnf`** `{ vnf_hostname, target_host_name }`

Atomic Neo4j transaction:
1. Validates VNF exists, is not already PROVISIONING, and is not already on target
2. Validates target host has sufficient vCPU capacity
3. Deletes old `HOSTS`/`CONSUMES` relationships, creates new ones, updates vCPU usage
4. Schedules `complete_provisioning` background task (30–120s delay, halved during maintenance window)
5. After delay, moves VNF to `VALIDATION` and starts a 120s watchdog

**`POST /api/mano/patch_vnf`** `{ vnf_hostname }`

- Max 5 concurrent patches (429 if exceeded)
- Sets `state=PATCHING`, `version_age=0` in Neo4j + Simulator
- After 60s, sets `state=ACTIVE`

**`POST /api/mano/verify_health`** `{ vnf_hostname }`

- Must be called while VNF is in `VALIDATION` state
- Cancels the watchdog, sets `state=ACTIVE`
- If not called within 120s, watchdog fires and sets `state=FAILED`

### Maintenance Windows

Timezone-aware maintenance windows (02:00–05:00 local time per site). A VNF migration targeting a site in its window gets a 50% provisioning delay reduction.

---

## 4. Frontend — `src/ui/static/js/`

| File | Role |
|---|---|
| `app.js` | Module entry point. WebSocket setup, fault state, UI controls (pause, reset, layer mode, chaos modal) |
| `graph.js` | Three.js/canvas topology renderer. Node colours, physics, layer mode (underlay/overlay/combined) |
| `discovery.js` | Discovery page: fault injection sidebar, NOC scoreboard, node inspector |

### Event Flow

```
Simulator ──HTTP──► Hub /ingest ──WS broadcast──► Browser app.js routeEvent()
                                                      ├── TMF_ALARM     → mark node faulty, update panel
                                                      ├── INTERNAL_UI_DEBUG → same (human UI only)
                                                      ├── SYSTEM_RESET  → clear all local fault state
                                                      ├── SYNC_STATE    → restore state on reconnect
                                                      └── SYSLOG/METRIC/NETFLOW → telemetry log panel
```

### Browser Caching

`app.js` and `graph.js` are served as ES modules (`type="module"`). Browsers cache modules aggressively. After any JS change, force a hard refresh: **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (Mac).

---

## 5. Neo4j Schema

```
(:Device {hostname, role, site, state, vcpu_usage, total_vcpu, version_age, ...})
  -[:INTERCONNECT {bandwidth_gbps}]->(:Device)   # physical links
  -[:CONNECTED_TO]->(:Device)                     # alias, same query
  -[:HOSTS {available_slots}]->(:Device {role:"VNF"})
  -[:CONSUMES {priority}]->(:Device)              # VNF back-ref to host

(:Company)-[:CUSTOMER_OF]->(:Device)
```

Roles: `HOST`, `VNF`, `ROUTER`, `SWITCH`, `FIREWALL`, and others.  
Sites: `PAR`, `LON`, `FRA`, `BER`, `MUM`, `SFO`, `NYC`, `SIN`, `TOK`, `SYD`.

---

## 6. Key Data Files

| File | Purpose |
|---|---|
| `docs/fault_symptoms_database.json` | Maps fault IDs to syslog symptom sequences + candidate fixes |
| `data/apex/infrastructure_sid.json` | Fallback topology (used if Neo4j is offline at simulator startup) |
| `.env` | `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `SIMULATOR_URL`, `MGMT_HUB_URL` |

---

## 7. Known Gotchas

**Startup order**: Start Neo4j first, then Hub, then Simulator. If the Simulator starts without Neo4j, it falls back to the local JSON file which uses different link key names than `/api/topology`. Fix: after Neo4j is up, call `POST http://localhost:9999/api/infrastructure/sync`.

**Template caching**: Hub loads HTML templates into memory at startup. Editing a template requires restarting the Hub.

**Alarm deduplication**: Only `Communication Loss` alarms are deduplicated. All other alarm types append on each trigger — running the simulator for long periods accumulates alarms in `active_alarms`. A `/api/reset` call clears them.

**APScheduler "max instances" warnings**: The 500ms NetFlow job occasionally overlaps with itself under load. These warnings are benign — the scheduler skips the overlapping instance.
