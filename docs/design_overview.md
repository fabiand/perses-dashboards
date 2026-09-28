# Overview Dashboard Design

## Purpose

Single-screen cluster health assessment across all three resources (Memory, CPU, I/O). One glance reveals which resource needs attention.

## Layout

**3 rows × 4 columns = 12 StatCharts** (resource-first organization)

```
┌─────────────────────────────────────────────────────┐
│                   Overview                          │
│               (15m window, 15s refresh)             │
├─────────────┬─────────────┬─────────────┬──────────┤
│   Memory:   │   Memory:   │   Memory:   │  Memory: │
│ Utilization │  Pressure   │  Imbalance  │ Virtual  │
│             │    (PSI)    │             │  Commit  │
├─────────────┼─────────────┼─────────────┼──────────┤
│    CPU:     │    CPU:     │    CPU:     │   CPU:   │
│ Utilization │  Pressure   │  Imbalance  │ Virtual  │
│             │    (PSI)    │             │  Commit  │
├─────────────┼─────────────┼─────────────┼──────────┤
│    I/O:     │    I/O:     │    I/O:     │   I/O:   │
│ Utilization │  Pressure   │  Imbalance  │ Latency  │
│             │    (PSI)    │             │  (p95)   │
└─────────────┴─────────────┴─────────────┴──────────┘
```

## Design Principles

1. **StatCharts, not gauges** - Show current value with sparkline (mini time-series)
2. **Resource-first grouping** - Each row is one resource, scan horizontally to assess that resource
3. **Consistent gauge order** - Same 4 metrics per resource: Utilization, Pressure, Imbalance, Resource-Specific
4. **Color-driven assessment** - All green = healthy, red = action needed
5. **Drill-down ready** - Click any metric to jump to detailed resource dashboard

## StatChart Configuration

- **Sparkline**: Blue-grey mini time-series showing 15-minute trend
- **Value**: Current value with 1 decimal place precision
- **Thresholds**: Green/yellow/red color coding matching resource dashboards
- **Auto-refresh**: 15 seconds

## Metric Details

### Row 1: Memory
1. **Utilization** - Physical memory used / allocatable (70% / 85% thresholds)
2. **Pressure (PSI)** - Max node memory contention (10% / 30% thresholds)
3. **Imbalance** - Coefficient of variation across nodes (0.3 / 0.6 thresholds)
4. **Virtual Commitment** - Committed virtual memory / physical capacity (120% / 150% thresholds)

### Row 2: CPU
1. **Utilization** - CPU used / allocatable (70% / 85% thresholds)
2. **Pressure (PSI)** - Max node CPU contention (10% / 30% thresholds)
3. **Imbalance** - Coefficient of variation across nodes (0.3 / 0.6 thresholds)
4. **Virtual Commitment** - Committed virtual CPU / physical capacity (120% / 150% thresholds)

### Row 3: I/O
1. **Utilization** - Max device busy time (70% / 85% thresholds)
2. **Pressure (PSI)** - Max node I/O contention (10% / 30% thresholds)
3. **Imbalance** - Coefficient of variation of p95 latency across nodes (0.3 / 0.6 thresholds)
4. **Latency (p95)** - 95th percentile I/O latency (30ms / 60ms thresholds)

## Workflow

1. **Scan overview** - Identify red/yellow metrics
2. **Assess severity** - Sparkline shows if trending worse
3. **Drill down** - Navigate to resource-specific dashboard for details
4. **Investigate** - Use resource dashboard's detailed panels and history

## Recording Rules

All metrics use pre-calculated recording rules for performance:

- `openshift:cluster:memory:utilization:ratio`
- `openshift:cluster:memory:pressure:ratio{severity="some"}`
- `openshift:cluster:memory:imbalance:ratio`
- `openshift:cluster:cpu:utilization:ratio`
- `openshift:cluster:cpu:pressure:ratio{severity="some"}`
- `openshift:cluster:cpu:imbalance:ratio`
- `openshift:cluster:io:utilization:ratio`
- `openshift:cluster:io:pressure:ratio{severity="some"}`
- `openshift:cluster:io:latency:imbalance:ratio`
- `openshift:cluster:io:latency:p95`

## Key Differences from Resource Dashboards

| Aspect | Resource Dashboards | Overview Dashboard |
|--------|-------------------|-------------------|
| **Chart Type** | GaugeChart | StatChart (with sparkline) |
| **Time Series** | Full panel groups with history | Embedded sparklines only |
| **Time Window** | 1-24 hours (variable) | Fixed 15 minutes |
| **Refresh** | Manual or 15s | Always 15s auto-refresh |
| **Detail Level** | Deep (multiple panel groups) | Surface (12 key metrics only) |
| **Purpose** | Investigation & analysis | Quick health check |

## Use Cases

- **Operations handoff** - Quick cluster status summary
- **Incident triage** - Rapidly identify which resource is stressed
- **Capacity monitoring** - Track all resources in one view
- **Executive dashboard** - Non-technical stakeholder visibility

## Future Enhancements

- Cluster selector (multi-cluster support)
- Severity-based sorting (worst metrics first)
- Alert count integration (show active alerts per resource)
- Historical comparison (compare current vs 1-hour ago)
