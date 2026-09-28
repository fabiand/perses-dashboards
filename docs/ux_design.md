# UX Design Principles

## Core Philosophy

**Instant comprehension with zero cognitive load.** Operators assess cluster health at a glance without mental math, memorizing thresholds, or consulting documentation.

## Principles

### 1. Color-Driven Assessment
Operational state encoded in color, not numbers. Green = healthy, yellow = monitor, red = action required. Thresholds encode operational knowledge so operators respond to color, not raw values.

### 2. Spatial Consistency
Same metrics always in same positions across dashboards. Gauge order: (1) Utilization, (2) Pressure, (3) Imbalance, (4) Resource-specific. Switch dashboards → instantly oriented.

### 3. Resource-Agnostic Titles
Gauge titles are universal ("Utilization"), panel group provides context ("At a Glance - CPU"). Same titles across all dashboards. Scalable pattern for new resources.

### 4. Self-Documenting Panels
Every panel description ends with **"Answers: \<question\>?"** Panels are queryable and discoverable without external docs.

### 5. Progressive Disclosure
Three-level hierarchy: Overview (12 metrics) → Resource Dashboard (gauges + history) → Details (full time series). Default view shows surface-level health, drill-down reveals increasing detail.

## Anti-Patterns

**Avoid:**
- ❌ Displaying raw metrics without thresholds (forces operator to interpret)
- ❌ Inconsistent gauge ordering across dashboards (breaks muscle memory)
- ❌ Resource-specific titles on common metrics ("CPU Utilization", "Memory Utilization")
- ❌ Panels without "Answers:" descriptions (not self-documenting)
- ❌ Flat dashboards with everything visible (overwhelming, no hierarchy)

## Outcome

Operators should be able to:
1. Assess cluster health in <5 seconds (scan Overview, look for red)
2. Identify problem resource in <10 seconds (navigate to red metric's dashboard)
3. Understand metric meaning without external docs (self-documenting descriptions)
4. Operate across dashboards without reorientation (spatial consistency)
