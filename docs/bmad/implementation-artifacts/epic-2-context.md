# Epic 2 Context: Configure enterprise, shifts and equipment

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Enable authenticated users to configure the enterprise hierarchy, shift calendar, equipment, telemetry signals, and machine state rules that downstream telemetry and generation depend on. The planning-artifacts directory contains architecture and analytics design notes, but no PRD, UX/design, or product brief; the roadmap remains the source for epic goals and story titles.

## Stories

- Story 2.1: Enterprise and shift calendar
- Story 2.2: Lines and machine assignment
- Story 2.3: Component and signal configuration
- Story 2.4: Machine state configuration
- Story 2.5: Configuration journey

## Requirements & Constraints

- Configuration records use only `ACTIVE` and `DISABLED`; do not physically delete them through user APIs. New records may start disabled, and activation requires full domain validation. Store an independent status on each entity; do not infer or expose an effective status.
- Enterprise has a required IANA timezone. Once telemetry, incidents, generator runs, or calculated analytics exist, its timezone cannot change.
- Shifts repeat daily in the Enterprise timezone during their validity interval. Resolve an occurrence from event time and identify it by `shiftId` plus local `shiftDate`. Prevent overlapping schedules; gaps are allowed and resolve to no shift. Preserve used boundaries by closing the old definition and creating a new Shift identity/code for a changed schedule. Disabled shifts remain available for historical reads and recalculation but not new operational configuration or runs.
- Stable technical codes are separate from UUIDs. Enterprise codes are globally unique; Shift and ProductionLine codes are unique within Enterprise; Machine codes are unique within Enterprise; Component and TelemetrySignal codes are unique within Machine. The frontend supplies codes; the backend validates and stores them without generating or transliterating them. Codes are immutable.
- A Machine always belongs to an Enterprise and may initially have no line. Assignment is a one-way transition from unassigned to a line in the same Enterprise. Do not move or unassign machines in the MVP. Batch assignment is atomic: any conflict rejects the entire batch. Unassigned machines can be configured but cannot participate in generation, production telemetry ingestion, or analytics.
- ProductionLine ordering uses `sortOrder`, then stable code; when omitted, assign the next value in increments of 10. Machine starts `DISABLED`; optional inventory number is unique within Enterprise, and nominal rate requires a positive value paired with a production unit.
- Components form a machine-owned tree; parent changes stay within the same Machine and must prevent cycles. Sensor, instrument, tool, mechanism, and utility are Component kinds, not separate entities. Component disablement does not cascade.
- A TelemetrySignal belongs to a Machine and may reference only a Component on that same Machine; no component means machine-level signal. MVP value types are `DOUBLE`, `LONG`, `BOOLEAN`, and `STRING`; sequence kinds are `GAUGE`, `COUNTER`, and `STATE`. Semantic and unit codes are stable extensible catalog codes. Preserve out-of-range raw values with quality metadata. After first raw use, signal identity and semantic fields cannot change; a change in physical meaning requires a new signal.
- Keep one unversioned current MachineStateConfig per Machine. Validate the full configuration and save it atomically. Rules have unique priority, target state, enter/optional exit conditions, activation/release delays, and a default state; `OFFLINE` is system-reserved. Conditions use a bounded `ALL`/`ANY`/`NOT`/`COMPARE` tree and supported comparison operators. `DOUBLE` equality/inequality requires tolerance. No signal-to-signal comparisons, arithmetic, regex, scripts, or windows. Evaluation uses TRUE/FALSE/UNKNOWN, selects by priority, falls back to the default state, and reports complete/degraded quality.
- Analytics owns the `equipment` schema and its APIs/data. Use normalized ownership relationships and foreign keys; keep configurable display parameters validated and out of filters/calculations. Analytics is the sole Liquibase migration owner.

## Technical Decisions

- Keep Analytics as one Spring Boot deployable with internal domain modules and one PostgreSQL database divided into logical schemas. Equipment configuration is owned and written by Analytics; Generator consumes its contract.
- Enforce Enterprise/Machine ownership with foreign keys and composite foreign keys. Serialize component-tree mutations on the Machine owner and shift schedule mutations on the Enterprise. Coordinate first signal use and semantic changes with transaction advisory locks derived from `signal_id`.
- Use `TIMESTAMPTZ(3)` for event/audit instants and local `TIME(0)` plus `DATE` for shift-local values. UUIDs are backend assigned; SQL names use `snake_case`.
- Do not version machine configuration in this MVP. Generator runs take an independent configuration snapshot; subsequent edits do not alter a running snapshot. Recalculation of old telemetry uses current rules.

## Cross-Story Dependencies

- Epic 1 authentication and Analytics-owned schema/migration readiness are prerequisites for configuration APIs.
- Within Epic 2, Enterprise ownership and timezone underpin shifts, lines, and machines; Machine ownership underpins component trees, signals, and state configuration. Story 2.5 composes these APIs into the frontend setup journey and verifies AC-1.
- Epic 3 ingestion and state evaluation depend on configured machines, signals, and validated state rules. Generator runs additionally require assigned, active equipment and applicable active shifts.
