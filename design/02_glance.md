# At a Glance Panel Design

## Goal

Tell you if the cluster is healthy or broken in one glance. Green = you're good, red = go fix something. That's it.

## Key Design Principles

1. **Color-driven status**
   - Every gauge shows green, yellow, or red
   - All green? Cluster's healthy, go get coffee
   - Something red? That's your problem, right there
   - You don't need to know what the numbers mean - the color tells you what to do
   - Thresholds encode what "good" looks like so you don't have to remember

2. **Same layout everywhere**
   - Gauges always in the same spots
   - Same titles across all dashboards - resource name comes from the panel group
   - Row 1: Four gauges (utilization, pressure, node imbalance, resource-specific)
   - Row 2: Time series showing what matters for that resource
   - Switch from Memory to CPU to I/O - your eyes know where to look

3. **Self-documenting panels**
   - Each panel description explains what it shows and why you care
   - Ends with: "Answers: <question>?" so you know the use-case
   - No digging through docs to figure out what something means

4. **Domain-specific time series**
   - Memory: utilization history with tier breakdown (DRAM vs swap)
   - CPU: system vs workload breakdown (who's using the CPU?)
   - I/O: max and average device busy time (how saturated?)

## Panel Group Schema

**Panel Group Title:** `At a Glance - <Resource>` (Memory, CPU, or I/O)

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

**Key idea:** Gauge titles don't include the resource name. "Utilization", not "CPU Utilization". The panel group title ("At a Glance - CPU") gives you that context.

**What goes in Row 2:**
- Memory: cluster utilization with tier breakdown
- CPU: system vs workload busy/idle breakdown
- I/O: max and average device busy time

### Gauge Details

**Gauge 1: Utilization**
- **Use-case:** Is the cluster running out of this resource?
- Shows percentage of capacity in use
- Thresholds: <70% green, 70-85% yellow, >85% red
- Red means you need more capacity or need to shed load

**Gauge 2: Pressure (PSI)**
- **Use-case:** Are workloads waiting for this resource?
- Shows worst-case contention across nodes (max node value)
- Thresholds: <10% green, 10-30% yellow, >30% red
- Red means something's starving - go find which node

**Gauge 3: Node Imbalance**
- **Use-case:** Is load distributed evenly or is one node getting hammered?
- Shows coefficient of variation across nodes
- Thresholds: <0.3 green, 0.3-0.6 yellow, >0.6 red
- Red means rebalance workloads

**Gauge 4: Resource-Specific**
Two different use-cases depending on the resource:

- **CPU & Memory:** Virtual Commitment
  - **Use-case:** Are we overcommitting virtual resources?
  - Shows overcommit ratio as percentage (150% = 1.5× overcommit)
  - Format: percent (not ratio)
  - Thresholds: <120% green, 120-150% yellow, >150% red
  - Red means reduce overcommit or prepare for contention

- **I/O:** Latency Quantiles
  - **Use-case:** How fast is I/O right now?
  - Shows p50/p95/p99 latency percentiles
  - Format: milliseconds
  - Thresholds: <30ms green, 30-60ms yellow, >60ms red
  - Red means investigate I/O performance

### Time Series Examples

**Memory Dashboard** ("At a Glance - Memory")
- Cluster utilization history with tier breakdown
- Stacked area chart: system (red), workloads (orange), committed (blue dashed)
- **Use-case:** See memory consumption trends over time

**CPU Dashboard** ("At a Glance - CPU")
- Cluster CPU utilization over time
- Stacked area chart: system (red), workloads busy (orange), workloads idle (green), committed (blue dashed)
- **Use-case:** See where CPU is going - system overhead vs workloads vs idle

**I/O Dashboard** ("At a Glance - I/O")
- Device utilization history (max and average)
- Line chart: max (orange), avg (green)
- **Use-case:** See if I/O saturation is trending up

## Implementation Notes

- **Panel group title:** Include resource name (e.g., "At a Glance - Memory")
- **Gauge titles:** Resource-agnostic - same across all dashboards
- **Gauge width:** 6 units each (4 gauges across 24-unit grid)
- **Time series height:** 9-13 units depending on content density
- **Gauge precision:** 1 decimal place
- **Color palette:** green (#59CC8D), yellow (#FFB249), red (#EE6C6C)
- **Gauge order:** Never change it - consistency is the point
