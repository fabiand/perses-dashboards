# Overview Dashboard Design

## Purpose

See the health of your whole cluster on one screen. Memory, CPU, I/O - 12 key metrics, all in one place. Spot problems in seconds.

## Layout

**3 panel groups × 4 metrics = 12 StatCharts**

```
┌─────────────────────────────────────────────────────┐
│                   Overview                          │
│               (15m window, 15s refresh)             │
├─────────────┬─────────────┬─────────────┬──────────┤
│   Memory    │   Memory    │   Memory    │  Memory  │
│ Utilization │  Pressure   │  Imbalance  │ Virtual  │
│             │    (PSI)    │             │  Commit  │
├─────────────┼─────────────┼─────────────┼──────────┤
│    CPU      │    CPU      │    CPU      │   CPU    │
│ Utilization │  Pressure   │  Imbalance  │ Virtual  │
│             │    (PSI)    │             │  Commit  │
├─────────────┼─────────────┼─────────────┼──────────┤
│    I/O      │    I/O      │    I/O      │   I/O    │
│ Utilization │  Pressure   │  Imbalance  │ Latency  │
│             │    (PSI)    │             │  (p95)   │
└─────────────┴─────────────┴─────────────┴──────────┘
```

## Design Principles

1. **StatCharts with sparklines** - Current value plus mini trend line so you can see if it's getting worse
2. **Resource-first grouping** - One row per resource, scan left-to-right to check that resource
3. **Same metrics everywhere** - Utilization, Pressure, Imbalance, then one resource-specific metric
4. **Color tells you what to do** - All green? Great. Red? Click it and go fix it.
5. **Click to drill down** - Every panel links to the full dashboard for that resource

## StatChart Configuration

- **Sparkline**: Blue-grey mini time-series (last 15 minutes)
- **Value**: Current number with 1 decimal place
- **Thresholds**: Green/yellow/red matching the detailed dashboards
- **Auto-refresh**: Every 15 seconds

## What the Metrics Mean

### Row 1: Memory
- **Utilization** - How much memory is in use (red at 85%)
- **Pressure (PSI)** - Worst-case memory contention across nodes (red at 30%)
- **Imbalance** - How unevenly distributed is memory usage (red at 0.6)
- **Virtual Commitment** - Are VMs overcommitted on memory (red at 150%)

### Row 2: CPU
- **Utilization** - How much CPU is in use (red at 85%)
- **Pressure (PSI)** - Worst-case CPU contention across nodes (red at 30%)
- **Imbalance** - How unevenly distributed is CPU usage (red at 0.6)
- **Virtual Commitment** - Are VMs overcommitted on CPU (red at 150%)

### Row 3: I/O
- **Utilization** - Max device busy time (red at 85%)
- **Pressure (PSI)** - Worst-case I/O contention across nodes (red at 30%)
- **Imbalance** - How unevenly distributed is I/O latency (red at 0.6)
- **Latency (p95)** - 95th percentile I/O latency (red at 60ms)

## Workflow (How to Use It)

1. **Scan for red** - Look for red or yellow panels
2. **Check the sparkline** - Is it trending up? Getting worse?
3. **Click the red thing** - Drill down to that resource's dashboard
4. **Investigate** - Use the detailed panels and history to figure out what's wrong

## Use-Cases

**Operations handoff:**  
Quick status check before handing off to the next shift

**Incident triage:**  
Rapidly identify which resource is struggling

**Capacity monitoring:**  
Keep an eye on all resources without switching between dashboards

**Executive dashboard:**  
Show cluster health to non-technical stakeholders

## Recording Rules Used

All metrics come from pre-calculated recording rules (fast queries):

- `openshift:cluster:memory:utilization:ratio`
- `max(openshift:node:memory:pressure:ratio{severity="some"} @ end())`
- `openshift:cluster:memory:imbalance:p80distance`
- `openshift:cluster:cpu:utilization:ratio`
- `max(openshift:node:cpu:pressure:ratio{severity="some"} @ end())`
- `openshift:cluster:cpu:imbalance:p80distance`
- `openshift:cluster:io:utilization:ratio`
- `max(openshift:node:io:pressure:ratio{severity="some"} @ end())`
- `openshift:cluster:io:latency:imbalance:p80distance`
- `openshift:cluster:io:latency:p95`

Note: Pressure metrics aggregate at query time (max across nodes) rather than using cluster-level recording rules.

## Comparison: Overview vs Resource Dashboards

| What | Overview Dashboard | Resource Dashboards |
|------|-------------------|---------------------|
| **Chart type** | StatChart (value + sparkline) | GaugeChart (just value) + full time series |
| **Time window** | Fixed 15 minutes | Variable (1-24 hours) |
| **Refresh** | Always 15 seconds | User-controlled or 15s |
| **Detail level** | 12 key metrics only | Deep dive with multiple panel groups |
| **Use-case** | Quick health check | Investigation and analysis |
| **When to use** | "Is something broken?" | "Why is it broken?" |
