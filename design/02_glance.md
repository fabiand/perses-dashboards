# At a Glance Panel Design

## Goal

Provide instant cluster health assessment. Green = healthy, red = requires action. One glance tells you if intervention is needed.

## Key Design Principles

1. **Color-driven status, no contextual awareness required**
   - Every gauge uses color coding: green/yellow/red
   - All green → cluster healthy, no action needed
   - Red panel → specific issue requiring attention
   - Admin assesses health without needing to know what "good" values are
   - Use gauge thresholds to encode operational state

2. **Consistent layout across dashboards to know what you see without contextual awareness**
   - Same structure every time → gauges always in same positions
   - Same gauge titles across dashboards → resource context from panel group title
   - Row 1: Four gauges (utilization, pressure, node imbalance, resource-specific)
   - Row 2: Domain-specific time series
   - Switch dashboards, instantly oriented

3. **Every panel has a descriptive purpose**
   - Description explains what the panel shows and how to interpret it
   - Must end with: "Answers: <operational question>?"
   - Makes panels self-documenting and queryable

4. **Domain-specific time series**
   - Memory: cluster utilization history with tier breakdown
   - I/O: utilization history (max and average device busy time)
   - CPU: system/workloads busy/idle breakdown

## Panel Group Schema

**Panel Group Title:** `At a Glance - <Resource>` (e.g., "At a Glance - Memory", "At a Glance - CPU")

```
At a Glance - <Resource>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Row 1: Gauges (equal width, 6 units each)
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Utilization  │  Pressure    │     Node     │  Resource-   │
│              │    (PSI)     │  Imbalance   │   Specific   │
└──────────────┴──────────────┴──────────────┴──────────────┘

Row 2: Time Series (full width, 24 units)
┌───────────────────────────────────────────────────────────┐
│         Domain-Specific Critical Metric History           │
└───────────────────────────────────────────────────────────┘
```

**Design Principle:** Gauge titles are resource-agnostic. The panel group title provides resource context.

**Examples:**
- Memory: "At a Glance - Memory", Row 2 shows cluster utilization with tier breakdown
- CPU: "At a Glance - CPU", Row 2 shows system/workloads busy/idle
- I/O: "At a Glance - I/O", Row 2 shows utilization history (max/avg device busy time)

### Gauge Details

**Gauge 1: Utilization**
- Shows: percentage of cluster resource in use
- Thresholds: <70% green, 70-85% yellow, >85% red
- Action: Red = cluster needs scaling or workload reduction

**Gauge 2: Pressure (PSI)**
- Shows: worst-case contention across nodes (max node)
- Thresholds: <10% green, 10-30% yellow, >30% red
- Action: Red = investigate node under pressure

**Gauge 3: Node Imbalance**
- Shows: coefficient of variation across nodes
- Thresholds: <0.3 green, 0.3-0.6 yellow, >0.6 red
- Action: Red = rebalance workloads across nodes

**Gauge 4: Resource-Specific**
- **CPU/Memory:** Virtual Commitment
  - Shows: overcommit ratio as percentage (virtual/physical × 100)
  - Format: percent (150% means 1.5× overcommit)
  - Thresholds: <120% green, 120-150% yellow, >150% red
  - Action: Red = reduce overcommit or prepare for contention
- **I/O:** Latency Quantiles
  - Shows: p50/p95/p99 latency percentiles
  - Format: milliseconds
  - Thresholds: <30ms green, 30-60ms yellow, >60ms red
  - Action: Red = investigate I/O performance

### Time Series Examples

**Memory Dashboard** ("At a Glance - Memory")
- Cluster utilization history with tier breakdown
- Stacked area chart: system (red), workloads (orange), committed (blue dashed)

**CPU Dashboard** ("At a Glance - CPU")
- Cluster CPU utilization over time
- Stacked area chart: system (red), workloads busy (orange), workloads idle (green), committed (blue dashed)

**I/O Dashboard** ("At a Glance - I/O")
- I/O utilization history (max and average device busy time)
- Line chart showing max (orange) and avg (green) utilization trends

## Implementation Notes

- **Panel group title:** Include resource name (e.g., "At a Glance - Memory")
- **Gauge titles:** Resource-agnostic across all dashboards (same titles, different data)
- **Gauge width:** 6 units each (24-unit grid → 4 gauges)
- **Time series height:** 9-13 units depending on content density
- **Gauge precision:** All gauges use 1 decimal place
- **Color palette:** green (#59CC8D), yellow (#FFB249), red (#EE6C6C)
- **Gauge order:** Must remain consistent across all resource dashboards
