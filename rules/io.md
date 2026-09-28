# I/O Recording Rules

## Objective

I/O performance directly impacts workload responsiveness and throughput. These recording rules measure device utilization and latency to enable:

- **Performance monitoring** - Detect I/O bottlenecks before they impact workloads
- **Capacity planning** - Understand device busy time and saturation
- **Anomaly detection** - Identify latency spikes and performance degradation

## Concept

Recording rules pre-calculate I/O metrics to simplify dashboard queries and provide consistent performance baselines. The core principle: **measure both device utilization (busy time) and operation latency**.

Two primary dimensions characterize I/O performance:
- **Utilization** - fraction of time devices are busy (device busy time)
- **Latency** - time from request submission to completion (host-to-device)

### Device Utilization

Device utilization measures the fraction of wall-clock time when at least one I/O request was in flight on a device. This differs from storage capacity (disk space) and instead indicates how busy the I/O subsystem is.

| Utilization Range | Interpretation |
|------------------|----------------|
| 0.0 - 0.7 | Healthy capacity |
| 0.7 - 0.85 | Monitor usage |
| > 0.85 | High utilization, potential bottleneck |

**Source metric**: `node_disk_io_time_seconds_total` - cumulative time the device had at least one I/O in flight.

#### Example

```promql
# Per-node device utilization (busy time)
openshift:node:io:utilization:ratio

# Cluster-wide max device utilization
openshift:cluster:io:utilization:ratio
```

### Latency Distribution

I/O latency is measured as a histogram showing the distribution of operation completion times. Latency quantiles (p50, p95, p99) reveal typical and tail performance.

| Latency Range | Interpretation |
|--------------|----------------|
| < 30ms | Good performance |
| 30-60ms | Monitor performance |
| > 60ms | Degraded performance |

**Source metric**: `kme_system_block_io_latency_seconds_bucket` - histogram of I/O operation latencies from host to device.

#### Example

```promql
# Cluster-wide p50 (median) latency
openshift:cluster:io:latency:p50

# Cluster-wide p95 latency
openshift:cluster:io:latency:p95

# Cluster-wide p99 (tail) latency
openshift:cluster:io:latency:p99
```

### Imbalance

I/O imbalance measures how evenly latency is distributed across nodes using the p80 quantile of percentage distance from mean latency.

| Imbalance Range | Interpretation |
|----------------|----------------|
| < 0.10 (±10%) | Well balanced |
| 0.10 - 0.15 | Moderate imbalance |
| 0.15 - 0.20 | Significant imbalance |
| > 0.20 | Severe imbalance - investigate node differences |

Shows the spread: 80% of nodes are within this percentage of the mean latency.

#### Example

```promql
# Cluster I/O latency imbalance
openshift:cluster:io:latency:imbalance:p80distance
```

## Recording Rule Structure

All rules use **colon hierarchy** (Prometheus convention):

```
openshift:node:io:utilization:ratio{node}
openshift:cluster:io:utilization:ratio
openshift:node:io:latency:p95{node}
openshift:cluster:io:latency:p50
openshift:cluster:io:latency:p95
openshift:cluster:io:latency:p99
openshift:cluster:io:latency:imbalance:p80distance
openshift:cluster:io:latency_bucket:ratio{le, g}
```

### Label Dimensions

- **segment**: `host_to_device` - measurement point (host to block device)
- **protocol**: `block` - storage protocol type
- **unit**: `ratio` or `seconds` - metric unit
- **le**: histogram bucket upper bound (latency buckets)
- **g**: histogram bucket lower bound (for ranged buckets)

### Node-level Metrics

| Metric | Description |
|--------|-------------|
| `openshift:node:io:utilization:ratio` | Per-device busy time (max across devices on node) |
| `openshift:node:io:latency:rate` | Per-node latency histogram rate |
| `openshift:node:io:latency:p95` | Per-node 95th percentile latency |

### Cluster-level Metrics

| Metric | Description |
|--------|-------------|
| `openshift:cluster:io:utilization:ratio` | Max device utilization across all nodes |
| `openshift:cluster:io:latency:p50` | Cluster-wide median latency |
| `openshift:cluster:io:latency:p95` | Cluster-wide 95th percentile latency |
| `openshift:cluster:io:latency:p99` | Cluster-wide 99th percentile latency |
| `openshift:cluster:io:latency:imbalance:p80distance` | p80 quantile of percentage distance from mean p95 latency across nodes |
| `openshift:cluster:io:latency_bucket:ratio{le,g}` | Latency distribution by bucket |

## Latency Buckets

Latency distribution is bucketed to show operation completion time ranges:

| Bucket | Range | Label |
|--------|-------|-------|
| 1 | 0-10ms | `le="0.01"` |
| 2 | 10-100ms | `le="0.1", g="0.01"` |
| 3 | 100ms-1s | `le="1.0", g="0.1"` |
| 4 | >1s | `le="+Inf", g="1.0"` |

Ideal distribution: most operations in 0-10ms, minimal in >100ms.

## Source Metrics

| Source Metric | Description |
|--------------|-------------|
| `node_disk_io_time_seconds_total{device=~"nvme.*\|sd.*"}` | Cumulative device busy time |
| `kme_system_block_io_latency_seconds_bucket` | I/O latency histogram |
| `kme_system_block_io_latency_seconds_count` | Total I/O operation count |

Device filter includes NVMe and SCSI disks; excludes loop devices and partitions.

## Common Queries

### Performance Monitoring

```promql
# Nodes with high device utilization (>85%)
openshift:node:io:utilization:ratio > 0.85

# Cluster max device utilization
openshift:cluster:io:utilization:ratio
```

### Latency Analysis

```promql
# Typical latency (p50)
openshift:cluster:io:latency:p50

# SLA latency (p95)
openshift:cluster:io:latency:p95

# Tail latency (p99)
openshift:cluster:io:latency:p99
```

### Imbalance Detection

```promql
# Detect unbalanced I/O performance (>20% spread)
openshift:cluster:io:latency:imbalance:p80distance > 0.20
```

### Distribution Analysis

```promql
# Fast operations (0-10ms)
openshift:cluster:io:latency_bucket:ratio{le="0.01"}

# Slow operations (>1s)
openshift:cluster:io:latency_bucket:ratio{le="+Inf", g="1.0"}
```

## Important Notes

- **Device Busy Time vs Space**: `io:utilization` measures device busy time (I/O saturation), not storage capacity (disk space used/total).
- **Rate Windows**: All rate calculations use 2-minute windows `[2m]` for stability.
- **Latency Measurement**: Host-to-device latency includes queue time, command processing, and device service time.
- **Quantile Calculation**: Uses `histogram_quantile()` over rate-summed buckets for cluster-wide percentiles.
- **Imbalance**: Computed as `stddev(p95) / avg(p95)` across nodes to detect performance variance.
