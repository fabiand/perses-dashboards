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
   - Row 1: Four gauges (cluster util, node imbalance, top-1 pressure, virtual commitment)
   - Row 2: Domain-specific time series
   - Switch dashboards, instantly oriented

3. **Every panel has a descriptive purpose**
   - Description explains what the panel shows and how to interpret it
   - Must end with: "Answers: <operational question>?"
   - Makes panels self-documenting and queryable

4. **Domain-specific time series**
   - Memory: cluster utilization history with tier breakdown
   - Storage: latency quantiles (p50/p95/p99)
   - CPU: overcommit ratio per node

## Panel Group Schema

```
At a Glance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Row 1: Gauges (equal width, 6 units each)
┌──────────────┬──────────────┬──────────────┬──────────────┐
│   Cluster    │     Node     │    Top-1     │   Virtual    │
│ Utilization  │  Imbalance   │   Pressure   │ Commitment   │
└──────────────┴──────────────┴──────────────┴──────────────┘

Row 2: Time Series (full width, 24 units)
┌───────────────────────────────────────────────────────────┐
│         Domain-Specific Critical Metric History           │
└───────────────────────────────────────────────────────────┘
```

**Examples:**
- Memory: Row 2 shows cluster utilization with tier breakdown
- Storage: Row 2 shows latency quantiles (p50/p95/p99)
- CPU: Row 2 shows per-node overcommit ratios

### Gauge Details

**Cluster Utilization**
- Shows: percentage of cluster resource in use
- Thresholds: <70% green, 70-85% yellow, >85% red
- Action: Red = cluster needs scaling or workload reduction

**Node Imbalance**
- Shows: coefficient of variation across nodes
- Thresholds: <0.3 green, 0.3-0.6 yellow, >0.6 red
- Action: Red = rebalance workloads across nodes

**Top-1 Pressure** (max node)
- Shows: worst-case contention (PSI)
- Thresholds: <10% green, 10-30% yellow, >30% red
- Action: Red = investigate node under pressure

**Virtual Commitment** (memory/CPU)
- Shows: overcommit ratio as percentage (virtual/physical × 100)
- Format: percent (150% means 1.5× overcommit)
- Thresholds: <120% green, 120-150% yellow, >150% red
- Action: Red = reduce overcommit or prepare for contention

### Time Series Examples

**Memory Dashboard**
- Cluster utilization history with tier breakdown (DRAM, swap, overflow)
- Stacked area chart showing capacity consumption over time

**Storage Dashboard**
- Latency quantiles (p50, p95, p99)
- Line chart showing latency trends

**CPU Dashboard**
- vCPU overcommit ratio per node
- Multi-line chart identifying overcommitted nodes

## Implementation Notes

- Gauge width: 6 units each (24-unit grid → 4 gauges)
- Time series height: 9-13 units depending on content density
- All gauges use 1 decimal place precision
- Color palette: green (#59CC8D), yellow (#FFB249), red (#EE6C6C)
